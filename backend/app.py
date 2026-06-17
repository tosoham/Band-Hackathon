import asyncio
import json
import shutil
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from agents.approval import apply_decision
from agents.live_orchestrator import HumanDecision
from core.export import audit_trail_records, final_response_markdown, promise_ledger_records
from core.orchestrator_store import get_orchestrator, reset_orchestrator
from core.paths import project_root
from core.provider_config import load_provider_config
from core.state_store import get_state, reset_state

app = FastAPI(title="BandGate API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- request models ----------


class DecisionRequest(BaseModel):
    decision: str
    approver_role: str
    approver_name: str | None = None
    comment: str | None = None
    final_answer: str | None = None


class LoginRequest(BaseModel):
    org_slug: str
    email: str


class HumanMessageRequest(BaseModel):
    question_id: str
    content: str
    action: str = "comment"
    mentions: list[str] | None = None
    final_answer: str | None = None
    approver_role: str | None = None
    approver_name: str | None = None


# ---------- basic surfaces ----------


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
        "aiml_embedding_model": config.aiml_embedding_model,
        "featherless_model": config.featherless_model,
        "aiml_live_limits": {
            "normalize": config.aiml_normalize_live_limit,
            "sales_draft": config.aiml_sales_live_limit,
            "drift": config.aiml_drift_live_limit,
            "intake_risk": config.aiml_intake_risk_live_limit,
            "report": config.aiml_report_live_limit,
            "reasoning": config.aiml_reasoning_live_limit,
            "embedding": config.aiml_embedding_live_limit,
            "rerank": config.aiml_rerank_live_limit,
        },
        "featherless_live_limits": {
            "review": config.featherless_review_live_limit,
        },
        "band_default_room_id": config.band_default_room_id,
        "band_rest_url": config.band_rest_url,
        "band_ws_url": config.band_ws_url,
    }


@app.get("/band/events")
def band_events() -> list[dict]:
    path = _event_log_path()
    if not path.exists():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events[-100:]


# ---------- exports ----------


@app.get("/exports/final-response", response_class=PlainTextResponse)
def final_response_export() -> str:
    return final_response_markdown(get_state())


@app.get("/exports/audit-trail")
def audit_trail_export() -> list[dict]:
    return audit_trail_records(get_state())


@app.get("/exports/promise-ledger")
def promise_ledger_export() -> list[dict]:
    return promise_ledger_records(get_state())


@app.get("/exports/band-chat-report", response_class=PlainTextResponse)
def band_chat_report_export() -> str:
    path = project_root() / "output" / "band_chat_report.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="band chat report has not been generated")
    return path.read_text(encoding="utf-8")


@app.get("/exports/hardening-report", response_class=PlainTextResponse)
def hardening_report_export() -> str:
    path = project_root() / "output" / "hardening_report.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="hardening report has not been generated")
    return path.read_text(encoding="utf-8")


@app.get("/exports/submission-readiness", response_class=PlainTextResponse)
def submission_readiness_export() -> str:
    path = project_root() / "output" / "submission_readiness.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="submission readiness report has not been generated")
    return path.read_text(encoding="utf-8")


# ---------- legacy human decision (kept for the dashboard) ----------


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
    reset_orchestrator()
    return {"status": "reset", "questions": len(state.questions)}


# ---------- v2: auth stub ----------


@app.post("/auth/login")
def auth_login(body: LoginRequest, response: Response) -> dict:
    org = body.org_slug.strip().lower()
    if not org:
        raise HTTPException(status_code=400, detail="org_slug required")
    if not body.email or "@" not in body.email:
        raise HTTPException(status_code=400, detail="valid email required")
    token = f"demo:{org}:{body.email}"
    response.set_cookie(
        key="bandgate_session",
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=60 * 60 * 8,
    )
    return {
        "token": token,
        "org": "SentinelAI Security Platform",
        "org_slug": org,
        "user_email": body.email,
    }


@app.post("/auth/logout")
def auth_logout(response: Response) -> dict:
    response.delete_cookie("bandgate_session", path="/")
    return {"status": "logged_out"}


