from utils import get_file_path

import geopandas as gpd


from sources import *


def map_grid_cells_to_areas(
    raster_gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Expects a GeoDataFrame containing raster-based grid cells and returns a
    GeoDataFrame containing polygons representing the affected areas.

    `raster_gdf` is assumed to be sparse, that is, the only grid cells contained
    are those for which an alert should be created (so threshold filtering of
    grid cells must happen before invoking this function).

    The returned administrative areas are "affected" and included in the output
    if they contain or are close to any grid cell.
    """
    level = 3  # gadm level. See cadastre/README.md.

    # Distance ensures that even beyond administrative boundaries, all regions
    # close to a flood hazard are included.
    # This magic value was obtained empirically (use of GIS software).
    neighbour_distance = 0.03  # 0.05 is okay for gadm level 2.

    gdf_adm = gpd.read_file(get_file_path(f"cadastre/gadm41_IDN_{level}_Java.shp"))

    gdf_affected_adm_areas = gpd.sjoin(
        gdf_adm,
        raster_gdf,
        how="inner",
        # For predicates, see: https://stackoverflow.com/a/69797992
        predicate="dwithin",  # Alternatively: "intersects" without `distance`.
        distance=neighbour_distance,
    )

    return gdf_affected_adm_areas.drop_duplicates(subset=[f"GID_{level}"])
