"""The Kyivvodokanal Cabinet integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .api import KyivvodokanalApiError
from .coordinator import KyivvodokanalDataUpdateCoordinator
from .const import DOMAIN, EVENT_READINGS_FAILED, EVENT_READINGS_SUBMITTED

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kyivvodokanal from a config entry."""
    _LOGGER.debug("Setting up Kyivvodokanal Cabinet integration for entry ID %s", entry.entry_id)
    coordinator = KyivvodokanalDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register update service
    async def async_update_data(service_call: ServiceCall) -> None:
        """Update data from Kyivvodokanal API."""
        _LOGGER.debug("Manual update requested for Kyivvodokanal Cabinet")
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, "update_data", async_update_data, schema={}
    )

    # Register submit readings service
    async def async_submit_readings(service_call: ServiceCall) -> None:
        """Submit meter readings to Kyivvodokanal API."""
        counter_id = service_call.data.get("counter_id")
        reading_value = service_call.data.get("reading_value")
        factor_type_code = service_call.data.get("factor_type_code")

        if not counter_id or reading_value is None:
            _LOGGER.error("Missing required parameters: counter_id and reading_value")
            return

        try:
            # Prepare reading data
            reading_data = {
                "counterId": int(counter_id),
                "factor": float(reading_value),
            }
            if factor_type_code:
                reading_data["factorTypeCode"] = factor_type_code

            readings = [reading_data]

            # Submit readings
            api_client = coordinator.api
            result = await api_client.async_submit_readings(readings)

            _LOGGER.info("Successfully submitted reading for counter %s: %s", counter_id, reading_value)
            hass.bus.async_fire(
                EVENT_READINGS_SUBMITTED,
                {"counter_id": counter_id, "reading_value": reading_value},
            )

            # Refresh data after submission
            await coordinator.async_request_refresh()

        except KyivvodokanalApiError as err:
            _LOGGER.error("Failed to submit readings: %s", err)
            hass.bus.async_fire(
                EVENT_READINGS_FAILED,
                {"counter_id": counter_id, "error": str(err)},
            )
        except ValueError as err:
            _LOGGER.error("Invalid parameter format: %s", err)
            hass.bus.async_fire(
                EVENT_READINGS_FAILED,
                {"counter_id": counter_id, "error": str(err)},
            )
        except Exception as err:
            _LOGGER.error("Unexpected error submitting readings: %s", err)
            hass.bus.async_fire(
                EVENT_READINGS_FAILED,
                {"counter_id": counter_id, "error": str(err)},
            )

    hass.services.async_register(
        DOMAIN, "submit_readings", async_submit_readings
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("Finished setting up Kyivvodokanal Cabinet integration for entry ID %s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
