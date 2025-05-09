import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from weather_scraper import get_weather_data_html_weather_gov, build_weather_gov_url_from_location, get_coordinates, get_hourly_forecast_weather_gov, get_digital_forecast_table_weather_gov
import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.collections import PolyCollection
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import requests
from bs4 import BeautifulSoup
import pytz
import random
import re
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter

def create_temperature_plotly_visualization(df, card_bg, heading_color, text_color, border_color):
    """
    Creates a Plotly visualization for temperature data with proper date handling.
    """
    # Extract date blocks and their corresponding hours and temperatures
    date_blocks = []
    hours_blocks = []
    temps_blocks = []
    
    # Process the data in blocks
    for i in range(0, len(df), 3):  # Process 3 rows at a time (Date, Hour, Temperature)
        if i + 2 < len(df):  # Ensure we have all three rows
            # Get the rows for this block
            date_row = df.iloc[i]
            hour_row = df.iloc[i+1]
            temp_row = df.iloc[i+2]
            
            # Extract the date from the first non-empty cell in the date row
            date = None
            for cell in date_row[1:]:  # Skip the first column (label)
                if pd.notna(cell) and str(cell).strip():
                    date = str(cell).strip()
                    break
            
            if date:
                # Extract hours and temperatures
                hours = []
                temps = []
                for h, t in zip(hour_row[1:], temp_row[1:]):  # Skip the first column (label)
                    if pd.notna(h) and pd.notna(t):
                        try:
                            hour = int(str(h).strip())
                            temp = float(str(t).replace('°F', '').strip())
                            hours.append(hour)
                            temps.append(temp)
                        except (ValueError, TypeError):
                            continue
                
                if hours and temps:
                    date_blocks.append(date)
                    hours_blocks.append(hours)
                    temps_blocks.append(temps)
    
    # Expand the blocks into flat lists
    all_days = []
    all_hours_flat = []
    all_temps_flat = []
    
    for date, hours, temps in zip(date_blocks, hours_blocks, temps_blocks):
        all_days.extend([date] * len(hours))
        all_hours_flat.extend(hours)
        all_temps_flat.extend(temps)
    
    # Create the DataFrame for plotting
    plotly_temperature_data = pd.DataFrame({
        'Day': all_days,
        'Hour': all_hours_flat,
        'Temperature (F)': all_temps_flat
    })
    
    # Create the Plotly figure
    fig = px.scatter(
        plotly_temperature_data,
        x='Hour',
        y='Temperature (F)',
        color='Day',
        title='Temperature vs Hour (Plotly)',
        height=400
    )
    
    # Update the figure styling
    fig.update_traces(marker=dict(line=dict(width=1, color=border_color)))
    fig.update_layout(
        plot_bgcolor=card_bg,
        paper_bgcolor=card_bg,
        font_color=text_color,
        title_font_color=heading_color,
        xaxis=dict(
            showgrid=True,
            gridcolor=border_color,
            linecolor=border_color,
            tickfont=dict(color=text_color)
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=border_color,
            linecolor=border_color,
            tickfont=dict(color=text_color)
        ),
    )
    
    return fig, plotly_temperature_data

# Get city and state from coordinates ------------------------------------------------------------------------------------------------------------------------
def get_city_state_from_coords(lat, lon):
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10"
    headers = {'User-Agent': 'WeatherDashboard/1.0'}
    resp = requests.get(url, headers=headers)
    data = resp.json()
    address = data.get('address', {})
    city = address.get('city') or address.get('town') or address.get('village') or address.get('hamlet') or ''
    state = address.get('state') or ''
    return city, state


# Page Configuration and Layout Setup ------------------------------------------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Weather Dashboard",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Helper Functions for Data Processing ------------------------------------------------------------------------------------------------------------------------
def arrow(val, yest):
    try:
        if yest is None or val is None or pd.isna(val) or pd.isna(yest):
            return ""
        val_f = float(val)
        yest_f = float(yest)
        if val_f > yest_f:
            return "<span style='color:#43a047;font-size:1.1em;'>&#8593;</span>"
        elif val_f < yest_f:
            return "<span style='color:#e53935;font-size:1.1em;'>&#8595;</span>"
        else:
            return ""
    except Exception:
        return ""

def parse_datetime(date_str):
    try:
        base, hour = [s.strip() for s in date_str.split(',')]
        dt_obj = datetime.datetime.strptime(base + ' ' + hour, '%B %d %H:%M')
        return dt_obj
    except Exception:
        return None

def convert_rgba_to_hex(rgba_str):
    try:
        rgba = rgba_str.replace('rgba(', '').replace(')', '').split(',')
        r, g, b = map(int, rgba[:3])
        return f'#{r:02x}{g:02x}{b:02x}'
    except:
        return '#ffffff'  

def highlight_temp(val):
    color = "#fff"  # default
    try:
        v = float(val)
        if v >= 80:
            color = "#ffe082"  # warm yellow
        elif v <= 32:
            color = "#b3e5fc"  # cool blue
    except:
        pass
    return f"background-color: {color}; font-weight: 600;"

def highlight_humidity(val):
    try:
        v = float(val)
        if v >= 80:
            return "color: #1976d2; font-weight: 600;"
        elif v <= 30:
            return "color: #757575; font-style: italic;"
    except:
        pass
    return ""


