from fastapi import FastAPI

from agents.orchestrator import build_demo_state
from core.provider_config import load_provider_config

app = FastAPI(title="BandGate API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "bandgate-backend"}


@app.get("/state")
def state() -> dict:
    return build_demo_state().model_dump(mode="json")


@app.get("/providers")
def providers() -> dict[str, str | bool | None]:
    config = load_provider_config()
    return {
        "band_mode": config.band_mode,
        "featherless_mode": config.featherless_mode,
        "aiml_mode": config.aiml_mode,
        "featherless_configured": bool(config.featherless_api_key),
        "aiml_configured": bool(config.aiml_api_key),
        "band_default_room_id": config.band_default_room_id,
        "thenvoi_rest_url": config.thenvoi_rest_url,
        "thenvoi_ws_url": config.thenvoi_ws_url,
    }
