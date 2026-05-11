"""Sensor platform for Kyivvodokanal Cabinet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KyivvodokanalDataUpdateCoordinator
from .entity import KyivvodokanalEntity


@dataclass(frozen=True)
class KyivvodokanalSensorDescription(SensorEntityDescription):
    """Describe Kyivvodokanal sensor."""
    value_key: str = ""


SENSORS: tuple[KyivvodokanalSensorDescription, ...] = (
    KyivvodokanalSensorDescription(
        key="last_payment_date",
        translation_key="last_payment_date",
        name="Last Payment Date",
        value_key="last_payment_date",
        icon="mdi:calendar-month-outline",
        device_class="date",
    ),
    KyivvodokanalSensorDescription(
        key="last_transmission_date",
        translation_key="last_transmission_date",
        name="Last Transmission Date",
        value_key="last_transmission_date",
        icon="mdi:calendar-month-outline",
        device_class="date",
    ),
    KyivvodokanalSensorDescription(
        key="hot_water_last_transmission_date",
        translation_key="hot_water_last_transmission_date",
        name="Hot Water Last Transmission Date",
        value_key="hot_water_last_transmission_date",
        icon="mdi:calendar-month-outline",
        device_class="date",
    ),
    KyivvodokanalSensorDescription(
        key="cold_water_last_transmission_date",
        translation_key="cold_water_last_transmission_date",
        name="Cold Water Last Transmission Date",
        value_key="cold_water_last_transmission_date",
        icon="mdi:calendar-month-outline",
        device_class="date",
    ),
    KyivvodokanalSensorDescription(
        key="service_provider_name",
        translation_key="service_provider_name",
        name="Water Provider",
        value_key="service_provider_name",
        icon="mdi:water-opacity",
    ),
    KyivvodokanalSensorDescription(
        key="tariff_cold_water",
        translation_key="tariff_cold_water",
        name="Tariff Cold Water",
        value_key="tariff_cold_water",
        icon="mdi:water-percent",
        native_unit_of_measurement="UAH/m³",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KyivvodokanalSensorDescription(
        key="tariff_sewerage",
        translation_key="tariff_sewerage",
        name="Tariff Sewerage",
        value_key="tariff_sewerage",
        icon="mdi:water-percent",
        native_unit_of_measurement="UAH/m³",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KyivvodokanalSensorDescription(
        key="tariff_abone",
        translation_key="tariff_abone",
        name="Tariff Abonement",
        value_key="tariff_abone",
        icon="mdi:cash-multiple",
        native_unit_of_measurement="UAH",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KyivvodokanalSensorDescription(
        key="debt",
        translation_key="debt",
        name="Debt",
        value_key="debt",
        icon="mdi:cash-minus",
        native_unit_of_measurement="UAH",
        state_class=SensorStateClass.MEASUREMENT,
    ),

    KyivvodokanalSensorDescription(
        key="amount_to_pay",
        translation_key="amount_to_pay",
        name="Amount to Pay",
        value_key="amount_to_pay",
        icon="mdi:cash-check",
        native_unit_of_measurement="UAH",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KyivvodokanalSensorDescription(
        key="hot_water_counter_number",
        translation_key="hot_water_counter_number",
        name="Hot Water Counter Number",
        value_key="hot_water_counter_number",
        icon="mdi:counter",
    ),
    KyivvodokanalSensorDescription(
        key="hot_water_counter_check_date",
        translation_key="hot_water_counter_check_date",
        name="Hot Water Counter Check Date",
        value_key="hot_water_counter_check_date",
        icon="mdi:calendar-check",
    ),
    KyivvodokanalSensorDescription(
        key="hot_water_counter_next_check_date",
        translation_key="hot_water_counter_next_check_date",
        name="Hot Water Counter Next Check Date",
        value_key="hot_water_counter_next_check_date",
        icon="mdi:calendar-check",
    ),
    KyivvodokanalSensorDescription(
        key="hot_water_last_reading",
        translation_key="hot_water_last_reading",
        name="Hot Water Last Reading",
        value_key="hot_water_last_reading",
        icon="mdi:water-pump",
        native_unit_of_measurement="m³",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KyivvodokanalSensorDescription(
        key="cold_water_counter_number",
        translation_key="cold_water_counter_number",
        name="Cold Water Counter Number",
        value_key="cold_water_counter_number",
        icon="mdi:counter",
    ),
    KyivvodokanalSensorDescription(
        key="cold_water_counter_check_date",
        translation_key="cold_water_counter_check_date",
        name="Cold Water Counter Check Date",
        value_key="cold_water_counter_check_date",
        icon="mdi:calendar-check",
    ),
    KyivvodokanalSensorDescription(
        key="cold_water_counter_next_check_date",
        translation_key="cold_water_counter_next_check_date",
        name="Cold Water Counter Next Check Date",
        value_key="cold_water_counter_next_check_date",
        icon="mdi:calendar-check",
    ),
    KyivvodokanalSensorDescription(
        key="cold_water_last_reading",
        translation_key="cold_water_last_reading",
        name="Cold Water Last Reading",
        value_key="cold_water_last_reading",
        icon="mdi:water-pump",
        native_unit_of_measurement="m³",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities for Kyivvodokanal."""
    coordinator: KyivvodokanalDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[KyivvodokanalBaseSensor] = [KyivvodokanalSensor(coordinator, config_entry, description) for description in SENSORS]
    async_add_entities(entities)


class KyivvodokanalBaseSensor(KyivvodokanalEntity, SensorEntity):
    """Base entity for Kyivvodokanal sensors."""

    def __init__(self, coordinator: KyivvodokanalDataUpdateCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)


class KyivvodokanalSensor(KyivvodokanalBaseSensor):
    """Sensor for Kyivvodokanal data."""

    entity_description: KyivvodokanalSensorDescription

    def __init__(
        self,
        coordinator: KyivvodokanalDataUpdateCoordinator,
        config_entry: ConfigEntry,
        description: KyivvodokanalSensorDescription,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self.entity_description = description
        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> float | str | None:
        data = self.coordinator.data or {}
        return data.get(self.entity_description.value_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self.coordinator.data or {}
        if self.entity_description.key == "payments_count":
            return {
                "finance_partners": [partner.get("name") for partner in data.get("finance_partners", [])],
                "invoice_account_code": next(
                    (
                        payment.get("invoiceAccount", {}).get("code")
                        for payment in data.get("payments", [])
                        if payment.get("invoiceAccount")
                    ),
                    None,
                ),
            }
        return None