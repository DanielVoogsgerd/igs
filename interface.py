from abc import ABC, abstractmethod
from dataclasses import dataclass
from collections import namedtuple

import geopandas as gpd
from shapely.geometry import Polygon
import numpy as np

import typing
import logging

logger = logging.getLogger(__name__)

# Extent = typing.Tuple[int, int, int, int]
Bounds = typing.Tuple[float, float, float, float]
Resolution = namedtuple("Resolution", ["lon", "lat"])
Coordinate = typing.Tuple[float, float]

SourceIdentifier = str
HazardIndexIdentifier = str

Angle = float


@dataclass
class Extent:
    lon_min: Angle
    lon_max: Angle
    lat_min: Angle
    lat_max: Angle

    # TODO: Implement different projections

    @staticmethod
    def from_bounds(bounds: Bounds) -> "Extent":
        lon_min, lat_min, lon_max, lat_max = bounds
        return Extent(lon_min, lon_max, lat_min, lat_max)

    @property
    def as_tuple(self) -> typing.Tuple[Angle, Angle, Angle, Angle]:
        return (self.lon_min, self.lon_max, self.lat_min, self.lat_max)

    @property
    def lon_range(self) -> typing.Tuple[Angle, Angle]:
        return self.lon_min, self.lon_max

    @property
    def lat_range(self) -> typing.Tuple[Angle, Angle]:
        return self.lat_min, self.lat_max

    @property
    def bounds(self) -> Bounds:
        return (self.lon_min, self.lat_min, self.lon_max, self.lat_max)

    def grow_extent(self, resolution: float) -> "Extent":
        (lon_min, lon_max, lat_min, lat_max) = self.as_tuple
        lat_min = np.floor(lat_min / resolution) * resolution
        lat_max = np.ceil(lat_max / resolution) * resolution

        lon_min = np.floor(lon_min / resolution) * resolution
        lon_max = np.ceil(lon_max / resolution) * resolution

        return Extent(lon_min, lon_max, lat_min, lat_max)

    # TODO: Rename `lon_res` and `lat_res`.
    def lon_res(self, angular_resolution: float) -> int:
        return int((self.lon_max - self.lon_min) // angular_resolution + 1)

    def lat_res(self, angular_resolution: float) -> int:
        return int((self.lat_max - self.lat_min) // angular_resolution + 1)

    def reproject(self, src_crs, dst_crs) -> "Extent":
        dst_lon_min, dst_lat_min = dst_crs.transform_point(
            self.lon_min, self.lat_min, src_crs
        )

        dst_lon_max, dst_lat_max = dst_crs.transform_point(
            self.lon_max, self.lat_max, src_crs
        )

        return Extent(dst_lon_min, dst_lon_max, dst_lat_min, dst_lat_max)

    def pixel_size(self, resolution: Resolution):
        """Calculates the size of each pixel given a certain image resolution for this extent

        Warning: This resolution expects latitude first, so (lat, lon)
        """
        psize_lon = (self.lon_max - self.lon_min) / resolution.lon
        psize_lat = (self.lat_max - self.lat_min) / resolution.lat

        return (psize_lon, psize_lat)


@dataclass
class RasterizedInformation:
    """A rasterized data object storing geographical data with its metadata.

    Note: This representation expects the data and extent to use a PlateCarree projection of the earth with angles as Unit of Measurement (UoM)

    It provides some convenience methods for common operations on this data
    """

    extent: Extent
    raster: np.ndarray

    def __mul__(self, other):
        # TODO: We could return a subset if the maps overlap but have a different extent
        if isinstance(other, type(self)):
            if self.extent != other.extent:
                raise Exception("Rasters do not line up")

            if self.raster.shape != other.raster.shape:
                raise Exception("Rasters are not of the same shape")

            return RasterizedInformation(self.extent, self.raster * other.raster)

        return RasterizedInformation(self.extent, self.raster * other)

    __rmul__ = __mul__

    def __add__(self, other):
        # TODO: We could return a subset if the maps overlap but have a different extent
        if isinstance(other, type(self)):
            if self.extent != other.extent:
                raise Exception("Rasters do not line up")

            if self.raster.shape != other.raster.shape:
                raise Exception("Rasters are not of the same shape")

            return RasterizedInformation(self.extent, self.raster + other.raster)

        return RasterizedInformation(self.extent, self.raster + other)

    def plot(self, ax, **kwargs):
        kwargs["extent"] = self.extent.as_tuple
        logger.debug(f"plot: {ax}, {kwargs}")
        ax.imshow(self.raster, **kwargs)

    # TODO: Confirm why this CRS is being used.
    def to_gdf(self, crs="EPSG:4326") -> gpd.GeoDataFrame:
        """Converts the raster into a GeoDataFrame of polygons.

        Raster array values are stored in the "value" column.
        The polygons are stored in the "geometry" column.
        """
        yn, xn = self.raster.shape
        pixel_width, pixel_height = self.extent.pixel_size(Resolution(lat=yn, lon=xn))
        assert pixel_width > 0
        assert pixel_height > 0

        polygons, values = [], []

        for y in range(yn):
            for x in range(xn):
                x0 = self.extent.lon_min + x * pixel_width
                y0 = self.extent.lat_max - (y + 1) * pixel_height
                x1 = x0 + pixel_width
                y1 = y0 + pixel_height
                polygons.append(
                    Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])
                )
                values.append(self.raster[y, x])

        # TODO: Extract column names to constants.
        gdf = gpd.GeoDataFrame({"value": values, "geometry": polygons}, crs=crs)
        return gdf


