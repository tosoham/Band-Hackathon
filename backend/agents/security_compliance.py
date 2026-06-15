from core.schemas import AgentOpinion, Evidence, RFPQuestionState


def _evidence(source_id: str, document_name: str, quote: str, confidence: float = 0.9) -> Evidence:
    return Evidence(
        source_id=source_id,
        document_name=document_name,
        chunk_id="approved-wording",
        quote=quote,
        confidence=confidence,
    )


def retrieve_security_answer(question: RFPQuestionState) -> AgentOpinion:
    text = question.raw_question.lower()
    evidence: list[Evidence] = []

    if "fedramp" in text:
        answer = "SentinelAI is not currently FedRAMP authorized; readiness work is in progress."
        evidence.append(_evidence("security/fedramp_status", "fedramp_status.md", answer))
    elif "soc 2" in text:
        answer = "SentinelAI maintains SOC 2 Type II coverage for Security, Availability, and Confidentiality."
        evidence.append(_evidence("security/soc2_summary", "soc2_summary.md", answer))
    elif "iso 27001" in text:
        answer = "SentinelAI maintains ISO 27001-aligned information security management controls."
        evidence.append(_evidence("security/iso27001_controls", "iso27001_controls.md", answer))
    elif "encrypt" in text or "key" in text:
        answer = "Customer data is encrypted at rest and in transit; customer-managed keys require enterprise scoping."
        evidence.append(_evidence("security/encryption_policy", "encryption_policy.md", answer))
    elif "breach" in text or "incident" in text:
        answer = "SentinelAI maintains a documented incident response process with contractual notification obligations."
        evidence.append(_evidence("security/incident_response_policy", "incident_response_policy.md", answer))
    elif "eu" in text or "telemetry" in text:
        answer = "Primary customer data can be hosted in the EU; limited operational telemetry may be processed globally."
        evidence.append(_evidence("privacy/data_residency", "data_residency.md", answer))
    elif "customer data" in text and "train" in text:
        answer = "Customer data is not used to train foundation models without explicit contractual approval."
        evidence.append(_evidence("privacy/ai_data_usage", "ai_data_usage.md", answer))
    elif "subprocessor" in text:
        answer = "SentinelAI maintains a subprocessors list and handles notice rights through the DPA."
        evidence.append(_evidence("privacy/subprocessors", "subprocessors.md", answer))
    else:
        answer = "No specific approved evidence was retrieved for this Day 2 demo question."

    return AgentOpinion(
        agent_name="security_compliance",
        answer=answer,
        confidence=0.88 if evidence else 0.45,
        evidence=evidence,
        risk_tags=question.risk_tags,
    )
