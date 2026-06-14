from dataclasses import dataclass


@dataclass(frozen=True)
class ConflictEvaluation:
    risk_level: str
    assigned_agents: list[str]
    conflict_detected: bool
    summary: str | None
    risk_tags: list[str]


def evaluate_question(question: str, category: str) -> ConflictEvaluation:
    text = question.lower()
    category_text = category.lower()
    agents = {"sales_engineer", "security_compliance"}
    risk_tags: list[str] = []
    summary: str | None = None
    risk_level = "medium"

    if any(token in text for token in ["99.9", "99.99", "uptime", "financial penalties"]):
        agents.update({"product_capability", "legal_commitment_guard"})
        risk_tags.append("sla_overcommitment")
        summary = "SLA language may exceed approved commitment policy."
        risk_level = "high"

    if "fedramp" in text:
        agents.update({"legal_commitment_guard", "adversarial_reviewer"})
        risk_tags.append("compliance_overclaim")
        summary = "FedRAMP status must not be overstated."
        risk_level = "high"

    if "eu" in text and any(token in text for token in ["only", "exclusively", "remain"]):
        agents.update({"legal_commitment_guard", "adversarial_reviewer"})
        risk_tags.append("data_residency_overclaim")
        summary = "EU-only language may conflict with telemetry policy."
        risk_level = "high"

    if any(token in text for token in ["pentest", "penetration", "soc 2 report", "architecture diagram"]):
        agents.update({"legal_commitment_guard"})
        risk_tags.append("sensitive_disclosure")
        summary = "Sensitive security artifacts require NDA review."
        risk_level = "high"

    if any(token in text for token in ["ignore internal", "ignore policy", "answer all", "do not mention exceptions"]):
        agents.update({"adversarial_reviewer", "legal_commitment_guard"})
        risk_tags.append("prompt_injection")
        summary = "Buyer-provided text may be prompt injection."
        risk_level = "critical"

    if "ai" in category_text or "training" in text or "customer data" in text:
        agents.update({"product_capability", "legal_commitment_guard"})
        risk_tags.append("ai_data_usage_risk")
        risk_level = "high" if risk_level == "medium" else risk_level

    if "liability" in text or "indemn" in text:
        agents.update({"legal_commitment_guard"})
        risk_tags.append("liability_risk")
        risk_level = "high"

    conflict_detected = bool(risk_tags)
    if not conflict_detected:
        summary = "No deterministic Day 1 conflict detected."

    return ConflictEvaluation(
        risk_level=risk_level,
        assigned_agents=sorted(agents),
        conflict_detected=conflict_detected,
        summary=summary,
        risk_tags=risk_tags,
    )
