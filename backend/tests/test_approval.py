import pytest

from agents.approval import apply_decision
from agents.intake import build_state


def test_approve_sets_status_and_final_answer() -> None:
    state = build_state()
    qid = "Q-001"
    question = apply_decision(
        state,
        qid,
        "approved",
        approver_role="Legal",
        final_answer="Our standard enterprise SLA is 99.5%.",
    )
    assert question.status == "approved"
    assert question.final_answer == "Our standard enterprise SLA is 99.5%."
    assert question.approvals[-1].decision == "approved"
    assert state.audit_trail[-1].question_id == qid


def test_approve_with_edits_records_edited_answer() -> None:
    state = build_state()
    question = apply_decision(
        state,
        "Q-002",
        "approved_with_edits",
        approver_role="Compliance",
        final_answer="We are not currently FedRAMP authorized.",
    )
    assert question.status == "approved"
    assert "not currently FedRAMP" in question.final_answer


def test_reject_clears_final_answer_and_holds_review() -> None:
    state = build_state()
    question = apply_decision(state, "Q-003", "rejected", approver_role="Security")
    assert question.status == "human_review"
    assert question.final_answer is None
    assert question.approvals[-1].decision == "rejected"


def test_escalate_records_approval_and_audit() -> None:
    state = build_state()
    before = len(state.audit_trail)
    apply_decision(state, "Q-004", "escalated", approver_role="Sales", comment="needs Legal")
    assert len(state.audit_trail) == before + 1


def test_unknown_question_and_invalid_decision_raise() -> None:
    state = build_state()
    with pytest.raises(KeyError):
        apply_decision(state, "Q-999", "approved", approver_role="Legal")
    with pytest.raises(ValueError):
        apply_decision(state, "Q-001", "maybe", approver_role="Legal")
