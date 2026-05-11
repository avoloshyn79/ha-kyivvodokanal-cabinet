"""Client for Kyivvodokanal Cabinet API."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urljoin

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import DEFAULT_CABINET_URL

_LOGGER = logging.getLogger(__name__)


class KyivvodokanalApiError(Exception):
    """Base error for Kyivvodokanal API."""


class KyivvodokanalAuthenticationError(KyivvodokanalApiError):
    """Authentication failed."""


class KyivvodokanalApiClient:
    """Client for Kyivvodokanal consumer API."""

    def __init__(self, session: ClientSession, cabinet_url: str, cookie: str | None, auth_header: str | None = None) -> None:
        self._session = session
        self._base_url = cabinet_url.rstrip("/") if cabinet_url else DEFAULT_CABINET_URL
        self._cookie = (cookie or "").strip()
        self._auth_header = (auth_header or "").strip()

    async def async_get_payments_history(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch payments history for the current consumer."""
        endpoint = "/api/warehouse/consumer/payments/history"
        payload = {
            "serviceProviderGroupIds": [22],
            "financePointId": "",
            "from": start_date,
            "to": end_date,
        }
        return await self._api_post(endpoint, payload)

    async def async_get_finance_partners(self) -> list[dict[str, Any]]:
        """Fetch available finance partners."""
        endpoint = "/api/warehouse/consumer/payments/finance/partners"
        return await self._api_get(endpoint)

    async def async_get_amount_to_pay(self, service_provider_code: str, invoice_account_code: str) -> dict[str, Any]:
        """Fetch current invoice amount and debt."""
        endpoint = f"/api/warehouse/consumer/invoice/amount_to_pay?serviceProviderCode={service_provider_code}&code={invoice_account_code}"
        return await self._api_get(endpoint)

    async def async_get_counters(self, service_provider_code: str, invoice_account_code: str) -> list[dict[str, Any]]:
        """Fetch registered counters for the current consumer."""
        endpoint = f"/api/warehouse/consumer/counters?serviceProviderCode={service_provider_code}&invoiceAccountCode={invoice_account_code}"
        return await self._api_get(endpoint)

    async def async_get_counter_factors_history(
        self,
        invoice_account_code: str,
        service_provider_code: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """Fetch meter factor history for the current counters."""
        endpoint = "/api/warehouse/consumer/counter/factors/history"
        payload = {
            "invoiceAccountCode": invoice_account_code,
            "serviceProviderCode": service_provider_code,
            "range": {"from": start_date, "to": end_date},
        }
        return await self._api_post(endpoint, payload)

    async def async_get_tariffs(self, service_provider_code: str, invoice_account_code: str) -> list[dict[str, Any]]:
        """Fetch tariffs for the current consumer."""
        endpoint = f"/api/warehouse/consumer/tariff?serviceProviderCode={service_provider_code}&invoiceAccountCode={invoice_account_code}"
        result = await self._api_get(endpoint)
        _LOGGER.debug("Tariffs API response: %s", result)
        
        # Handle case where response might be wrapped in {"text": "..."}
        if isinstance(result, dict) and "text" in result:
            _LOGGER.debug("Tariffs response has 'text' field, parsing it")
            text_content = result["text"]
            if isinstance(text_content, str):
                result = json.loads(text_content)
            else:
                result = text_content
        
        return result

    async def async_submit_readings(self, readings: list[dict[str, Any]]) -> dict[str, Any]:
        """Submit meter readings to the API.

        Args:
            readings: List of reading objects with keys:
                - counterId: Counter ID
                - factor: Reading value
                - factorTypeCode: Factor type code (optional)

        Returns:
            API response
        """
        endpoint = "/api/warehouse/consumer/counter/factor"
        return await self._api_post(endpoint, readings)

    async def async_get_last_factors(self, counter_id: str) -> dict[str, Any]:
        """Fetch last factors for a specific counter."""
        endpoint = f"/api/warehouse/consumer/counter/{counter_id}/last-factors"
        return await self._api_get(endpoint)

    def _get_cookie_value(self, name: str) -> str | None:
        for item in self._cookie.split(";"):
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            if key.strip() == name:
                return value.strip()
        return None

    def _default_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": self._base_url,
            "Origin": self._base_url,
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Dest": "empty",
        }
        if self._cookie:
            headers["Cookie"] = self._cookie
            x_xsrf_token = self._get_cookie_value("XSRF-TOKEN")
            if x_xsrf_token:
                headers["X-XSRF-TOKEN"] = x_xsrf_token
        if self._auth_header:
            headers["Authorization"] = self._auth_header

        return headers

    async def _api_get(self, path: str) -> Any:
        url = urljoin(self._base_url, path)
        headers = self._default_headers()

        _LOGGER.debug("API call GET to %s with headers: %s", url, headers)
        try:
            response = await self._session.get(url, headers=headers, timeout=ClientTimeout(total=30))
        except ClientError as err:
            _LOGGER.error("Network error reaching Kyivvodokanal API endpoint %s: %s", path, err)
            raise KyivvodokanalApiError("Cannot reach Kyivvodokanal API") from err

        _LOGGER.debug("API call GET response status: %s for %s", response.status, url)
        if response.status in (401, 403):
            _LOGGER.error("Kyivvodokanal authentication failed: %s %s", response.status, url)
            raise KyivvodokanalAuthenticationError("Authentication failed")
        if response.status >= 400:
            body = await response.text()
            _LOGGER.error(
                "Kyivvodokanal API error %s %s; body=%s",
                response.status,
                path,
                body[:200],
            )
            raise KyivvodokanalApiError(f"API error {response.status}")

        try:
            json_response = await response.json(content_type=None)
            _LOGGER.debug("API call GET successful for %s, response: %s", url, json_response)
            return json_response
        except ValueError as err:
            body = await response.text()
            _LOGGER.error("Invalid JSON from Kyivvodokanal API %s: %s; body=%s", path, err, body[:200])
            if "<html" in body.lower() or "login" in body.lower():
                raise KyivvodokanalAuthenticationError("Authentication failed or invalid session cookie") from err
            raise KyivvodokanalApiError("Invalid JSON response") from err

    async def _api_post(self, path: str, payload: dict[str, Any]) -> Any:
        url = urljoin(self._base_url, path)
        headers = self._default_headers()

        try:
            response = await self._session.post(url, json=payload, headers=headers, timeout=ClientTimeout(total=30))
        except ClientError as err:
            _LOGGER.error("Network error reaching Kyivvodokanal API endpoint %s: %s", path, err)
            raise KyivvodokanalApiError("Cannot reach Kyivvodokanal API") from err

        if response.status in (401, 403):
            raise KyivvodokanalAuthenticationError("Authentication failed")
        if response.status >= 400:
            _LOGGER.error("Kyivvodokanal API error %s %s", response.status, path)
            raise KyivvodokanalApiError(f"API error {response.status}")

        try:
            return await response.json(content_type=None)
        except ValueError as err:
            _LOGGER.error("Invalid JSON from Kyivvodokanal API %s: %s", path, err)
            raise KyivvodokanalApiError("Invalid JSON response") from err