from core.schemas import AgentOpinion, Evidence, RFPQuestionState


def check_product_capability(question: RFPQuestionState) -> AgentOpinion:
    text = question.raw_question.lower()
    evidence: list[Evidence] = []

    if "uptime" in text or "high availability" in text:
        answer = "99.9% uptime is architecturally possible only with HA deployment and a separate addendum."
        evidence.append(
            Evidence(
                source_id="product/ha_architecture",
                document_name="ha_architecture.md",
                chunk_id="ha-deployment",
                quote=answer,
                confidence=0.9,
            )
        )
    elif "deployment" in text or "two weeks" in text or "implementation" in text:
        answer = "Standard implementation is planned over at least 8 weeks; custom integrations require scoping."
        evidence.append(
            Evidence(
                source_id="product/implementation_timeline",
                document_name="implementation_timeline.md",
                chunk_id="standard-timeline",
                quote=answer,
                confidence=0.88,
            )
        )
    else:
        answer = "No product limitation was identified beyond normal enterprise scoping."

    return AgentOpinion(
        agent_name="product_capability",
        answer=answer,
        confidence=0.82 if evidence else 0.55,
        evidence=evidence,
        risk_tags=question.risk_tags,
    )
