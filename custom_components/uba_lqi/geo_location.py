"""Geolocation platform for UBA Luftqualitätsindex (LQI)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
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


class UbaLqiGeolocationEntity(GeolocationEvent):
    """Represent one UBA air-quality measurement station on HA maps."""

    _attr_should_poll = False
    _attr_source = SOURCE
    _attr_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_icon = "mdi:air-filter"

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
        self._attr_latitude = _as_float(station_info.get("latitude"))
        self._attr_longitude = _as_float(station_info.get("longitude"))
        self._sync_from_coordinator()

    @property
    def available(self) -> bool:
        """A selected station remains locatable even if a measurement is missing."""
        return self._attr_latitude is not None and self._attr_longitude is not None

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
        distance = station.get("distance_km")
        self._attr_distance = _as_float(distance)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose attributes usable by map label_mode: attribute."""
        station = self._coordinator.data.get(self._station_id, {})
        return {
            "lqi": station.get("index"),
            "lqi_label": station.get("label"),
            "station_id": station.get("station_id") or self._station_id,
            "station_code": self._station_info.get("code"),
            "station_name": self._station_info.get("name"),
            "city": self._station_info.get("city"),
            "distance_km": station.get("distance_km"),
        }


def _selected_area_name(hass: HomeAssistant, area_id: str | None) -> str | None:
    if not area_id:
        return None
    area = ar.async_get(hass).async_get_area(area_id)
    return area.name if area is not None else None


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
