#!/usr/bin/env python
from abc import ABC, abstractmethod
from datetime import timedelta
from io import BytesIO

import datetime
import gzip
import rasterio
import cartopy.crs as ccrs
import numpy as np
import requests_cache
import xarray as xr
from PIL import Image
from pyproj import CRS
from requests import Request

from custom_types import Extent, Resolution
from utils import (
    bounds_to_extent,
    get_bbox_xy,
    grow_extent,
    reproject_extent,
    reproject_gdal,
    _zoom_to_pixel_size,
)

PLATE_CARREE_EPSG = 32662

SESSION = requests_cache.CachedSession(
    "demo_cache",
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


class Source(ABC):
    @abstractmethod
    def image_for_domain(self, target_domain, zoom: int):
        pass

    @abstractmethod
    def data_for_domain(
        self,
        dst_extent: Extent,
        dst_resolution: Resolution,
        resampling: str,
    ) -> np.ndarray:
        pass


# Note that this is still slightly incorrect as our tiles are in the wrong projection, however the source is close to the equator and it.
# This can be fixed by either rewriting the entire image_factory (the cimgt.GoogleWTS base class). Or reprojecting the image to the correct crs afterwards


class BnpbSource(Source):
    # We can only request a certain dataset size from the server
    MAX_IMAGE_HEIGHT = 4100
    MAX_IMAGE_WIDTH = 15000

    DATA_RESOLUTION = 100  # in meters
    EPSG = 3395

    def __init__(self, source):
        self.bnpb_source = source
        self.crs = ccrs.epsg(str(self.EPSG))

    def _get_data(self, extent, resolution):
        lon_min, lon_max, lat_min, lat_max = extent

        lon = [lon_min, lon_max]
        lat = [lat_min, lat_max]

        bbox = get_bbox_xy(lon, lat)

        # print("Img pixel size", (lon_max - lon_min) / width)
        height, width = resolution

        assert width <= self.MAX_IMAGE_WIDTH
        assert height <= self.MAX_IMAGE_HEIGHT

        req = Request(
            "GET",
            f"https://gis.bnpb.go.id/server/rest/services/inarisk/{self.bnpb_source}/ImageServer/exportImage",
            params={
                "bbox": bbox,
                "f": "image",
                "format": "png8",
                "pixelType": "F32",
                "noDataInterpretation": "esriNoDataMatchAny",
                "interpolation": "RSP_BilinearInterpolation",
                "size": f"{width},{height}",
                "adjustAspectRatio": False,
                "lercVersion": 1,
            },
        ).prepare()

        res = SESSION.send(req)
        if res.status_code != 200:
            print("Bnpb request failed!")
            print(res.text)

        i = Image.open(BytesIO(res.content))
        return i

    def image_for_domain(self, target_domain, zoom):
        target_domain = target_domain.bounds
        lon_min, lat_min, lon_max, lat_max = target_domain
        extent = lon_min, lon_max, lat_min, lat_max

        _, lat_mean = ccrs.PlateCarree().transform_point(
            (lon_max + lon_min) / 2, (lat_max + lat_min) / 2, self.crs
        )

        pixel_size = _zoom_to_pixel_size(zoom, lat_mean)

        aspect = (lon_max - lon_min) / (lat_max - lat_min)

        width = int((lon_max - lon_min) / pixel_size)
        height = int(width / aspect)

        img = self._get_data(extent, (height, width))

        return img, extent, "upper"

    def data_for_domain(
        self,
        dst_extent: Extent,
        dst_resolution: Resolution,
        resampling: str = "bilinear",
    ) -> np.ndarray:
        src_crs = CRS.from_epsg(self.EPSG)
        dst_crs = CRS.from_epsg(PLATE_CARREE_EPSG)

        src_extent = reproject_extent(dst_extent, ccrs.PlateCarree(), self.crs)
        dst_extent = reproject_extent(
            dst_extent, ccrs.PlateCarree(), ccrs.Projection(dst_crs)
        )

        # Calculate pixel size (before growing src_extent)
        dst_psize_lon = (src_extent[1] - src_extent[0]) / dst_resolution[1]
        dst_psize_lat = (src_extent[3] - src_extent[2]) / dst_resolution[0]

        # Grow extent if necessary to match data resolution
        src_extent = grow_extent(src_extent, self.DATA_RESOLUTION)

        # Calculate required source resolution
        src_resolution_lon = int((src_extent[1] - src_extent[0]) / dst_psize_lon)
        src_resolution_lat = int((src_extent[3] - src_extent[2]) / dst_psize_lat)

        src_img = self._get_data(src_extent, (src_resolution_lat, src_resolution_lon))
        print("Image dimensions:", np.array(src_img).shape)
        # Combine RGB channels as it's a greyscale image
        src_data = np.sum(src_img, axis=2, dtype=np.float32)

        output = reproject_gdal(
            src_data,
            src_crs,
            src_extent,
            dst_resolution,
            dst_crs,
            dst_extent,
            resampling,
        )

        return output


class NOAAGfsSource(Source):
    DATA_RESOLUTION = 0.25

    def __init__(self, date, cycle, hours_ahead, dataset):
        self.crs = ccrs.PlateCarree()
        # Date format YYYYMMDD
        self.date = date
        # 4 cycles are published every day (one every six hours),
        # must be '00', '06', '12', or '18'
        self.cycle = cycle
        # The data is accumulated (summed) precipitation over X hours, indicate
        # here how many hours ahead you want to look (gets rounded down to 3h intervals)
        self.hours_ahead = hours_ahead
        self.dataset = dataset

    def _get_data(self, extent: Extent):
        lon_min, lon_max, lat_min, lat_max = extent

        url = f"https://nomads.ncep.noaa.gov/dods/gfs_0p25/gfs{self.date}/gfs_0p25_{self.cycle}z"
        ds = xr.open_dataset(url, decode_coords="all")

        # Select the accumulated precipitation at surface ('apcpsfc') for the 6-hour forecast
        # This could be done on initialization, or at least be cached after a single fetch
        prediction = ds[self.dataset].sel(time=ds.time[self.hours_ahead // 3])

        prediction_in_region = prediction.sel(
            lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max)
        )

        return prediction_in_region

    def image_for_domain(self, target_domain, target_z: int):
        """API interface for cartopy's add_image.

        It has its quirks, you probably do not want to use it yourself
        """

        from PIL import Image

        # Target domain is a shapely POLYGON object that wraps around the bounds of the domain, basically a "rectangle"
        # Lets just use the range in lat and lon
        # Unfortunately, the cartopy extent is ordered in a different way that the shapely bounds, so we have to re-arrange them as well
        extent = bounds_to_extent(target_domain.bounds)

        prediction_in_region = self._get_data(extent)

        data = prediction_in_region.values

        uint8_data = (
            (data - np.nanmin(data)) / (np.nanmax(data) - np.nanmin(data)) * 255
        ).astype(np.uint8)
        img = Image.fromarray(uint8_data, "L")

        return img, extent, "lower"

    def data_for_domain(
        self,
        dst_extent: Extent,
        dst_resolution: Resolution,
        resampling: str = "bilinear",
    ) -> np.ndarray:
        """

        Returns a two dimensional array of shape resolution
        """
        src_crs = CRS.from_epsg(PLATE_CARREE_EPSG)
        dst_crs = CRS.from_epsg(PLATE_CARREE_EPSG)

        src_extent = reproject_extent(dst_extent, ccrs.PlateCarree(), self.crs)

        # Grow extent if necessary to match data resolution
        src_extent = grow_extent(src_extent, self.DATA_RESOLUTION)

        src_data = self._get_data(src_extent)  # get source data

        # Reproject extents from angles to meters
        src_extent = reproject_extent(
            src_extent,
            ccrs.PlateCarree(),
            ccrs.Projection(src_crs),
        )
        dst_extent = reproject_extent(
            dst_extent, ccrs.PlateCarree(), ccrs.Projection(dst_crs)
        )

        output = reproject_gdal(
            np.flipud(src_data.values),
            src_crs,
            src_extent,
            dst_resolution,
            dst_crs,
            dst_extent,
            resampling,
        )

        return output


class BmkgSource(Source):
    # EPSG = 4326
    # FIXME: The server source is in 4326, but we run into some degree vs meter UoM mismatches, I think
    EPSG = 3395
    MAX_IMAGE_HEIGHT = 4096
    MAX_IMAGE_WIDTH = 4096

    def __init__(self):
        if self.EPSG == 4326:
            self.crs = ccrs.GOOGLE_MERCATOR
        else:
            self.crs = ccrs.epsg(self.EPSG)

    def image_for_domain(self, target_domain, zoom):
        target_domain = target_domain.bounds
        lon_min, lat_min, lon_max, lat_max = target_domain
        extent = lon_min, lon_max, lat_min, lat_max

        _, lat_mean = ccrs.PlateCarree().transform_point(
            (lon_max + lon_min) / 2, (lat_max + lat_min) / 2, self.crs
        )

        pixel_size = _zoom_to_pixel_size(zoom, lat_mean)

        aspect = (lon_max - lon_min) / (lat_max - lat_min)

        width = int((lon_max - lon_min) / pixel_size)
        height = int(width / aspect)

        img = self._get_data(extent, (height, width))

        return img, extent, "upper"

    def data_for_domain(
        self,
        dst_extent: Extent,
        resolution: Resolution,
        resampling: str,
    ) -> np.ndarray:
        src_crs = CRS.from_epsg(self.EPSG)
        dst_crs = CRS.from_epsg(PLATE_CARREE_EPSG)

        src_extent = reproject_extent(dst_extent, ccrs.PlateCarree(), self.crs)
        dst_extent = reproject_extent(
            dst_extent, ccrs.PlateCarree(), ccrs.Projection(dst_crs)
        )

        assert resolution[0] <= self.MAX_IMAGE_HEIGHT
        assert resolution[1] <= self.MAX_IMAGE_WIDTH

        src_img = self._get_data(src_extent, resolution)

        print("Image dimensions:", np.array(src_img).shape)

        # Combine RGB channels as it's a greyscale image
        src_data = np.sum(src_img, axis=2, dtype=np.float32)

        print(np.min(src_data), np.max(src_data))

        output = reproject_gdal(
            src_data,
            src_crs,
            src_extent,
            resolution,
            dst_crs,
            dst_extent,
            resampling,
        )

        return output

    def _get_data(self, extent: Extent, resolution: Resolution):
        width, height = resolution
        lon_min, lon_max, lat_min, lat_max = extent
        print("Getting rain data")
        base_url = "https://gis.bmkg.go.id/arcgis/services/Peta_Curah_Hujan_dan_Hari_Hujan_/MapServer/WMSServer"
        bbox = f"{lon_min:.6f},{lat_min:.6f},{lon_max:.6f},{lat_max:.6f}"
        params = {
            "service": "WMS",
            "version": "1.3.0",
            "request": "GetMap",
            "layers": 2,
            "styles": "default",
            "crs": f"EPSG:{self.EPSG}",
            "bbox": bbox,
            "width": RESOLUTION,
            "height": RESOLUTION,
            "format": "image/png",
        }

        req = SESSION.get(base_url, params=params)

        print(req.url)

        if req.headers.get("Content-Type") != "image/png":
            print(req.text)
            return

        i = Image.open(BytesIO(req.content))

        x = np.array(i)

        print(np.min(x), np.max(x))

        return i


class CHIRPSSource(Source):
    DATA_RESOLUTION = 0.05
    DATA_EXTENT = (-180, 180, -50, 50)
    EPSG = 4326

    def __init__(self, date: datetime.date):
        self.crs = ccrs.GOOGLE_MERCATOR
        self.date = date

    def _get_data(self):
        req = Request(
            "GET",
            f"https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/tifs/p05/{self.date.year}/chirps-v2.0.{self.date.strftime('%Y.%m.%d')}.tif.gz",
        ).prepare()

        print(req.url)

        res = SESSION.send(req)
        if res.status_code != 200:
            print("CHIRPS request failed!")
            print(res.text)

        decompressed = gzip.open(BytesIO(res.content))

        i = rasterio.open(decompressed)
        print("Data CRS:", i.crs)
        return i.read(1)

    def image_for_domain(self, target_domain, zoom):
        pass

    def data_for_domain(
        self,
        dst_extent: Extent,
        dst_resolution: Resolution,
        resampling: str = "bilinear",
    ) -> np.ndarray:
        src_crs = CRS.from_epsg(self.EPSG)
        dst_crs = CRS.from_epsg(PLATE_CARREE_EPSG)

        src_extent = reproject_extent(
            self.DATA_EXTENT, ccrs.PlateCarree(), ccrs.Projection(src_crs)
        )
        dst_extent = reproject_extent(
            dst_extent, ccrs.PlateCarree(), ccrs.Projection(dst_crs)
        )

        # Grow extent if necessary to match data resolution
        # src_extent = grow_extent(src_extent, self.DATA_RESOLUTION)

        src_data = self._get_data()
        src_data[src_data < 0] = 0
        print("Got data!", src_data.shape)
        print("Data CRS", self.crs)

        output = reproject_gdal(
            src_data,
            src_crs,
            src_extent,
            dst_resolution,
            dst_crs,
            dst_extent,
            resampling,
        )

        return output
