from scripts.run_band_collaboration import build_six_agent_transcript


def test_six_agent_transcript_contains_all_roles(monkeypatch) -> None:
    monkeypatch.setenv("AIML_MODE", "mock")
    monkeypatch.setenv("FEATHERLESS_MODE", "mock")

    messages, findings, summary = build_six_agent_transcript()
    agents = {message["agent"] for message in messages}

    assert {
        "intake_agent",
        "sales_engineer",
        "security_compliance",
        "product_capability",
        "legal_commitment_guard",
        "adversarial_reviewer",
    } <= agents
    assert "human_gate" in agents
    assert findings
    assert "six-agent" in summary.lower() or "six agent" in summary.lower()


def test_transcript_exposes_security_controls(monkeypatch) -> None:
    monkeypatch.setenv("AIML_MODE", "mock")
    monkeypatch.setenv("FEATHERLESS_MODE", "mock")

    messages, findings, _summary = build_six_agent_transcript()
    transcript = "\n".join(message["content"] for message in messages).lower()
    drift_tags = {tag for finding in findings for tag in finding["drift_tags"]}

    assert "fedramp" in transcript
    assert "prompt injection" in transcript
    assert "nda" in transcript
    assert "sales_sla_overpromise" in drift_tags
    assert "featherless fallback path" in transcript