# Theme and Style Configuration Functions ------------------------------------------------------------------------------------------------------------------------
def get_theme_colors(condition='', is_night=False):
    """
    Returns theme colors based on weather condition and time of day.
    
    Args:
        condition (str): Current weather condition
        is_night (bool): Whether it's night time
        
    Returns:
        dict: Dictionary containing theme colors for:
            - background_gradient: Background gradient CSS
            - text_color: Main text color
            - heading_color: Heading text color
            - card_bg: Card background color
            - card_shadow: Card shadow CSS
            - card_border: Card border CSS
            - header_bg: Table header background color
            - header_text: Table header text color
            - cell_bg: Table cell background color
            - cell_text: Table cell text color
            - border_color: Table border color
    """
    if is_night:
        return {
            'background_gradient': "linear-gradient(135deg, #1a237e 0%, #283593 40%, #3949ab 100%)",
            'text_color': "#e8eaf6",
            'heading_color': "#9fa8da",
            'card_bg': "rgba(25,118,210,0.15)",
            'card_shadow': "0 8px 32px 0 rgba(25,118,210,0.25)",
            'card_border': "1.5px solid #3949ab",
            'header_bg': "rgba(25,118,210,0.25)",
            'header_text': "#e8eaf6",
            'cell_bg': "rgba(25,118,210,0.15)",
            'cell_text': "#e8eaf6",
            'border_color': "#3949ab"
        }
    
    themes = {
        'thunderstorm': {
            'background_gradient': "linear-gradient(135deg, #424242 0%, #616161 40%, #757575 100%)",
            'text_color': "#e0e0e0",
            'heading_color': "#ffd54f",
            'card_bg': "rgba(33,33,33,0.85)",
            'card_shadow': "0 8px 32px 0 rgba(255,213,79,0.25)",
            'card_border': "1.5px solid #ffd54f",
            'header_bg': "rgba(33,33,33,0.95)",
            'header_text': "#ffd54f",
            'cell_bg': "rgba(33,33,33,0.85)",
            'cell_text': "#e0e0e0",
            'border_color': "#ffd54f"
        },
        'rain': {
            'background_gradient': "linear-gradient(135deg, #546e7a 0%, #78909c 40%, #90a4ae 100%)",
            'text_color': "#eceff1",
            'heading_color': "#b3e5fc",
            'card_bg': "rgba(69,90,100,0.85)",
            'card_shadow': "0 8px 32px 0 rgba(179,229,252,0.25)",
            'card_border': "1.5px solid #b3e5fc",
            'header_bg': "rgba(69,90,100,0.95)",
            'header_text': "#b3e5fc",
            'cell_bg': "rgba(69,90,100,0.85)",
            'cell_text': "#eceff1",
            'border_color': "#b3e5fc"
        },
        'snow': {
            'background_gradient': "linear-gradient(135deg, #e3f2fd 0%, #bbdefb 40%, #90caf9 100%)",
            'text_color': "#0d47a1",
            'heading_color': "#1976d2",
            'card_bg': "rgba(227,242,253,0.95)",
            'card_shadow': "0 8px 32px 0 rgba(25,118,210,0.15)",
            'card_border': "1.5px solid #1976d2",
            'header_bg': "rgba(25,118,210,0.15)",
            'header_text': "#0d47a1",
            'cell_bg': "rgba(227,242,253,0.95)",
            'cell_text': "#0d47a1",
            'border_color': "#1976d2"
        },
        'fog': {
            'background_gradient': "linear-gradient(135deg, #cfd8dc 0%, #b0bec5 40%, #90a4ae 100%)",
            'text_color': "#37474f",
            'heading_color': "#455a64",
            'card_bg': "rgba(207,216,220,0.95)",
            'card_shadow': "0 8px 32px 0 rgba(69,90,100,0.15)",
            'card_border': "1.5px solid #455a64",
            'header_bg': "rgba(69,90,100,0.15)",
            'header_text': "#37474f",
            'cell_bg': "rgba(207,216,220,0.95)",
            'cell_text': "#37474f",
            'border_color': "#455a64"
        },
        'wind': {
            'background_gradient': "linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 40%, #80deea 100%)",
            'text_color': "#006064",
            'heading_color': "#0097a7",
            'card_bg': "rgba(224,247,250,0.95)",
            'card_shadow': "0 8px 32px 0 rgba(0,151,167,0.15)",
            'card_border': "1.5px solid #0097a7",
            'header_bg': "rgba(0,151,167,0.15)",
            'header_text': "#006064",
            'cell_bg': "rgba(224,247,250,0.95)",
            'cell_text': "#006064",
            'border_color': "#0097a7"
        },
        'clear': {
            'background_gradient': "linear-gradient(135deg, #ffd54f 0%, #ffd54f 20%, #1e88e5 50%, #64b5f6 100%)",
            'text_color': "#01579b",
            'heading_color': "#039be5",
            'card_bg': "rgba(255,255,255,0.95)",
            'card_shadow': "0 8px 32px 0 rgba(3,155,229,0.12)",
            'card_border': "1.5px solid #039be5",
            'header_bg': "rgba(3,155,229,0.15)",
            'header_text': "#01579b",
            'cell_bg': "rgba(255,255,255,0.95)",
            'cell_text': "#01579b",
            'border_color': "#039be5"
        },
        'few_clouds': {
            'background_gradient': "linear-gradient(135deg, #e0f7fa 0%, #039be5 60%, #0d47a1 100%)",
            'text_color': "#01579b",
            'heading_color': "#039be5",
            'card_bg': "rgba(224,247,250,0.92)",
            'card_shadow': "0 8px 32px 0 rgba(3,155,229,0.18)",
            'card_border': "1.5px solid #039be5",
            'header_bg': "rgba(3,155,229,0.15)",
            'header_text': "#01579b",
            'cell_bg': "rgba(224,247,250,0.92)",
            'cell_text': "#01579b",
            'border_color': "#039be5"
        },
        'partly_cloudy': {
            'background_gradient': "linear-gradient(135deg, #e0f7fa 0%, #b3e5fc 30%, #81d4fa 60%, #ffffff 100%)",
            'text_color': "#0277bd",
            'heading_color': "#039be5",
            'card_bg': "rgba(224,247,250,0.92)",
            'card_shadow': "0 8px 32px 0 rgba(129,212,250,0.18)",
            'card_border': "1.5px solid #81d4fa",
            'header_bg': "rgba(129,212,250,0.15)",
            'header_text': "#0277bd",
            'cell_bg': "rgba(224,247,250,0.92)",
            'cell_text': "#0277bd",
            'border_color': "#81d4fa"
        },
        'mostly_cloudy': {
            'background_gradient': "linear-gradient(135deg, #e0eafc 0%, #b0bec5 60%, #757f9a 100%)",
            'text_color': "#37474f",
            'heading_color': "#757f9a",
            'card_bg': "rgba(176,190,197,0.85)",
            'card_shadow': "0 8px 32px 0 rgba(117,127,154,0.18)",
            'card_border': "1.5px solid #757f9a",
            'header_bg': "rgba(117,127,154,0.15)",
            'header_text': "#37474f",
            'cell_bg': "rgba(176,190,197,0.85)",
            'cell_text': "#37474f",
            'border_color': "#757f9a"
        },
        'overcast': {
            'background_gradient': "linear-gradient(135deg, #757f9a 0%, #37474f 60%, #232b36 100%)",
            'text_color': "#e0e0e0",
            'heading_color': "#b0bec5",
            'card_bg': "rgba(55,71,79,0.92)",
            'card_shadow': "0 8px 32px 0 rgba(35,43,54,0.45)",
            'card_border': "1.5px solid #232b36",
            'header_bg': "rgba(35,43,54,0.95)",
            'header_text': "#b0bec5",
            'cell_bg': "rgba(55,71,79,0.92)",
            'cell_text': "#e0e0e0",
            'border_color': "#232b36"
        }
    }
    
    # Default theme
    default_theme = {
        'background_gradient': "linear-gradient(135deg, #87ceeb 0%, #00bfff 60%, #ffffff 100%)",
        'text_color': "#01579b",
        'heading_color': "#039be5",
        'card_bg': "rgba(255,255,255,0.95)",
        'card_shadow': "0 8px 32px 0 rgba(3,155,229,0.12)",
        'card_border': "1.5px solid #039be5",
        'header_bg': "rgba(3,155,229,0.15)",
        'header_text': "#01579b",
        'cell_bg': "rgba(255,255,255,0.95)",
        'cell_text': "#01579b",
        'border_color': "#039be5"
    }
    
    # Determine which theme to use based on condition
    condition = condition.lower()
    if 'thunderstorm' in condition or 'thunder' in condition:
        return themes['thunderstorm']
    elif 'rain' in condition or 'shower' in condition or 'drizzle' in condition:
        return themes['rain']
    elif 'snow' in condition or 'flurries' in condition or 'sleet' in condition:
        return themes['snow']
    elif 'fog' in condition or 'mist' in condition or 'haze' in condition:
        return themes['fog']
    elif 'wind' in condition or 'breezy' in condition or 'gust' in condition:
        return themes['wind']
    elif 'clear' in condition or 'not a cloud' in condition:
        return themes['clear']
    elif 'few clouds' in condition:
        return themes['few_clouds']
    elif 'partly cloudy' in condition or 'partly sunny' in condition:
        return themes['partly_cloudy']
    elif 'mostly cloudy' in condition:
        return themes['mostly_cloudy']
    elif 'overcast' in condition:
        return themes['overcast']
    
    return default_theme

