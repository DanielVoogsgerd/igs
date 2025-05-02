#!/usr/bin/env python
import streamlit as st
from datetime import datetime, timedelta
import matplotlib
import sys
import os

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

matplotlib.use('Agg')  # Use Agg backend to avoid issues wiZZth streamlit

from map_utils import create_map_with_date

# Page configuration
st.set_page_config(
    page_title="Indonesia GIS Precipitation Forecast",
    page_icon="🌧️",
    layout="wide",
)

# Header
st.title("Indonesia GIS Precipitation Forecast")
st.markdown("""
This tool allows you to visualize precipitation forecasts and historical data for Indonesia, 
with a focus on the Bandung region. Select different dates to see the forecast and historical data.
""")

# Sidebar with date inputs
st.sidebar.header("Configure Map")

today = datetime.now()
default_forecast_date = today.strftime("%Y%m%d")

# Forecast date input
st.sidebar.subheader("Forecast Settings")
forecast_date = st.sidebar.date_input(
    "Select Forecast Date",
    value=today,
    min_value=today - timedelta(days=30),  # Allow some past dates for testing
    max_value=today + timedelta(days=365),
    help="The date for which you want to see the forecast"
)

# Convert to string format for NOAA GFS
forecast_date_str = forecast_date.strftime("%Y%m%d")

# Forecast cycle selector
cycle_options = ["00", "06", "12", "18"]
forecast_cycle = st.sidebar.selectbox(
    "Forecast Cycle",
    options=cycle_options,
    index=0,
    help="The forecast cycle hour (00, 06, 12, 18)"
)

# Hours ahead selector
hours_ahead_options = [3, 6, 12, 24, 48, 72]
forecast_hours_ahead = st.sidebar.selectbox(
    "Hours Ahead",
    options=hours_ahead_options,
    index=2,
    help="How many hours ahead to forecast"
)

# Historical date input
st.sidebar.subheader("Historical Data Settings")
historic_date = st.sidebar.date_input(
    "Select Historical Date",
    value=today - timedelta(days=365),  # Default to 1 year ago
    min_value=datetime(2000, 1, 1),  # CHIRPS data goes back to around 1981
    max_value=today - timedelta(days=30),  # Historical data typically has lag
    help="The date for which you want to see historical precipitation data"
)

# Convert to datetime object for CHIRPSSource
historic_datetime = datetime.combine(historic_date, datetime.min.time())


st.sidebar.subheader("Advanced Settings")
resolution_factor = st.sidebar.slider(
    "Map Resolution",
    min_value=0.01,
    max_value=0.2,
    value=0.05,
    step=0.01,
    help="Lower values give higher resolution but slower performance"
)

# Generate button
if st.sidebar.button("Generate Map", type="primary"):
    with st.spinner("Generating map visualization..."):
        try:

            fig = create_map_with_date(
                forecast_date_str,
                forecast_cycle,
                forecast_hours_ahead,
                historic_datetime,
                resolution_factor
            )
            
            # Display the map
            st.pyplot(fig)
            
            # Display additional information
            st.subheader("Map Details")
            st.markdown(f"""
            - **Forecast Date**: {forecast_date.strftime('%Y-%m-%d')}
            - **Forecast Cycle**: {forecast_cycle}:00 UTC
            - **Forecast Hours Ahead**: +{forecast_hours_ahead}h
            - **Historical Date**: {historic_date.strftime('%Y-%m-%d')}
            - **Map Resolution**: {resolution_factor} degrees
            """)
            
        except Exception as e:
            st.error(f"Error generating map: {str(e)}")
            st.error("Please try a different date or settings.")

# Information about the data sources
st.sidebar.markdown("---")
st.sidebar.subheader("Data Sources")
st.sidebar.markdown("""
- **Forecast Data**: NOAA GFS
- **Historical Data**: CHIRPS
- **Regional Boundaries**: GADM
""")

# Instructions for first-time use
if 'map_generated' not in st.session_state:
    st.session_state.map_generated = False
    st.info(" Select your parameters in the sidebar and click 'Generate Map' to begin!")