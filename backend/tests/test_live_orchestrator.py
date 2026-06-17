"""Tests for the v2 LiveOrchestrator multi-round deliberation loop."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from agents.live_orchestrator import HumanDecision, LiveOrchestrator
from core.band_publisher import BandPublisher
from core.policy_loader import load_commitment_policy
from core.provider_config import ProviderConfig
from core.schemas import BandGateState, RFPQuestionState


def _config() -> ProviderConfig:
    return ProviderConfig(
        band_mode="lite",
        featherless_mode="lite",
        aiml_mode="lite",
        featherless_api_key=None,
        aiml_api_key=None,
        band_default_room_id=None,
        band_rest_url="https://app.band.ai/",
        band_ws_url="wss://app.band.ai/api/v1/socket/websocket",
    )


def _state_with_one_question(question_id: str = "Q-001") -> BandGateState:
    question = RFPQuestionState(
        question_id=question_id,
        raw_question="Can you guarantee 99.9% uptime with financial penalties?",
        normalized_question="Can you guarantee 99.9% uptime with financial penalties?",
        category=["sla", "legal"],
        risk_level="high",
        assigned_agents=[
            "legal_commitment_guard",
            "product_capability",
            "sales_engineer",
            "security_compliance",
        ],
        status="open",
        conflict_detected=True,
        conflict_summary="SLA language may exceed approved commitment policy.",
        risk_tags=["sla_overcommitment"],
    )
    return BandGateState(
        rfp_id="RFP-TEST-001",
        buyer_name="Public Sector Buyer",
        vendor_name="SentinelAI",
        policy_version="2026.06",
        questions={question_id: question},
    )


def test_deliberate_reaches_finalized_with_pre_registered_approval(tmp_path: Path) -> None:
    os.environ["BANDGATE_HUMAN_WAIT_SECONDS"] = "5"
    state = _state_with_one_question()
    publisher = BandPublisher(_config(), event_log=str(tmp_path / "band_events.jsonl"))
    orch = LiveOrchestrator(
        state,
        publisher=publisher,
        policy=load_commitment_policy(),
        max_rounds=3,
    )
    orch.register_human_message(
        "Q-001",
        HumanDecision(
            action="approve",
            content="Approved with standard wording.",
        ),
    )
    result = asyncio.run(orch.deliberate("Q-001"))
    assert result.status == "finalized"
    assert result.final_answer
    # Deterministic legal violation must persist in the final answer for the
    # SLA question, regardless of AI/ML.
    assert "99.5%" in (result.final_answer or "") or "addendum" in (result.final_answer or "")
    # Audit trail has multiple turns plus finalize event.
    assert any(ev.action == "finalize_answer" for ev in state.audit_trail)
    # Promise ledger picks up the SLA commitment.
    assert any(entry.commitment_id == "COM-0001" for entry in state.promise_ledger)


def test_deliberate_creates_band_events_for_each_round(tmp_path: Path) -> None:
    os.environ["BANDGATE_HUMAN_WAIT_SECONDS"] = "5"
    log = tmp_path / "band_events.jsonl"
    state = _state_with_one_question("Q-005")
    state.questions["Q-005"].raw_question = "Do you use customer data to train AI models?"
    state.questions["Q-005"].normalized_question = state.questions["Q-005"].raw_question
    state.questions["Q-005"].risk_tags = ["ai_data_usage_risk"]
    publisher = BandPublisher(_config(), event_log=str(log))
    orch = LiveOrchestrator(state, publisher=publisher, max_rounds=2)
    orch.register_human_message(
        "Q-005",
        HumanDecision(action="approve", content="Approved."),
    )
    asyncio.run(orch.deliberate("Q-005"))

    lines = [line for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) > 5  # multiple turns + round markers + human + finalize
    events = [line for line in lines if '"event_type"' in line]
    assert any("round_start" in e for e in events)
    assert any("agent_output" in e for e in events)
    assert any("deliberation_finalized" in e for e in events)


def test_push_back_advances_to_second_pass(tmp_path: Path) -> None:
    os.environ["BANDGATE_HUMAN_WAIT_SECONDS"] = "5"
    state = _state_with_one_question("Q-003")
    state.questions["Q-003"].raw_question = "Will all customer data remain exclusively in the EU?"
    state.questions["Q-003"].normalized_question = state.questions["Q-003"].raw_question
    state.questions["Q-003"].risk_tags = ["data_residency_overclaim"]
    publisher = BandPublisher(_config(), event_log=str(tmp_path / "band_events.jsonl"))
    orch = LiveOrchestrator(state, publisher=publisher, max_rounds=2)

    # Two-step decision sequence: push_back, then approve.
    orch.register_human_message(
        "Q-003",
        HumanDecision(action="push_back", content="Tighten residency wording."),
    )

    async def driver() -> None:
        task = asyncio.create_task(orch.deliberate("Q-003"))
        # Once first push_back is consumed, queue the final approve.
        await asyncio.sleep(0.1)
        orch.register_human_message(
            "Q-003",
            HumanDecision(action="approve", content="OK with new wording."),
        )
        await task

    asyncio.run(driver())
    final = state.questions["Q-003"]
    assert final.status == "finalized"
    assert len(final.approvals) >= 2
