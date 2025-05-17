from dibi_hist_event_store import DIBIEventStore
from datetime import datetime
import numpy as np
from metrics import Metrics
import logging
from osgeo import gdal
import argparse

from sources import Extent, Resolution, BnpbInaRiskFloodRiskIndexSource, CHIRPSSource
from indices import HMHEWSHistoricalFloodHazardIndex
from notifiers import map_grid_cells_to_areas
from dibi_api_types import (
    ProvinceType,
    DisasterType,
    GADMLocationManager,
)
from utils import DateRange

logger = logging.getLogger(__name__)
args = None


gadm_location_manager = GADMLocationManager()


class DataSourceCache:
    def __init__(self):
        self.inarisk_flood_index = None
        self.chirps_by_date = {}


data_source_cache = DataSourceCache()


def compute_prediction(date: datetime, extent: Extent, resolution: Resolution, parameter_store: dict) -> set[str]:
    if data_source_cache.inarisk_flood_index is None:
        data_source_cache.inarisk_flood_index = (
            BnpbInaRiskFloodRiskIndexSource().fetch_data(extent, resolution)
        )

    if date not in data_source_cache.chirps_by_date:
        data_source_cache.chirps_by_date[date] = CHIRPSSource(date=date).fetch_data(
            extent, resolution
        )

    flood_prediction_raster = HMHEWSHistoricalFloodHazardIndex().calculate_index(
        {
            "bnpb-inarisk-flood-risk-index": data_source_cache.inarisk_flood_index,
            "chirps-historical-rain-data": data_source_cache.chirps_by_date[date],
        }
    )

    flood_prediction_raster_gdf = flood_prediction_raster.to_gdf()

    flood_prediction_raster_gdf_filtered = flood_prediction_raster_gdf[
        flood_prediction_raster_gdf["value"]
        >= parameter_store["hazard_index_threshold"]
    ]
    areas_gdf = map_grid_cells_to_areas(flood_prediction_raster_gdf_filtered)
    pred_events_on_date_gid2s = set(areas_gdf["GID_2"].tolist())
    return pred_events_on_date_gid2s


def main():
    set_up_logging()

    gdal.UseExceptions()

    ##### BEGIN: Backtesting configuration. #####
    angular_resolution = 0.05

    lat = np.array([-10.00, -4.75])
    lon = np.array([104.50, 120])

    extent = Extent(*lon, *lat).grow_extent(angular_resolution)
    del lon, lat

    resolution = Resolution(
        lon=extent.lon_res(angular_resolution),
        lat=extent.lat_res(angular_resolution),
    )

    date_range = DateRange(datetime(2022, 12, 26), datetime(2022, 12, 31))

    provinces = [
        ProvinceType.BANTEN,
        ProvinceType.BALI,
        ProvinceType.DKI_JAKARTA,
        ProvinceType.JAWA_BARAT,
        ProvinceType.JAWA_TENGAH,
        ProvinceType.JAWA_TIMUR,
        ProvinceType.DIY_YOGYAKARTA,
    ]

    # Stores the parameters used by the prediction pipeline, e.g., the hazard
    # index threshold.
    parameter_store = {
        "hazard_index_threshold": 6,
    }

    logger.info("Fetching historical flood data...")
    hist_event_store = DIBIEventStore(
        provinces=provinces,
        disaster_type=[DisasterType.FLOOD],
        year=[2022],  # TODO: Get year(s) dynamically from date_range.
    )
    ##### END: Backtesting configuration. #####

    logger.info(f"Number of historical flood events: {len(hist_event_store.events)}")
    logger.info("Computing districts to check...")

    gid2s_of_districts_to_check = (
        gadm_location_manager.get_all_district_gid2s_in_provinces(provinces)
    )
    logger.debug(f"Number of districts to check: {len(gid2s_of_districts_to_check)}")
    logger.debug(f"Districts to check: {gid2s_of_districts_to_check}")

    metrics = Metrics()

    logger.info(
        f"Predicting floods for date range: {date_range.start_date.date()} to {date_range.end_date_inclusive.date()}",
    )

    # Loop over date range.
    for date in date_range.date_range:
        logger.info(f"  Processing date: {date.date()}")

        pred_events_on_date_gid2s = compute_prediction(date, extent, resolution, parameter_store)
        hist_events_on_date_gid2s = hist_event_store.get_events_on_date_gid2s(date)

        logger.debug(
            f"Number of predicted events on date: {len(pred_events_on_date_gid2s)}"
        )
        logger.debug(
            f"Number of historical events on date: {len(hist_events_on_date_gid2s)}"
        )
        logger.debug(f"Predicted events on date: {pred_events_on_date_gid2s}")
        logger.debug(f"Historical events on date: {hist_events_on_date_gid2s}")

        for district_gid2 in gid2s_of_districts_to_check:
            # TODO: Use unions instead?
            if (
                district_gid2 in hist_events_on_date_gid2s
                and district_gid2 in pred_events_on_date_gid2s
            ):
                metrics.tp += 1
            elif district_gid2 in hist_events_on_date_gid2s:
                metrics.fn += 1
            elif district_gid2 in pred_events_on_date_gid2s:
                metrics.fp += 1
            else:
                metrics.tn += 1

    logger.info("Computing metrics...")
    logger.info(metrics)


def set_up_logging():
    logging.basicConfig(
        level=logging.getLevelName(get_args().logLevel),
        format="%(levelname)8s: %(message)s",
    )
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("requests_cache").setLevel(logging.WARNING)


def get_args():
    global args
    if args is None:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-l",
            "--log",
            dest="logLevel",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default="INFO",
            help="Set the logging level",
        )

        args = parser.parse_args()

    return args


if __name__ == "__main__":
    main()
