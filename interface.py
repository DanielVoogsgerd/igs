from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

import typing

# Extent = typing.Tuple[int, int, int, int]
Bounds = typing.Tuple[float, float, float, float]
Resolution = typing.Tuple[int, int]
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

    def reproject(self, src_crs, dst_crs) -> "Extent":
        dst_lon_min, dst_lat_min = dst_crs.transform_point(
            self.lon_min, self.lat_min, src_crs
        )

        dst_lon_max, dst_lat_max = dst_crs.transform_point(
            self.lon_max, self.lat_max, src_crs
        )

        return Extent(dst_lon_min, dst_lon_max, dst_lat_min, dst_lat_max)

    def pixel_size(self, resolution: Resolution):
        """Calcutes the size of each pixel given a certain image resolution for this extent

        Warning: This resolution expects latitude first, so (lat, lon)
        """
        psize_lon = (self.lon_max - self.lon_min) / resolution[1]
        psize_lat = (self.lat_max - self.lat_min) / resolution[0]

        return (psize_lon, psize_lat)


@dataclass
class RasterizedInformation:
    """A rasterized data object storing geographical data with its metadata.

    Note: This representation expects the data and extent to use a PlateCarree projcetion of the earth with angles as Unit of Measurement (UoM)

    It provides some convenience methods for common operations on this data
    """

    extent: Extent
    raster: np.ndarray

    def identify(self, identifier: SourceIdentifier):
        return IdentifiedRasterizedInformation(identifier, self.extent, self.raster)

    def __mul__(self, other):
        # TODO: We could return a subset if the maps overlap but have a different extent
        if isinstance(other, type(self)):
            print("Comparing apples to apples")
            if self.extent != other.extent:
                raise Exception("Rasters do not line up")

            if self.raster.shape != other.raster.shape:
                raise Exception("Rasters are not of the same shape")

            return RasterizedInformation(self.extent, self.raster * other.raster)

        return RasterizedInformation(self.extent, self.raster * other)

    def __add__(self, other):
        # TODO: We could return a subset if the maps overlap but have a different extent
        if isinstance(other, type(self)):
            print("Comparing apples to apples")
            if self.extent != other.extent:
                raise Exception("Rasters do not line up")

            if self.raster.shape != other.raster.shape:
                raise Exception("Rasters are not of the same shape")

            return RasterizedInformation(self.extent, self.raster + other.raster)

        return RasterizedInformation(self.extent, self.raster + other)

    def plot(self, ax, **kwargs):
        kwargs["extent"] = self.extent.as_tuple
        print(ax, kwargs)
        ax.imshow(self.raster, **kwargs)

    __rmul__ = __mul__


@dataclass
class IdentifiedRasterizedInformation(RasterizedInformation):
    """A wrapper around RasterizedInformation, but tagged with a identifier.

    This data can be used by notifiers to request certain datasets from a registry
    """

    identifier: SourceIdentifier
    extent: Extent
    raster: np.ndarray

    def __init__(
        self, identifier: SourceIdentifier, extent: Extent, raster: np.ndarray
    ):
        self.identifier = identifier
        self.extent = extent
        self.raster = raster

    def identify(self, identifier: SourceIdentifier):
        print("Warning, reidentifying identified data source")
        return super().identify(identifier)


class Source(ABC):
    @abstractmethod
    def fetch_data(
        self, extent: Extent, resolution: Resolution
    ) -> IdentifiedRasterizedInformation:
        pass

    @property
    @abstractmethod
    def max_resolution(self) -> Resolution:
        pass

    @property
    @abstractmethod
    def provides(self) -> SourceIdentifier:
        pass


class HazardIndex(ABC):
    @abstractmethod
    def calculate_index(
        self, rasters: typing.Dict[SourceIdentifier, IdentifiedRasterizedInformation]
    ) -> RasterizedInformation:
        pass

    @property
    @abstractmethod
    def required_sources(self) -> typing.List[SourceIdentifier]:
        pass

    @property
    @abstractmethod
    def provides(self) -> HazardIndexIdentifier:
        pass


class Notifier(ABC):
    @abstractmethod
    def notify(self, notify_raster: RasterizedInformation):
        pass

    @property
    @abstractmethod
    def responsible_extent(self) -> Extent:
        pass

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

    def run(self):
        # TODO:
        # - Find notifiers
        # - Find required hazard indices
        # - Find required sources
        # - Resolve dependency chain
        pass
