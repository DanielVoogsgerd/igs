import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import geopandas as gpd
import os


from interface import *
from sources import *
from indices import *
from areas import map_grid_cells_to_areas

MAP_PROJECTION = ccrs.PlateCarree()


class PlotNotifier(Notifier):
    def notify(
        self, notify_raster: typing.Dict[HazardIndexIdentifier, RasterizedInformation]
    ):
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1, projection=MAP_PROJECTION)
        ax.set_extent(notify_raster["inaware-flood-risk-index"].extent.as_tuple)

        gdf = gpd.read_file(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "cadastre/gadm41_IDN_2.shp"
            )
        )

        # Plot Bandung outline.
        bandung = gdf[(gdf["NAME_2"] == "Bandung") & (gdf["TYPE_2"] == "Kabupaten")]
        bandung.geometry.boundary.plot(ax=ax)

        notify_raster["inaware-flood-risk-index"].plot(ax, cmap="Reds")
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.STATES)

    @property
    def responsible_extent(self) -> Extent:
        return Extent(-180, 180, -90, 90)

    @property
    def required_indices(self) -> typing.List[HazardIndexIdentifier]:
        return ["inaware-flood-risk-index"]


class ConsoleAreaNotifier(Notifier):
    def notify(
        self, notify_raster: typing.Dict[HazardIndexIdentifier, RasterizedInformation]
    ):
        THRESHOLD_VALUE = 32

        raster_gdf = notify_raster["inaware-flood-risk-index"].to_gdf()
        raster_gdf_filtered = raster_gdf[raster_gdf["value"] >= THRESHOLD_VALUE]
        areas_gdf = map_grid_cells_to_areas(raster_gdf_filtered)

        if areas_gdf.empty:
            print("No affected areas found.")
            return

        print(f"Affected areas ({len(areas_gdf)}):")
        # Currently printed at gadm level 3.
        sorted_areas = areas_gdf.sort_values(by="NAME_3")
        for row in sorted_areas.itertuples():
            print(f"- {row.NAME_3}, GID: {row.GID_3}")

    @property
    def responsible_extent(self) -> Extent:
        return Extent(-180, 180, -90, 90)  # TODO(): What is this used for?

    @property
    def required_indices(self) -> typing.List[HazardIndexIdentifier]:
        return ["inaware-flood-risk-index"]
