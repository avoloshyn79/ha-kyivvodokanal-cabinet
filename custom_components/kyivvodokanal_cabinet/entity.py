"""Base entity for Kyivvodokanal Cabinet integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KyivvodokanalDataUpdateCoordinator


class KyivvodokanalEntity(CoordinatorEntity[KyivvodokanalDataUpdateCoordinator]):
    """Base entity for Kyivvodokanal entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: KyivvodokanalDataUpdateCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = config_entry

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "Kyivvodokanal Kyiv",
            "model": "Customer Cabinet",
        }           