"""Binary sensor (online) do mibo_sensor."""
from __future__ import annotations

from typing import override

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, DOMAIN, DP_ONLINE
from .coordinator import MiboConfigEntry, MiboDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MiboConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = config_entry.runtime_data
    async_add_entities([MiboOnlineSensor(coordinator, config_entry.data[CONF_DEVICE_ID])])


class MiboOnlineSensor(CoordinatorEntity[MiboDataUpdateCoordinator], BinarySensorEntity):
    """Indica se o sensor esta online, segundo a nuvem Mibo."""

    _attr_has_entity_name = True
    _attr_translation_key = "online"
    _attr_force_update = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: MiboDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_id}_online"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    @property
    @override
    def is_on(self) -> bool:
        return self.coordinator.data.get(DP_ONLINE) == 1
