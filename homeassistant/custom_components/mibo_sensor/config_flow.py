"""Config flow do mibo_sensor."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import MiboApiError, get_sensor_properties
from .const import CONF_DEVICE_ID, CONF_PRODUCT_ID, CONF_USERNAME, DEFAULT_NAME, DOMAIN

STEP_USER_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PRODUCT_ID): str,
    vol.Required(CONF_DEVICE_ID): str,
})


class CannotConnect(Exception):
    """Nao foi possivel falar com a API."""


async def _testar_conexao(hass: HomeAssistant, data: dict[str, Any]) -> None:
    def _call():
        return get_sensor_properties(data[CONF_USERNAME], data[CONF_PRODUCT_ID], data[CONF_DEVICE_ID])

    try:
        await hass.async_add_executor_job(_call)
    except MiboApiError as err:
        raise CannotConnect from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Fluxo de configuracao do mibo_sensor."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await _testar_conexao(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors,
            description_placeholders={
                "info": "username/product_id/device_id sao obtidos interceptando o trafego "
                        "do app Mibo uma vez -- veja METHODOLOGY.md no repositorio."
            },
        )
