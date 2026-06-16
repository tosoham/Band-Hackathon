import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agents.approval import apply_decision
from core.export import audit_trail_records, final_response_markdown, promise_ledger_records
from core.provider_config import load_provider_config
from core.state_store import get_state, reset_state
from fastapi.responses import PlainTextResponse

app = FastAPI(title="BandGate API", version="0.2.0")


class DecisionRequest(BaseModel):
    decision: str
    approver_role: str
    approver_name: str | None = None
    comment: str | None = None
    final_answer: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "bandgate-backend"}


@app.get("/state")
def state() -> dict:
    return get_state().model_dump(mode="json")


@app.get("/providers")
def providers() -> dict:
    config = load_provider_config()
    return {
        "band_mode": config.band_mode,
        "featherless_mode": config.featherless_mode,
        "aiml_mode": config.aiml_mode,
        "featherless_configured": bool(config.featherless_api_key),
        "aiml_configured": bool(config.aiml_api_key),
        "aiml_enabled": config.aiml_enabled,
        "featherless_live_ready": bool(
            config.featherless_api_key and config.featherless_base_url and config.featherless_model
        ),
        "aiml_model": config.aiml_model,
        "featherless_model": config.featherless_model,
        "aiml_live_limits": {
            "normalize": config.aiml_normalize_live_limit,
            "sales_draft": config.aiml_sales_live_limit,
        },
        "featherless_live_limits": {
            "review": config.featherless_review_live_limit,
        },
        "band_default_room_id": config.band_default_room_id,
        "thenvoi_rest_url": config.thenvoi_rest_url,
        "thenvoi_ws_url": config.thenvoi_ws_url,
    }


@app.get("/band/events")
def band_events() -> list[dict]:
    path = Path("output/band_events.jsonl")
    if not path.exists():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events[-100:]


@app.get("/exports/final-response", response_class=PlainTextResponse)
def final_response_export() -> str:
    return final_response_markdown(get_state())


@app.get("/exports/audit-trail")
def audit_trail_export() -> list[dict]:
    return audit_trail_records(get_state())


@app.get("/exports/promise-ledger")
def promise_ledger_export() -> list[dict]:
    return promise_ledger_records(get_state())


@app.post("/questions/{question_id}/decision")
def decide(question_id: str, body: DecisionRequest) -> dict:
    try:
        question = apply_decision(
            get_state(),
            question_id,
            body.decision,
            approver_role=body.approver_role,
            approver_name=body.approver_name,
            comment=body.comment,
            final_answer=body.final_answer,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="unknown question")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return question.model_dump(mode="json")


@app.post("/demo/reset")
def reset() -> dict:
    state = reset_state()
    return {"status": "reset", "questions": len(state.questions)}
