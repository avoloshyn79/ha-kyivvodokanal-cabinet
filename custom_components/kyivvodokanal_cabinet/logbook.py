"""Logbook support for Kyivvodokanal Cabinet."""

from homeassistant.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from homeassistant.core import callback

from .const import DOMAIN, EVENT_DATA_UPDATED, EVENT_READINGS_FAILED, EVENT_READINGS_SUBMITTED


@callback
def async_describe_events(hass, async_describe_event):
    """Describe logbook events."""

    @callback
    def async_describe_data_updated(event):
        debt = event.data.get("debt")
        amount = event.data.get("amount_to_pay")
        parts = ["Дані оновлено"]
        if debt is not None:
            parts.append(f"борг: {debt} грн")
        if amount is not None:
            parts.append(f"до сплати: {amount} грн")
        return {
            LOGBOOK_ENTRY_NAME: "Kyivvodokanal",
            LOGBOOK_ENTRY_MESSAGE: ". ".join(parts) if len(parts) == 1 else f"{parts[0]}. {', '.join(parts[1:])}",
        }

    @callback
    def async_describe_readings_submitted(event):
        counter_id = event.data.get("counter_id")
        value = event.data.get("reading_value")
        return {
            LOGBOOK_ENTRY_NAME: "Kyivvodokanal",
            LOGBOOK_ENTRY_MESSAGE: f"Передано показання лічильника {counter_id}: {value} м³",
        }

    @callback
    def async_describe_readings_failed(event):
        counter_id = event.data.get("counter_id")
        error = event.data.get("error", "невідома помилка")
        return {
            LOGBOOK_ENTRY_NAME: "Kyivvodokanal",
            LOGBOOK_ENTRY_MESSAGE: f"Помилка передачі показань лічильника {counter_id}: {error}",
        }

    async_describe_event(DOMAIN, EVENT_DATA_UPDATED, async_describe_data_updated)
    async_describe_event(DOMAIN, EVENT_READINGS_SUBMITTED, async_describe_readings_submitted)
    async_describe_event(DOMAIN, EVENT_READINGS_FAILED, async_describe_readings_failed)