def create_metric_card(title, value, arrow=""):
    """
    Creates a styled metric card with title, value, and optional arrow.
    
    Args:
        title (str): Card title (e.g., "Temperature", "Humidity")
        value (str): Card value to display
        arrow (str, optional): HTML arrow indicator for trend
        
    Returns:
        str: HTML string for the metric card
    """
    return f"""
        <div class='weather-metric-card'>
            <h3 style='margin-top: 0;'>{title}</h3>
            <h2 style='margin-bottom: 0;'>{value} {arrow}</h2>
        </div>
    """

def create_plot_style(fig, ax, plot_edge_color, plot_text_color, plot_bg_color):
    """
    Applies consistent styling to matplotlib plots.
    
    Args:
        fig (matplotlib.figure.Figure): The figure object
        ax (matplotlib.axes.Axes): The axes object
        plot_edge_color (str): Color for plot edges and borders
        plot_text_color (str): Color for plot text
        plot_bg_color (str): Color for plot background
    """
    fig.patch.set_facecolor('none')
    ax.set_facecolor('none')
    
    # Add background rectangle
    rect = FancyBboxPatch((0, 0), 1, 1,
                        boxstyle="round,pad=0.05,rounding_size=40",
                        linewidth=2,
                        edgecolor=plot_edge_color,
                        facecolor=plot_bg_color,
                        alpha=0.4,
                        zorder=0,
                        transform=ax.transAxes)
    ax.add_patch(rect)
    
    # Style the spines
    for spine in ax.spines.values():
        spine.set_linewidth(2)
        spine.set_edgecolor(plot_edge_color)
    
    # Set up colors
    ax.tick_params(axis='x', colors=plot_text_color)
    ax.tick_params(axis='y', colors=plot_text_color)
    
    dark_label_color = '#111111'
    ax.xaxis.label.set_color(dark_label_color)
    ax.yaxis.label.set_color(dark_label_color)
    ax.title.set_color(plot_edge_color)

def format_date_with_suffix(x, pos=None):
    """
    Formats date with ordinal suffix for plot labels.
    
    Args:
        x (float): Matplotlib date number
        pos (int, optional): Position parameter for formatter
        
    Returns:
        str: Formatted date string (e.g., "May 8th, 12:00 PM")
    """
    dt = mdates.num2date(x)
    day = dt.day
    if 11 <= day <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return dt.strftime(f'%b {day}{suffix}, %I:%M %p')

# Plotly Scatter Plot with Dynamic Theme Colors ------------------------------------------------------------------------------------------------------------------------
def themed_plotly_scatter(
    df, x, y, title, 
    card_bg, heading_color, text_color, border_color, height=400
):
    """
    Create a Plotly scatter plot with dynamic theme colors.
    """
    fig = px.scatter(df, x=x, y=y, title=title, height=height)
    fig.update_traces(marker=dict(color=heading_color))
    fig.update_layout(
        plot_bgcolor=card_bg,
        paper_bgcolor=card_bg,
        font_color=text_color,
        title_font_color=heading_color,
        xaxis=dict(showgrid=True, gridcolor=border_color, linecolor=border_color, tickfont=dict(color=text_color)),
        yaxis=dict(showgrid=True, gridcolor=border_color, linecolor=border_color, tickfont=dict(color=text_color)),
    )
    return fig


# Main Dashboard Layout and Content ------------------------------------------------------------------------------------------------------------------------
main_content = st.empty()

with st.sidebar:
    st.markdown("""
        <div style='
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 24px;
            margin: 16px 0;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
        '>
            <h2 style='
                color: var(--weather-heading);
                margin-bottom: 24px;
                font-size: 1.8em;
                text-align: center;
                text-shadow: 0 2px 4px rgba(0,0,0,0.2);
            '>Location Settings</h2>
        </div>
    """, unsafe_allow_html=True)
    location = st.text_input("Enter city name, state", "Salt Lake City, UT")


