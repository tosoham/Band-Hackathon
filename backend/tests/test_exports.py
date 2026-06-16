from agents.orchestrator import build_demo_state
from core.export import final_response_markdown, promise_ledger_records
import pytest


def test_final_response_markdown_includes_evidence_and_approvals() -> None:
    state = build_demo_state(post_band_events=False)
    markdown = final_response_markdown(state)

    assert "# BandGate Final RFP Response" in markdown
    assert "Policy version: 2026.06" in markdown
    assert "## Q-001" in markdown
    assert "99.5%" in markdown
    assert "**Approval trail:**" in markdown


def test_promise_ledger_records_are_json_ready() -> None:
    state = build_demo_state(post_band_events=False)
    records = promise_ledger_records(state)

    assert records
    assert records[0]["commitment_id"].startswith("COM-")
    assert records[0]["approval_required"] is True


def test_export_endpoints() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from app import app

    client = TestClient(app)

    final_response = client.get("/exports/final-response")
    audit = client.get("/exports/audit-trail")
    ledger = client.get("/exports/promise-ledger")

    assert final_response.status_code == 200
    assert "BandGate Final RFP Response" in final_response.text
    assert audit.status_code == 200
    assert isinstance(audit.json(), list)
    assert ledger.status_code == 200
    assert isinstance(ledger.json(), list)
