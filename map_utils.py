#!/usr/bin/env python
from datetime import datetime
import os
import sys

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import cartopy.feature as cfeature
import geopandas as gpd
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
import io


from sources import (NOAAGfsSource, CHIRPSSource, BnpbSource, BmkgSource)
from utils import grow_extent

def create_map_with_date(forecast_date, forecast_cycle, forecast_hours_ahead, 
                          historic_date, resolution_factor=0.05):


    # Set up the base map
    angular_resolution = resolution_factor

    lat = np.array([-10.00, -4.75])
    lon = np.array([104.50, 120])

    extent = grow_extent((*lon, *lat), angular_resolution)
    del lon, lat

    lon_res = int((extent[1] - extent[0]) // angular_resolution + 1)
    lat_res = int((extent[3] - extent[2]) // angular_resolution + 1)

    resolution = lat_res, lon_res
    
    # Create the figure and map
    map_projection = ccrs.PlateCarree()
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(1, 1, 1, projection=map_projection)
    ax.set_extent(extent)

    # Set title with the forecast and historic dates
    ax.set_title(f"Precipitation Forecast: {forecast_date} (Cycle: {forecast_cycle}, +{forecast_hours_ahead}h)\n" +
                 f"Historical Data: {historic_date.strftime('%Y-%m-%d')}")
    

    ax.add_feature(cfeature.COASTLINE)
    
    # Check if COUNTRIES is available, otherwise use BORDERS
    try:
        ax.add_feature(cfeature.COUNTRIES)
    except AttributeError:
        # Older versions of cartopy might not have COUNTRIES
        print("COUNTRIES feature not found, using BORDERS instead")
        ax.add_feature(cfeature.BORDERS)
    
    # Add Indonesian regions
    try:
        gdf = gpd.read_file(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "cadastre/gadm41_IDN_2.shp"
            )
        )
        bandung = gdf[(gdf["NAME_2"] == "Bandung") & (gdf["TYPE_2"] == "Kabupaten")]
        bandung.geometry.boundary.plot(ax=ax, color='darkgreen', linewidth=2)
    except Exception as e:
        print(f"Could not load region data: {e}")
    
    # Add NOAA GFS precipitation forecast
    try:
        precipitation_factory = NOAAGfsSource(forecast_date, forecast_cycle, forecast_hours_ahead, "apcpsfc")
        data = precipitation_factory.data_for_domain(extent, resolution)
        forecast = ax.imshow(
            data,
            extent=extent,
            cmap="Blues",
            alpha=0.7,
            transform=ccrs.PlateCarree()
        )
        plt.colorbar(forecast, ax=ax, orientation='vertical', label='Forecast Precipitation')
    except Exception as e:
        print(f"Could not load forecast data: {e}")
    
    # Add CHIRPS historical precipitation
    try:
        hist_precipitation_factory = CHIRPSSource(date=historic_date)
        data = hist_precipitation_factory.data_for_domain(extent, resolution)
        historic = ax.imshow(
            data,
            extent=extent,
            cmap="Greens",
            alpha=0.4,
            transform=ccrs.PlateCarree()
        )
        plt.colorbar(historic, ax=ax, orientation='vertical', label='Historic Precipitation')
    except Exception as e:
        print(f"Could not load historic data: {e}")
    
    # Add a pin for Bandung
    ax.plot([107.6292202], [-6.9934492], color="red", marker="v", 
            markersize=10, transform=ccrs.PlateCarree())
    ax.text(107.7, -6.9, "Bandung", transform=ccrs.PlateCarree(), 
            fontsize=12, color='red')
    
    return fig

def get_map_as_bytes(fig):
    """Convert a matplotlib figure to bytes for Streamlit display"""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    return buf