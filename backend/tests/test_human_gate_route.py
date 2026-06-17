"""Tests for the v2 human-gate POST route — verifies routing only.

The route registers a HumanDecision with the singleton orchestrator. Full
end-to-end flow is covered in test_live_orchestrator.py. Skipped silently
when httpx (FastAPI's TestClient dependency) is not installed.
"""

import pytest

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    TestClient = None  # type: ignore[assignment]

import app as backend_app
from core import orchestrator_store
from core.state_store import reset_state


pytestmark = pytest.mark.skipif(TestClient is None, reason="httpx not installed for TestClient")


def test_human_message_routes_to_orchestrator() -> None:
    reset_state()
    orchestrator_store.reset_orchestrator()
    orch = orchestrator_store.get_orchestrator()
    qid = next(iter(orch.state.questions))
    client = TestClient(backend_app.app)
    response = client.post(
        "/rooms/room-1/human-message",
        json={
            "question_id": qid,
            "content": "Please use approved SLA wording.",
            "action": "approve",
            "mentions": ["legal_commitment_guard"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["question_id"] == qid
    assert qid in orch._human_decisions
    decision = orch._human_decisions[qid]
    assert decision.action == "approve"
    assert decision.mentions == ["legal_commitment_guard"]


def test_human_message_404_for_unknown_question() -> None:
    reset_state()
    orchestrator_store.reset_orchestrator()
    client = TestClient(backend_app.app)
    response = client.post(
        "/rooms/room-1/human-message",
        json={"question_id": "Q-DOES-NOT-EXIST", "content": "hi", "action": "comment"},
    )
    assert response.status_code == 404


def test_auth_login_sets_cookie_and_validates_org() -> None:
    client = TestClient(backend_app.app)
    response = client.post("/auth/login", json={"org_slug": "demo", "email": "agnik@bandgate.test"})
    assert response.status_code == 200
    # starlette quotes cookie values containing ":" per RFC 6265 — strip them
    # before asserting on the token shape.
    cookie = (response.cookies.get("bandgate_session") or "").strip('"')
    assert cookie.startswith("demo:")

    bad = client.post("/auth/login", json={"org_slug": "", "email": "x@example.com"})
    assert bad.status_code == 400

    bad_email = client.post("/auth/login", json={"org_slug": "demo", "email": "not-an-email"})
    assert bad_email.status_code == 400


def test_rfp_list_returns_question_summaries() -> None:
    reset_state()
    orchestrator_store.reset_orchestrator()
    client = TestClient(backend_app.app)
    response = client.get("/rfp/list")
    assert response.status_code == 200
    body = response.json()
    assert body["rfp_id"]
    assert isinstance(body["questions"], list)
    assert body["question_count"] == len(body["questions"])
    assert all("question_id" in q and "risk_level" in q for q in body["questions"][:5])