# Data Processing and Visualization ------------------------------------------------------------------------------------------------------------------------
try:
    # Get all required data
    lat, lon = get_coordinates(location)
    city, state = get_city_state_from_coords(lat, lon)
    city_display = f"{city}, {state}" if state else city
    weather_gov_url = build_weather_gov_url_from_location(location)
    current_weather = get_weather_data_html_weather_gov(weather_gov_url)
    cond = current_weather.get('conditions', '')
    
    # Dynamic Background and Theme Settings ------------------------------------------------------------------------------------------------------------------------
    current_hour = datetime.datetime.now().hour
    is_night = current_hour < 6 or current_hour >= 18
    theme = get_theme_colors(cond, is_night)
    background_gradient = theme['background_gradient']
    text_color = theme['text_color']
    heading_color = theme['heading_color']
    card_bg = theme['card_bg']
    card_shadow = theme['card_shadow']
    card_border = theme['card_border']
    header_bg = theme['header_bg']
    header_text = theme['header_text']
    cell_bg = theme['cell_bg']
    cell_text = theme['cell_text']
    border_color = theme['border_color']

    # Get yesterday's data ------------------------------------------------------------------------------------------------------------------------
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    try:
        yesterday_data = get_historical_data(location, yesterday, yesterday)
        if not yesterday_data.empty:
            yest_temp = yesterday_data.iloc[-1]['temperature'] if 'temperature' in yesterday_data else None
            yest_hum = yesterday_data.iloc[-1]['humidity'] if 'humidity' in yesterday_data else None
            yest_wind = yesterday_data.iloc[-1]['wind_speed'] if 'wind_speed' in yesterday_data else None
        else:
            yest_temp = yest_hum = yest_wind = None
    except Exception:
        yest_temp = yest_hum = yest_wind = None

    # Get hourly forecast ------------------------------------------------------------------------------------------------------------------------
    hourly_df = get_hourly_forecast_weather_gov(lat, lon)
    
    # Get digital forecast data ------------------------------------------------------------------------------------------------------------------------
    url = f"https://forecast.weather.gov/MapClick.php?lat={lat}&lon={lon}&lg=english&&FcstType=digital"
    headers = {'User-Agent': 'WeatherDashboard/1.0'}
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.content, "html.parser")
    table = soup.find_all("table")[4]
    rows = table.find_all("tr")
    
    # Process forecast data ------------------------------------------------------------------------------------------------------------------------
    all_dates = []
    all_hours = []
    temp_values = []
    wind_values = []
    humidity_values = []
    
    for row in rows:
        cells = row.find_all(["td", "th"])
        if cells and cells[0].get_text(strip=True) == "Date":
            all_dates += [c.get_text(strip=True) for c in cells[1:] if c.get_text(strip=True)]
        if cells and cells[0].get_text(strip=True).startswith("Hour ("):
            all_hours += [c.get_text(strip=True) for c in cells[1:] if c.get_text(strip=True)]
        if cells and cells[0].get_text(strip=True) == "Temperature (°F)":
            temp_values += [c.get_text(strip=True) for c in cells[1:] if c.get_text(strip=True)]
        if cells and cells[0].get_text(strip=True) == "Surface Wind (mph)":
            wind_values += [c.get_text(strip=True) for c in cells[1:] if c.get_text(strip=True)]
        if cells and cells[0].get_text(strip=True) == "Relative Humidity (%)":
            humidity_values += [c.get_text(strip=True) for c in cells[1:] if c.get_text(strip=True)]

    # Combine dates and hours into [date, hour] pairs ------------------------------------------------------------------------------------------------------------------------
    combined = []
    if len(all_dates) > 0 and len(all_hours) > 0:
        hours_per_block = len(all_hours) // len(all_dates)
        idx = 0
        for date in all_dates:
            if date == all_dates[-1]:
                hours = all_hours[idx:]
            else:
                hours = all_hours[idx:idx+hours_per_block]
            for hour in hours:
                combined.append([date, hour])
            idx += len(hours)

    # Format as 'Month Day, HH:00' ------------------------------------------------------------------------------------------------------------------------ 
    formatted = []
    for date, hour in combined:
        try:
            dt = datetime.strptime(date, "%m/%d")
            date_str = dt.strftime("%B %-d") if hasattr(dt, 'strftime') else dt.strftime("%B %d").replace(' 0', ' ')
        except Exception:
            date_str = date
        hour_str = f"{int(hour):02d}:00"
        formatted.append(f"{date_str}, {hour_str}")

    # Now display everything at once in the main container ------------------------------------------------------------------------------------------------------------------------
    with main_content.container():
        # Title and description
        st.markdown(f"""
            <div class='weather-metric-card' style='text-align: center;'>
                <h1 style='
                    margin-bottom: 12px;
                    font-size: 2.5em;
                    font-weight: 700;
                    color: #1a237e;
                    text-shadow: 2px 4px 8px rgba(0,0,0,0.25), 0 2px 8px rgba(0,0,0,0.18);
                    letter-spacing: 0.02em;
                    background: rgba(255, 255, 255, 0.1);
                    padding: 16px;
                    border-radius: 16px;
                    backdrop-filter: blur(8px);
                '>Weather Dashboard</h1>
                <p style='
                    margin: 0;
                    font-size: 1.1em;
                    color: var(--weather-text);
                    text-shadow: 1px 2px 6px rgba(0,0,0,0.12);
                '>
                    Get real-time weather information and historical data for any location.
                    Simply enter a City Name, State to get started!
                </p>
            </div>
        """, unsafe_allow_html=True)

        # Current weather header ------------------------------------------------------------------------------------------------------------------------
        local_time = datetime.datetime.now().strftime('%I:%M %p')
        st.markdown(f'''
            <div style="
                display: inline-block;
                width: 100%;
                padding: 18px 32px 18px 32px;
                border-radius: 24px;
                margin-bottom: 18px;
                font-size: 2.1em;
                font-weight: 600;
                background: linear-gradient(90deg, rgba(255,255,255,0.01) 0%, #fff 55%);
                box-shadow: 0 4px 24px rgba(0,0,0,0.08);
                color: #1976d2;
                letter-spacing: 0.01em;
                text-shadow: 0 1px 2px rgba(0,0,0,0.08);
            ">
                Current Weather: {city_display} | Local Time: {local_time}
            </div>
        ''', unsafe_allow_html=True)

        # Weather metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            temp_value = current_weather['temperature'] if pd.notna(current_weather['temperature']) else "Not Available"
            temp_arrow = arrow(current_weather.get('temperature'), yest_temp)
            st.markdown(create_metric_card("Temperature", temp_value, temp_arrow), unsafe_allow_html=True)
        
        with col2:
            humidity_value = current_weather['humidity'] if pd.notna(current_weather['humidity']) else "Not Available"
            hum_arrow = arrow(current_weather.get('humidity'), yest_hum)
            st.markdown(create_metric_card("Humidity", humidity_value, hum_arrow), unsafe_allow_html=True)
        
        with col3:
            wind_value = current_weather['wind_speed'] if pd.notna(current_weather['wind_speed']) else "Not Available"
            wind_arrow = arrow(current_weather.get('wind_speed'), yest_wind)
            st.markdown(create_metric_card("Wind Speed", wind_value, wind_arrow), unsafe_allow_html=True)
        
        with col4:
            conditions_value = current_weather['conditions'] if pd.notna(current_weather['conditions']) else "Not Available"
            st.markdown(create_metric_card("Conditions", conditions_value), unsafe_allow_html=True)

        # Hourly forecast ------------------------------------------------------------------------------------------------------------------------
        if not hourly_df.empty:
            st.markdown("### Hourly Temperature Forecast")
            fig = px.line(hourly_df, x='hour', y='temperature', title='Hourly Temperature')
            st.plotly_chart(fig, use_container_width=True)

        # Forecast table ------------------------------------------------------------------------------------------------------------------------
        st.markdown(f"""
            <div class='weather-metric-card' style='
                margin-top: 32px;
                padding: 24px;
                background: {background_gradient};
                border-radius: 24px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.12), 0 4px 8px rgba(0,0,0,0.06);
            '>
                <h1 style='font-size: 2.8em; margin-bottom: 0.5em; color: {heading_color}; text-shadow: 2px 4px 8px rgba(0,0,0,0.25), 0 2px 8px rgba(0,0,0,0.18); font-weight: 700;'>8 Hour Forecast</h1>
            </div>
        """, unsafe_allow_html=True)

        # Create and display forecast table------------------------------------------------------------------------------------------------------------------------ 
        df = pd.DataFrame({
            'Date': formatted,
            'Temperature (F)': pd.to_numeric([t.replace('°F', '').strip() for t in temp_values], errors='coerce'),
            'Surface Wind Speed (mph)': pd.to_numeric([w.replace('mph', '').strip() for w in wind_values], errors='coerce'),
            'Relative Humidity (%)': pd.to_numeric([h.replace('%', '').strip() for h in humidity_values], errors='coerce')
        })
        
        df_display = df.head(10).copy()
        df_display['Temperature (F)'] = df_display['Temperature (F)'].astype(str) + '°F'
        df_display['Surface Wind Speed (mph)'] = df_display['Surface Wind Speed (mph)'].astype(str) + ' mph'
        df_display['Relative Humidity (%)'] = df_display['Relative Humidity (%)'].astype(str) + '%'

        styled_df = (
            df_display
            .style
            .set_table_styles([
                {'selector': 'th', 'props': [
                    ('background-color', header_bg),
                    ('color', header_text),
                    ('font-family', 'Garamond, serif'),
                    ('font-size', '16px'),
                    ('border', f'1.5px solid {border_color}')
                ]},
                {'selector': 'td', 'props': [
                    ('background-color', cell_bg),
                    ('color', cell_text),
                    ('font-family', 'Garamond, serif'),
                    ('font-size', '15px'),
                    ('border', f'1px solid {border_color}')
                ]},
                {'selector': 'table', 'props': [
                    ('border-collapse', 'separate'),
                    ('border-spacing', '0'),
                    ('width', '100%'),
                    ('border-radius', '32px'),
                    ('box-shadow', card_shadow),
                    ('overflow', 'hidden')
                ]}
            ])
            .set_properties(**{'text-align': 'left'})
            .map(highlight_temp, subset=['Temperature (F)'])
            .map(highlight_humidity, subset=['Relative Humidity (%)'])
        )
        st.table(styled_df)

        # Session State Management ------------------------------------------------------------------------------------------------------------------------
        # Ensure session state key is initialized
        if 'show_scatter' not in st.session_state:
            st.session_state['show_scatter'] = False
        if 'show_humidity' not in st.session_state:
            st.session_state['show_humidity'] = False
        if 'show_wind' not in st.session_state:
            st.session_state['show_wind'] = False
        if 'show_temp_humidity' not in st.session_state:
            st.session_state['show_temp_humidity'] = False


