from core.citation_gate import SUPPORTED_TAG, UNSUPPORTED_TAG, enforce, is_grounded
from core.schemas import AgentOpinion


def test_citation_gate_downgrades_ungrounded_supported_claim() -> None:
    opinion = AgentOpinion(
        agent_name="security_compliance",
        provider="deterministic",
        model_name="test",
        answer="This claim is supported.",
        confidence=0.9,
        risk_tags=[SUPPORTED_TAG],
    )

    gated = enforce(opinion)

    assert is_grounded(opinion) is False
    assert gated.confidence == 0.0
    assert SUPPORTED_TAG not in gated.risk_tags
    assert UNSUPPORTED_TAG in gated.risk_tags
    assert "No approved evidence" in gated.answer
