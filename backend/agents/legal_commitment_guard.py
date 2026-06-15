from typing import Any

from core.schemas import AgentOpinion, PolicyViolation, RFPQuestionState


def review_commitment(question: RFPQuestionState, policy: dict[str, Any]) -> AgentOpinion:
    text = question.raw_question.lower()
    violations: list[PolicyViolation] = []
    answer = "Approved with standard evidence-backed wording."
    confidence = 0.86

    if "uptime" in text:
        answer = (
            "Blocked risky SLA wording. Our standard enterprise SLA is 99.5%; "
            "99.9% may be available under a separate HA deployment addendum."
        )
        violations.append(
            PolicyViolation(
                policy_id="sla.max_without_approval",
                severity="high",
                claim="guarantee 99.9% uptime with financial penalties",
                allowed_position=policy["sla"]["approved_phrase"],
                recommended_fix="Use standard SLA wording and require HA addendum for 99.9%.",
            )
        )

    if "fedramp" in text:
        answer = "Blocked FedRAMP overclaim. SentinelAI is not currently FedRAMP authorized."
        violations.append(
            PolicyViolation(
                policy_id="compliance.fedramp_status",
                severity="high",
                claim="FedRAMP authorized",
                allowed_position="in_process_not_authorized",
                recommended_fix="State that FedRAMP readiness is in progress, not authorized.",
            )
        )

    if "eu" in text and ("exclusively" in text or "remain" in text):
        answer = policy["privacy"]["approved_data_residency_phrase"]
        violations.append(
            PolicyViolation(
                policy_id="privacy.eu_only_processing",
                severity="high",
                claim="all customer data remains exclusively in the EU",
                allowed_position=answer,
                recommended_fix="Use approved EU primary hosting wording with telemetry exception.",
            )
        )

    if "customer data" in text and "train" in text:
        answer = "Customer data is not used to train foundation models without explicit contractual approval."

    if "penetration" in text or "soc 2 report" in text or "architecture diagram" in text:
        answer = "Sensitive security artifacts may be made available under NDA after Security and Legal review."
        violations.append(
            PolicyViolation(
                policy_id="security_artifacts.nda_required",
                severity="high",
                claim="share sensitive security artifact before approval",
                allowed_position="NDA and Security/Legal review required",
                recommended_fix="Escalate for NDA confirmation before sharing artifacts.",
            )
        )

    if "liability" in text or "indemn" in text:
        answer = "Liability and indemnity terms are governed by the MSA; custom terms require Legal review."
        violations.append(
            PolicyViolation(
                policy_id="legal.liability_cap",
                severity="high",
                claim="uncapped or custom liability/indemnity",
                allowed_position=policy["legal"]["liability_cap"],
                recommended_fix="Escalate any custom liability or indemnity language to Legal.",
            )
        )

    if not violations:
        confidence = 0.78

    return AgentOpinion(
        agent_name="legal_commitment_guard",
        answer=answer,
        confidence=confidence,
        policy_violations=violations,
        risk_tags=question.risk_tags,
    )
