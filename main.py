#!/usr/env/python
from datetime import timedelta, datetime
import logging

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from osgeo import gdal

import requests_cache
import numpy as np

from interface import *
from sources import *
from indices import *
from notifiers import *

import argparse

logger = logging.getLogger(__name__)
args = None

SESSION = requests_cache.CachedSession(
    "fews",
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
MAP_PROJECTION = ccrs.PlateCarree()


def main(
    use_whatsapp=True,
    use_telegram=True,
    use_whatsapp_fallback_only=False,
    language="en",
):
    gdal.UseExceptions()

    # angular_resolution = 0.01  # pretty, but slow
    angular_resolution = 0.05

    lat = np.array([-10.00, -4.75])
    lon = np.array([104.50, 120])

    extent = Extent(*lon, *lat).grow_extent(angular_resolution)
    del lon, lat

    logger.debug(f"Map extent: {extent}")

    resolution = Resolution(
        lon=extent.lon_res(angular_resolution), lat=extent.lat_res(angular_resolution)
    )
    logger.debug(f"Map resolution: {resolution}")

    logger.info("Setting up registry")
    registry = Registry()
    # Configure date for noaagfs source here. Must be recent.
    noaagfs_date = (datetime.now() - timedelta(days=2)).strftime("%Y%m%d")
    registry.register_source(NOAAGfsSource(noaagfs_date, "00", 12, "apcpsfc"))
    registry.register_source(BnpbInaRiskFloodRiskIndexSource())
    registry.register_source(BnpbInaRiskFlashFloodRiskIndexSource())

    registry.register_hazard_index(HMHEWSFloodHazardIndex())

    registry.register_notifier(PlotNotifier())
    registry.register_notifier(ConsoleAreaNotifier())
    registry.register_notifier(ConsoleGridNotifier())

    # Configure messaging settings - update with your actual values as needed
    whatsapp_group_id = "<insert group id>"  # Replace with your WhatsApp group ID
    whatsapp_phone_number = (
        "<insert phone number>"  # Replace with your WhatsApp phone number
    )
    telegram_chat_id = "@fewsbandungML"  # Replace with your Telegram channel

    # Register the alert notifier with messaging configuration
    registry.register_notifier(
        AlertNotifier(
            whatsapp_group_id=whatsapp_group_id,
            whatsapp_phone_number=whatsapp_phone_number,
            telegram_chat_id=telegram_chat_id,
            use_whatsapp=use_whatsapp,
            use_telegram=use_telegram,
            use_whatsapp_fallback_only=use_whatsapp_fallback_only,
            language=language,
        )
    )

    registry.run(extent, resolution)

    plt.show()


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Indonesian Flood Early Warning System"
    )
    parser.add_argument(
        "--no-whatsapp", action="store_true", help="Disable WhatsApp notifications"
    )
    parser.add_argument(
        "--no-telegram", action="store_true", help="Disable Telegram notifications"
    )
    parser.add_argument(
        "--fallback-only", action="store_true", help="Use only WhatsApp fallback method"
    )
    parser.add_argument(
        "--language",
        choices=["en", "id"],
        default="en",
        help="Message language (en=English, id=Indonesian)",
    )
    parser.add_argument(
        "-l",
        "--log",
        dest="logLevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.getLevelName(args.logLevel),
        format="%(levelname)8s: %(message)s",
    )
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("requests_cache").setLevel(logging.WARNING)

    # Run main function with parsed arguments
    main(
        use_whatsapp=not args.no_whatsapp,
        use_telegram=not args.no_telegram,
        use_whatsapp_fallback_only=args.fallback_only,
        language=args.language,
    )
