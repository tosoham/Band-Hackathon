import os
from dataclasses import dataclass
from typing import Literal

ProviderMode = Literal["mock", "lite", "live"]


def _mode(name: str, default: str = "lite") -> ProviderMode:
    value = os.getenv(name, os.getenv("DEMO_MODE", default)).lower()
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
    band_rest_url: str
    band_ws_url: str
    aiml_enabled: bool = True
    aiml_base_url: str = "https://api.aimlapi.com/v1"
    aiml_model: str = "google/gemma-3-4b-it"
    aiml_embedding_model: str = "text-embedding-3-small"
    featherless_base_url: str | None = None
    featherless_model: str | None = None
    aiml_normalize_live_limit: int = 20
    aiml_sales_live_limit: int = 30
    aiml_drift_live_limit: int = 30
    aiml_intake_risk_live_limit: int = 30
    aiml_report_live_limit: int = 10
    aiml_reasoning_live_limit: int = 200
    aiml_embedding_live_limit: int = 200
    aiml_rerank_live_limit: int = 200
    featherless_review_live_limit: int = 30


def load_provider_config() -> ProviderConfig:
    return ProviderConfig(
        band_mode=_mode("BAND_MODE", default="lite"),
        featherless_mode=_mode("FEATHERLESS_MODE", default="lite"),
        aiml_mode=_mode("AIML_MODE", default="live"),
        featherless_api_key=os.getenv("FEATHERLESS_API_KEY") or None,
        aiml_api_key=os.getenv("AIML_API_KEY") or None,
        band_default_room_id=os.getenv("BAND_DEFAULT_ROOM_ID") or None,
        band_rest_url=_env_alias("BAND_REST_URL", "THENVOI_REST_URL", "https://app.band.ai/"),
        band_ws_url=_env_alias("BAND_WS_URL", "THENVOI_WS_URL", "wss://app.band.ai/api/v1/socket/websocket"),
        aiml_enabled=os.getenv("AIML_ENABLED", "true").lower() == "true",
        aiml_base_url=os.getenv("AIML_BASE_URL", "https://api.aimlapi.com/v1").rstrip("/"),
        aiml_model=os.getenv("AIML_MODEL", "google/gemma-3-4b-it"),
        aiml_embedding_model=os.getenv("AIML_EMBEDDING_MODEL", "text-embedding-3-small"),
        featherless_base_url=(os.getenv("FEATHERLESS_BASE_URL") or "https://api.featherless.ai/v1").rstrip("/"),
        featherless_model=os.getenv("FEATHERLESS_MODEL") or "Qwen/Qwen2.5-7B-Instruct",
        aiml_normalize_live_limit=_int_env("AIML_NORMALIZE_LIVE_LIMIT", 20),
        aiml_sales_live_limit=_int_env("AIML_SALES_LIVE_LIMIT", 30),
        aiml_drift_live_limit=_int_env("AIML_DRIFT_LIVE_LIMIT", 30),
        aiml_intake_risk_live_limit=_int_env("AIML_INTAKE_RISK_LIVE_LIMIT", 30),
        aiml_report_live_limit=_int_env("AIML_REPORT_LIVE_LIMIT", 10),
        aiml_reasoning_live_limit=_int_env("AIML_REASONING_LIVE_LIMIT", 200),
        aiml_embedding_live_limit=_int_env("AIML_EMBEDDING_LIVE_LIMIT", 200),
        aiml_rerank_live_limit=_int_env("AIML_RERANK_LIVE_LIMIT", 200),
        featherless_review_live_limit=_int_env("FEATHERLESS_REVIEW_LIVE_LIMIT", 30),
    )


def _int_env(name: str, default: int) -> int:
    try:
        return max(int(os.getenv(name, str(default))), 0)
    except ValueError:
        return default


def _env_alias(primary: str, legacy: str, default: str) -> str:
    return os.getenv(primary) or os.getenv(legacy) or default
