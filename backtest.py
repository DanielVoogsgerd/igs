#!/usr/env/python
from datetime import timedelta, date, datetime

import cartopy.feature as cfeature
from tqdm import tqdm
import geopandas as gpd

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from pyproj import Transformer
from matplotlib import figure

import requests_cache
import numpy as np

from sources import *
from utils import grow_extent


import typing


def create_colormap(name: str, pairs: typing.Sequence[typing.Tuple[str, float]]):
    """Create colormap from pairs of colors and values"""
    import matplotlib

    cvals = [0, 0.5, 1]
    colors = ["white", "yellow", "red"]

    norm = plt.Normalize(min(cvals), max(cvals))
    tuples = list(zip(map(norm, cvals), colors))

    return matplotlib.colors.LinearSegmentedColormap.from_list(name, tuples)


RISK_CMAP = create_colormap("risk", [("white", 0), ("yellow", 0.5), ("red", 1)])
PRECIPITATION_CMAP = "Blues"


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

DEFAULT_MAP_PROJECTION = ccrs.PlateCarree()

DEFAULT_MAP_FEATURES = [cfeature.COASTLINE, cfeature.STATES]


def main():
    # angular_resolution = 0.01  # pretty, but slow
    angular_resolution = 0.05

    lat = np.array([-10.00, -4.75])
    lon = np.array([104.50, 120])

    extent = grow_extent((*lon, *lat), angular_resolution)
    small_extent = (108, 115, -8, -6)  # for debugging purposes
    del lon, lat

    lon_res = int((extent[1] - extent[0]) // angular_resolution + 1)
    lat_res = int((extent[3] - extent[2]) // angular_resolution + 1)

    resolution = lat_res, lon_res

    # calculate_prediction_inaware_score(extent, resolution, date.today())
    # calculate_historic_inaware_score(extent, resolution, date.today())
    lat = -6.9842310
    lon = 107.6230921
    # historic_for_coordinate(lat, lon, angular_resolution)
    dates, data = historic_run(
        extent, [datetime(2024, 1, 1), datetime(2024, 2, 1)], angular_resolution
    )

    print(np.max(data.reshape(np.size(data))))
    plt.show()


def plot_extent(
    fig: figure.Figure,
    ax,
    data: np.ndarray,
    extent: Extent,
    title: str,
    features: typing.Optional[typing.Sequence[cfeature.Feature]] = None,
    cmap=None,
    color_bar_label: typing.Optional[str] = None,
    plot_kwargs: typing.Optional[typing.Dict[str, typing.Any]] = None,
):
    plot_kwargs = plot_kwargs if plot_kwargs is not None else {}
    ax.add_feature(cfeature.COASTLINE)
    ax.set_extent(extent)

    ax.set_title(title)
    x = ax.imshow(data, extent=extent, cmap=cmap, **plot_kwargs)

    if color_bar_label is not None:
        fig.colorbar(x, label=color_bar_label)


def historic_run(
    extent: Extent,
    date_range: typing.Tuple[datetime, datetime],
    angular_resolution: float,
):
    lon_res = int((extent[1] - extent[0]) // angular_resolution + 1)
    lat_res = int((extent[3] - extent[2]) // angular_resolution + 1)

    resolution = lat_res, lon_res

    dates = []
    date = date_range[0]
    dates.append(date)
    while date < date_range[1]:
        date += timedelta(days=1)
        dates.append(date)

    scores = np.empty((*resolution, len(dates)))
    for i, date in tqdm(enumerate(dates)):
        scores[:, :, i] = calculate_historic_inaware_score(extent, resolution, date)

    return dates, scores


def historic_for_coordinate(lat, lon, angular_resolution):
    import matplotlib.dates

    datefmt = matplotlib.dates.DateFormatter("%d-%b-%Y")
    fmt = lambda x, y: "{}, {:.5g}".format(datefmt(x), y)

    fig, ax = plt.subplots()

    ax.format_coord = fmt
    datefmt = matplotlib.dates.DateFormatter("%Y-%m-%d")
    surrounding_pixels = 3

    lat_min = lat - surrounding_pixels * angular_resolution
    lat_max = lat + surrounding_pixels * angular_resolution
    lon_min = lon - surrounding_pixels * angular_resolution
    lon_max = lon + surrounding_pixels * angular_resolution

    extent = (lon_min, lon_max, lat_min, lat_max)

    lon_res = int((extent[1] - extent[0]) // angular_resolution + 1)
    lat_res = int((extent[3] - extent[2]) // angular_resolution + 1)

    resolution = lat_res, lon_res

    dates = []
    date = datetime(2024, 1, 1)
    dates.append(date)
    while date < datetime(2025, 1, 1):
        date += timedelta(days=1)
        dates.append(date)

    scores = [
        np.max(calculate_historic_inaware_score(extent, resolution, date))
        for date in dates
    ]
    ulim = max(15, np.max(scores))
    plt.hlines(8, datetime(2024, 1, 1), datetime(2024, 12, 31))
    plt.hlines(11, datetime(2024, 1, 1), datetime(2024, 12, 31))
    plt.hlines(15, datetime(2024, 1, 1), datetime(2024, 12, 31))
    ax.fill_between(dates, 0, 8, facecolor="green", alpha=0.5)
    ax.fill_between(dates, 8, 11, facecolor="yellow", alpha=0.5)
    ax.fill_between(dates, 11, ulim, facecolor="red", alpha=0.5)
    plt.vlines(
        [datetime(2024, 11, 24), datetime(2024, 12, 6)],
        0,
        ulim,
        linestyles="--",
        colors="k",
    )

    ax.set_xlim(min(dates), max(dates))
    ax.set_ylim(0, ulim)

    ax.plot(dates, scores)


def calculate_historic_inaware_score(
    extent: Extent, resolution: Resolution, date: date
):
    flood_image_factory = BnpbSource("INDEKS_BAHAYA_BANJIR")
    precipitation_factory = CHIRPSSource(date=date)

    risk = flood_image_factory.data_for_domain(extent, resolution)
    precipitation = precipitation_factory.data_for_domain(extent, resolution) / 8
    flood_hazard_index = 0.2 * risk * 20 * precipitation * 0.8

    return flood_hazard_index

    # fig = plt.figure()
    #
    # ax = fig.add_subplot(1, 1, 1, projection=DEFAULT_MAP_PROJECTION)
    #
    # plot_extent(
    #     fig,
    #     ax,
    #     flood_hazard_index,
    #     extent,
    #     "Flood hazard index",
    #     features=DEFAULT_MAP_FEATURES,
    #     cmap=RISK_CMAP,
    #     color_bar_label="index",
    # )


def calculate_prediction_inaware_score(
    extent: Extent, resolution: Resolution, date: date
):
    flood_image_factory = BnpbSource("INDEKS_BAHAYA_BANJIR")
    precipitation_factory = NOAAGfsSource(date.strftime("%Y%m%d"), "00", 3, "apcpsfc")

    risk = flood_image_factory.data_for_domain(extent, resolution)
    precipitation = precipitation_factory.data_for_domain(extent, resolution)
    flood_hazard_index = 0.2 * risk * 20 * precipitation * 0.8

    fig = plt.figure()

    ax = fig.add_subplot(3, 1, 1, projection=DEFAULT_MAP_PROJECTION)
    plot_extent(
        fig,
        ax,
        risk,
        extent,
        "inaRISK index",
        features=DEFAULT_MAP_FEATURES,
        cmap=RISK_CMAP,
        color_bar_label="index",
    )

    ax = fig.add_subplot(3, 1, 2, projection=DEFAULT_MAP_PROJECTION)
    plot_extent(
        fig,
        ax,
        precipitation,
        extent,
        "Predicted precipitation (next three hours)",
        features=DEFAULT_MAP_FEATURES,
        cmap=PRECIPITATION_CMAP,
        color_bar_label="mm/3h",
    )

    ax = fig.add_subplot(3, 1, 3, projection=DEFAULT_MAP_PROJECTION)
    plot_extent(
        fig,
        ax,
        flood_hazard_index,
        extent,
        "Flood hazard index",
        features=DEFAULT_MAP_FEATURES,
        cmap=RISK_CMAP,
        color_bar_label="index",
        plot_kwargs={"vmin": 0, "vmax": 15},
    )


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
