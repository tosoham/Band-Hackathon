"""Legal / Commitment Guard.

Deterministic policy detection is the hard gate — it identifies every
PolicyViolation that the commitment policy YAML disallows. AI/ML adds a
reasoning trace and a richer answer, but it can never remove a violation.
Provider stays as ``aiml`` only when reasoning succeeded; the deterministic
violations always win on the final answer when they are present.
"""

from typing import Any

from core.model_clients import aiml_available, aiml_reason
from core.provider_config import load_provider_config
from core.schemas import AgentOpinion, PolicyViolation, RFPQuestionState


def review_commitment(question: RFPQuestionState, policy: dict[str, Any]) -> AgentOpinion:
    text = question.raw_question.lower()
    violations: list[PolicyViolation] = []
    deterministic_answer = "Approved with standard evidence-backed wording."
    confidence = 0.86

    if "uptime" in text:
        deterministic_answer = (
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
        deterministic_answer = "Blocked FedRAMP overclaim. SentinelAI is not currently FedRAMP authorized."
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
        deterministic_answer = policy["privacy"]["approved_data_residency_phrase"]
        violations.append(
            PolicyViolation(
                policy_id="privacy.eu_only_processing",
                severity="high",
                claim="all customer data remains exclusively in the EU",
                allowed_position=deterministic_answer,
                recommended_fix="Use approved EU primary hosting wording with telemetry exception.",
            )
        )

    if "customer data" in text and "train" in text:
        deterministic_answer = "Customer data is not used to train foundation models without explicit contractual approval."

    if "penetration" in text or "soc 2 report" in text or "architecture diagram" in text:
        deterministic_answer = "Sensitive security artifacts may be made available under NDA after Security and Legal review."
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
        deterministic_answer = "Liability and indemnity terms are governed by the MSA; custom terms require Legal review."
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

    provider = "deterministic"
    model_name = "day2-rule"
    answer = deterministic_answer

    # AI/ML reasoning trace: enrich the answer's wording, but the deterministic
    # rules above remain the hard gate. AI/ML never removes a violation.
    if aiml_available():
        ai_result = aiml_reason(
            "legal_commitment_guard",
            question.raw_question,
            policy_slice=_relevant_policy_slice(policy, violations),
            extra_instructions=(
                "Use the policy slice as the source of truth. If the deterministic "
                "violations list is non-empty, your answer must align with the "
                "allowed_position for each violation. Do not soften refusals."
            ),
        )
        if ai_result is not None:
            provider = "aiml"
            model_name = load_provider_config().aiml_model
            ai_answer = ai_result["answer"]
            # When deterministic policy already produced an approved refusal, keep
            # the AI/ML wording but always prepend the deterministic verdict so
            # the policy line never gets diluted.
            if violations:
                answer = f"{deterministic_answer} {ai_answer}".strip()
            else:
                answer = ai_answer
            confidence = max(confidence, ai_result["confidence"])

    return AgentOpinion(
        agent_name="legal_commitment_guard",
        provider=provider,
        model_name=model_name,
        answer=answer,
        confidence=round(min(1.0, max(0.0, confidence)), 2),
        policy_violations=violations,
        risk_tags=question.risk_tags,
    )


def _relevant_policy_slice(policy: dict[str, Any], violations: list[PolicyViolation]) -> dict[str, Any]:
    keys = {v.policy_id.split(".")[0] for v in violations}
    if not keys:
        return {k: policy.get(k) for k in ("sla", "compliance", "legal", "privacy")}
    return {k: policy.get(k) for k in keys if k in policy}
