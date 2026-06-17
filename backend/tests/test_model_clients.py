from core.model_clients import (
    aiml_available,
    describe_model_call,
    featherless_available,
    get_provider_call_counts,
    reset_provider_call_counts,
)


def test_aiml_disabled_explicitly_blocks_calls_even_with_key(monkeypatch) -> None:
    # v2 flipped AIML_ENABLED to default true. The remaining safety check is
    # that an explicit false still blocks live calls.
    monkeypatch.setenv("AIML_MODE", "live")
    monkeypatch.setenv("AIML_API_KEY", "test-key")
    monkeypatch.setenv("AIML_ENABLED", "false")

    assert aiml_available() is False
    plan = describe_model_call("aiml")
    assert plan.mode == "live"
    assert plan.live_enabled is False


def test_aiml_enabled_by_default_when_key_and_mode_set(monkeypatch) -> None:
    monkeypatch.setenv("AIML_MODE", "live")
    monkeypatch.setenv("AIML_API_KEY", "test-key")
    monkeypatch.delenv("AIML_ENABLED", raising=False)

    assert aiml_available() is True


def test_aiml_can_be_enabled_explicitly(monkeypatch) -> None:
    monkeypatch.setenv("AIML_MODE", "live")
    monkeypatch.setenv("AIML_API_KEY", "test-key")
    monkeypatch.setenv("AIML_ENABLED", "true")

    assert aiml_available() is True


def test_featherless_live_uses_documented_defaults(monkeypatch) -> None:
    monkeypatch.setenv("FEATHERLESS_MODE", "live")
    monkeypatch.setenv("FEATHERLESS_API_KEY", "test-key")
    monkeypatch.delenv("FEATHERLESS_BASE_URL", raising=False)
    monkeypatch.delenv("FEATHERLESS_MODEL", raising=False)

    assert featherless_available() is True


def test_provider_call_counts_can_reset() -> None:
    reset_provider_call_counts()
    counts = get_provider_call_counts()
    counts["aiml_report"] = 99

    assert get_provider_call_counts() == {}


def test_aiml_new_demo_budgets_are_configurable(monkeypatch) -> None:
    monkeypatch.setenv("AIML_DRIFT_LIVE_LIMIT", "4")
    monkeypatch.setenv("AIML_INTAKE_RISK_LIVE_LIMIT", "5")
    monkeypatch.setenv("AIML_REPORT_LIVE_LIMIT", "1")

    from core.provider_config import load_provider_config

    config = load_provider_config()
    assert config.aiml_drift_live_limit == 4
    assert config.aiml_intake_risk_live_limit == 5
    assert config.aiml_report_live_limit == 1