class Identifiable(ABC):
    """A class that has an `IDENTIFIER` attribute."""

    IDENTIFIER = "unset"

    def __str__(self):
        return f"{self.IDENTIFIER}"

    def __repr__(self):
        return f"{self.IDENTIFIER}"


class Source(Identifiable):
    @abstractmethod
    def fetch_data(
        self, extent: Extent, resolution: Resolution
    ) -> RasterizedInformation:
        pass

    @property
    @abstractmethod
    def max_resolution(self) -> Resolution:
        pass

    @property
    def provides(self) -> SourceIdentifier:
        return self.IDENTIFIER


class HazardIndex(Identifiable):
    @abstractmethod
    def calculate_index(
        self,
        rasters: typing.Dict[SourceIdentifier, RasterizedInformation],
    ) -> RasterizedInformation:
        pass

    @property
    @abstractmethod
    def required_sources(self) -> typing.List[SourceIdentifier]:
        pass

    @property
    def provides(self) -> HazardIndexIdentifier:
        return self.IDENTIFIER


class Notifier(Identifiable):
    @abstractmethod
    def notify(
        self,
        notify_raster: typing.Dict[HazardIndexIdentifier, RasterizedInformation],
    ):
        pass

    @property
    @abstractmethod
    def responsible_extent(self) -> Extent:
        pass

    # TODO: Add support for generic index or passed in the constructor.
    @property
    @abstractmethod
    def required_indices(self) -> typing.List[HazardIndexIdentifier]:
        pass


class Registry:
    def __init__(self):
        self._sources = {}
        self._hazard_indices = {}
        self._notifiers = []

    def register_source(self, source: Source):
        identifier = source.provides

        if identifier in self._sources:
            print("Warning: Re-registering an existing source, overwriting")

        self._sources[identifier] = source

    def register_hazard_index(self, index: HazardIndex):
        identifier = index.provides

        if identifier in self._hazard_indices:
            print("Warning: Re-registering an existing hazard index, overwriting")

        self._hazard_indices[identifier] = index

    def register_notifier(self, notifier: Notifier):
        self._notifiers.append(notifier)

    def run(self, extent: Extent, resolution: Resolution):
        # TODO: Refactor to generic job queue, where we don't distinguish
        # between sources, indices and notifiers.
        # TODO: Parallelize the fetching of data and computation of indices.

        logger.info("Determining dependencies")
        indices = set(
            [
                index_id
                for notifier in self._notifiers
                for index_id in notifier.required_indices
            ]
        )
        sources = set(
            [
                source_id
                for index in indices
                for source_id in self._hazard_indices[index].required_sources
            ]
        )
        logger.debug(f"Notifiers: {self._notifiers}")
        logger.debug(f"Hazard indices in use: {indices}")
        logger.debug(f"Sources in use: {sources}")

        logger.info("Fetching data")
        source_res = {
            source_id: self._sources[source_id].fetch_data(extent, resolution)
            for source_id in sources
        }

        logger.info("Calculating indices")
        index_res = {
            index_identifier: self._hazard_indices[index_identifier].calculate_index(
                source_res
            )
            for index_identifier in indices
        }

        logger.info("Running notifiers")
        for notifier in self._notifiers:
            notifier.notify(index_res)
