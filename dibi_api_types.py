from enum import Enum
from dataclasses import dataclass
import re
from typing import TypedDict
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests_cache
import logging
import geopandas as gpd
from shapely.geometry import Point

from utils import get_file_path


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

logger = logging.getLogger(__name__)


class ProvinceType(Enum):
    """All provinces in Indonesia. Used for querying the DIBI v3 API.

    Source: https://dibi.bnpb.go.id/"""

    UNSET = ""
    ACEH = "11"
    SUMATERA_UTARA = "12"
    SUMATERA_BARAT = "13"
    RIAU = "14"
    JAMBI = "15"
    SUMATERA_SELATAN = "16"
    BENGKULU = "17"
    LAMPUNG = "18"
    KEPULAUAN_BANGKA_BELITUNG = "19"
    KEPULAUAN_RIAU = "21"
    DKI_JAKARTA = "31"
    JAWA_BARAT = "32"
    JAWA_TENGAH = "33"
    DIY_YOGYAKARTA = "34"
    JAWA_TIMUR = "35"
    BANTEN = "36"
    BALI = "51"
    NUSA_TENGGARA_BARAT = "52"
    NUSA_TENGGARA_TIMUR = "53"
    KALIMANTAN_BARAT = "61"
    KALIMANTAN_TENGAH = "62"
    KALIMANTAN_SELATAN = "63"
    KALIMANTAN_TIMUR = "64"
    KALIMANTAN_UTARA = "65"
    SULAWESI_UTARA = "71"
    SULAWESI_TENGAH = "72"
    SULAWESI_SELATAN = "73"
    SULAWESI_TENGGARA = "74"
    GORONTALO = "75"
    SULAWESI_BARAT = "76"
    MALUKU = "81"
    MALUKU_UTARA = "82"
    PAPUA = "91"
    PAPUA_BARAT = "92"
    PAPUA_SELATAN = "93"
    PAPUA_TENGAH = "94"
    PAPUA_PEGUNUNGAN = "95"
    PAPUA_BARAT_DAYA = "96"


class JawaBaratDistrictType(Enum):
    """All districts in Jawa Barat. Used for querying the DIBI v3 API.

    Source: https://dibi.bnpb.go.id/"""

    UNSET = ""
    BOGOR = "01"
    SUKABUMI = "02"
    CIANJUR = "03"
    BANDUNG = "04"
    GARUT = "05"
    TASIKMALAYA = "06"
    CIAMIS = "07"
    KUNINGAN = "08"
    CIREBON = "09"
    MAJALENGKA = "10"
    SUMEDANG = "11"
    INDRAMAYU = "12"
    SUBANG = "13"
    PURWAKARTA = "14"
    KARAWANG = "15"
    BEKASI = "16"
    BANDUNG_BARAT = "17"
    PANGANDARAN = "18"
    KOTA_BOGOR = "71"
    KOTA_SUKABUMI = "72"
    KOTA_BANDUNG = "73"
    KOTA_CIREBON = "74"
    KOTA_BEKASI = "75"
    KOTA_DEPOK = "76"
    KOTA_CIMAHI = "77"
    KOTA_TASIKMALAYA = "78"
    KOTA_BANJAR = "79"


class DisasterType(Enum):
    """All disaster types in Indonesia. Used for querying the DIBI v3 API.

    Source: https://dibi.bnpb.go.id/"""

    UNSET = ""
    FLOOD = "101"
    # TODO: Add other disaster types.


