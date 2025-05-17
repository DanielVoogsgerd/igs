import urllib.request
import urllib.parse
from datetime import timedelta, datetime
import requests_cache
import logging

from dibi_api_types import (
    DIBIEvent,
    ProvinceType,
    JawaBaratDistrictType,
    DisasterType,
    RawEventData,
)
from typing import List


logger = logging.getLogger(__name__)

# Set up a cached session similar to sources.py
SESSION = requests_cache.CachedSession(
    "dibi_cache",
    use_cache_dir=True,  # Save files in the default user cache dir
    cache_control=False,  # Use Cache-Control response headers for expiration, if available
    expire_after=timedelta(days=7),  # Cache for 7 days
    allowable_codes=[200],
    allowable_methods=["GET", "POST"],
    stale_if_error=True,  # In case of request errors, use stale cache data if possible
)


class DIBIEventStore:
    MAX_EVENTS = 100000
    events: List[DIBIEvent] = []

    def __init__(
        self,
        provinces: List[ProvinceType] = [ProvinceType.UNSET],
        districts: List[JawaBaratDistrictType] = [JawaBaratDistrictType.UNSET],
        year: List[int] = [""],
        month: List[int] = [""],
        disaster_type: List[DisasterType] = [DisasterType.UNSET],
    ):
        self.province = provinces
        self.district = districts
        self.year = year
        self.month = month
        self.disaster_type = disaster_type
        for province_h in provinces:
            for district_h in districts:
                for year_h in year:
                    for month_h in month:
                        for disaster_type_h in disaster_type:
                            logger.info(
                                f"  Retrieving events for province: {province_h.name}"
                            )
                            self.events.extend(
                                self._fetch_events(
                                    self.MAX_EVENTS,
                                    province_h,
                                    district_h,
                                    year_h,
                                    month_h,
                                    disaster_type_h,
                                )
                            )
                            logger.debug(
                                f"    Cumulative number of events: {len(self.events)}"
                            )

    def get_events_on_date(self, date: datetime) -> List[DIBIEvent]:
        return [e for e in self.events if e.datetime.date() == date.date()]

    def get_events_on_date_gid2s(self, date: datetime) -> set[str]:
        return set(
            [e.location.gadm_district_gid2 for e in self.get_events_on_date(date)]
        )

    def _fetch_events(
        self,
        num_events_to_fetch: int = 5,
        province: ProvinceType = ProvinceType.UNSET,
        district: JawaBaratDistrictType = JawaBaratDistrictType.UNSET,
        year: int = "",
        month: int = "",
        disaster_type: DisasterType = DisasterType.UNSET,
    ) -> List[DIBIEvent]:
        assert num_events_to_fetch > 0
        assert year == "" or int(year) in range(1800, 2026)
        assert month == "" or int(month) in range(1, 13)

        url = "https://dibi.bnpb.go.id/dibi3x/get_dibi3x"
        # TODO: Trim headers.
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "pragma": "no-cache",
        }
        data = {
            "start": "0",  # For pagination
            "length": num_events_to_fetch,  # Number of events to fetch.
            "search[value]": "",
            "search[regex]": "false",
            "pr": province.value,  # Province: dibi_api_types.ProvinceType
            "kb": district.value,  # District: dibi_api_types.JawaBaratDistrictType
            "th": year,  # Year
            "bl": month,  # Month
            "jn": disaster_type.value,  # Disaster Type: dibi_api_types.DisasterType
            "cr": "",  # String search
        }

        encoded_data = urllib.parse.urlencode(data).encode("utf-8")
        response = SESSION.post(url, data=encoded_data, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data: {response.status_code}")

        try:
            data = response.json()
        # Quick way to handle when no events are found for the query.
        except ValueError:
            return []

        return [DIBIEvent(RawEventData(**row)) for row in data["aaData"]]
