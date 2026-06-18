"""Product Capability agent.

Classifies what the product can actually do today, so the final answer never
treats roadmap or scoping-dependent features as standard. AI/ML drives the
synthesis when available; deterministic keyword rules from the original
implementation remain as the fallback.
"""

from agents.reviewer_note import append_reviewer_note, normalize_reviewer_note
from core.model_clients import aiml_available, aiml_reason
from core.provider_config import load_provider_config
from core.rag import retrieve
from core.schemas import AgentOpinion

AGENT_NAME = "product_capability"

_LEVELS = (
    "generally_available",
    "architecturally_possible",
    "requires_custom_scoping",
    "roadmap_only",
    "contractually_approved",
)

# (capability level, human summary, keywords that imply it). First match wins.
_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    (
        "architecturally_possible",
        "Available only under a specific deployment option or addendum, not as a "
        "standard commitment.",
        ("99.9", "99.99", "uptime", "high availability", "ha "),
    ),
    (
        "requires_custom_scoping",
        "Feasible but requires technical scoping before a timeline or commitment "
        "can be given.",
        ("custom", "integration", "two weeks", "timeline", "managed keys", "byok"),
    ),
    (
        "roadmap_only",
        "Planned on the roadmap and must not be committed in an RFP response.",
        ("roadmap", "future", "planned", "upcoming"),
    ),
]

_DEFAULT = (
    "generally_available",
    "Generally available to enterprise customers today.",
)


def assess_capability(
    question: str, top_k: int = 4, human_note: str | None = None
) -> AgentOpinion:
    # ``human_note`` is a reviewer @mention instruction from the human gate. It
    # can steer the explanation but never upgrades the capability level beyond
    # what the product actually supports.
    note = normalize_reviewer_note(human_note)
    # Cite product corpus where possible.
    evidence = [e for e in retrieve(question, top_k=top_k) if e.document_name.startswith("product/")]

    if aiml_available():
        evidence_payload = [
            {"chunk_id": ev.chunk_id, "document_name": ev.document_name, "quote": ev.quote}
            for ev in evidence
        ]
        extra_instructions = (
            "Classify the capability as one of: "
            + ", ".join(_LEVELS)
            + ". State the level explicitly in the answer."
        )
        if note is not None:
            extra_instructions += (
                f" Human reviewer instruction to address (without overstating the "
                f"true capability level): {note}"
            )
        ai_result = aiml_reason(
            "product_capability",
            question,
            evidence=evidence_payload,
            extra_instructions=extra_instructions,
        )
        if ai_result is not None:
            level = _detect_level(ai_result["answer"])
            return AgentOpinion(
                agent_name=AGENT_NAME,
                provider="aiml",
                model_name=load_provider_config().aiml_model,
                answer=ai_result["answer"],
                confidence=round(min(1.0, max(0.0, ai_result["confidence"])), 2),
                evidence=evidence,
                risk_tags=[f"capability_{level}"],
            )

    text = question.lower()
    level, summary = _DEFAULT
    for candidate_level, candidate_summary, keywords in _RULES:
        if any(keyword in text for keyword in keywords):
            level, summary = candidate_level, candidate_summary
            break

    answer = f"Capability: {level.replace('_', ' ')}. {summary}"
    answer = append_reviewer_note(answer, note)

    return AgentOpinion(
        agent_name=AGENT_NAME,
        provider="deterministic",
        model_name="day2-rule",
        answer=answer,
        confidence=0.6,
        evidence=evidence,
        risk_tags=[f"capability_{level}"],
    )


def _detect_level(text: str) -> str:
    lowered = text.lower()
    for level in _LEVELS:
        if level.replace("_", " ") in lowered or level in lowered:
            return level
    if "roadmap" in lowered:
        return "roadmap_only"
    if "custom scoping" in lowered or "scoping" in lowered:
        return "requires_custom_scoping"
    if "addendum" in lowered or "high availability" in lowered:
        return "architecturally_possible"
    return "generally_available"