# DIBI: https://dibi.bnpb.go.id/dibi3x/
# GADM: https://gadm.org/maps/IDN_1.html
DIBI_PROVINCE_TO_GADM_L1_MAPPING = {
    "ACEH": "Aceh",
    "BALI": "Bali",
    "BANTEN": "Banten",
    "BENGKULU": "Bengkulu",
    "DIY_YOGYAKARTA": "Yogyakarta",
    "DKI_JAKARTA": "Jakarta Raya",
    "GORONTALO": "Gorontalo",
    "JAMBI": "Jambi",
    "JAWA_BARAT": "Jawa Barat",
    "JAWA_TENGAH": "Jawa Tengah",
    "JAWA_TIMUR": "Jawa Timur",
    "KALIMANTAN_BARAT": "Kalimantan Barat",
    "KALIMANTAN_SELATAN": "Kalimantan Selatan",
    "KALIMANTAN_TENGAH": "Kalimantan Tengah",
    "KALIMANTAN_TIMUR": "Kalimantan Timur",
    "KALIMANTAN_UTARA": "Kalimantan Utara",
    "KEPULAUAN_BANGKA_BELITUNG": "Bangka-Belitung",
    "KEPULAUAN_RIAU": "Kepulauan Riau",
    "LAMPUNG": "Lampung",
    "MALUKU": "Maluku",
    "MALUKU_UTARA": "Maluku Utara",
    "NUSA_TENGGARA_BARAT": "Nusa Tenggara Barat",
    "NUSA_TENGGARA_TIMUR": "Nusa Tenggara Timur",
    "PAPUA": "Papua",
    "RIAU": "Riau",
    "SULAWESI_BARAT": "Sulawesi Barat",
    "SULAWESI_SELATAN": "Sulawesi Selatan",
    "SULAWESI_TENGAH": "Sulawesi Tengah",
    "SULAWESI_TENGGARA": "Sulawesi Tenggara",
    "SULAWESI_UTARA": "Sulawesi Utara",
    "SUMATERA_BARAT": "Sumatera Barat",
    "SUMATERA_SELATAN": "Sumatera Selatan",
    "SUMATERA_UTARA": "Sumatera Utara",
    # Custom mappings. To be confirmed.
    "PAPUA_BARAT": "Irian Jaya Barat",
    "PAPUA_BARAT_DAYA": "Irian Jaya Barat",
    "PAPUA_PEGUNUNGAN": "Irian Jaya Barat",
    "PAPUA_SELATAN": "Papua",
    "PAPUA_TENGAH": "Papua",
}


class GADMLocationManager:
    """Performs conversions between DIBI and GADM identifiers."""

    def __init__(self):
        self.gdf_adm_l2 = gpd.read_file(get_file_path("cadastre/gadm41_IDN_2.shp"))
        self.l2_cache = {}

    def get_district_gid2(
        self,
        dibi_province_str: str,
        dibi_district_str: str,
        longitude: float = None,
        latitude: float = None,
    ) -> str:
        if (dibi_province_str, dibi_district_str) in self.l2_cache:
            return self.l2_cache[(dibi_province_str, dibi_district_str)]

        gdf_adm_filtered = self.gdf_adm_l2[
            self.gdf_adm_l2["NAME_1"] == dibi_province_str
        ]
        gdf_adm_filtered = gdf_adm_filtered[
            gdf_adm_filtered["NAME_2"] == dibi_district_str
        ]
        if gdf_adm_filtered.empty:
            if longitude is None or latitude is None:
                return None
            gdf_adm_filtered = self.gdf_adm_l2[
                self.gdf_adm_l2.geometry.contains(Point(longitude, latitude))
            ]
            logger.debug(
                f"Location used to determine mapping: ({dibi_province_str}, {dibi_district_str}) -> {gdf_adm_filtered.iloc[0]['GID_2']}"
            )
        self.l2_cache[(dibi_province_str, dibi_district_str)] = gdf_adm_filtered.iloc[
            0
        ]["GID_2"]
        return self.l2_cache[(dibi_province_str, dibi_district_str)]

    def get_all_district_gid2s_in_provinces(
        self, provinces: list[ProvinceType]
    ) -> set[str]:
        res = set()
        for province in provinces:
            gadm_province_name = DIBI_PROVINCE_TO_GADM_L1_MAPPING[province.name]
            logger.debug(
                f"dibi province.name: {province.name} gadm province: {gadm_province_name}"
            )
            gdf_adm_filtered = self.gdf_adm_l2[
                self.gdf_adm_l2["NAME_1"] == gadm_province_name
            ]
            res.update(set(gdf_adm_filtered["GID_2"].tolist()))
        return res


gadm_location_manager = GADMLocationManager()


class RawEventData(TypedDict):
    level0: int
    level1: int
    nwil: str
    nprop: str
    nkab: str
    kejadian: str
    tglan: str
    kib: str
    idj: int
    meninggal: int
    hilang: int
    terluka: int
    menderita: int
    mengungsi: int
    rumah_rusak_berat: int
    rumah_rusak_sedang: int
    rumah_rusak_ringan: int
    rumah_terendam: int
    pendidikan: int
    kesehatan: int
    peribadatan: int
    fasum: int
    sql: str
    act: str


@dataclass
class Location:
    level0: ProvinceType
    level1: int
    full_location: str  # nwil
    province: str  # nprop
    district: str  # nkab
    latitude: float = None
    longitude: float = None
    gadm_district_gid2: str = None

    def __str__(self):
        return f"lat: {self.latitude}, lon: {self.longitude}, {self.full_location}"


@dataclass
class HouseDamage:
    severely_damaged: int  # rumah_rusak_berat
    moderately_damaged: int  # rumah_rusak_sedang
    lightly_damaged: int  # rumah_rusak_ringan
    submerged: int  # rumah_terendam

    def __str__(self):
        return f"houses: {self.severely_damaged} severely damaged, {self.moderately_damaged} moderately damaged, {self.lightly_damaged} lightly damaged, {self.submerged} submerged"


