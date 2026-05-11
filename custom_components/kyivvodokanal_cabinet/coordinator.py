"""Data coordinator for Kyivvodokanal Cabinet."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KyivvodokanalApiClient, KyivvodokanalApiError, KyivvodokanalAuthenticationError
from .const import (
    CONF_CABINET_URL,
    CONF_COOKIE,
    CONF_SCAN_INTERVAL,
    CONF_AUTH_HEADER,
    COUNTER_TYPE_COLD_KEYWORDS,
    COUNTER_TYPE_HOT_KEYWORDS,
    DEFAULT_SERVICE_PROVIDER_CODE,
    DOMAIN,
    EVENT_DATA_UPDATED,
)

_LOGGER = logging.getLogger(__name__)


class KyivvodokanalDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Kyivvodokanal data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        session = async_get_clientsession(hass)
        self.api = KyivvodokanalApiClient(
            session=session,
            cabinet_url=entry.data[CONF_CABINET_URL],
            auth_header=entry.data.get(CONF_AUTH_HEADER),
            cookie=entry.data.get(CONF_COOKIE),
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=entry.options.get(CONF_SCAN_INTERVAL, 360)),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest data from Kyivvodokanal."""
        now = datetime.utcnow()
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now

        try:
            payments = await self.api.async_get_payments_history(
                start_date=start.isoformat() + "Z",
                end_date=end.isoformat() + "Z",
            )
            partners = await self.api.async_get_finance_partners()
        except KyivvodokanalAuthenticationError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except KyivvodokanalApiError as err:
            raise UpdateFailed(str(err)) from err

        service_provider_code, invoice_account_code = self._extract_service_provider_and_invoice_code(payments)
        invoice_amount: dict[str, Any] = {}
        counters: list[dict[str, Any]] = []
        factors: list[dict[str, Any]] = []
        tariffs: list[dict[str, Any]] = []

        if invoice_account_code:
            if not service_provider_code:
                service_provider_code = DEFAULT_SERVICE_PROVIDER_CODE
            invoice_amount = await self.api.async_get_amount_to_pay(
                service_provider_code=service_provider_code,
                invoice_account_code=invoice_account_code,
            )
            counters = await self.api.async_get_counters(
                service_provider_code=service_provider_code,
                invoice_account_code=invoice_account_code,
            )
            factors = await self.api.async_get_counter_factors_history(
                invoice_account_code=invoice_account_code,
                service_provider_code=service_provider_code,
                start_date=start.isoformat() + "Z",
                end_date=end.isoformat() + "Z",
            )
            tariffs = await self.api.async_get_tariffs(
                service_provider_code=service_provider_code,
                invoice_account_code=invoice_account_code,
            )
            _LOGGER.debug("Raw tariffs response: %s", tariffs)

        # Get last factors for each counter
        last_factors: list[dict[str, Any]] = []
        if counters:
            for counter in counters:
                counter_id = counter.get("id")
                if counter_id:
                    try:
                        last_factor = await self.api.async_get_last_factors(str(counter_id))
                        last_factors.append(last_factor)
                    except KyivvodokanalApiError as err:
                        _LOGGER.warning("Failed to get last factors for counter %s: %s", counter_id, err)

        counters_summary, counter_type_by_id = self._parse_counters_summary(counters)

        data = {
            "payments": payments,
            "finance_partners": partners,
            "invoice_amount": invoice_amount,
            "counters": counters,
            "counter_factors": factors,
            "last_factors": last_factors,
            **self._parse_invoice_summary(invoice_amount),
            **self._parse_last_payment_date(payments),
            **self._get_service_provider_name(payments),
            **self._parse_tariffs(tariffs),
            **counters_summary,
            **self._parse_counter_factors_summary(factors, counter_type_by_id),
            **self._parse_last_factors_dates(last_factors, counter_type_by_id),
        }
        _LOGGER.debug("Final coordinator data: tariff_abone=%s", data.get("tariff_abone"))
        self.hass.bus.async_fire(
            EVENT_DATA_UPDATED,
            {
                "debt": data.get("debt"),
                "amount_to_pay": data.get("amount_to_pay"),
            },
        )
        return data

    def _extract_service_provider_and_invoice_code(
        self, payments: list[dict[str, Any]]
    ) -> tuple[str | None, str | None]:
        """Extract service provider and invoice account codes from payments."""
        for item in payments:
            service_provider = item.get("serviceProvider") or {}
            invoice_account = item.get("invoiceAccount") or {}
            service_provider_code = service_provider.get("code")
            invoice_account_code = invoice_account.get("code")
            if service_provider_code and invoice_account_code:
                return service_provider_code, invoice_account_code
        return None, None

    def _parse_invoice_summary(self, invoice_data: dict[str, Any]) -> dict[str, Any]:
        """Parse invoice amount values."""
        return {
            "debt": invoice_data.get("debt"),
            "amount_to_pay": invoice_data.get("amountToPay"),
        }

    def _parse_last_payment_date(self, payments: list[dict[str, Any]]) -> dict[str, Any]:
        """Parse the last payment date from payment history."""
        last_payment_date = None
        
        for payment_item in payments:
            payment_obj = payment_item.get("payment") or {}
            payment_date_str = payment_obj.get("date")
            if not payment_date_str:
                _LOGGER.debug("No payment date found in payment item: %s", payment_item)
                continue
            
            try:
                payment_date = datetime.fromisoformat(payment_date_str.replace("Z", "+00:00"))
                if last_payment_date is None or payment_date > last_payment_date:
                    _LOGGER.debug("Updated last_payment_date to %s", payment_date.strftime('%Y-%m-%d'))
                    last_payment_date = payment_date
            except (ValueError, AttributeError) as err:
                _LOGGER.warning("Failed to parse payment date %s: %s", payment_date_str, err)
                continue
        
        return {
            "last_payment_date": last_payment_date.date() if last_payment_date else None
        }

    def _get_service_provider_name(self, payments: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract service provider name from payments."""
        service_provider_name = None
        
        for payment_item in payments:
            service_provider = payment_item.get("serviceProvider") or {}
            name = service_provider.get("name")
            if name:
                service_provider_name = name
                _LOGGER.debug("Found service provider name: %s", service_provider_name)
                break
        
        return {
            "service_provider_name": service_provider_name
        }

    def _parse_tariffs(self, tariffs: list[dict[str, Any]]) -> dict[str, Any]:
        """Parse tariffs by service type."""
        summary: dict[str, Any] = {
            "tariff_cold_water": None,
            "tariff_sewerage": None,
            "tariff_abone": None,
        }
        _LOGGER.debug("Parsing tariffs. Tariffs count: %d", len(tariffs))
        
        for tariff in tariffs:
            _LOGGER.debug("Processing tariff: %s", tariff)
            invoice_account = tariff.get("invoiceAccount") or {}
            invoice_account_code = invoice_account.get("code", "")
            _LOGGER.debug("Tariff invoice_account_code: %s", invoice_account_code)
            
            service_type = tariff.get("serviceType") or {}
            service_type_name = service_type.get("name", "").lower()
            service_code = tariff.get("service", {}).get("code", "")
            sub_service = tariff.get("subService") or {}
            sub_service_name = sub_service.get("name", "").lower()
            tariff_amount = tariff.get("tariffAmount")
            
            if tariff_amount is None:
                continue
            
            service = tariff.get("service") or {}
            service_name = service.get("name", "").lower()
            _LOGGER.debug("Tariff service details: name=%s, code=%s, type_name=%s", service_name, service_code, service_type_name)
            
            # Абонплата - має serviceType.name = "Абонплата", service.code = "35" або service.name містить "абонентське"
            if ("абон" in service_type_name or 
                service_code == "35" or 
                "абонентське" in service_name):
                summary["tariff_abone"] = tariff_amount
                _LOGGER.debug("Found abonement tariff: %s (service_code: %s, service_name: %s)", tariff_amount, service_code, service_name)
            # Водовідведення - має subService.name з "водовідведення" або "каналіз"
            elif "водовідведення" in sub_service_name or "каналіз" in sub_service_name:
                summary["tariff_sewerage"] = tariff_amount
                _LOGGER.debug("Found sewerage tariff: %s", tariff_amount)
            # Холодна вода - має subService.name з "водопостачання (хв)"
            elif "водопостачання" in sub_service_name and "хв" in sub_service_name:
                summary["tariff_cold_water"] = tariff_amount
                _LOGGER.debug("Found cold water tariff: %s", tariff_amount)
            else:
                _LOGGER.debug("Tariff not matched: service_type_name=%s, sub_service_name=%s, service_code=%s", service_type_name, sub_service_name, service_code)
        
        _LOGGER.debug("Final tariffs summary: %s", summary)
        return summary

    def _parse_counters_summary(
        self, counters: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], dict[int, str]]:
        """Parse counter numbers and check dates."""
        summary: dict[str, Any] = {
            "hot_water_counter_number": None,
            "hot_water_counter_check_date": None,
            "hot_water_counter_next_check_date": None,
            "cold_water_counter_number": None,
            "cold_water_counter_check_date": None,
            "cold_water_counter_next_check_date": None,
        }
        counter_type_by_id: dict[int, str] = {}
        _LOGGER.debug("Parsing counters: %s", counters)

        for counter in counters:
            counter_id = counter.get("id")
            counter_type = (counter.get("counterType") or {}).get("name", "")
            counter_type_lower = counter_type.lower()
            prefix = None
            if any(keyword in counter_type_lower for keyword in COUNTER_TYPE_HOT_KEYWORDS):
                prefix = "hot_water"
            elif any(keyword in counter_type_lower for keyword in COUNTER_TYPE_COLD_KEYWORDS):
                prefix = "cold_water"
            if not prefix or counter_id is None:
                continue

            summary[f"{prefix}_counter_number"] = counter.get("number")
            # Parse and format check dates to YYYY-MM-DD
            check_date_str = counter.get("checkDate")
            summary[f"{prefix}_counter_check_date"] = (
                datetime.fromisoformat(check_date_str.replace("Z", "+00:00")).strftime('%Y-%m-%d')
                if check_date_str else None
            )
            next_check_date_str = counter.get("nextCheckDate")
            summary[f"{prefix}_counter_next_check_date"] = (
                datetime.fromisoformat(next_check_date_str.replace("Z", "+00:00")).strftime('%Y-%m-%d')
                if next_check_date_str else None
            )
            counter_type_by_id[counter_id] = prefix

        _LOGGER.debug("Counter type by ID mapping: %s", counter_type_by_id)
        return summary, counter_type_by_id

    def _parse_counter_factors_summary(
        self,
        factors: list[dict[str, Any]],
        counter_type_by_id: dict[int, str],
    ) -> dict[str, Any]:
        """Parse the last meter readings for hot and cold counters."""
        summary: dict[str, Any] = {
            "hot_water_last_reading": None,
            "cold_water_last_reading": None,
        }
        last_periods: dict[str, datetime] = {}
        _LOGGER.debug("Parsing counter factors. Factors count: %d, Counter type by ID: %s", len(factors), counter_type_by_id)

        for factor in factors:
            counter_id = factor.get("counterId")
            _LOGGER.debug("Processing factor: counterId=%s, factor=%s", counter_id, factor)
            prefix = counter_type_by_id.get(counter_id)
            if not prefix:
                _LOGGER.debug("No prefix found for counter_id %s in counter_type_by_id", counter_id)
                continue

            period_str = factor.get("invoicePeriod")
            try:
                period = datetime.fromisoformat(period_str.replace("Z", "+00:00")) if period_str else None
            except ValueError:
                _LOGGER.warning("Failed to parse invoicePeriod: %s", period_str)
                period = None
            if period is None:
                _LOGGER.debug("Period is None for counter_id %s", counter_id)
                continue

            end_factor = factor.get("endFactor")
            if end_factor is None:
                _LOGGER.debug("endFactor is None for counter_id %s", counter_id)
                continue

            if prefix not in last_periods or period > last_periods[prefix]:
                summary[f"{prefix}_last_reading"] = end_factor
                last_periods[prefix] = period

        _LOGGER.debug("Final counter factors summary: %s", summary)
        return summary

    def _parse_last_factors_dates(
        self,
        last_factors: list[dict[str, Any]],
        counter_type_by_id: dict[int, str],
    ) -> dict[str, Any]:
        """Parse the last transmission dates from last-factors API."""
        summary: dict[str, Any] = {
            "hot_water_last_transmission_date": None,
            "cold_water_last_transmission_date": None,
            "last_transmission_date": None,
        }

        _LOGGER.debug("Parsing last factors dates. Last factors count: %d", len(last_factors))

        for factor in last_factors:
            counter_id = factor.get("id")
            _LOGGER.debug("Processing last factor: counterId=%s, factor=%s", counter_id, factor)
            prefix = counter_type_by_id.get(counter_id)
            if not prefix:
                _LOGGER.debug("No prefix found for counter_id %s in counter_type_by_id", counter_id)
                continue

            date_from_str = factor.get("dateFrom")
            if not date_from_str:
                _LOGGER.debug("No dateFrom found for counter_id %s", counter_id)
                continue

            try:
                date_from = datetime.fromisoformat(date_from_str.replace("Z", "+00:00"))
                summary[f"{prefix}_last_transmission_date"] = date_from.date()
                _LOGGER.debug("Parsed %s last transmission date: %s", prefix, summary[f"{prefix}_last_transmission_date"])
            except ValueError:
                _LOGGER.warning("Failed to parse dateFrom: %s", date_from_str)
                continue

        # Set overall last transmission date as the most recent one
        dates = []
        if summary["hot_water_last_transmission_date"]:
            dates.append(summary["hot_water_last_transmission_date"])
        if summary["cold_water_last_transmission_date"]:
            dates.append(summary["cold_water_last_transmission_date"])

        if dates:
            overall_last_date = max(dates)
            summary["last_transmission_date"] = overall_last_date
            _LOGGER.debug("Overall last transmission date: %s", summary["last_transmission_date"])

        _LOGGER.debug("Final last factors dates summary: %s", summary)
        return summary