# Interactive Button Callbacks ------------------------------------------------------------------------------------------------------------------------
        def show_scatter_callback():
            st.session_state['show_scatter'] = True
            st.session_state['show_humidity'] = False
            st.session_state['show_wind'] = False
            st.session_state['show_temp_humidity'] = False

        def show_humidity_callback():
            st.session_state['show_humidity'] = True
            st.session_state['show_scatter'] = False
            st.session_state['show_wind'] = False
            st.session_state['show_temp_humidity'] = False

        def show_wind_callback():
            st.session_state['show_wind'] = True
            st.session_state['show_scatter'] = False
            st.session_state['show_humidity'] = False
            st.session_state['show_temp_humidity'] = False

        def show_temp_humidity_callback():
            st.session_state['show_temp_humidity'] = True
            st.session_state['show_scatter'] = False
            st.session_state['show_humidity'] = False
            st.session_state['show_wind'] = False


# Interactive Button Layout ------------------------------------------------------------------------------------------------------------------------
        if not st.session_state['show_scatter'] and not st.session_state['show_humidity'] and not st.session_state['show_wind'] and not st.session_state['show_temp_humidity']:
            empty_col1, empty_col2, empty_col3, empty_col4 = st.columns(4)
            with empty_col1:
                if st.button('Show Temperature Data Table', key='scatter_btn', help='Click to view temperature data table', on_click=show_scatter_callback):
                    st.session_state['show_scatter'] = True
            with empty_col2:
                if st.button('Show Relative Humidity', key='humidity_btn', help='Click to view relative humidity data', on_click=show_humidity_callback):
                    st.session_state['show_humidity'] = True
            with empty_col3:
                if st.button('Show Surface Wind Speed (mph) Distribution', key='wind_btn', help='Click to view wind speed distribution', on_click=show_wind_callback):
                    st.session_state['show_wind'] = True
            with empty_col4:
                if st.button('Temperature and Humidity', key='temp_humidity_btn', help='Click to view temperature and humidity combined data', on_click=show_temp_humidity_callback):
                    st.session_state['show_temp_humidity'] = True


# Temperature Scatter Plot Visualization ------------------------------------------------------------------------------------------------------------------------
        elif st.session_state['show_scatter']:
            st.markdown(f"""
                <div class='weather-metric-card' style='margin-top: 32px; padding: 24px; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.12), 0 4px 8px rgba(0,0,0,0.06); width: 100%; text-align: center;'>
                    <h1 style='font-size: 2.8em; margin-bottom: 0.5em; color: {text_color}; text-shadow: 2px 4px 8px rgba(0,0,0,0.25), 0 2px 8px rgba(0,0,0,0.18); font-weight: 700;'>Temperature Distribution Scatterplot</h1>
                </div>
            """, unsafe_allow_html=True)
            temp_df = df.copy()
            st.write("DEBUG: Raw Data for Plotting", temp_df[['Date', 'Temperature (F)']])
            # Plot raw data without conversion
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(temp_df['Date'], temp_df['Temperature (F)'], marker='o', linestyle='-', color='tab:blue')
            ax.set_xlabel('Date (raw)')
            ax.set_ylabel('Temperature (F) (raw)')
            ax.set_title('Raw Temperature Data')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            st.pyplot(fig)
            
            # New: Improved Table with correct rolling forecast grouping
            temp_df = df.copy()
            # Parse the 'Date' column to datetime
            temp_df['DateTime'] = pd.to_datetime(temp_df['Date'], format='%B %d, %H:%M', errors='coerce')
            temp_df = temp_df.sort_values('DateTime').reset_index(drop=True)
            # Extract hour as string (HH:MM)
            temp_df['Hour'] = temp_df['DateTime'].dt.strftime('%H:%M')
            # Assign Day_1, Day_2, Day_3 based on midnight boundaries
            day_labels = []
            day_counter = 1
            for i, row in temp_df.iterrows():
                if i == 0:
                    day_labels.append(f'Day_{day_counter}')
                else:
                    # If hour is 00:00, increment day_counter
                    if row['Hour'] == '00:00':
                        day_counter += 1
                    day_labels.append(f'Day_{day_counter}')
            temp_df['Day'] = day_labels
            improved_table = temp_df[['Day', 'Hour', 'Temperature (F)']]
            st.markdown('#### Improved Table: Rolling Forecast Assignment')
            st.dataframe(improved_table)
            
            if st.button('Back to Dashboard', key='back_btn'):
                st.session_state['show_scatter'] = False


