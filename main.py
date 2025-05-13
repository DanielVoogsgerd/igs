#!/usr/env/python
from datetime import timedelta

import cartopy.feature as cfeature
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import geopandas as gpd
import os

import requests_cache
import numpy as np

from sources import *
from utils import grow_extent
from interface import *

SESSION = requests_cache.CachedSession(
    "demo_cache",
    use_cache_dir=True,  # Save files in the default user cache dir
    cache_control=False,  # Use Cache-Control response headers for expiration, if available
    expire_after=timedelta(days=7),  # Otherwise expire responses after one day
    allowable_codes=[
        200,
    ],
    allowable_methods=["GET", "POST"],  # Cache whatever HTTP methods you want
    stale_if_error=True,  # In case of request errors, use stale cache data if possible
)

RESOLUTION = 2**10
PLATE_CARREE_EPSG = 32662


def main():
    # angular_resolution = 0.01  # pretty, but slow
    angular_resolution = 0.05

    lat = np.array([-10.00, -4.75])
    lon = np.array([104.50, 120])

    extent = grow_extent((*lon, *lat), angular_resolution)
    small_extent = (108, 115, -8, -6)  # for debugging purposes
    del lon, lat

    print("Map extent: ", extent)

    lon_res = int((extent[1] - extent[0]) // angular_resolution + 1)
    lat_res = int((extent[3] - extent[2]) // angular_resolution + 1)

    resolution = lat_res, lon_res
    print("Map resolution", resolution)

    map_projection = ccrs.PlateCarree()

    precipitation_factory = NOAAGfsSource("20250513", "00", 12, "apcpsfc")
    rain_data = precipitation_factory.fetch_data(extent, resolution)

    flood_risk_data = rain_data  # Temporary as Bnpb (InaRisk) is down
    # flood_image_factory = BnpbSource("INDEKS_BAHAYA_BANJIR")
    # flood_risk_data = flood_image_factory.fetch_data(extent, resolution)

    flood_hazard_index = 0.2 * flood_risk_data * 20 * rain_data * 0.8

    print(type(flood_hazard_index))
    print(np.max(flood_hazard_index))

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, projection=map_projection)
    # ax.set_extent((-180, 180, -90, 90))
    ax.set_extent(extent)

    gdf = gpd.read_file(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "cadastre/gadm41_IDN_2.shp"
        )
    )
    gdf = gpd.read_file(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "cadastre/gadm41_IDN_2.shp"
        )
    )

    bandung = gdf[(gdf["NAME_2"] == "Bandung") & (gdf["TYPE_2"] == "Kabupaten")]
    bandung.geometry.boundary.plot(ax=ax)
    bandung = gdf[(gdf["NAME_2"] == "Bandung") & (gdf["TYPE_2"] == "Kabupaten")]
    bandung.geometry.boundary.plot(ax=ax)

    flood_hazard_index.plot(ax, cmap="Reds")
    rain_data.plot(ax, cmap="Reds")
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.STATES)

    plt.show()


if __name__ == "__main__":
    main()
