"""Integracao mibo_sensor -- le sensores Zigbee pareados via hub Mibo/Dahua
(ex: Intelbras MTU 1001 + MCA 1002) direto da API nao-oficial da nuvem."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .coordinator import MiboConfigEntry, MiboDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: MiboConfigEntry) -> bool:
    coordinator = MiboDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MiboConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