@app.get("/auth/session")
def auth_session(request: Request) -> dict:
    token = request.cookies.get("bandgate_session")
    if not token:
        raise HTTPException(status_code=401, detail="not authenticated")
    return {"token": token}


# ---------- v2: RFP intake ----------


@app.get("/rfp/list")
def rfp_list() -> dict:
    state = get_state()
    questions = []
    for question in state.questions.values():
        questions.append(
            {
                "question_id": question.question_id,
                "raw_question": question.raw_question,
                "normalized_question": question.normalized_question,
                "category": question.category,
                "risk_level": question.risk_level,
                "risk_tags": question.risk_tags,
                "status": question.status,
                "conflict_summary": question.conflict_summary,
                "has_final_answer": bool(question.final_answer),
            }
        )
    return {
        "rfp_id": state.rfp_id,
        "buyer_name": state.buyer_name,
        "vendor_name": state.vendor_name,
        "policy_version": state.policy_version,
        "question_count": len(questions),
        "questions": questions,
    }


@app.post("/rfp/upload")
async def rfp_upload(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")
    target = project_root() / "data" / "uploaded_rfp.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        await asyncio.to_thread(shutil.copyfileobj, file.file, handle)
    new_state = reset_state()
    reset_orchestrator()
    return {"status": "ok", "rfp_id": new_state.rfp_id, "questions": len(new_state.questions)}


# ---------- v2: live deliberation ----------


@app.post("/deliberate/{question_id}")
async def deliberate(question_id: str, background_tasks: BackgroundTasks) -> dict:
    orchestrator = get_orchestrator()
    if question_id not in orchestrator.state.questions:
        raise HTTPException(status_code=404, detail="unknown question")
    if orchestrator.is_active(question_id):
        return {"status": "already_active", "question_id": question_id}
    background_tasks.add_task(_run_deliberation, question_id)
    return {"status": "started", "question_id": question_id}


async def _run_deliberation(question_id: str) -> None:
    orchestrator = get_orchestrator()
    try:
        await orchestrator.deliberate(question_id)
    except Exception as exc:  # noqa: BLE001 - log only
        print(f"[deliberate] {question_id} failed: {exc}")


@app.post("/rooms/{room_id}/human-message")
def human_message(room_id: str, body: HumanMessageRequest) -> dict:
    orchestrator = get_orchestrator()
    if body.question_id not in orchestrator.state.questions:
        raise HTTPException(status_code=404, detail="unknown question")
    decision = HumanDecision(
        action=body.action,
        content=body.content,
        mentions=body.mentions or [],
        approver_role=body.approver_role or "Demo Human Reviewer",
        approver_name=body.approver_name or "BandGate Operator",
        final_answer=body.final_answer,
    )
    orchestrator.register_human_message(body.question_id, decision)
    return {"status": "queued", "question_id": body.question_id, "room_id": room_id}


@app.get("/rooms/{room_id}/events")
async def room_events(
    room_id: str,
    request: Request,
    question_id: str | None = Query(default=None),
    since: float | None = Query(default=None),
) -> StreamingResponse:
    async def generator():
        path = _event_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        offset = 0
        # Replay from start (or from `since` ms) so a late subscriber catches up.
        if since is None or since <= 0:
            offset = 0
        with path.open("r", encoding="utf-8") as handle:
            handle.seek(offset)
            buffer = ""
            last_keepalive = asyncio.get_event_loop().time()
            while True:
                if await request.is_disconnected():
                    break
                line = handle.readline()
                if line:
                    buffer += line
                    if buffer.endswith("\n"):
                        try:
                            record = json.loads(buffer.strip())
                            if question_id and record.get("question_id") not in (None, question_id):
                                buffer = ""
                                continue
                            yield f"event: band-event\ndata: {json.dumps(record)}\n\n"
                        except json.JSONDecodeError:
                            pass
                        buffer = ""
                        last_keepalive = asyncio.get_event_loop().time()
                    continue
                now = asyncio.get_event_loop().time()
                if now - last_keepalive >= 15:
                    last_keepalive = now
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.5)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _event_log_path() -> Path:
    return project_root() / "output" / "band_events.jsonl"
