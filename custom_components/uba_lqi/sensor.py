"""Sensor platform for UBA Luftqualitätsindex (LQI)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    API_DOCS_URL,
    CONF_AREA_ID,
    AQI_OPTIONS,
    CONF_COMPONENT_DETAILS,
    CONF_SELECTED_STATIONS,
    CONF_STATION_DETAILS,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)
from .coordinator import UbaLqiDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class UbaLqiSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    extra_attributes_fn: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any] | None] | None = None
    enum_options: list[str] | None = None
    display_precision: int | None = None


BASE_SENSOR_DESCRIPTIONS: tuple[UbaLqiSensorDescription, ...] = (
    UbaLqiSensorDescription(
        key="lqi_label",
        name="Luftqualitätsindex (LQI)",
        icon="mdi:weather-hazy",
        device_class=SensorDeviceClass.ENUM,
        value_fn=lambda station: station.get("label") or "unbekannt",
        enum_options=AQI_OPTIONS,
        extra_attributes_fn=lambda station, station_info: _primary_attributes(station, station_info),
    ),
    UbaLqiSensorDescription(
        key="lqi_numeric",
        name="LQI numerisch",
        icon="mdi:numeric",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        value_fn=lambda station: station.get("index"),
    ),
    UbaLqiSensorDescription(
        key="map_lqi",
        name="Karte (LQI)",
        icon="mdi:map-marker",
        entity_registry_enabled_default=True,
        value_fn=lambda station: station.get("index"),
        extra_attributes_fn=lambda station, station_info: _map_attributes(station, station_info),
        display_precision=0,
    ),
    UbaLqiSensorDescription(
        key="measurement_start",
        name="Messbeginn",
        icon="mdi:clock-start",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        value_fn=lambda station: _parse_datetime(station.get("start_time")),
    ),
    UbaLqiSensorDescription(
        key="measurement_end",
        name="Messende",
        icon="mdi:clock-end",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        value_fn=lambda station: _parse_datetime(station.get("end_time")),
    ),
    UbaLqiSensorDescription(
        key="distance",
        name="Entfernung",
        icon="mdi:map-marker-distance",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement="km",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        value_fn=lambda station: station.get("distance_km"),
        display_precision=2,
    ),
    UbaLqiSensorDescription(
        key="data_completeness",
        name="Datenvollständigkeit",
        icon="mdi:database-check",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
        value_fn=lambda station: "vollständig" if station.get("incomplete") == 0 else "unvollständig",
        enum_options=["vollständig", "unvollständig"],
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: UbaLqiDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    merged = {**entry.data, **entry.options}
    station_details: dict[str, dict[str, Any]] = merged.get(CONF_STATION_DETAILS, {})
    component_details: dict[str, dict[str, Any]] = merged.get(CONF_COMPONENT_DETAILS, {})
    area_name = _selected_area_name(hass, merged.get(CONF_AREA_ID))

    entities: list[SensorEntity] = []
    for station_id in merged.get(CONF_SELECTED_STATIONS, []):
        station_id = str(station_id)
        station_info = station_details.get(station_id, {})
        for description in BASE_SENSOR_DESCRIPTIONS:
            entities.append(UbaLqiStationSensor(coordinator, description, station_id, station_info, area_name))

        for component_id, component in component_details.items():
            entities.append(UbaLqiComponentSensor(coordinator, station_id, station_info, str(component_id), component, area_name))

    async_add_entities(entities)


class UbaLqiStationSensor(CoordinatorEntity[UbaLqiDataUpdateCoordinator], SensorEntity):
    entity_description: UbaLqiSensorDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator: UbaLqiDataUpdateCoordinator, description: UbaLqiSensorDescription, station_id: str, station_info: dict[str, Any], area_name: str | None) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._station_id = station_id
        self._station_info = station_info
        self._area_name = area_name
        self._attr_unique_id = f"{station_id}_{description.key}"
        if description.enum_options is not None:
            self._attr_options = description.enum_options
        if description.display_precision is not None:
            self._attr_suggested_display_precision = description.display_precision

    @property
    def available(self) -> bool:
        return self._station_id in self.coordinator.data

    @property
    def native_value(self) -> Any:
        station = self.coordinator.data.get(self._station_id)
        if station is None:
            return None
        return self.entity_description.value_fn(station)

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._station_id, self._station_info, self._area_name)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.extra_attributes_fn is None:
            return None
        station = self.coordinator.data.get(self._station_id, {})
        return self.entity_description.extra_attributes_fn(station, self._station_info)


class UbaLqiComponentSensor(CoordinatorEntity[UbaLqiDataUpdateCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: UbaLqiDataUpdateCoordinator, station_id: str, station_info: dict[str, Any], component_id: str, component_info: dict[str, Any], area_name: str | None) -> None:
        super().__init__(coordinator)
        self._station_id = station_id
        self._station_info = station_info
        self._area_name = area_name
        self._component_id = component_id
        self._component_info = component_info
        self._attr_unique_id = f"{station_id}_component_{component_id}"
        self._attr_name = component_info.get("name") or component_info.get("code") or component_id
        self._attr_icon = "mdi:molecule"
        self._attr_native_unit_of_measurement = component_info.get("unit")
        self._attr_suggested_display_precision = 1

    @property
    def available(self) -> bool:
        station = self.coordinator.data.get(self._station_id)
        return bool(station and self._component_id in station.get("components", {}))

    @property
    def native_value(self) -> float | None:
        component = self._component_state
        return None if component is None else component.get("value")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        component = self._component_state
        if component is None:
            return None
        return {
            "component_id": self._component_id,
            "code": component.get("code") or self._component_info.get("code"),
            "name": component.get("name") or self._component_info.get("name"),
            "index": component.get("index"),
            "threshold_progress": component.get("threshold_progress"),
        }

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self._station_id, self._station_info, self._area_name)

    @property
    def _component_state(self) -> dict[str, Any] | None:
        station = self.coordinator.data.get(self._station_id)
        return None if station is None else station.get("components", {}).get(self._component_id)


def _device_info(station_id: str, station_info: dict[str, Any], area_name: str | None = None) -> DeviceInfo:
    name = station_info.get("name") or station_id
    city = station_info.get("city")
    code = station_info.get("code")
    display_name = name
    if city:
        display_name = f"{name} · {city}"
    if code:
        display_name = f"{display_name} ({code})"
    return DeviceInfo(
        identifiers={(DOMAIN, station_id)},
        manufacturer=MANUFACTURER,
        model=MODEL,
        name=display_name,
        configuration_url=API_DOCS_URL,
        suggested_area=area_name,
    )


def _selected_area_name(hass: HomeAssistant, area_id: str | None) -> str | None:
    if not area_id:
        return None
    area = ar.async_get(hass).async_get_area(area_id)
    return area.name if area is not None else None


def _map_attributes(station: dict[str, Any], station_info: dict[str, Any]) -> dict[str, Any]:
    return {
        "latitude": station_info.get("latitude"),
        "longitude": station_info.get("longitude"),
        "station_id": station.get("station_id") or station_info.get("station_id"),
        "station_code": station_info.get("code"),
        "station_name": station_info.get("name"),
        "city": station_info.get("city"),
        "lqi": station.get("index"),
        "lqi_label": station.get("label"),
        "distance_km": station.get("distance_km"),
    }


def _primary_attributes(station: dict[str, Any], station_info: dict[str, Any]) -> dict[str, Any]:
    components = {}
    for component in station.get("components", {}).values():
        code = component.get("code") or component.get("component_id")
        components[str(code)] = {
            "name": component.get("name"),
            "value": component.get("value"),
            "unit": component.get("unit"),
            "index": component.get("index"),
            "threshold_progress": component.get("threshold_progress"),
        }
    latitude = station_info.get("latitude")
    longitude = station_info.get("longitude")
    coordinate_text = None
    if latitude is not None and longitude is not None:
        coordinate_text = f"{float(latitude):.5f}, {float(longitude):.5f}"
    return {
        "station_id": station.get("station_id"),
        "stationscode": station_info.get("code"),
        "name": station_info.get("name"),
        "stadt": station_info.get("city"),
        "netz": station_info.get("network_name"),
        "stationsumgebung": station_info.get("station_setting_name"),
        "stationstyp": station_info.get("station_type_name"),
        "adresse": _format_address(station_info),
        "koordinaten": coordinate_text,
        "latitude": latitude,
        "longitude": longitude,
        "entfernung_km": station.get("distance_km"),
        "lqi_nummer": station.get("index"),
        "datenvollstaendig": station.get("incomplete") == 0 if station.get("incomplete") is not None else None,
        "messbeginn": station.get("start_time"),
        "messende": station.get("end_time"),
        "komponenten": components,
    }


def _format_address(station_info: dict[str, Any]) -> str | None:
    first = " ".join(part for part in [station_info.get("street"), station_info.get("street_number")] if part)
    second = " ".join(part for part in [station_info.get("zip_code"), station_info.get("city")] if part)
    text = ", ".join(part for part in [first, second] if part)
    return text or None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    dt_value = dt_util.parse_datetime(value)
    if dt_value is None:
        dt_value = dt_util.parse_datetime(value.replace(" ", "T"))
    if dt_value is None:
        return None
    return dt_util.as_utc(dt_value) if dt_value.tzinfo is None else dt_value