@dataclass
class FacilityDamage:
    education: int  # pendidikan
    health: int  # kesehatan
    worship: int  # peribadatan
    general: int  # fasum

    def __str__(self):
        return f"facilities: {self.education} education, {self.health} health, {self.worship} worship, {self.general} general"


@dataclass
class MaterialLoss:
    house: HouseDamage
    facility: FacilityDamage

    def __str__(self):
        return f"{self.house}, {self.facility}"


@dataclass
class Victims:
    died: int  # meninggal
    missing: int  # hilang
    injured: int  # terluka
    suffering: int  # menderita
    evacuated: int  # mengungsi

    def __str__(self):
        return f"{self.died} died, {self.missing} missing, {self.injured} injured, {self.suffering} suffering, {self.evacuated} evacuated"


@dataclass
class DIBIEvent:
    """A fetched and parsed DIBI event. Properties are grouped."""

    def __init__(self, raw: RawEventData):
        self.incident_id = int(re.search(r"/d/r/(\d+)", raw["kejadian"]).group(1))
        self.disaster_type = raw["idj"]
        self.location = Location(
            raw["level0"], raw["level1"], raw["nwil"], raw["nprop"], raw["nkab"]
        )
        self.datetime = datetime.strptime(raw["tglan"], "%Y-%m-%d")
        self.raw_html_kejadian = raw["kejadian"]
        self.raw_html_kib = raw["kib"]
        self.victims = Victims(
            died=raw["meninggal"],
            missing=raw["hilang"],
            injured=raw["terluka"],
            suffering=raw["menderita"],
            evacuated=raw["mengungsi"],
        )
        self.material_loss = MaterialLoss(
            house=HouseDamage(
                severely_damaged=raw["rumah_rusak_berat"],
                moderately_damaged=raw["rumah_rusak_sedang"],
                lightly_damaged=raw["rumah_rusak_ringan"],
                submerged=raw["rumah_terendam"],
            ),
            facility=FacilityDamage(
                education=raw["pendidikan"],
                health=raw["kesehatan"],
                worship=raw["peribadatan"],
                general=raw["fasum"],
            ),
        )
        self.sql = raw["sql"]
        self.act = raw["act"]
        self.set_gadm_district_gid2()

    incident_id: DisasterType
    disaster_type: int  # idj
    location: Location
    datetime: datetime  # tglan
    raw_html_kejadian: str  # incident
    raw_html_kib: str  # kib
    victims: Victims
    material_loss: MaterialLoss
    sql: str
    act: str
    submitter: str = None  # name of the person who submitted the event
    event_details_fetched: bool = False  # See: pull_event_details.

    def __str__(self):
        ignore_keys = ["raw_html_kejadian", "raw_html_kib", "sql", "act"]
        return f"Incident {self.incident_id}:\n" + "\n".join(
            "  %s: %s" % item
            for item in vars(self).items()
            if item[0] not in ignore_keys
        )

    def set_gadm_district_gid2(self):
        self.location.gadm_district_gid2 = gadm_location_manager.get_district_gid2(
            self.location.province, self.location.district
        )
        if self.location.gadm_district_gid2 is None:
            self.pull_event_details()
            self.location.gadm_district_gid2 = gadm_location_manager.get_district_gid2(
                self.location.province,
                self.location.district,
                self.location.longitude,
                self.location.latitude,
            )

    def pull_event_details(self):
        """Fetch additional event details from this specific event's details page
        and set new properties in this object.

        Note: This triggers a request to the DIBI v3 API.
        """
        if self.event_details_fetched:
            return

        response = SESSION.get(f"https://dibi.bnpb.go.id/d/r/{self.incident_id}")
        if response.status_code != 200:
            raise Exception(f"Failed to fetch event details: {response.status_code}")

        # Only an HTML response is available from the API, so we have to parse.
        soup = BeautifulSoup(response.text, "html.parser")

        lat_input = soup.find("input", {"name": "f[lat]"}).get("value")
        lng_input = soup.find("input", {"name": "f[lng]"}).get("value")
        self.location.latitude = float(lat_input)
        self.location.longitude = float(lng_input)

        submitter_name = soup.find("input", {"name": "f[input_oleh]"}).get("value")
        self.submitter = submitter_name

        time_str = soup.find("input", {"name": "f[jam]"}).get("value")
        if time_str:
            time_obj = datetime.strptime(time_str, "%H.%M").time()
            if time_obj:
                self.datetime = datetime.combine(self.datetime.date(), time_obj)

        self.event_details_fetched = True
