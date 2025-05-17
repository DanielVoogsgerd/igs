from sources import *
from interface import *

import logging

logger = logging.getLogger(__name__)


class HMHEWSFloodHazardIndex(HazardIndex):
    """A flood risk hazard index. Based on the H-MHEWS system.

    Source:
    Susandi, Armi & Tamamadin, Mamad & Pratama, Alvin & Faisal, Irvan & Wijaya,
    Aristyo & Pratama, Angga & Pandini, Olgha & Widiawan, Destika. (2018).
    Development of Hydro-Meteorological Hazard Early Warning System in
    Indonesia. Journal of Engineering and Technological Sciences. 50. 461-478.
    10.5614/j.eng.technol.sci.2018.50.4.2.
    """

    IDENTIFIER = "h-mhews-flood-risk-index"

    def calculate_index(
        self, rasters: typing.Dict[SourceIdentifier, RasterizedInformation]
    ) -> RasterizedInformation:
        # Calculation is as described in the H-MHEWS paper.
        return (
            rasters["bnpb-inarisk-flood-risk-index"] * 0.2 * 20
            + rasters["noaa-gfs-rain-data"] * 0.8
        )

    @property
    def required_sources(self) -> typing.List[SourceIdentifier]:
        return ["noaa-gfs-rain-data", "bnpb-inarisk-flood-risk-index"]


class HMHEWSHistoricalFloodHazardIndex(HazardIndex):
    """A flood risk hazard index. Based on the H-MHEWS system. Uses CHIRPS
    historical rain data instead of NOAA GFS predicted rain data.

    Used for backtesting. For more details, see the HMHEWSFloodHazardIndex
    class.
    """

    IDENTIFIER = "h-mhews-historical-flood-risk-index"

    def calculate_index(
        self, rasters: typing.Dict[SourceIdentifier, RasterizedInformation]
    ) -> RasterizedInformation:
        return (
            rasters["bnpb-inarisk-flood-risk-index"] * 0.2 * 20
            + rasters["chirps-historical-rain-data"] * 0.8 * 0.125
        )

    @property
    def required_sources(self) -> typing.List[SourceIdentifier]:
        return ["chirps-historical-rain-data", "bnpb-inarisk-flood-risk-index"]
