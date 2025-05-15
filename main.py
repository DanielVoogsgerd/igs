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
MAP_PROJECTION = ccrs.PlateCarree()


def main():
    # angular_resolution = 0.01  # pretty, but slow
    angular_resolution = 0.05

    lat = np.array([-10.00, -4.75])
    lon = np.array([104.50, 120])

    extent = Extent(*lon, *lat).grow_extent(angular_resolution)
    del lon, lat

    print("Map extent: ", extent)

    lon_res = int((extent.lon_max - extent.lon_min) // angular_resolution + 1)
    lat_res = int((extent.lat_max - extent.lat_min) // angular_resolution + 1)

    resolution = lat_res, lon_res
    print("Map resolution", resolution)

    registry = Registry()
    registry.register_source(NOAAGfsSource("20250513", "00", 12, "apcpsfc"))
    registry.register_source(BnpbSource("INDEKS_BAHAYA_BANJIR"))

    hazard_index = InAWAREHazardIndex()

    # TODO: Link the

    plt.show()


class InAWAREHazardIndex(HazardIndex):
    def calculate_index(
        self, rasters: typing.Dict[SourceIdentifier, IdentifiedRasterizedInformation]
    ) -> RasterizedInformation:
        return (
            rasters["inarisk-flood-risk-index"] * 0.2 * 20
            + rasters["rain-data-today"] * 0.8
        )

    @property
    def required_sources(self) -> typing.List[SourceIdentifier]:
        return ["rain-data-today", "inarisk-flood-risk-index"]


class PlotNotifier(Notifier):
    def notify(self, notify_raster: RasterizedInformation):
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1, projection=MAP_PROJECTION)
        ax.set_extent(notify_raster.extent)

        gdf = gpd.read_file(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "cadastre/gadm41_IDN_2.shp"
            )
        )

        bandung = gdf[(gdf["NAME_2"] == "Bandung") & (gdf["TYPE_2"] == "Kabupaten")]
        bandung.geometry.boundary.plot(ax=ax)

        notify_raster.plot(ax, cmap="Reds")
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.STATES)

    @property
    def responsible_extent(self) -> Extent:
        return Extent(-180, 180, -90, 90)


if __name__ == "__main__":
    main()
