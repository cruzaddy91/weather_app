import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from weather_scraper import get_weather_data_html_weather_gov, build_weather_gov_url_from_location, get_coordinates, get_hourly_forecast_weather_gov, get_digital_forecast_table_weather_gov, save_forecast_to_csv
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

def safe_color(val, fallback):
    if isinstance(val, str) and val.startswith('#'):
        return val
    if isinstance(val, str) and val.lower() in mcolors.CSS4_COLORS:
        return val
    return fallback

def get_city_state_from_coords(lat, lon):
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10"
    headers = {'User-Agent': 'WeatherDashboard/1.0'}
    resp = requests.get(url, headers=headers)
    data = resp.json()
    address = data.get('address', {})
    city = address.get('city') or address.get('town') or address.get('village') or address.get('hamlet') or ''
    state = address.get('state') or ''
    return city, state

# Set page config
st.set_page_config(
    page_title="Weather Dashboard",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Create a single container for all main content
main_content = st.empty()

# Sidebar for location input
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

# Define helper functions
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

# Define table styling variables
header_bg = "#e3f2fd"
header_text = "#1976d2"
cell_bg = "rgba(255,255,255,0.80)"
cell_text = "#222"
border_color = "#e0e0e0"
shadow = "12px 24px 48px 8px rgba(30,30,60,0.35), 0 8px 32px rgba(0,0,0,0.10)"

# Load all data first
try:
    # Get all required data
    lat, lon = get_coordinates(location)
    city, state = get_city_state_from_coords(lat, lon)
    city_display = f"{city}, {state}" if state else city
    weather_gov_url = build_weather_gov_url_from_location(location)
    current_weather = get_weather_data_html_weather_gov(weather_gov_url)

    # --- MOVE DYNAMIC BACKGROUND LOGIC HERE ---
    cond = current_weather.get('conditions', '').strip().lower() if current_weather else ''
    temp = current_weather.get('temperature', 70) if current_weather else 70
    # Default background
    background_gradient = "linear-gradient(135deg, #87ceeb 0%, #00bfff 60%, #ffffff 100%)"
    text_color = "#01579b"
    heading_color = "#039be5"
    card_bg = "rgba(255,255,255,0.95)"
    card_shadow = "0 8px 32px 0 rgba(3,155,229,0.12)"
    card_border = "1.5px solid #039be5"
    current_hour = datetime.datetime.now().hour
    is_night = current_hour < 6 or current_hour >= 18
    if is_night:
        background_gradient = "linear-gradient(135deg, #1a237e 0%, #283593 40%, #3949ab 100%)"
        text_color = "#e8eaf6"
        heading_color = "#9fa8da"
        card_bg = "rgba(25,118,210,0.15)"
        card_shadow = "0 8px 32px 0 rgba(25,118,210,0.25)"
        card_border = "1.5px solid #3949ab"
    elif 'thunderstorm' in cond or 'thunder' in cond:
        background_gradient = "linear-gradient(135deg, #424242 0%, #616161 40%, #757575 100%)"
        text_color = "#e0e0e0"
        heading_color = "#ffd54f"
        card_bg = "rgba(33,33,33,0.85)"
        card_shadow = "0 8px 32px 0 rgba(255,213,79,0.25)"
        card_border = "1.5px solid #ffd54f"
    elif 'rain' in cond or 'shower' in cond or 'drizzle' in cond:
        background_gradient = "linear-gradient(135deg, #546e7a 0%, #78909c 40%, #90a4ae 100%)"
        text_color = "#eceff1"
        heading_color = "#b3e5fc"
        card_bg = "rgba(69,90,100,0.85)"
        card_shadow = "0 8px 32px 0 rgba(179,229,252,0.25)"
        card_border = "1.5px solid #b3e5fc"
    elif 'snow' in cond or 'flurries' in cond or 'sleet' in cond:
        background_gradient = "linear-gradient(135deg, #e3f2fd 0%, #bbdefb 40%, #90caf9 100%)"
        text_color = "#0d47a1"
        heading_color = "#1976d2"
        card_bg = "rgba(227,242,253,0.95)"
        card_shadow = "0 8px 32px 0 rgba(25,118,210,0.15)"
        card_border = "1.5px solid #1976d2"
    elif 'fog' in cond or 'mist' in cond or 'haze' in cond:
        background_gradient = "linear-gradient(135deg, #cfd8dc 0%, #b0bec5 40%, #90a4ae 100%)"
        text_color = "#37474f"
        heading_color = "#455a64"
        card_bg = "rgba(207,216,220,0.95)"
        card_shadow = "0 8px 32px 0 rgba(69,90,100,0.15)"
        card_border = "1.5px solid #455a64"
    elif 'wind' in cond or 'breezy' in cond or 'gust' in cond:
        background_gradient = "linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 40%, #80deea 100%)"
        text_color = "#006064"
        heading_color = "#0097a7"
        card_bg = "rgba(224,247,250,0.95)"
        card_shadow = "0 8px 32px 0 rgba(0,151,167,0.15)"
        card_border = "1.5px solid #0097a7"
    elif 'clear' in cond or 'not a cloud' in cond:
        background_gradient = "linear-gradient(135deg, #ffd54f 0%, #ffd54f 20%, #1e88e5 50%, #64b5f6 100%)"
        text_color = "#01579b"
        heading_color = "#039be5"
        card_bg = "rgba(255,255,255,0.95)"
        card_shadow = "0 8px 32px 0 rgba(3,155,229,0.12)"
        card_border = "1.5px solid #039be5"
    elif 'few clouds' in cond:
        background_gradient = "linear-gradient(135deg, #e0f7fa 0%, #039be5 60%, #0d47a1 100%)"
        text_color = "#01579b"
        heading_color = "#039be5"
        card_bg = "rgba(224,247,250,0.92)"
        card_shadow = "0 8px 32px 0 rgba(3,155,229,0.18)"
        card_border = "1.5px solid #039be5"
    elif 'partly cloudy' in cond or 'partly sunny' in cond:
        background_gradient = "linear-gradient(135deg, #e0f7fa 0%, #b3e5fc 30%, #81d4fa 60%, #ffffff 100%)"
        text_color = "#0277bd"
        heading_color = "#039be5"
        card_bg = "rgba(224,247,250,0.92)"
        card_shadow = "0 8px 32px 0 rgba(129,212,250,0.18)"
        card_border = "1.5px solid #81d4fa"
    elif 'mostly cloudy' in cond:
        background_gradient = "linear-gradient(135deg, #e0eafc 0%, #b0bec5 60%, #757f9a 100%)"
        text_color = "#37474f"
        heading_color = "#757f9a"
        card_bg = "rgba(176,190,197,0.85)"
        card_shadow = "0 8px 32px 0 rgba(117,127,154,0.18)"
        card_border = "1.5px solid #757f9a"
    elif 'overcast' in cond:
        background_gradient = "linear-gradient(135deg, #757f9a 0%, #37474f 60%, #232b36 100%)"
        text_color = "#e0e0e0"
        heading_color = "#b0bec5"
        card_bg = "rgba(55,71,79,0.92)"
        card_shadow = "0 8px 32px 0 rgba(35,43,54,0.45)"
        card_border = "1.5px solid #232b36"
    # --- END MOVE ---

    # Get yesterday's data
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

    # Get hourly forecast
    hourly_df = get_hourly_forecast_weather_gov(lat, lon)
    
    # Get digital forecast data
    url = f"https://forecast.weather.gov/MapClick.php?lat={lat}&lon={lon}&lg=english&&FcstType=digital"
    headers = {'User-Agent': 'WeatherDashboard/1.0'}
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.content, "html.parser")
    table = soup.find_all("table")[4]
    rows = table.find_all("tr")
    
    # Process forecast data
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

    # Combine dates and hours into [date, hour] pairs
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

    # Format as 'Month Day, HH:00'
    formatted = []
    for date, hour in combined:
        try:
            dt = datetime.strptime(date, "%m/%d")
            date_str = dt.strftime("%B %-d") if hasattr(dt, 'strftime') else dt.strftime("%B %d").replace(' 0', ' ')
        except Exception:
            date_str = date
        hour_str = f"{int(hour):02d}:00"
        formatted.append(f"{date_str}, {hour_str}")

    # After processing forecast data and before displaying, save to CSV
    df = pd.DataFrame({
        'Date': formatted,
        'Temperature (F)': temp_values,
        'Surface Wind Speed (mph)': wind_values,
        'Relative Humidity (%)': humidity_values
    })
    
    save_forecast_to_csv(
        df['Date'].tolist(),
        [d.split(',')[1].strip() if ',' in d else '' for d in df['Date'].tolist()],
        df['Temperature (F)'].tolist(),
        df['Surface Wind Speed (mph)'].tolist(),
        df['Relative Humidity (%)'].tolist()
    )

    # Now display everything at once in the main container
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

        # Current weather header
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
            st.markdown(f"""
                <div class='weather-metric-card'>
                    <h3 style='margin-top: 0;'>Temperature</h3>
                    <h2 style='margin-bottom: 0;'>{temp_value} {temp_arrow}</h2>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            humidity_value = current_weather['humidity'] if pd.notna(current_weather['humidity']) else "Not Available"
            hum_arrow = arrow(current_weather.get('humidity'), yest_hum)
            st.markdown(f"""
                <div class='weather-metric-card'>
                    <h3 style='margin-top: 0;'>Humidity</h3>
                    <h2 style='margin-bottom: 0;'>{humidity_value} {hum_arrow}</h2>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            wind_value = current_weather['wind_speed'] if pd.notna(current_weather['wind_speed']) else "Not Available"
            wind_arrow = arrow(current_weather.get('wind_speed'), yest_wind)
            st.markdown(f"""
                <div class='weather-metric-card'>
                    <h3 style='margin-top: 0;'>Wind Speed</h3>
                    <h2 style='margin-bottom: 0;'>{wind_value} {wind_arrow}</h2>
                </div>
            """, unsafe_allow_html=True)
        
        with col4:
            conditions_value = current_weather['conditions'] if pd.notna(current_weather['conditions']) else "Not Available"
            st.markdown(f"""
                <div class='weather-metric-card'>
                    <h3 style='margin-top: 0;'>Conditions</h3>
                    <h2 style='margin-bottom: 0;'>{conditions_value}</h2>
                </div>
            """, unsafe_allow_html=True)

        # Hourly forecast
        if not hourly_df.empty:
            st.markdown("### Hourly Temperature Forecast")
            fig = px.line(hourly_df, x='hour', y='temperature', title='Hourly Temperature')
            st.plotly_chart(fig, use_container_width=True)

        # Forecast table
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

        # Create and display forecast table
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
                    ('box-shadow', shadow),
                    ('overflow', 'hidden')
                ]}
            ])
            .set_properties(**{'text-align': 'left'})
            .applymap(highlight_temp, subset=['Temperature (F)'])
            .applymap(highlight_humidity, subset=['Relative Humidity (%)'])
        )
        st.table(styled_df)

        # Ensure session state key is initialized
        if 'show_scatter' not in st.session_state:
            st.session_state['show_scatter'] = False

        # Add 4 containers in a row, leftmost is clickable for scatter plot
        def show_scatter_callback():
            st.session_state['show_scatter'] = True

        if not st.session_state['show_scatter'] and not st.session_state.get('show_humidity_scatter', False):
            empty_col1, empty_col2, empty_col3, empty_col4 = st.columns(4)
            with empty_col1:
                if st.button('Show Temperature Data Table', key='scatter_btn', help='Click to view temperature data table', on_click=show_scatter_callback):
                    pass
                st.markdown("<div class='weather-metric-card' style='height: 120px;'></div>", unsafe_allow_html=True)
            with empty_col2:
                def show_humidity_scatter_callback():
                    st.session_state['show_humidity_scatter'] = True
                if st.button('Show Relative Humidity Data Table', key='humidity_btn', help='Click to view relative humidity data table', on_click=show_humidity_scatter_callback):
                    pass
                st.markdown("<div class='weather-metric-card' style='height: 120px;'></div>", unsafe_allow_html=True)
            with empty_col3:
                st.markdown("<div class='weather-metric-card' style='height: 120px;'></div>", unsafe_allow_html=True)
            with empty_col4:
                st.markdown("<div class='weather-metric-card' style='height: 120px;'></div>", unsafe_allow_html=True)
        elif st.session_state.get('show_humidity_scatter', False):
            st.markdown(f"""
                <div class='weather-metric-card' style='margin-top: 32px; padding: 24px; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.12), 0 4px 8px rgba(0,0,0,0.06); width: 100%; text-align: center;'>
                    <h1 style='font-size: 2.8em; margin-bottom: 0.5em; color: {text_color}; text-shadow: 2px 4px 8px rgba(0,0,0,0.25), 0 2px 8px rgba(0,0,0,0.18); font-weight: 700;'>Relative Humidity Distribution Scatterplot</h1>
                </div>
            """, unsafe_allow_html=True)
            hum_df = df.copy()
            import datetime as dt
            def parse_datetime(date_str):
                try:
                    base, hour = [s.strip() for s in date_str.split(',')]
                    dt_obj = dt.datetime.strptime(base + ' ' + hour, '%m/%d %H:%M')
                    return dt_obj
                except Exception:
                    return None
            hum_df['DateTime'] = hum_df['Date'].apply(parse_datetime)
            hum_df['Humidity_numeric'] = pd.to_numeric(hum_df['Relative Humidity (%)'].str.replace('%','').str.strip(), errors='coerce')
            hum_df = hum_df.sort_values('DateTime')
            fig, ax = plt.subplots(figsize=(8, 4))
            mpl_card_bg = safe_color(card_bg, 'white')
            mpl_heading_color = safe_color(heading_color, '#1a237e')
            mpl_text_color = safe_color(text_color, 'black')
            rect = FancyBboxPatch((0, 0), 1, 1,
                                  boxstyle="round,pad=0.05,rounding_size=40",
                                  linewidth=2,
                                  edgecolor=mpl_heading_color,
                                  facecolor=mpl_card_bg,
                                  alpha=0.4,
                                  zorder=0,
                                  transform=ax.transAxes)
            ax.add_patch(rect)
            for spine in ax.spines.values():
                spine.set_linewidth(2)
                spine.set_edgecolor(mpl_heading_color)
            ax.spines['bottom'].set_color(mpl_heading_color)
            ax.spines['top'].set_color(mpl_heading_color)
            ax.spines['right'].set_color(mpl_heading_color)
            ax.spines['left'].set_color(mpl_heading_color)
            ax.tick_params(axis='x', colors=mpl_text_color)
            ax.tick_params(axis='y', colors=mpl_text_color)
            dark_label_color = '#111111'
            ax.xaxis.label.set_color(dark_label_color)
            ax.yaxis.label.set_color(dark_label_color)
            ax.title.set_color(mpl_heading_color)
            def add_suffix(x, pos=None):
                dt = mdates.num2date(x)
                day = dt.day
                if 11 <= day <= 13:
                    suffix = 'th'
                else:
                    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                return dt.strftime(f'%b {day}{suffix}, %I:%M %p')
            ax.xaxis.set_major_formatter(FuncFormatter(add_suffix))
            x_vals = hum_df['DateTime']
            y_vals = hum_df['Humidity_numeric']
            AV_VAL = y_vals.mean()
            if AV_VAL > 50:
                cmap = plt.get_cmap('Blues')
                norm = plt.Normalize(AV_VAL-20, AV_VAL+20)
            else:
                cmap = plt.get_cmap('Reds')
                norm = plt.Normalize(y_vals.min(), AV_VAL+10)
            for i in range(len(x_vals)-1):
                ax.fill_between([x_vals.iloc[i], x_vals.iloc[i+1]], [y_vals.iloc[i], y_vals.iloc[i+1]],
                                color=cmap(norm((y_vals.iloc[i]+y_vals.iloc[i+1])/2)), alpha=0.8, zorder=1)
            hum_df.plot.scatter(x='DateTime', y='Humidity_numeric', ax=ax, color=mpl_heading_color, s=40, zorder=3)
            ax.plot(hum_df['DateTime'], hum_df['Humidity_numeric'], color=mpl_heading_color, linewidth=2, zorder=2)
            y_min = max(0, y_vals.min() - 2)
            y_max = min(100, y_vals.max() + 2)
            ax.set_ylim(y_min, y_max)
            ax.grid(True, color='#222222', alpha=0.7, linewidth=1, zorder=0)
            ax.set_xlabel('Date & Hour')
            ax.set_ylabel('Relative Humidity (%)')
            ax.set_title('')
            plt.xticks(rotation=45, ha='right', color=mpl_text_color)
            plt.yticks(color=mpl_text_color)
            plt.tight_layout()
            st.pyplot(fig)
            if st.button('Back to Dashboard', key='back_btn_humidity'):
                st.session_state['show_humidity_scatter'] = False
                st.experimental_rerun()

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

def get_accuweather_city_url(city_query):
    """
    Given a city name or ZIP, search AccuWeather and return the first matching city weather URL.
    """
    import urllib.parse
    search_url = f"https://www.accuweather.com/en/search-locations?query={urllib.parse.quote(city_query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    resp = requests.get(search_url, headers=headers, timeout=10)
    soup = BeautifulSoup(resp.content, "html.parser")
    # Find the first city result link
    link = soup.find("a", class_="result-city")
    if not link or not link.get("href"):
        raise Exception(f"Could not find AccuWeather city for: {city_query}")
    city_url = "https://www.accuweather.com" + link.get("href")
    st.text(soup.prettify()[:2000])  # Show the first 2000 characters of the HTML
    for script in soup.find_all('script'):
        st.text(script.string)
    return city_url 