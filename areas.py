#!/usr/env/python
from datetime import datetime
from utils import get_file_path

import geopandas as gpd

import numpy as np

from sources import *
from utils import grow_extent
from shapely.geometry import Polygon

from notification import ConsoleNotificationBackend
from custom_types import Extent


def array_to_gdf(
    data: np.ndarray,
    extent: Extent,
) -> gpd.GeoDataFrame:
    lon_min, lon_max, lat_min, lat_max = extent
    yn, xn = data.shape

    pixel_width = (lon_max - lon_min) / xn
    pixel_height = (lat_max - lat_min) / yn
    assert pixel_width > 0
    assert pixel_height > 0

    polygons, values = [], []

    for y in range(yn):
        for x in range(xn):
            x0 = lon_min + x * pixel_width
            y0 = lat_max - (y + 1) * pixel_height
            x1 = x0 + pixel_width
            y1 = y0 + pixel_height

            polygons.append(
                Polygon(
                    [
                        (x0, y0),  # Lower left
                        (x1, y0),  # Lower right
                        (x1, y1),  # Upper right
                        (x0, y1),  # Upper left
                        (x0, y0),  # Close the polygon
                    ]
                )
            )
            values.append(data[y, x])

    gdf = gpd.GeoDataFrame({"value": values, "geometry": polygons}, crs=f"EPSG:4326")

    return gdf


def get_affected_areas(
    hazard_squares: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    level = 3  # gadm level. See cadastre/README.md.
    # Distance ensures that even beyond administrative boundaries, all regions
    # close to a flood hazard are included.
    neighbour_distance = 0.03  # 0.05 is okay for gadm level 2.

    gdf_adm = gpd.read_file(get_file_path(f"cadastre/gadm41_IDN_{level}_Java.shp"))

    gdf_affected_adm_areas = gpd.sjoin(
        gdf_adm,
        hazard_squares,
        how="inner",
        # For predicates, see: https://stackoverflow.com/a/69797992
        predicate="dwithin",  # Alternatively: "intersects" without `distance`.
        distance=neighbour_distance,
    )

    uniq_gdf = gdf_affected_adm_areas.drop_duplicates(subset=[f"GID_{level}"])

    return uniq_gdf


def main():
    angular_resolution = 0.05
    lat = np.array([-10.00, -4.75])
    lon = np.array([104.50, 120])

    extent = grow_extent((*lon, *lat), angular_resolution)

    lon_res = int((extent[1] - extent[0]) // angular_resolution + 1)
    lat_res = int((extent[3] - extent[2]) // angular_resolution + 1)

    resolution = lat_res, lon_res

    # Get data
    hist_precipitation_factory = CHIRPSSource(date=datetime.datetime(2024, 1, 1))
    data = hist_precipitation_factory.data_for_domain(extent, resolution)

    gdf = array_to_gdf(data, extent)
    # gdf.to_file(f"points/points_no_threshold.shp")

    threshold = 32
    gdf_filtered = gdf[gdf["value"] > threshold]
    # gdf_filtered.to_file(f"points/points_gt_{threshold}.shp")

    affected_areas = get_affected_areas(gdf_filtered)
    # affected_areas.to_file("points/points_affected-IDN3-Java-005.shp")

    ConsoleNotificationBackend().notify(affected_areas)


if __name__ == "__main__":
    main()
