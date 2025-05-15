import typing
import os

import numpy as np

from interface import Resolution, Extent
from pyproj import CRS
from osgeo import gdal, osr
import cartopy.crs as ccrs


def _zoom_to_pixel_size(zoom: int, lat: float):
    """Converts a Google WTS zoom level to a pixel size

    Source: https://wiki.openstreetmap.org/wiki/Zoom_levels
    """
    import math

    circumference = ccrs.WGS84_SEMIMAJOR_AXIS * 2 * math.pi
    pixel_size = circumference * math.cos(lat / 180 * math.pi) / (2 ** (zoom + 8))

    return pixel_size


def get_bbox(lat, lon) -> str:
    return f"{lat[0]:.6f},{lon[0]:.6f},{lat[1]:.6f},{lon[1]:.6f}"


def get_bbox_xy(x: typing.Tuple[float, float], y: typing.Tuple[float, float]) -> str:
    return f"{x[0]:.6f},{y[0]:.6f},{x[1]:.6f},{y[1]:.6f}"


def reproject_gdal(
    src_data: np.ndarray,
    src_crs: CRS,
    src_extent: Extent,
    dst_resolution: Resolution,
    dst_crs: CRS,
    dst_extent: Extent,
    resampling: str,
):
    assert src_data.dtype == np.float32

    driver = gdal.GetDriverByName("MEM")
    src_ds = driver.Create(
        "", src_data.shape[1], src_data.shape[0], 1, gdal.GDT_Float32
    )
    src_ds.GetRasterBand(1).WriteArray(src_data)

    # Define spatial reference and geo-transform

    src_srs = osr.SpatialReference()
    src_srs.ImportFromProj4(src_crs.to_proj4())
    src_ds.SetProjection(src_srs.ExportToWkt())

    xn, yn = src_data.shape
    src_resolution = Resolution(lon=yn, lat=xn)

    pixel_width, pixel_height = src_extent.pixel_size(src_resolution)

    src_ds.SetGeoTransform(
        [src_extent.lon_min, pixel_width, 0, src_extent.lat_max, 0, -pixel_height]
    )

    dst_proj4_string = dst_crs.to_proj4()
    dst_srs = osr.SpatialReference()
    dst_srs.ImportFromProj4(dst_proj4_string)

    warped_ds = gdal.Warp(
        "",  # in-memory output
        src_ds,  # source dataset
        format="MEM",
        dstSRS=dst_srs,
        width=dst_resolution.lon,
        height=dst_resolution.lat,
        resampleAlg=resampling,
        outputBounds=dst_extent.bounds,
        dstNodata=np.nan,
        outputBoundsSRS=dst_srs,
    )

    warped_array = warped_ds.GetRasterBand(1).ReadAsArray()

    return warped_array


def tile_to_mercator(x_tile: int, y_tile: int, zoom: int):
    """Maps the WTS x, y, z coordinates to lat, lon in EPSG:4326

    Source: https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
    """
    from math import atan, pi, sinh

    n = 2**zoom

    lon = x_tile * 360 / n - 180
    lat = atan(sinh(pi * (1 - 2 * y_tile / n))) * 180 / pi

    return lon, lat


def get_file_path(filename):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)
