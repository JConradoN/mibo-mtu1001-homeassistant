"""Sensores do mibo_sensor."""
from __future__ import annotations

from dataclasses import dataclass
from typing import override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, DOMAIN, DP_BATTERY, DP_HUMIDITY, DP_TEMPERATURE
from .coordinator import MiboConfigEntry, MiboDataUpdateCoordinator


@dataclass(kw_only=True, frozen=True)
class MiboSensorEntityDescription(SensorEntityDescription):
    """Descreve um sensor do mibo_sensor."""

    dp_key: str


SENSOR_DESCRIPTIONS: tuple[MiboSensorEntityDescription, ...] = (
    MiboSensorEntityDescription(
        key="temperature", translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        dp_key=DP_TEMPERATURE,
    ),
    MiboSensorEntityDescription(
        # a nuvem Dahua/Mibo atualiza esse DP com bem menos frequencia que o
        # de temperatura -- pode ficar parado por 10+ min mesmo com tudo
        # funcionando certo aqui. Nao e bug desta integracao, confirmado
        # comparando contra chamada isolada na API em tempo real. Ver README.
        key="humidity", translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        dp_key=DP_HUMIDITY,
    ),
    MiboSensorEntityDescription(
        key="battery", translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        dp_key=DP_BATTERY,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: MiboConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = config_entry.runtime_data
    async_add_entities(
        MiboSensor(coordinator, description, config_entry.data[CONF_DEVICE_ID])
        for description in SENSOR_DESCRIPTIONS
    )


class MiboSensor(CoordinatorEntity[MiboDataUpdateCoordinator], SensorEntity):
    """Sensor do mibo_sensor."""

    _attr_has_entity_name = True
    # por padrao o HA so atualiza o timestamp quando o valor muda -- com
    # polling na nuvem isso faz um sensor estavel (ex: umidade parada numa
    # mesma casa decimal por varios ciclos) parecer "travado" mesmo
    # funcionando certo. force_update garante que o timestamp sempre reflete
    # o ultimo poll de verdade, nao a ultima vez que o valor mudou.
    _attr_force_update = True
    entity_description: MiboSensorEntityDescription

    def __init__(
        self,
        coordinator: MiboDataUpdateCoordinator,
        description: MiboSensorEntityDescription,
        device_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            manufacturer="Mibo/Dahua (ex: Intelbras)",
            name="Sensor Mibo",
            model="MTU 1001 / similar",
        )

    @property
    @override
    def native_value(self) -> float | None:
        return self.coordinator.data.get(self.entity_description.dp_key)
