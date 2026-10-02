"""Constants for the UBA Luftqualitätsindex (LQI) integration."""

from __future__ import annotations

DOMAIN = "uba_lqi"
INTEGRATION_NAME = "UBA Luftqualitätsindex (LQI)"
REPO_URL = "https://github.com/Q14siX/uba_lqi/"
API_DOCS_URL = "https://luftqualitaet.api.bund.dev"

CONF_AREA_ID = "area_id"
CONF_LATITUDE = "latitude"
CONF_LOCATION_SOURCE = "location_source"
CONF_LONGITUDE = "longitude"
CONF_MAX_CANDIDATES = "max_candidates"
CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"
CONF_SEARCH_RADIUS_KM = "search_radius_km"
CONF_SELECTED_STATIONS = "selected_stations"
CONF_STATION_DETAILS = "station_details"
CONF_COMPONENT_DETAILS = "component_details"

DEFAULT_MAX_CANDIDATES = 20
DEFAULT_SCAN_INTERVAL_MINUTES = 30
DEFAULT_SEARCH_RADIUS_KM = 75
DEFAULT_STATION_COUNT = 3

LOCATION_SOURCE_HOME = "home"
LOCATION_SOURCE_MANUAL = "manual"

API_BASE_URLS = [
    "https://www.umweltbundesamt.de/api/air_data/v2",
    "https://umweltbundesamt.api.proxy.bund.dev/api/air_data/v2",
    "https://luftdaten.umweltbundesamt.de/api-proxy",
]
API_TIMEOUT_SECONDS = 30
DEFAULT_LANGUAGE = "de"

AQI_LABELS_DE: dict[int, str] = {
    0: "sehr gut",
    1: "gut",
    2: "mäßig",
    3: "schlecht",
    4: "sehr schlecht",
}
AQI_OPTIONS = ["sehr gut", "gut", "mäßig", "schlecht", "sehr schlecht", "unbekannt"]

MANUFACTURER = "Umweltbundesamt"
MODEL = "Luftmessstation"
