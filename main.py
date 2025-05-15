#!/usr/env/python
from datetime import timedelta
import logging

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from osgeo import gdal

import requests_cache
import numpy as np

from interface import *
from sources import *
from indices import *
from notifiers import *

logger = logging.getLogger(__name__)

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
MAP_PROJECTION = ccrs.PlateCarree()


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)8s: %(message)s")
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("requests_cache").setLevel(logging.WARNING)

    gdal.UseExceptions()

    # angular_resolution = 0.01  # pretty, but slow
    angular_resolution = 0.05

    lat = np.array([-10.00, -4.75])
    lon = np.array([104.50, 120])

    extent = Extent(*lon, *lat).grow_extent(angular_resolution)
    del lon, lat

    logger.debug(f"Map extent: {extent}")

    lon_res = int((extent.lon_max - extent.lon_min) // angular_resolution + 1)
    lat_res = int((extent.lat_max - extent.lat_min) // angular_resolution + 1)

    resolution = lat_res, lon_res
    logger.debug(f"Map resolution: {resolution}")

    logger.info("Setting up registry")
    registry = Registry()
    registry.register_source(NOAAGfsSource("20250513", "00", 12, "apcpsfc"))
    registry.register_source(BnpbInaRiskFloodRiskIndexSource())
    registry.register_source(BnpbInaRiskFlashFloodRiskIndexSource())

    registry.register_hazard_index(InAWAREHazardIndex())

    registry.register_notifier(PlotNotifier())
    registry.register_notifier(ConsoleAreaNotifier())

    registry.run(extent, resolution)

    plt.show()


if __name__ == "__main__":
    main()