# Temperature and Humidity Combined Plot ------------------------------------------------------------------------------------------------------------------------
        elif st.session_state['show_temp_humidity']:
            st.markdown(f"""
                <div class='weather-metric-card' style='margin-top: 32px; padding: 24px; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.12), 0 4px 8px rgba(0,0,0,0.06); width: 100%; text-align: center;'>
                    <h1 style='font-size: 2.8em; margin-bottom: 0.5em; color: {text_color}; text-shadow: 2px 4px 8px rgba(0,0,0,0.25), 0 2px 8px rgba(0,0,0,0.18); font-weight: 700;'>Temperature and Humidity Distribution</h1>
                </div>
            """, unsafe_allow_html=True)
            
            # Debug prints
            st.write("Debug - Raw DataFrame:")
            st.write(df.head())
            
            # Create combined plot
            temp_df = df.copy()
            st.write("Debug - After copy:")
            st.write(temp_df.head())
            
            temp_df['Temperature_numeric'] = pd.to_numeric(temp_df['Temperature (F)'].str.replace('°F', '').str.strip(), errors='coerce')
            st.write("Debug - After Temperature conversion:")
            st.write(temp_df['Temperature_numeric'].head())
            
            temp_df['Humidity_numeric'] = pd.to_numeric(temp_df['Relative Humidity (%)'].str.replace('%', '').str.strip(), errors='coerce')
            st.write("Debug - After Humidity conversion:")
            st.write(temp_df['Humidity_numeric'].head())
            
            # Convert date strings to datetime
            def parse_datetime(date_str):
                try:
                    base, hour = [s.strip() for s in date_str.split(',')]
                    dt_obj = datetime.datetime.strptime(base + ' ' + hour, '%B %d %H:%M')
                    return dt_obj
                except Exception:
                    return None
            
            temp_df['DateTime'] = temp_df['Date'].apply(parse_datetime)
            temp_df = temp_df.sort_values('DateTime')
            st.write("Debug - After sorting:")
            st.write(temp_df[['DateTime', 'Temperature_numeric', 'Humidity_numeric']].head())

            # Create figure with two y-axes
            fig, ax1 = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor('none')
            ax1.set_facecolor('none')

            # Convert colors to hex format
            plot_bg_color = convert_rgba_to_hex(card_bg)
            plot_edge_color = convert_rgba_to_hex(heading_color)
            plot_text_color = convert_rgba_to_hex(text_color)

            # Add background rectangle
            rect = FancyBboxPatch((0, 0), 1, 1,
                                boxstyle="round,pad=0.05,rounding_size=40",
                                linewidth=2,
                                edgecolor=plot_edge_color,
                                facecolor=plot_bg_color,
                                alpha=0.4,
                                zorder=0,
                                transform=ax1.transAxes)
            ax1.add_patch(rect)

            # Create second y-axis
            ax2 = ax1.twinx()

            # Plot temperature on first y-axis
            line1 = ax1.plot(temp_df['DateTime'], temp_df['Temperature_numeric'], 
                           color='#e53935', label='Temperature', linewidth=2)
            ax1.scatter(temp_df['DateTime'], temp_df['Temperature_numeric'], 
                       color='#e53935', s=40, zorder=3)

            # Plot humidity on second y-axis
            line2 = ax2.plot(temp_df['DateTime'], temp_df['Humidity_numeric'], 
                           color='#1976d2', label='Humidity', linewidth=2)
            ax2.scatter(temp_df['DateTime'], temp_df['Humidity_numeric'], 
                       color='#1976d2', s=40, zorder=3)

            # Style the axes
            ax1.set_xlabel('Date & Hour', color=plot_text_color)
            ax1.set_ylabel('Temperature (°F)', color='#e53935')
            ax2.set_ylabel('Relative Humidity (%)', color='#1976d2')

            # Format x-axis
            ax1.xaxis.set_major_formatter(FuncFormatter(format_date_with_suffix))

            # Set y-axis limits with some padding
            temp_min = max(0, temp_df['Temperature_numeric'].min() - 5)
            temp_max = temp_df['Temperature_numeric'].max() + 5
            hum_min = max(0, temp_df['Humidity_numeric'].min() - 5)
            hum_max = min(100, temp_df['Humidity_numeric'].max() + 5)

            ax1.set_ylim(temp_min, temp_max)
            ax2.set_ylim(hum_min, hum_max)

            # Add grid
            ax1.grid(True, color='#222222', alpha=0.3, linewidth=1, zorder=0)

            # Format ticks
            plt.xticks(rotation=45, ha='right', color=plot_text_color)
            ax1.tick_params(axis='y', colors='#e53935')
            ax2.tick_params(axis='y', colors='#1976d2')

            # Add legend
            lines = line1 + line2
            labels = [l.get_label() for l in lines]
            ax1.legend(lines, labels, loc='upper right', 
                      bbox_to_anchor=(1, 1.15),
                      frameon=True,
                      facecolor=plot_bg_color,
                      edgecolor=plot_edge_color)

            plt.tight_layout()
            st.pyplot(fig)

            # Back to Dashboard button
            if st.button('Back to Dashboard', key='back_btn_temp_humidity'):
                st.session_state['show_temp_humidity'] = False


