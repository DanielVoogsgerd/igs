#!/usr/env/python
from datetime import timedelta, datetime
import os

import cartopy.feature as cfeature
import geopandas as gpd

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from pyproj import Transformer

import requests_cache
import numpy as np

from sources import *
from utils import grow_extent

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

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, projection=map_projection)
    ax.set_extent(extent)

    ax.set_title("Data (using data_for_domain)")
    ax.add_feature(cfeature.COASTLINE)

    # FIXME: write this geometry to somewhere or make this file available somehow
    gdf = gpd.read_file(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "cadastre/gadm41_IDN_2.shp"
        )
    )
    bandung = gdf[(gdf["NAME_2"] == "Bandung") & (gdf["TYPE_2"] == "Kabupaten")]
    bandung.geometry.boundary.plot(ax=ax)

    # NOTE: -- PRECIPITATION (prediction)
    precipitation_factory = NOAAGfsSource("20250429", "00", 12, "apcpsfc")
    data = precipitation_factory.data_for_domain(extent, resolution)
    ax.imshow(
        data,
        extent=extent,
        cmap="Blues",
        alpha=1,
    )

    # NOTE: -- PRECIPITATION (historic)
    hist_precipitation_factory = CHIRPSSource(date=datetime.datetime(2024, 1, 1))
    data = hist_precipitation_factory.data_for_domain(extent, resolution)
    ax.imshow(
        data,
        extent=extent,
        cmap="Greens",
        alpha=0.4,
    )

    # NOTE: -- FLOOD RISK
    flood_image_factory = BnpbSource("INDEKS_BAHAYA_BANJIR")
    # data = flood_image_factory.data_for_domain(extent, resolution)
    # ax.imshow(
    #     data,
    #     extent=extent,
    #     cmap="Reds",
    #     alpha=0.4,
    # )
    #
    # NOTE: -- FLASH FLOOD RISK
    flash_flood_image_factory = BnpbSource("INDEKS_BAHAYA_BANJIRBANDANG")
    # data = flash_flood_image_factory.data_for_domain(extent, resolution)
    # ax.imshow(
    #     data,
    #     extent=extent,
    #     cmap="Greens",
    #     alpha=0.4,
    # )

    # NOTE: -- RAIN, work in progress, quite useless right now
    bmkg_image_factory = BmkgSource()
    # data = bmkg_image_factory.data_for_domain(extent, resolution, "bilinear")
    # ax.imshow(
    #     data,
    #     extent=extent,
    #     cmap="Greens",
    #     alpha=1,
    # )

    plot_map_cartopy((extent[2], extent[3]), (extent[0], extent[1]))

    plt.show()


def plot_map(lat, lon):
    lat_0 = (lat[1] + lat[0]) / 2
    lon_0 = (lon[1] + lon[0]) / 2

    fig = plt.figure()
    ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])

    m = Basemap(
        llcrnrlon=lon[0],
        llcrnrlat=lat[0],
        urcrnrlon=lon[1],
        urcrnrlat=lat[1],
        lat_1=lat[0],
        lat_2=lat[1],
        lon_1=lon[0],
        lon_2=lon[1],
        lat_0=lat_0,
        lon_0=lon_0,
        rsphere=(6378137.00, 6356752.3142),
        resolution="l",
        area_thresh=1000.0,
        projection="cyl",
        ax=ax,
    )

    m.drawcoastlines()
    m.drawcountries()

    i = get_gis_data_rain(lat, lon)
    m.imshow(
        i,
        extent=(lon[0], lon[1], lat[0], lat[1]),
        origin="upper",
        interpolation="nearest",
    )
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3395", always_xy=True)
    x, y = transformer.transform(lon, lat)

    # Placing pin in target region
    mlat, mlon = -6.9934492, 107.6292202
    plt.plot([mlon], [mlat], color="red", marker="v", ms=20)


def plot_map_cartopy(lat, lon):
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.set_title("map_cartopy")
    extent = [lon[0], lon[1], lat[0], lat[1]]
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    flood_image_factory = BnpbSource("INDEKS_BAHAYA_BANJIR")  # Flood
    flash_flood_image_factory = BnpbSource("INDEKS_BAHAYA_BANJIRBANDANG")  # Flash flood
    precipitation_image_factory = NOAAGfsSource("20250429", "00", 12, "apcpsfc")
    indo_precipitation_image_factory = BmkgSource()

    # ax.add_feature(cfeature.LAND)
    # ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.STATES)
    # ax.add_feature(cfeature.BORDERS, linestyle=":")
    # ax.add_feature(cfeature.LAKES, alpha=0.5)
    # ax.add_feature(cfeature.RIVERS)

    gdf = gpd.read_file("cadastre/gadm41_IDN_2.shp")
    bandung = gdf[(gdf["NAME_2"] == "Bandung") & (gdf["TYPE_2"] == "Kabupaten")]

    # ax.add_geometries(bandung.geometry, crs=gdf.crs)

    bandung.geometry.boundary.plot(ax=ax)

    ax.add_image(precipitation_image_factory, 5, cmap="Blues")
    # ax.add_image(indo_precipitation_image_factory, 5, cmap="Blues")

    # Project image
    # transformer = Transformer.from_crs("EPSG:4326", "EPSG:3395", always_xy=True)
    # x, y = transformer.transform(lon, lat)
    # i = get_gis_data_rain(lat, lon)
    # ax.imshow(i, extent=[*lon, *lat], origin="upper")


if __name__ == "__main__":
    main()
