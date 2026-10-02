"""Geolocation platform for UBA Luftqualitätsindex (LQI)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    API_DOCS_URL,
    CONF_AREA_ID,
    CONF_SELECTED_STATIONS,
    CONF_STATION_DETAILS,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)
from .coordinator import UbaLqiDataUpdateCoordinator

SOURCE = DOMAIN

LQI_COLORS: dict[int, tuple[str, str]] = {
    0: ("#2E7D32", "#FFFFFF"),
    1: ("#7CB342", "#102000"),
    2: ("#FBC02D", "#1F1F1F"),
    3: ("#EF6C00", "#FFFFFF"),
    4: ("#C62828", "#FFFFFF"),
}
UNKNOWN_COLOR = ("#616161", "#FFFFFF")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UBA LQI geolocation entities."""
    coordinator: UbaLqiDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    merged = {**entry.data, **entry.options}
    station_details: dict[str, dict[str, Any]] = merged.get(CONF_STATION_DETAILS, {})
    area_name = _selected_area_name(hass, merged.get(CONF_AREA_ID))

    async_add_entities(
        [
            UbaLqiGeolocationEntity(
                coordinator=coordinator,
                station_id=str(station_id),
                station_info=station_details.get(str(station_id), {}),
                area_name=area_name,
            )
            for station_id in merged.get(CONF_SELECTED_STATIONS, [])
        ]
    )


class UbaLqiGeolocationEntity(SensorEntity):
    """Represent one UBA air-quality station as a map-ready numeric entity.

    The entity deliberately lives on the geo_location platform so all selected
    stations can be added to one map through geo_location_sources. Its state is
    the measured numeric LQI instead of the distance, which makes the normal
    Home Assistant more-info dialog show the LQI value and its history.
    """

    _attr_should_poll = False
    _attr_icon = "mdi:air-filter"
    _attr_suggested_display_precision = 0

    def __init__(
        self,
        coordinator: UbaLqiDataUpdateCoordinator,
        station_id: str,
        station_info: dict[str, Any],
        area_name: str | None,
    ) -> None:
        self._coordinator = coordinator
        self._station_id = station_id
        self._station_info = station_info
        self._area_name = area_name

        self._attr_unique_id = f"{station_id}_geo_location"
        self._attr_name = (
            station_info.get("name")
            or station_info.get("code")
            or f"UBA LQI {station_id}"
        )
        self._latitude = _as_float(station_info.get("latitude"))
        self._longitude = _as_float(station_info.get("longitude"))
        self._attr_entity_picture = _lqi_marker_picture(None)
        self._sync_from_coordinator()

    @property
    def available(self) -> bool:
        """Keep the station on the map whenever its coordinates are known."""
        return self._latitude is not None and self._longitude is not None

    @property
    def native_value(self) -> int | None:
        """Return the numeric UBA LQI so more-info and history use the LQI."""
        station = self._coordinator.data.get(self._station_id, {})
        return _as_int(station.get("index"))

    @property
    def device_info(self) -> DeviceInfo:
        """Attach the map entity to the same station device as the sensors."""
        name = self._station_info.get("name") or self._station_id
        city = self._station_info.get("city")
        code = self._station_info.get("code")
        display_name = name
        if city:
            display_name = f"{name} · {city}"
        if code:
            display_name = f"{display_name} ({code})"
        return DeviceInfo(
            identifiers={(DOMAIN, self._station_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=display_name,
            configuration_url=API_DOCS_URL,
            suggested_area=self._area_name,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        self._sync_from_coordinator()
        self.async_write_ha_state()

    def _sync_from_coordinator(self) -> None:
        station = self._coordinator.data.get(self._station_id, {})
        self._attr_entity_picture = _lqi_marker_picture(_as_int(station.get("index")))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose map location and station metadata."""
        station = self._coordinator.data.get(self._station_id, {})
        return {
            "source": SOURCE,
            "latitude": self._latitude,
            "longitude": self._longitude,
            "lqi": _as_int(station.get("index")),
            "lqi_label": station.get("label"),
            "station_id": station.get("station_id") or self._station_id,
            "station_code": self._station_info.get("code"),
            "station_name": self._station_info.get("name"),
            "city": self._station_info.get("city"),
            "distance_km": station.get("distance_km"),
            "measurement_start": station.get("start_time"),
            "measurement_end": station.get("end_time"),
        }


def _lqi_marker_picture(index: int | None) -> str:
    """Return a compact SVG marker with the LQI number in the center."""
    background, foreground = LQI_COLORS.get(index, UNKNOWN_COLOR)
    label = str(index) if index is not None else "?"
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" '
        'viewBox="0 0 64 64">'
        f'<circle cx="32" cy="32" r="29" fill="{background}" '
        'stroke="#FFFFFF" stroke-width="4"/>'
        f'<text x="32" y="42" text-anchor="middle" fill="{foreground}" '
        'font-family="Arial,sans-serif" font-size="32" font-weight="700">'
        f"{label}</text></svg>"
    )
    return f"data:image/svg+xml;charset=UTF-8,{quote(svg, safe='')}"


def _selected_area_name(hass: HomeAssistant, area_id: str | None) -> str | None:
    if not area_id:
        return None
    area = ar.async_get(hass).async_get_area(area_id)
    return area.name if area is not None else None


def _as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
