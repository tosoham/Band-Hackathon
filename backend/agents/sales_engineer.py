from core.schemas import AgentOpinion, RFPQuestionState


def draft_answer(question: RFPQuestionState) -> AgentOpinion:
    text = question.raw_question.lower()

    if "uptime" in text:
        answer = "Yes, our enterprise platform supports 99.9% uptime for qualified enterprise deployments."
    elif "fedramp" in text:
        answer = "We meet many FedRAMP-aligned security requirements and can discuss our roadmap."
    elif "eu" in text and "data" in text:
        answer = "Yes, customer data can be hosted in the EU for eligible deployments."
    elif "customer data" in text and "train" in text:
        answer = "No, customer data is not used to train foundation models without explicit contractual approval."
    elif "penetration" in text or "soc 2 report" in text or "architecture diagram" in text:
        answer = "Security artifacts can be shared with qualified buyers under the appropriate review process."
    elif "liability" in text or "indemn" in text:
        answer = "Commercial and legal terms are handled through our standard MSA and review process."
    else:
        answer = "SentinelAI can support this requirement subject to standard enterprise scoping and approval."

    return AgentOpinion(
        agent_name="sales_engineer",
        answer=answer,
        confidence=0.72,
        risk_tags=question.risk_tags,
    )