# Humidity Plot Visualization ------------------------------------------------------------------------------------------------------------------------
        elif st.session_state['show_humidity']:
            st.markdown(f"""
                <div class='weather-metric-card' style='margin-top: 32px; padding: 24px; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.12), 0 4px 8px rgba(0,0,0,0.06); width: 100%; text-align: center;'>
                    <h1 style='font-size: 2.8em; margin-bottom: 0.5em; color: {text_color}; text-shadow: 2px 4px 8px rgba(0,0,0,0.25), 0 2px 8px rgba(0,0,0,0.18); font-weight: 700;'>Relative Humidity Distribution</h1>
                </div>
            """, unsafe_allow_html=True)
            
            # Create plot with styling matching temperature plot
            temp_df = df.copy()
            temp_df['DateTime'] = temp_df['Date'].apply(parse_datetime)
            temp_df = temp_df.sort_values('DateTime')

            # Set up the plot
            fig, ax = plt.subplots(figsize=(8, 4))
            create_plot_style(fig, ax, plot_edge_color, plot_text_color, plot_bg_color)
            ax.xaxis.set_major_formatter(FuncFormatter(format_date_with_suffix))

            # Calculate average temperature
            AV_VAL = temp_df['Temperature_numeric'].mean()
            if AV_VAL > 10:
                cmap = plt.get_cmap('Reds')
                norm = plt.Normalize(AV_VAL-5, AV_VAL+15)
            else:
                cmap = plt.get_cmap('Blues')
                norm = plt.Normalize(temp_df['Temperature_numeric'].min(), AV_VAL-3)
            # Create gradient fill under the line
            x_vals = temp_df['DateTime']
            y_vals = temp_df['Temperature_numeric']
            for i in range(len(x_vals)-1):
                ax.fill_between([x_vals.iloc[i], x_vals.iloc[i+1]], [y_vals.iloc[i], y_vals.iloc[i+1]],
                                color=cmap(norm((y_vals.iloc[i]+y_vals.iloc[i+1])/2)), alpha=0.8, zorder=1)
            temp_df.plot.scatter(x='DateTime', y='Temperature_numeric', ax=ax, color=plot_edge_color, s=40, zorder=3)
            # Connect the points with a line in chronological order
            ax.plot(temp_df['DateTime'], temp_df['Temperature_numeric'], color=plot_edge_color, linewidth=2, zorder=2)
            # Set y-axis to fit the data with a small margin
            y_min = max(0, y_vals.min() - 2)
            y_max = y_vals.max() + 2
            ax.set_ylim(y_min, y_max)
            ax.grid(True, color='#222222', alpha=0.7, linewidth=1, zorder=0)
            ax.set_xlabel('Date & Hour')
            ax.set_ylabel('Temperature (°F)')
            ax.set_title('')
            plt.xticks(rotation=45, ha='right', color=plot_text_color)
            plt.yticks(color=plot_text_color)
            plt.tight_layout()
            st.pyplot(fig)

            # Back to Dashboard button
            if st.button('Back to Dashboard', key='back_btn_temp_humidity'):
                st.session_state['show_temp_humidity'] = False


# Wind Speed Plot Visualization ------------------------------------------------------------------------------------------------------------------------
        elif st.session_state['show_wind']:
            st.markdown(f"""
                <div class='weather-metric-card' style='margin-top: 32px; padding: 24px; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.12), 0 4px 8px rgba(0,0,0,0.06); width: 100%; text-align: center;'>
                    <h1 style='font-size: 2.8em; margin-bottom: 0.5em; color: {text_color}; text-shadow: 2px 4px 8px rgba(0,0,0,0.25), 0 2px 8px rgba(0,0,0,0.18); font-weight: 700;'>Surface Wind Speed Distribution</h1>
                </div>
            """, unsafe_allow_html=True)
            
            # Create wind speed plot
            temp_df = df.copy()
            temp_df['DateTime'] = temp_df['Date'].apply(parse_datetime)
            temp_df['Wind_numeric'] = pd.to_numeric(temp_df['Surface Wind Speed (mph)'].str.replace('mph','').str.strip(), errors='coerce')
            temp_df = temp_df.sort_values('DateTime')

            # Set up the plot
            fig, ax = plt.subplots(figsize=(8, 4))
            create_plot_style(fig, ax, plot_edge_color, plot_text_color, plot_bg_color)
            ax.xaxis.set_major_formatter(FuncFormatter(format_date_with_suffix))

            # Calculate average wind speed
            AV_VAL = temp_df['Wind_numeric'].mean()
            
            # Choose colormap based on AV_VAL
            if AV_VAL > 10:
                cmap = plt.get_cmap('Reds')
                norm = plt.Normalize(AV_VAL-5, AV_VAL+15)
            else:
                cmap = plt.get_cmap('Blues')
                norm = plt.Normalize(temp_df['Wind_numeric'].min(), AV_VAL-3)

            # Plot the data
            x_vals = temp_df['DateTime']
            y_vals = temp_df['Wind_numeric']

            # Add gradient fill
            for i in range(len(x_vals)-1):
                ax.fill_between([x_vals.iloc[i], x_vals.iloc[i+1]], 
                              [y_vals.iloc[i], y_vals.iloc[i+1]],
                              color=cmap(norm((y_vals.iloc[i]+y_vals.iloc[i+1])/2)), 
                              alpha=0.8, 
                              zorder=1)

            # Add scatter points and line
            temp_df.plot.scatter(x='DateTime', y='Wind_numeric', ax=ax, color=plot_edge_color, s=40, zorder=3)
            ax.plot(temp_df['DateTime'], temp_df['Wind_numeric'], color=plot_edge_color, linewidth=2, zorder=2)

            # Set y-axis limits
            y_min = max(0, y_vals.min() - 2)
            y_max = y_vals.max() + 2
            ax.set_ylim(y_min, y_max)
            
            # Add grid and labels
            ax.grid(True, color='#222222', alpha=0.7, linewidth=1, zorder=0)
            ax.set_xlabel('Date & Hour')
            ax.set_ylabel('Surface Wind Speed (mph)')
            ax.set_title('')
            
            # Format ticks
            plt.xticks(rotation=45, ha='right', color=plot_text_color)
            plt.yticks(color=plot_text_color)
            plt.tight_layout()
            st.pyplot(fig)

            # Back to Dashboard button
            if st.button('Back to Dashboard', key='back_btn_wind'):
                st.session_state['show_wind'] = False


# Clean Data Display ------------------------------------------------------------------------------------------------------------------------
        # Display the clean dataframe
        st.markdown("### Clean Data for Graphs")
        st.dataframe(df)


