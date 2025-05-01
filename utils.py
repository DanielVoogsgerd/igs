import typing

from custom_types import Extent, Resolution
import numpy as np

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


def bounds_to_extent(bounds):
    return bounds[0], bounds[2], bounds[1], bounds[3]


def extent_to_bounds(extent):
    return extent[0], extent[2], extent[1], extent[3]


def grow_extent(extent: Extent, resolution: float):
    (lon_min, lon_max, lat_min, lat_max) = extent
    lat_min = np.floor(lat_min / resolution) * resolution
    lat_max = np.ceil(lat_max / resolution) * resolution

    lon_min = np.floor(lon_min / resolution) * resolution
    lon_max = np.ceil(lon_max / resolution) * resolution

    return (lon_min, lon_max, lat_min, lat_max)


def reproject_extent(src_extent, src_crs, dst_crs):
    src_lon_min, src_lon_max, src_lat_min, src_lat_max = src_extent

    dst_lon_min, dst_lat_min = dst_crs.transform_point(
        src_lon_min, src_lat_min, src_crs
    )

    dst_lon_max, dst_lat_max = dst_crs.transform_point(
        src_lon_max, src_lat_max, src_crs
    )

    return dst_lon_min, dst_lon_max, dst_lat_min, dst_lat_max


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

    pixel_width = (src_extent[1] - src_extent[0]) / src_data.shape[1]
    pixel_height = (src_extent[2] - src_extent[3]) / src_data.shape[0]
    src_ds.SetGeoTransform(
        [src_extent[0], pixel_width, 0, src_extent[3], 0, pixel_height]
    )

    dst_proj4_string = dst_crs.to_proj4()
    dst_srs = osr.SpatialReference()
    dst_srs.ImportFromProj4(dst_proj4_string)

    warped_ds = gdal.Warp(
        "",  # in-memory output
        src_ds,  # source dataset
        format="MEM",
        dstSRS=dst_srs,
        width=dst_resolution[1],
        height=dst_resolution[0],
        resampleAlg=resampling,
        outputBounds=extent_to_bounds(dst_extent),
        dstNodata=-9000,
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
