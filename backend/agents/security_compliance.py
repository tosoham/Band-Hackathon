"""Security & Compliance RAG agent.

Now AI/ML-led: the agent retrieves evidence via embedding RAG, then asks
AI/ML to synthesize an answer strictly from that evidence. The
deterministic citation-gated quote stitching is the fallback when AI/ML is
unavailable or fails. Either way, no evidence means no supported claim.
"""

from core.model_clients import aiml_available, aiml_reason
from core.provider_config import load_provider_config
from core.rag import retrieve
from core.schemas import AgentOpinion

AGENT_NAME = "security_compliance"

_UNSUPPORTED = (
    "No approved evidence was found for this question. The claim is unsupported "
    "and must be escalated rather than answered."
)


def answer_from_evidence(question: str, top_k: int = 4) -> AgentOpinion:
    evidence = retrieve(question, top_k=top_k)

    if not evidence:
        return AgentOpinion(
            agent_name=AGENT_NAME,
            provider="deterministic",
            model_name="day2-rag",
            answer=_UNSUPPORTED,
            confidence=0.0,
            evidence=[],
            risk_tags=["unsupported"],
        )

    evidence_payload = [
        {
            "chunk_id": ev.chunk_id,
            "document_name": ev.document_name,
            "quote": ev.quote,
        }
        for ev in evidence
    ]

    if aiml_available():
        result = aiml_reason(
            "security_compliance",
            question,
            evidence=evidence_payload,
            extra_instructions=(
                "Reply with the safest cited answer. If the evidence does not "
                "fully support a yes, say so explicitly. citations must use "
                "chunk_ids from the retrieved evidence."
            ),
            max_tokens=320,
        )
        if result is not None:
            confidence = float(result["confidence"])
            return AgentOpinion(
                agent_name=AGENT_NAME,
                provider="aiml",
                model_name=load_provider_config().aiml_model,
                answer=result["answer"],
                confidence=round(min(1.0, max(0.0, confidence)), 2),
                evidence=evidence,
                risk_tags=["supported_by_evidence"],
            )

    # Deterministic fallback: build the answer from the highest-confidence approved
    # wording we retrieved.
    answer = evidence[0].quote
    confidence = round(min(1.0, sum(e.confidence for e in evidence) / len(evidence)), 2)

    return AgentOpinion(
        agent_name=AGENT_NAME,
        provider="deterministic",
        model_name="day2-rag",
        answer=answer,
        confidence=confidence,
        evidence=evidence,
        risk_tags=["supported_by_evidence"],
    )