# Footer Section ------------------------------------------------------------------------------------------------------------------------
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center;'>
            Data provided by weather.gov | Last updated: {}
        </div>
    """.format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error loading weather data: {str(e)}")
    st.info("Please try a different location or check your internet connection.")

# Dynamic background based on current weather (single injection at the end)
if 'current_weather' in locals() and current_weather:
    dynamic_css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600&display=swap');
    :root {{
        --weather-text: {text_color};
        --weather-heading: {heading_color};
        --weather-card-bg: {card_bg};
        --weather-card-shadow: {card_shadow};
        --weather-card-border: {card_border};
        --weather-font: 'Cormorant Garamond', serif;
        --weather-modern-font: 'Montserrat', sans-serif;
    }}
    /* Use Montserrat everywhere except tables/plots */
    html, body, .stApp, .stMarkdown, .stTextInput, .stDateInput, .stSelectbox, .stInfo, .stButton, h1, h2, h3, h4, h5, h6, .weather-metric-card, .stSidebar, .css-1d391kg, .css-1lcbmhc, .css-1v0mbdj, .css-1vq4p4l, .css-1cypcdb {{
        font-family: var(--weather-modern-font) !important;
        font-weight: 400 !important;
    }}
    /* Use thin Times New Roman for tables/plots */
    .stTable, .stTable th, .stTable td, .stDataFrame, .stDataFrame th, .stDataFrame td {{
        font-family: 'Times New Roman', Times, serif !important;
        font-weight: 300 !important;
    }}
    body, .stApp {{
        background: {background_gradient} !important;
        background-attachment: fixed !important;
        background-size: cover !important;
    }}
    /* Headings */
    h1, h2, h3, h4, h5, h6, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
        color: var(--weather-heading) !important;
    }}
    /* General text */
    body, .stApp, .stMarkdown, .stTextInput, .stDateInput, .stSelectbox, .stInfo, .stButton, .stTable, .stDataFrame {{
        color: var(--weather-text) !important;
    }}
    /* Enhanced Cards (metric bubbles) */
    div.weather-metric-card {{
        background: var(--weather-card-bg) !important;
        color: var(--weather-text) !important;
        border-radius: 24px !important;
        box-shadow: 
            0 10px 30px rgba(0,0,0,0.12),
            0 4px 8px rgba(0,0,0,0.06),
            var(--weather-card-shadow) !important;
        border: var(--weather-card-border) !important;
        padding: 32px 24px !important;
        margin-bottom: 16px !important;
        backdrop-filter: blur(8px) !important;
        transition: all 0.3s ease !important;
        position: relative !important;
        overflow: hidden !important;
    }}
    /* Table container styling congruent with cards */
    div.weather-table-container {{
        background: var(--weather-card-bg) !important;
        color: var(--weather-text) !important;
        border-radius: 24px !important;
        box-shadow: 
            0 10px 30px rgba(0,0,0,0.12),
            0 4px 8px rgba(0,0,0,0.06),
            var(--weather-card-shadow) !important;
        border: var(--weather-card-border) !important;
        padding: 32px 24px !important;
        margin-bottom: 16px !important;
        backdrop-filter: blur(8px) !important;
        transition: all 0.3s ease !important;
        position: relative !important;
        overflow: auto !important;
    }}
    /* Make the table and its cells fully opaque and readable */
    div.weather-table-container table,
    div.weather-table-container th,
    div.weather-table-container td {{
        background: var(--weather-card-bg) !important;
        color: var(--weather-text) !important;
    }}
    /* Enhanced heading styles */
    div.weather-metric-card h3 {{
        font-size: 1.4em !important;
        margin-bottom: 12px !important;
        color: #1a237e !important;
        text-shadow: 2px 4px 8px rgba(0,0,0,0.25), 0 2px 8px rgba(0,0,0,0.18) !important;
        background: rgba(255, 255, 255, 0.1) !important;
        padding: 8px 16px !important;
        border-radius: 12px !important;
        backdrop-filter: blur(8px) !important;
        display: inline-block !important;
        font-weight: 700 !important;
        letter-spacing: 0.02em !important;
    }}
    div.weather-metric-card h2 {{
        font-size: 2.2em !important;
        margin: 0 !important;
        color: #1a237e !important;
        text-shadow: 2px 4px 8px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.12) !important;
        font-weight: 700 !important;
        letter-spacing: 0.02em !important;
    }}
    /* Hover effect */
    div.weather-metric-card:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 
            0 15px 35px rgba(0,0,0,0.15),
            0 5px 10px rgba(0,0,0,0.08),
            var(--weather-card-shadow) !important;
    }}
    /* Sidebar */
    .stSidebar, .css-1d391kg, .css-1lcbmhc, .css-1v0mbdj, .css-1vq4p4l, .css-1cypcdb {{
        color: var(--weather-text) !important;
    }}
    /* Plot styling */
    .js-plotly-plot, .plotly-graph-div {{
        background: var(--weather-card-bg) !important;
        border-radius: 24px !important;
        box-shadow: var(--weather-card-shadow) !important;
        border: var(--weather-card-border) !important;
    }}
    /* Input fields */
    .stTextInput input, .stSelectbox select {{
        background: var(--weather-card-bg) !important;
        color: var(--weather-text) !important;
        border: var(--weather-card-border) !important;
    }}
    /* Buttons */
    .stButton button {{
        background: var(--weather-card-bg) !important;
        color: var(--weather-text) !important;
        border: var(--weather-card-border) !important;
        box-shadow: var(--weather-card-shadow) !important;
    }}
    /* Enhanced Sidebar Styling */
    .css-1d391kg, .css-1lcbmhc, .css-1v0mbdj, .css-1vq4p4l, .css-1cypcdb {{
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
    }}
    
    /* Sidebar Input Styling */
    .stSidebar .stTextInput input {{
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        color: var(--weather-text) !important;
        font-size: 1.1em !important;
        backdrop-filter: blur(10px) !important;
        transition: all 0.3s ease !important;
    }}
    
    .stSidebar .stTextInput input:focus {{
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: rgba(255, 255, 255, 0.3) !important;
        box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.1) !important;
    }}
    
    .stSidebar .stTextInput input::placeholder {{
        color: rgba(255, 255, 255, 0.4) !important;
    }}
    
    /* Sidebar Label Styling */
    .stSidebar .stTextInput label {{
        color: var(--weather-heading) !important;
        font-size: 1.1em !important;
        font-weight: 500 !important;
        margin-bottom: 8px !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.2) !important;
        opacity: 0.9 !important;
    }}
    
    /* Sidebar Container Spacing */
    .stSidebar .block-container {{
        padding-top: 2rem !important;
    }}

    /* Main content area transparency */
    .main .block-container {{
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(20px) !important;
    }}

    /* Weather metric cards transparency */
    div.weather-metric-card {{
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }}

    /* Table container transparency */
    div.weather-table-container {{
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }}

    /* Plot container transparency */
    .js-plotly-plot, .plotly-graph-div {{
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }}

    /* Forecast Header Styling */
    div.weather-metric-card h1[style*="8 Hour Forecast"] {{
        font-size: 2.2em !important;
        margin-bottom: 1em !important;
        color: #1a237e !important;
        text-shadow: 2px 4px 8px rgba(0,0,0,0.25), 0 2px 8px rgba(0,0,0,0.18) !important;
        background: rgba(255, 255, 255, 0.1) !important;
        padding: 16px 24px !important;
        border-radius: 16px !important;
        backdrop-filter: blur(8px) !important;
        display: inline-block !important;
        font-weight: 700 !important;
        letter-spacing: 0.02em !important;
    }}

    /* Current Weather Header */
    div[style*="Current Weather"] {{
        background: rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(8px) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        text-shadow: 2px 4px 8px rgba(0,0,0,0.25), 0 2px 8px rgba(0,0,0,0.18) !important;
        color: #1a237e !important;
    }}

    /* Table Headers */
    .stTable th {{
        background: rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(8px) !important;
        color: #1a237e !important;
        text-shadow: 1px 2px 6px rgba(0,0,0,0.15) !important;
        font-weight: 700 !important;
        letter-spacing: 0.02em !important;
    }}
    </style>
    """
    st.markdown(dynamic_css, unsafe_allow_html=True)
