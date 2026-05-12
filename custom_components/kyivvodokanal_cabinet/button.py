"""Button platform for Kyivvodokanal Cabinet integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import KyivvodokanalDataUpdateCoordinator
from .entity import KyivvodokanalEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Kyivvodokanal button."""
    coordinator = hass.data["kyivvodokanal_cabinet"][entry.entry_id]
    async_add_entities([KyivvodokanalUpdateButton(coordinator, entry)])


class KyivvodokanalUpdateButton(KyivvodokanalEntity, ButtonEntity):
    """Button to manually update Kyivvodokanal data."""

    _attr_translation_key = "update_data"

    def __init__(
        self,
        coordinator: KyivvodokanalDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_update_data"
        self._attr_icon = "mdi:refresh"

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Manual update requested via button")
        await self.coordinator.async_refresh()