from sources import *
from interface import *


# TODO: Change to H-MHEWS
class InAWAREHazardIndex(HazardIndex):
    def calculate_index(
        self, rasters: typing.Dict[SourceIdentifier, IdentifiedRasterizedInformation]
    ) -> RasterizedInformation:
        return (
            rasters["bnpb-inarisk-flood-risk-index"] * 0.2 * 20
            + rasters["noaa-gfs-rain-data"] * 0.8
        )

    @property
    def required_sources(self) -> typing.List[SourceIdentifier]:
        return ["noaa-gfs-rain-data", "bnpb-inarisk-flood-risk-index"]

    @property
    def provides(self) -> HazardIndexIdentifier:
        return "inaware-flood-risk-index"
