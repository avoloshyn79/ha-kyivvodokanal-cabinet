"""Config flow for Kyivvodokanal Cabinet integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig

from .api import KyivvodokanalApiClient, KyivvodokanalApiError, KyivvodokanalAuthenticationError
from .const import (
    CONF_CABINET_URL,
    CONF_COOKIE,
    CONF_SCAN_INTERVAL,
    CONF_AUTH_HEADER,
    DEFAULT_CABINET_URL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)


class KyivvodokanalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kyivvodokanal Cabinet."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Mapping[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_CABINET_URL])
            self._abort_if_unique_id_configured()

            if await self._async_validate_input(user_input, errors):
                data = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_CABINET_URL: user_input[CONF_CABINET_URL],
                    CONF_COOKIE: user_input.get(CONF_COOKIE),
                    CONF_AUTH_HEADER: user_input.get(CONF_AUTH_HEADER),
                }
                options = {CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]}
                return self.async_create_entry(title=user_input[CONF_NAME], data=data, options=options)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(CONF_CABINET_URL, default=DEFAULT_CABINET_URL): str,
                    vol.Required(CONF_COOKIE): str,
                    vol.Optional(CONF_AUTH_HEADER): str,
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=DEFAULT_SCAN_INTERVAL_MINUTES,
                    ): NumberSelector(
                        NumberSelectorConfig(min=5, max=1440, mode="box", step=5)
                    ),
                }
            ),
            errors=errors,
        )

    async def _async_validate_input(
        self, user_input: Mapping[str, Any], errors: dict[str, str]
    ) -> bool:
        session = async_get_clientsession(self.hass)
        client = KyivvodokanalApiClient(
            session=session,
            cabinet_url=user_input[CONF_CABINET_URL],
            cookie=user_input.get(CONF_COOKIE),
            auth_header=user_input.get(CONF_AUTH_HEADER),
        )
        try:
            await client.async_get_finance_partners()
        except KyivvodokanalAuthenticationError:
            errors["base"] = "auth"
            return False
        except KyivvodokanalApiError:
            errors["base"] = "cannot_connect"
            return False
        return True

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return KyivvodokanalOptionsFlow(config_entry)


class KyivvodokanalOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Kyivvodokanal Cabinet."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: Mapping[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            test_data = {
                CONF_CABINET_URL: self._entry.data[CONF_CABINET_URL],
                CONF_COOKIE: user_input[CONF_COOKIE],
                CONF_AUTH_HEADER: user_input.get(CONF_AUTH_HEADER) or None,
            }
            if await self._async_validate_input(test_data, errors):
                new_data = {
                    **self._entry.data,
                    CONF_COOKIE: user_input[CONF_COOKIE],
                    CONF_AUTH_HEADER: user_input.get(CONF_AUTH_HEADER) or None,
                }
                self.hass.config_entries.async_update_entry(self._entry, data=new_data)
                return self.async_create_entry(
                    title="",
                    data={CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]},
                )

        current_cookie = self._entry.data.get(CONF_COOKIE, "")
        current_auth = self._entry.data.get(CONF_AUTH_HEADER) or ""

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COOKIE, default=current_cookie): str,
                    vol.Optional(
                        CONF_AUTH_HEADER,
                        description={"suggested_value": current_auth},
                    ): str,
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self._entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(min=5, max=1440, mode="box", step=5)
                    ),
                }
            ),
            errors=errors,
        )

    async def _async_validate_input(
        self, user_input: Mapping[str, Any], errors: dict[str, str]
    ) -> bool:
        session = async_get_clientsession(self.hass)
        client = KyivvodokanalApiClient(
            session=session,
            cabinet_url=user_input[CONF_CABINET_URL],
            cookie=user_input.get(CONF_COOKIE),
            auth_header=user_input.get(CONF_AUTH_HEADER),
        )
        try:
            await client.async_get_finance_partners()
        except KyivvodokanalAuthenticationError:
            errors["base"] = "auth"
            return False
        except KyivvodokanalApiError:
            errors["base"] = "cannot_connect"
            return False
        return True