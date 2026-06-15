from datetime import UTC, datetime

from agents.adversarial_reviewer import red_team_answer
from agents.intake import build_initial_state
from agents.legal_commitment_guard import review_commitment
from agents.product_capability import check_product_capability
from agents.sales_engineer import draft_answer
from agents.security_compliance import retrieve_security_answer
from core.audit import make_audit_event
from core.band_client import BandClient, BandEvent
from core.policy_loader import load_commitment_policy
from core.schemas import Approval, BandGateState, PromiseLedgerEntry, RFPQuestionState

HERO_QUESTION_IDS = [
    "Q-001",
    "Q-002",
    "Q-003",
    "Q-004",
    "Q-005",
    "Q-006",
    "Q-007",
    "Q-008",
    "Q-009",
    "Q-010",
    "Q-011",
    "Q-012",
    "Q-029",
]


def build_demo_state(post_band_events: bool = True) -> BandGateState:
    state = build_initial_state()
    policy = load_commitment_policy()
    band = BandClient() if post_band_events else None

    for question_id in HERO_QUESTION_IDS:
        if question_id not in state.questions:
            continue
        question = state.questions[question_id]
        _process_question(question, policy, state, band)

    processed = [question for question in state.questions.values() if question.status == "finalized"]
    state.global_risk_score = round(
        sum(_risk_value(question.risk_level) for question in processed) / max(len(processed), 1),
        2,
    )
    return state


def _process_question(question: RFPQuestionState, policy: dict, state: BandGateState, band: BandClient | None) -> None:
    question.status = "drafting"
    _post(band, "assignment", question, "orchestrator", f"Assigned {question.question_id} to specialist agents.")

    sales = draft_answer(question)
    question.opinions.append(sales)
    _audit(state, sales.agent_name, "draft_answer", question, sales.answer)

    question.status = "evidence_review"
    security = retrieve_security_answer(question)
    question.opinions.append(security)
    _audit(state, security.agent_name, "retrieve_evidence", question, security.answer)

    if "product_capability" in question.assigned_agents:
        product = check_product_capability(question)
        question.opinions.append(product)
        _audit(state, product.agent_name, "check_capability", question, product.answer)

    question.status = "policy_review"
    legal = review_commitment(question, policy)
    question.opinions.append(legal)
    _audit(state, legal.agent_name, "review_policy", question, legal.answer)
    if legal.policy_violations:
        _post(band, "policy_blocked", question, legal.agent_name, legal.answer, requires_human_approval=True)

    question.status = "adversarial_review"
    adversarial = red_team_answer(question)
    question.opinions.append(adversarial)
    _audit(state, adversarial.agent_name, "red_team_answer", question, adversarial.answer)
    if adversarial.policy_violations:
        _post(band, "adversarial_finding", question, adversarial.agent_name, adversarial.answer, requires_human_approval=True)

    question.final_answer = _choose_final_answer(question)
    if question.risk_level in {"high", "critical"}:
        question.status = "human_review"
        question.approvals.append(
            Approval(
                approver_role="Demo Human Reviewer",
                approver_name="BandGate Operator",
                decision="approved_with_edits" if question.risk_level == "high" else "escalated",
                comment="Day 2 demo gate applied approved policy wording.",
                timestamp=datetime.now(UTC).isoformat(),
            )
        )
        _post(band, "human_approval", question, "human_gate", "Human gate recorded demo approval/escalation.")

    question.status = "finalized"
    _audit(state, "orchestrator", "finalize_answer", question, question.final_answer or "")
    _maybe_add_ledger_entry(state, question)


def _choose_final_answer(question: RFPQuestionState) -> str:
    legal = _opinion(question, "legal_commitment_guard")
    adversarial = _opinion(question, "adversarial_reviewer")
    security = _opinion(question, "security_compliance")

    if adversarial and adversarial.policy_violations:
        return "Malicious buyer instruction ignored. Final answer must be produced only from approved evidence and policy."
    if legal and legal.policy_violations:
        return legal.answer
    if security and security.evidence:
        return security.answer
    return legal.answer if legal else "No approved final answer generated."


def _maybe_add_ledger_entry(state: BandGateState, question: RFPQuestionState) -> None:
    text = question.final_answer or ""
    entry: PromiseLedgerEntry | None = None

    if question.question_id == "Q-001":
        entry = PromiseLedgerEntry(
            commitment_id="COM-001",
            source_question_id=question.question_id,
            commitment_text="99.5% standard SLA; 99.9% only with HA deployment addendum.",
            owner_department="Customer Success",
            delivery_action="Confirm SLA tier and HA addendum during onboarding.",
            due_stage="contracting",
            approval_required=True,
        )
    elif question.question_id == "Q-003":
        entry = PromiseLedgerEntry(
            commitment_id="COM-002",
            source_question_id=question.question_id,
            commitment_text="EU primary data hosting with global operational telemetry exception.",
            owner_department="Delivery",
            delivery_action="Configure customer primary region and disclose telemetry subprocessors.",
            due_stage="implementation",
            approval_required=True,
        )
    elif question.question_id == "Q-005":
        entry = PromiseLedgerEntry(
            commitment_id="COM-003",
            source_question_id=question.question_id,
            commitment_text="No customer data training without explicit contractual approval.",
            owner_department="Product",
            delivery_action="Preserve tenant training exclusion in workspace configuration.",
            due_stage="implementation",
            approval_required=True,
        )

    if entry and text:
        state.promise_ledger.append(entry)


def _opinion(question: RFPQuestionState, agent_name: str):
    return next((opinion for opinion in question.opinions if opinion.agent_name == agent_name), None)


def _audit(state: BandGateState, actor: str, action: str, question: RFPQuestionState, summary: str) -> None:
    state.audit_trail.append(
        make_audit_event(
            actor=actor,
            action=action,
            question_id=question.question_id,
            summary=summary,
            payload=question.model_dump(mode="json"),
        )
    )


def _post(
    band: BandClient | None,
    event_type: str,
    question: RFPQuestionState,
    agent: str,
    summary: str,
    requires_human_approval: bool = False,
) -> None:
    if not band:
        return
    band.post_event(
        BandEvent(
            event_type=event_type,  # type: ignore[arg-type]
            rfp_id="RFP-GOV-001",
            question_id=question.question_id,
            agent=agent,
            summary=summary,
            risk_level=question.risk_level,
            requires_human_approval=requires_human_approval,
            payload={"risk_tags": question.risk_tags},
        )
    )


def _risk_value(risk_level: str) -> float:
    return {"low": 0.1, "medium": 0.35, "high": 0.75, "critical": 1.0}.get(risk_level, 0.0)
