import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import geopandas as gpd
import os
import logging
import numpy as np

from interface import *
from sources import *
from indices import *
from areas import map_grid_cells_to_areas
from flood_threat import alert_on_flood_threat

logger = logging.getLogger(__name__)

MAP_PROJECTION = ccrs.PlateCarree()


class PlotNotifier(Notifier):
    IDENTIFIER = "plot-notifier"

    def notify(
        self, notify_raster: typing.Dict[HazardIndexIdentifier, RasterizedInformation]
    ):
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1, projection=MAP_PROJECTION)
        ax.set_extent(notify_raster["h-mhews-flood-risk-index"].extent.as_tuple)

        gdf = gpd.read_file(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "cadastre/gadm41_IDN_2.shp"
            )
        )

        # Plot Bandung outline.
        bandung = gdf[(gdf["NAME_2"] == "Bandung") & (gdf["TYPE_2"] == "Kabupaten")]
        bandung.geometry.boundary.plot(ax=ax)

        notify_raster["h-mhews-flood-risk-index"].plot(ax, cmap="Reds")
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.STATES)

    @property
    def responsible_extent(self) -> Extent:
        return Extent(-180, 180, -90, 90)

    @property
    def required_indices(self) -> typing.List[HazardIndexIdentifier]:
        return ["h-mhews-flood-risk-index"]


class ConsoleGridNotifier(Notifier):
    IDENTIFIER = "console-grid-notifier"

    def notify(
        self, notify_raster: typing.Dict[HazardIndexIdentifier, RasterizedInformation]
    ):
        THRESHOLD_VALUE = 32

        raster_gdf = notify_raster["h-mhews-flood-risk-index"].to_gdf()
        raster_gdf_filtered = raster_gdf[raster_gdf["value"] >= THRESHOLD_VALUE]

        if raster_gdf_filtered.empty:
            logger.info("ConsoleGridNotifier: No grid cells found.")
            return

        logger.info(
            f"ConsoleGridNotifier - Affected grid cells ({len(raster_gdf_filtered)}):"
        )
        for cell in raster_gdf_filtered.itertuples():
            coords = cell.geometry.exterior.coords
            logger.info(f"- Value: {cell.value:.2f}")
            logger.info(
                f"  ⌜{coords[0][0]:.2f}, {coords[0][1]:.2f} - {coords[1][0]:.2f}, {coords[1][1]:.2f}⌝"
            )
            logger.info(
                f"  ⌞{coords[3][0]:.2f}, {coords[3][1]:.2f} - {coords[2][0]:.2f}, {coords[2][1]:.2f}⌟"
            )

    @property
    def responsible_extent(self) -> Extent:
        return Extent(-180, 180, -90, 90)  # TODO(): What is this used for?

    @property
    def required_indices(self) -> typing.List[HazardIndexIdentifier]:
        return ["h-mhews-flood-risk-index"]


class ConsoleAreaNotifier(Notifier):
    IDENTIFIER = "console-area-notifier"

    def notify(
        self, notify_raster: typing.Dict[HazardIndexIdentifier, RasterizedInformation]
    ):
        THRESHOLD_VALUE = 32

        raster_gdf = notify_raster["h-mhews-flood-risk-index"].to_gdf()
        raster_gdf_filtered = raster_gdf[raster_gdf["value"] >= THRESHOLD_VALUE]
        areas_gdf = map_grid_cells_to_areas(raster_gdf_filtered)

        if areas_gdf.empty:
            logger.info("ConsoleAreaNotifier: No affected areas found.")
            return

        logger.info(f"ConsoleAreaNotifier - Affected areas ({len(areas_gdf)}):")
        # Currently printed at gadm level 3.
        sorted_areas = areas_gdf.sort_values(by="NAME_3")
        for row in sorted_areas.itertuples():
            logger.info(f"- {row.NAME_3}, GID: {row.GID_3}")

    @property
    def responsible_extent(self) -> Extent:
        return Extent(-180, 180, -90, 90)  # TODO(): What is this used for?

    @property
    def required_indices(self) -> typing.List[HazardIndexIdentifier]:
        return ["h-mhews-flood-risk-index"]


class AlertNotifier(Notifier):
    IDENTIFIER = "alert-notifier"
    
    def __init__(self, whatsapp_group_id=None, whatsapp_phone_number=None, telegram_chat_id=None, 
                 use_whatsapp=True, use_telegram=True, use_whatsapp_fallback_only=False, language='en'):
        self.whatsapp_group_id = whatsapp_group_id
        self.whatsapp_phone_number = whatsapp_phone_number
        self.telegram_chat_id = telegram_chat_id
        self.use_whatsapp = use_whatsapp
        self.use_telegram = use_telegram
        self.use_whatsapp_fallback_only = use_whatsapp_fallback_only
        self.language = language
        
    def notify(
        self, notify_raster: typing.Dict[HazardIndexIdentifier, RasterizedInformation]
    ):
        # Get the flood risk index raster
        risk_index_raster = notify_raster["h-mhews-flood-risk-index"]
        
        # Calculate average flood hazard index for the entire region
        # This is a simple approach - you might want to use a more sophisticated approach
        # such as max value or a weighted average based on population density
        average_index = float(np.nanmean(risk_index_raster.raster))
        
        # Scale the index to a 0-1 range if it's not already
        # Assuming the index is originally in range 0-100
        scaled_index = average_index / 100.0 if average_index > 1.0 else average_index
        
        # Send flood threat alert with the raster data for region information
        is_threat, alert_status = alert_on_flood_threat(
            scaled_index,
            whatsapp_group_id=self.whatsapp_group_id,
            whatsapp_phone_number=self.whatsapp_phone_number,
            telegram_chat_id=self.telegram_chat_id,
            should_notify=True,
            raster_data=risk_index_raster,
            use_whatsapp=self.use_whatsapp,
            use_telegram=self.use_telegram,
            use_whatsapp_fallback_only=self.use_whatsapp_fallback_only,
            language=self.language
        )
        
        if is_threat:
            logger.info(f"AlertNotifier: Flood threat detected! Alert sent with status: {alert_status}")
        else:
            logger.info(f"AlertNotifier: No flood threat detected. Index: {scaled_index:.2f}")

    @property
    def responsible_extent(self) -> Extent:
        return Extent(-180, 180, -90, 90)

    @property
    def required_indices(self) -> typing.List[HazardIndexIdentifier]:
        return ["h-mhews-flood-risk-index"]
