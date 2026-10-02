"""The UBA Luftqualitätsindex (LQI) integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import UbaLqiApiClient
from .const import DOMAIN
from .coordinator import UbaLqiDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.GEO_LOCATION]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    api = UbaLqiApiClient(session)
    coordinator = UbaLqiDataUpdateCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
