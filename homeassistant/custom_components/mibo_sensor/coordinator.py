"""DataUpdateCoordinator do mibo_sensor."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MiboApiError, get_sensor_properties
from .const import CONF_DEVICE_ID, CONF_PRODUCT_ID, CONF_USERNAME, DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

type MiboConfigEntry = ConfigEntry["MiboDataUpdateCoordinator"]


class MiboDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    """Busca as properties do sensor periodicamente."""

    config_entry: MiboConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: MiboConfigEntry) -> None:
        self.username = config_entry.data[CONF_USERNAME]
        self.product_id = config_entry.data[CONF_PRODUCT_ID]
        self.device_id = config_entry.data[CONF_DEVICE_ID]
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )

    async def _async_update_data(self) -> dict:
        try:
            return await self.hass.async_add_executor_job(
                get_sensor_properties, self.username, self.product_id, self.device_id,
            )
        except MiboApiError as err:
            raise UpdateFailed(str(err)) from err
