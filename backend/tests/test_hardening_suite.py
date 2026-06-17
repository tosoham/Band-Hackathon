from scripts.run_hardening_suite import run_hardening_suite


def test_hardening_suite_returns_four_scenarios(monkeypatch) -> None:
    monkeypatch.setenv("AIML_MODE", "mock")
    monkeypatch.setenv("FEATHERLESS_MODE", "mock")

    report = run_hardening_suite()

    assert len(report["results"]) == 4
    assert "hardening" in report["summary"].lower()
    assert all(item["blocked"] for item in report["results"])


def test_hardening_suite_catches_secret_leakage(monkeypatch) -> None:
    monkeypatch.setenv("AIML_MODE", "mock")
    monkeypatch.setenv("FEATHERLESS_MODE", "mock")

    report = run_hardening_suite()
    secret_case = next(item for item in report["results"] if item["id"] == "H-004")
    tags = set(secret_case["draft_drift"]["drift_tags"])

    assert "sales_training_data_overclaim" in tags
    assert secret_case["blocked"] is True
