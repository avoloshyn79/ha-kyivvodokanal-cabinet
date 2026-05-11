"""Constants for the Kyivvodokanal Cabinet integration."""

from __future__ import annotations

DOMAIN = "kyivvodokanal_cabinet"

CONF_CABINET_URL = "cabinet_url"
CONF_COOKIE = "cookie"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_AUTH_HEADER = "auth_header"

DEFAULT_NAME = "Kyivvodokanal Cabinet"
DEFAULT_CABINET_URL = "https://my.vodokanal.kiev.ua"
DEFAULT_SCAN_INTERVAL_MINUTES = 1440
DEFAULT_SERVICE_PROVIDER_CODE = "999"

COUNTER_TYPE_HOT_KEYWORDS = ("гаряч", "hot")
COUNTER_TYPE_COLD_KEYWORDS = ("холод", "cold")
SERVICE_CODE_ABONEMENT = "35"
SERVICE_TYPE_NAME_ABONEMENT = "абонплата"

EVENT_DATA_UPDATED = f"{DOMAIN}_data_updated"
EVENT_READINGS_SUBMITTED = f"{DOMAIN}_readings_submitted"
EVENT_READINGS_FAILED = f"{DOMAIN}_readings_failed"