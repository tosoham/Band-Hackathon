"""Promise Ledger detection.

A finalized BandGate answer creates a commitment when it carries a risk tag
that delivery teams must own post-sale: SLA, residency, AI data use,
sensitive artifact sharing, liability. This module is the single source of
that mapping so the v1 demo orchestrator and the v2 live orchestrator stay
in sync.
"""

from __future__ import annotations

from core.schemas import BandGateState, PromiseLedgerEntry, RFPQuestionState

_TAG_TO_TEMPLATE: list[tuple[str, dict[str, str]]] = [
    (
        "sla_overcommitment",
        {
            "commitment_text": "99.5% standard SLA; 99.9% only with HA deployment addendum.",
            "owner_department": "Customer Success",
            "delivery_action": "Confirm SLA tier and HA addendum during onboarding.",
            "due_stage": "contracting",
        },
    ),
    (
        "data_residency_overclaim",
        {
            "commitment_text": "EU primary data hosting with global operational telemetry exception.",
            "owner_department": "Delivery",
            "delivery_action": "Configure customer primary region and disclose telemetry subprocessors.",
            "due_stage": "implementation",
        },
    ),
    (
        "ai_data_usage_risk",
        {
            "commitment_text": "No customer data training without explicit contractual approval.",
            "owner_department": "Product",
            "delivery_action": "Preserve tenant training exclusion in workspace configuration.",
            "due_stage": "implementation",
        },
    ),
    (
        "sensitive_disclosure",
        {
            "commitment_text": "Sensitive security artifacts shared under NDA after Security/Legal review.",
            "owner_department": "Security",
            "delivery_action": "Track NDA execution and artifact transmittal log.",
            "due_stage": "contracting",
        },
    ),
    (
        "liability_risk",
        {
            "commitment_text": "Liability/indemnity governed by MSA standard cap; custom terms require Legal sign-off.",
            "owner_department": "Legal",
            "delivery_action": "Attach approved MSA addendum to contract package.",
            "due_stage": "contracting",
        },
    ),
    (
        "compliance_overclaim",
        {
            "commitment_text": "FedRAMP status disclosed as in-process, not authorized; reassess at FedRAMP authorization.",
            "owner_department": "Security",
            "delivery_action": "Update buyer when authorization status changes.",
            "due_stage": "renewal",
        },
    ),
]


def detect_ledger_entry(question: RFPQuestionState) -> dict | None:
    """Return the template for the first matching risk tag, or None."""
    for tag, template in _TAG_TO_TEMPLATE:
        if tag in question.risk_tags:
            return template
    return None


def add_ledger_entry_if_new(state: BandGateState, question: RFPQuestionState) -> PromiseLedgerEntry | None:
    """Append a Promise Ledger entry for ``question`` if one matches and is new."""
    if not question.final_answer:
        return None
    template = detect_ledger_entry(question)
    if not template:
        return None
    commitment_id = _commitment_id_for(question.question_id)
    existing = {item.commitment_id for item in state.promise_ledger}
    if commitment_id in existing:
        return None
    entry = PromiseLedgerEntry(
        commitment_id=commitment_id,
        source_question_id=question.question_id,
        commitment_text=template["commitment_text"],
        owner_department=template["owner_department"],  # type: ignore[arg-type]
        delivery_action=template["delivery_action"],
        due_stage=template["due_stage"],  # type: ignore[arg-type]
        approval_required=True,
    )
    state.promise_ledger.append(entry)
    return entry


def _commitment_id_for(question_id: str) -> str:
    return f"COM-{question_id.replace('Q-', '').zfill(4)}"
