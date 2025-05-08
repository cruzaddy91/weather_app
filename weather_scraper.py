import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re
import time
import streamlit as st


def get_coordinates(location):
    """
    Convert location to coordinates using OpenStreetMap's Nominatim service
    """
    try:
        # Format the location for the API
        formatted_location = location.replace(' ', '+')
        
        # Construct the URL for Nominatim
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={formatted_location}"
        
        # Add headers to identify our application
        headers = {
            'User-Agent': 'WeatherDashboard/1.0 (https://github.com/yourusername/weather-dashboard)'
        }
        
        # Make the request
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Geocoding API request failed with status code: {response.status_code}")
            
        data = response.json()
        
        if not data:
            raise Exception(f"No coordinates found for location: {location}")
            
        # Get the first result (most relevant)
        first_result = data[0]
        lat = first_result['lat']
        lon = first_result['lon']
        
        # Respect Nominatim's usage policy by adding a delay
        time.sleep(1)
        
        return lat, lon
        
    except Exception as e:
        raise Exception(f"Error getting coordinates: {str(e)}")

def get_weather_data(location):
    """
    Fetch current weather data for a given location from weather.gov
    """
    try:
        # Convert location to coordinates
        lat, lon = get_coordinates(location)
        
        # Construct the URL for the weather.gov API
        url = f"https://api.weather.gov/points/{lat},{lon}"
        
        # Get the forecast URL
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"API request failed with status code: {response.status_code}")
            
        data = response.json()
        
        if 'properties' not in data:
            raise Exception("Invalid response from weather.gov API")
            
        forecast_url = data['properties']['forecast']
        
        # Get the current weather
        forecast_response = requests.get(forecast_url)
        if forecast_response.status_code != 200:
            raise Exception(f"Forecast API request failed with status code: {forecast_response.status_code}")
            
        forecast_data = forecast_response.json()
        
        if 'properties' not in forecast_data or 'periods' not in forecast_data['properties']:
            raise Exception("Invalid forecast data from weather.gov API")
            
        # Extract current conditions
        current_period = forecast_data['properties']['periods'][0]
        
        # Get detailed current conditions
        observation_url = data['properties']['observationStations']
        obs_response = requests.get(observation_url)
        if obs_response.status_code == 200:
            obs_data = obs_response.json()
            if 'features' in obs_data and obs_data['features']:
                station_url = obs_data['features'][0]['id'] + '/observations/latest'
                station_response = requests.get(station_url)
                if station_response.status_code == 200:
                    station_data = station_response.json()
                    if 'properties' in station_data:
                        humidity = station_data['properties'].get('relativeHumidity', {}).get('value')
                        if humidity is not None:
                            return {
                                'temperature': current_period.get('temperature', 'N/A'),
                                'humidity': f"{humidity:.0f}%",
                                'wind_speed': current_period.get('windSpeed', 'N/A'),
                                'conditions': current_period.get('shortForecast', 'N/A')
                            }
        
        # Fallback to forecast data if observation data is not available
        return {
            'temperature': current_period.get('temperature', 'N/A'),
            'humidity': 'N/A',  # Forecast doesn't provide humidity
            'wind_speed': current_period.get('windSpeed', 'N/A'),
            'conditions': current_period.get('shortForecast', 'N/A')
        }
    except Exception as e:
        raise Exception(f"Error fetching weather data: {str(e)}")



def get_weather_data_accuweather(url=None, city_slug=None):
    """
    Scrape current weather data from an AccuWeather city page.
    Args:
        url: Full AccuWeather city URL (if provided, use directly)
        city_slug: e.g. 'us/salt-lake-city/84101/current-weather/331216' (if provided, build URL)
    Returns:
        dict with temperature, humidity, wind_speed, and conditions
    """
    if not url and not city_slug:
        raise ValueError("Must provide either url or city_slug.")
    if not url:
        url = f"https://www.accuweather.com/en/{city_slug}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch AccuWeather page: {response.status_code}")
        soup = BeautifulSoup(response.content, "html.parser")
        # Temperature
        temp_div = soup.find("div", class_="display-temp")
        temperature = temp_div.text.strip() if temp_div else "N/A"
        # Conditions
        cond_div = soup.find("div", class_="phrase")
        conditions = cond_div.text.strip() if cond_div else "N/A"
        # Details (Humidity, Wind, etc.)
        details = soup.find_all("div", class_="detail-item spaced-content")
        humidity = wind = "N/A"
        for item in details:
            label = item.find("div", class_="label")
            value = item.find("div", class_="value")
            if label and value:
                if "Humidity" in label.text:
                    humidity = value.text.strip()
                if "Wind" in label.text:
                    wind = value.text.strip()
        return {
            "temperature": temperature,
            "humidity": humidity,
            "wind_speed": wind,
            "conditions": conditions
        }
    except requests.Timeout:
        raise Exception("Timeout while fetching weather data from AccuWeather. Please try again later.")
    except Exception as e:
        raise Exception(f"Error in get_weather_data_accuweather: {str(e)}")

def get_weather_data_html_weather_gov(url):
    """
    Scrape current weather data from a weather.gov MapClick page.
    Args:
        url: Full weather.gov MapClick URL
    Returns:
        dict with temperature, humidity, wind_speed, and conditions
    """
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    resp = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(resp.content, "html.parser")
    # Temperature
    temp = soup.find(class_="myforecast-current-lrg")
    temperature = temp.text.strip() if temp else "N/A"
    # Conditions
    cond = soup.find(class_="myforecast-current")
    conditions = cond.text.strip() if cond else "N/A"
    # Humidity and Wind (in the table) - robust extraction
    humidity = wind = "N/A"
    for row in soup.select("#current_conditions_detail tr"):
        cells = row.find_all("td")
        if len(cells) == 2:
            label = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)
            if "Humidity" in label:
                humidity = value
            if "Wind" in label:
                wind = value
    return {
        "temperature": temperature,
        "humidity": humidity,
        "wind_speed": wind,
        "conditions": conditions
    }

