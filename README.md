# Weather Dashboard

A Streamlit application that provides current weather information and historical trends for user-specified locations.

## Features

- Current weather display (temperature, humidity, wind speed, conditions)
- Historical weather trends visualization
- Location-based weather data
- Interactive date range selection for historical data

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Open your web browser and navigate to the URL shown in the terminal (typically http://localhost:8501)

3. Enter a city name or ZIP code in the sidebar to view weather information

## Data Sources

This app uses data from the National Weather Service API (weather.gov).

## Note

This is a demo application. For production use, you would need to:
- Implement proper geocoding for location to coordinates conversion
- Add error handling for API rate limits
- Consider using a paid weather API for more reliable data
- Add caching to reduce API calls

## License

MIT License 