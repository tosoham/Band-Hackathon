from fastapi import FastAPI

from agents.intake import build_initial_state

app = FastAPI(title="BandGate API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "bandgate-backend"}


@app.get("/state")
def state() -> dict:
    return build_initial_state().model_dump(mode="json")