def build_weather_gov_url_from_location(location):
    lat, lon = get_coordinates(location)
    return f"https://forecast.weather.gov/MapClick.php?lat={lat}&lon={lon}"

def get_hourly_forecast_weather_gov(lat, lon):
    """
    Scrape the hourly graphical forecast from weather.gov for a given lat/lon.
    Returns a DataFrame with columns: hour, temperature, wind_speed, humidity (if available)
    """
    import requests
    import pandas as pd
    from bs4 import BeautifulSoup

    url = f"https://forecast.weather.gov/MapClick.php?lat={lat}&lon={lon}&unit=0&lg=english&FcstType=graphical"
    headers = {'User-Agent': 'WeatherDashboard/1.0'}
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.content, "html.parser")

    # Find all script tags and look for the one containing hourly data arrays
    scripts = soup.find_all('script')
    temp_data, wind_data, hum_data, hours = [], [], [], []
    for script in scripts:
        text = script.string
        if not text:
            continue
        # Temperature
        temp_match = re.search(r'var temp = \[(.*?)\];', text)
        if temp_match:
            temp_data = [int(x) for x in temp_match.group(1).split(',')]
        # Wind Speed
        wind_match = re.search(r'var wspd = \[(.*?)\];', text)
        if wind_match:
            wind_data = [int(x) for x in wind_match.group(1).split(',')]
        # Humidity
        hum_match = re.search(r'var rh = \[(.*?)\];', text)
        if hum_match:
            hum_data = [int(x) for x in hum_match.group(1).split(',')]
        # Hours
        hour_match = re.search(r'var hour = \[(.*?)\];', text)
        if hour_match:
            hours = [int(x) for x in hour_match.group(1).split(',')]
    # If no hours, fallback to 0..N
    if not hours and temp_data:
        hours = list(range(len(temp_data)))
    # Build DataFrame
    df = pd.DataFrame({'hour': hours})
    if temp_data:
        df['temperature'] = temp_data
    if wind_data:
        df['wind_speed'] = wind_data
    if hum_data:
        df['humidity'] = hum_data
    return df

def get_hourly_forecast_svg_weather_gov(lat, lon):
    """
    Scrape the SVG charts from weather.gov's graphical forecast for a given lat/lon.
    Returns a DataFrame with columns: hour, temperature, wind_speed, humidity (if available)
    """
    import requests
    import pandas as pd
    from bs4 import BeautifulSoup

    url = f"https://forecast.weather.gov/MapClick.php?lat={lat}&lon={lon}&unit=0&lg=english&FcstType=graphical"
    headers = {'User-Agent': 'WeatherDashboard/1.0'}
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.content, "html.parser")

    # Find all SVGs (each chart is an SVG)
    svgs = soup.find_all('svg')
    if len(svgs) < 3:
        return pd.DataFrame()  # Not enough charts found

    # Helper to extract numbers from <text> nodes in an SVG
    def extract_svg_numbers(svg):
        numbers = []
        for t in svg.find_all('text'):
            try:
                val = t.get_text(strip=True)
                # Only keep numbers (skip axis labels, etc.)
                if val.replace('.', '', 1).replace('-', '', 1).isdigit():
                    numbers.append(float(val))
            except Exception:
                continue
        return numbers

    # Extract data from the first three SVGs
    temp_vals = extract_svg_numbers(svgs[0])
    wind_vals = extract_svg_numbers(svgs[1])
    hum_vals = extract_svg_numbers(svgs[2])

    # Try to get hour labels from the x-axis of the first SVG
    hour_labels = []
    for t in svgs[0].find_all('text'):
        val = t.get_text(strip=True)
        if (':' in val or val.endswith('am') or val.endswith('pm')) and not val.replace(':','').replace('am','').replace('pm','').isdigit():
            hour_labels.append(val)
    # Fallback: just use index
    n = min(len(temp_vals), len(wind_vals), len(hum_vals))
    if not hour_labels or len(hour_labels) != n:
        hour_labels = list(range(n))
    # Build DataFrame
    df = pd.DataFrame({
        'hour': hour_labels[:n],
        'temperature': temp_vals[:n],
        'wind_speed': wind_vals[:n],
        'humidity': hum_vals[:n],
    })
    return df

def get_digital_forecast_table_weather_gov(lat, lon):
    """
    Scrape the digital forecast table from weather.gov for a given lat/lon.
    (Table extraction logic temporarily removed for step-by-step debugging.)
    """
    pass

def save_forecast_to_csv(all_dates, all_hours, temp_values, wind_values, humidity_values, filename='weather_data.csv'):
    # Combine the data into a DataFrame
    data = []
    for i in range(len(all_dates)):
        data.append({
            'Date': all_dates[i] if i < len(all_dates) else '',
            'Hour': all_hours[i] if i < len(all_hours) else '',
            'Temperature (F)': temp_values[i] if i < len(temp_values) else '',
            'Surface Wind Speed (mph)': wind_values[i] if i < len(wind_values) else '',
            'Relative Humidity (%)': humidity_values[i] if i < len(humidity_values) else ''
        })
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)

# Example usage (call this after scraping in your main app):
# save_forecast_to_csv(all_dates, all_hours, temp_values, wind_values, humidity_values)