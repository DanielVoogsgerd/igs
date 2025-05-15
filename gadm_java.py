#!/usr/env/python
from utils import get_file_path
import geopandas as gpd


# For more details see `cadastre/README.md`.
def main():
    level = 2  # gadm level. See above.
    gdf_adm = gpd.read_file(get_file_path(f"cadastre/gadm41_IDN_{level}.shp"))

    # Using Google Maps' definition of Java: https://maps.app.goo.gl/FmuEA5rMc6BM7XpFA.
    # Note: Some parts are but should not be included (e.g., Pulau Madura).
    java_regions = [
        "Banten",
        "Jakarta Raya",
        "Jawa Barat",
        "Jawa Tengah",
        "Jawa Timur",
        "Yogyakarta",
    ]
    gdf_adm_java = gdf_adm[gdf_adm["NAME_1"].isin(java_regions)]

    gdf_adm_java.to_file(get_file_path(f"cadastre/gadm41_IDN_{level}_Java.shp"))


if __name__ == "__main__":
    main()
