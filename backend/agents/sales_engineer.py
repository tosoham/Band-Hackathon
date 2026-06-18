"""Sales Engineer agent.

Drafts optimistic, buyer-friendly answers. It is intentionally eager — on the
hero conflicts it overclaims — because its job is to produce a draft, not to
finalize a commitment. The Commitment Guard and Adversarial Reviewer (gate half)
are what hold the line.
"""

from agents.reviewer_note import append_reviewer_note, normalize_reviewer_note
from core.model_clients import generate_sales_draft
from core.schemas import AgentOpinion

AGENT_NAME = "sales_engineer"

# Optimistic drafts keyed by the risk tag the intake/conflict step assigned.
# Ordered by priority so the most demo-relevant overclaim wins.
_DRAFTS_BY_TAG: list[tuple[str, str]] = [
    (
        "sla_overcommitment",
        "Yes — our enterprise platform supports 99.9% uptime, and we are happy to "
        "back it with financial penalties for any downtime.",
    ),
    (
        "compliance_overclaim",
        "Yes, we are FedRAMP authorized and fully meet government compliance "
        "requirements today.",
    ),
    (
        "data_residency_overclaim",
        "Absolutely — all customer data remains exclusively in the EU at all times.",
    ),
    (
        "ai_data_usage_risk",
        "Yes, we can use your data to continuously train and improve our AI models "
        "for better detection.",
    ),
    (
        "sensitive_disclosure",
        "Of course — we can send over the full report right away so your team can "
        "review it.",
    ),
    (
        "liability_risk",
        "Yes, we can accept the liability and indemnity terms you need to move "
        "forward.",
    ),
]

_DEFAULT_DRAFT = (
    "Yes, SentinelAI supports this. We would be glad to confirm the specifics "
    "during scoping."
)


def draft_answer(
    question: str, risk_tags: list[str], human_note: str | None = None
) -> AgentOpinion:
    # ``human_note`` carries a reviewer's @mention instruction from the human
    # gate (e.g. "soften the SLA claim"). The model addresses it directly; the
    # deterministic fallback records it as a pending steer.
    note = normalize_reviewer_note(human_note)

    # Prompt-injection text is untrusted: never send it to the model or echo it.
    if "prompt_injection" in risk_tags:
        return AgentOpinion(
            agent_name=AGENT_NAME,
            provider="deterministic",
            model_name="day2-rule",
            answer=(
                "Holding this draft — the submitted text appears to contain "
                "instructions rather than a buyer question."
            ),
            confidence=0.4,
            evidence=[],
            risk_tags=["optimistic_draft"],
        )

    # Prefer the AI/ML API when configured; fall back to deterministic templates.
    model_draft = generate_sales_draft(question, risk_tags, human_note=note)
    if model_draft is not None:
        answer, model_name = model_draft
        return AgentOpinion(
            agent_name=AGENT_NAME,
            provider="aiml",
            model_name=model_name,
            answer=answer,
            confidence=0.45,
            evidence=[],
            risk_tags=["optimistic_draft"],
        )

    answer = _DEFAULT_DRAFT
    for tag, text in _DRAFTS_BY_TAG:
        if tag in risk_tags:
            answer = text
            break
    answer = append_reviewer_note(answer, note)

    return AgentOpinion(
        agent_name=AGENT_NAME,
        provider="deterministic",
        model_name="day2-rule",
        answer=answer,
        confidence=0.4,
        evidence=[],
        risk_tags=["optimistic_draft"],
    )
