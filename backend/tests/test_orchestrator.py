from agents.orchestrator import build_demo_state


def test_demo_state_finalizes_hero_questions() -> None:
    state = build_demo_state(post_band_events=False)
    finalized = [question for question in state.questions.values() if question.status == "finalized"]

    # v1 sample was 40 questions; v2 builder extends to 115. Either is fine
    # for the demo as long as the hero set is finalized.
    assert len(state.questions) >= 40
    assert len(finalized) >= 8
    assert state.questions["Q-001"].final_answer
    assert "99.5%" in state.questions["Q-001"].final_answer
    assert state.questions["Q-029"].risk_level == "critical"
    assert state.promise_ledger
    assert state.audit_trail


def test_final_answers_are_policy_or_evidence_backed() -> None:
    state = build_demo_state(post_band_events=False)

    for question_id in ["Q-001", "Q-002", "Q-003", "Q-005"]:
        question = state.questions[question_id]
        assert question.final_answer
        assert any(opinion.evidence or opinion.policy_violations for opinion in question.opinions)
