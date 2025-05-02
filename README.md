# Indonesia GIS Precipitation Forecast

A GIS visualization tool for precipitation forecasts and historical data in Indonesia, with a focus on the Bandung region.

## Features

- Visualize NOAA GFS forecast data for precipitation
- View historical precipitation data from CHIRPS
- Display Indonesian regional boundaries from GADM
- Interactive date selection via Streamlit interface
- Command-line map visualization

## Setup

1. Clone this repository:
   ```
   git clone <repository-url>
   cd igs
   ```

2. Set up the virtual environment and install dependencies:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install streamlit
   ```

## Usage

### Command Line Mode

To run the standard map visualization with default settings:

```bash
./run.sh
```

This will display a map with:
- NOAA GFS forecast precipitation data
- CHIRPS historical precipitation data
- Regional boundaries for Bandung, Indonesia

### Interactive Streamlit Interface

To run the interactive Streamlit interface:

```bash
./run.sh streamlit
```

The Streamlit interface allows you to:
- Select different forecast dates
- Choose forecast cycles (00, 06, 12, 18)
- Select hours ahead for the forecast (3, 6, 12, 24, 48, 72)
- Choose different historical dates
- Adjust the map resolution

## Data Sources

- **Forecast Data**: NOAA GFS (Global Forecast System)
- **Historical Data**: CHIRPS (Climate Hazards Group InfraRed Precipitation with Station data)
- **Regional Boundaries**: GADM (Database of Global Administrative Areas)

## Project Structure

- `map.py` - Main script for command-line map visualization
- `streamlit_app.py` - Streamlit interactive interface
- `map_utils.py` - Helper functions for map generation
- `sources.py` - Data source implementations
- `utils.py` - Utility functions for coordinate transformations
- `custom_types.py` - Type definitions
- `run.sh` - Shell script to run the application

## Requirements

- Python 3.9+
- See `requirements.txt` for full list of dependencies