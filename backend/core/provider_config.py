import os
from dataclasses import dataclass
from typing import Literal

ProviderMode = Literal["mock", "lite", "live"]


def _mode(name: str) -> ProviderMode:
    value = os.getenv(name, os.getenv("DEMO_MODE", "mock")).lower()
    if value not in {"mock", "lite", "live"}:
        return "mock"
    return value  # type: ignore[return-value]


@dataclass(frozen=True)
class ProviderConfig:
    band_mode: ProviderMode
    featherless_mode: ProviderMode
    aiml_mode: ProviderMode
    featherless_api_key: str | None
    aiml_api_key: str | None
    band_default_room_id: str | None
    thenvoi_rest_url: str
    thenvoi_ws_url: str
    aiml_enabled: bool = False
    aiml_base_url: str = "https://api.aimlapi.com/v1"
    aiml_model: str = "google/gemma-3-4b-it"
    featherless_base_url: str | None = None
    featherless_model: str | None = None
    aiml_normalize_live_limit: int = 2
    aiml_sales_live_limit: int = 2
    featherless_review_live_limit: int = 3


def load_provider_config() -> ProviderConfig:
    return ProviderConfig(
        band_mode=_mode("BAND_MODE"),
        featherless_mode=_mode("FEATHERLESS_MODE"),
        aiml_mode=_mode("AIML_MODE"),
        featherless_api_key=os.getenv("FEATHERLESS_API_KEY") or None,
        aiml_api_key=os.getenv("AIML_API_KEY") or None,
        band_default_room_id=os.getenv("BAND_DEFAULT_ROOM_ID") or None,
        thenvoi_rest_url=os.getenv("THENVOI_REST_URL", "https://app.band.ai/"),
        thenvoi_ws_url=os.getenv("THENVOI_WS_URL", "wss://app.band.ai/api/v1/socket/websocket"),
        aiml_enabled=os.getenv("AIML_ENABLED", "false").lower() == "true",
        aiml_base_url=os.getenv("AIML_BASE_URL", "https://api.aimlapi.com/v1").rstrip("/"),
        aiml_model=os.getenv("AIML_MODEL", "google/gemma-3-4b-it"),
        featherless_base_url=(os.getenv("FEATHERLESS_BASE_URL") or "https://api.featherless.ai/v1").rstrip("/"),
        featherless_model=os.getenv("FEATHERLESS_MODEL") or "Qwen/Qwen2.5-7B-Instruct",
        aiml_normalize_live_limit=_int_env("AIML_NORMALIZE_LIVE_LIMIT", 2),
        aiml_sales_live_limit=_int_env("AIML_SALES_LIVE_LIMIT", 2),
        featherless_review_live_limit=_int_env("FEATHERLESS_REVIEW_LIVE_LIMIT", 3),
    )


def _int_env(name: str, default: int) -> int:
    try:
        return max(int(os.getenv(name, str(default))), 0)
    except ValueError:
        return default
