import urllib.error

import pytest

import core.model_clients as mc
from core.rag import load_corpus, retrieve
from core.rfp_parser import load_questions


def test_rag_handles_missing_corpus() -> None:
    load_corpus.cache_clear()
    assert load_corpus("definitely_not_a_real_kb_dir") == ()
    assert retrieve("anything", kb_root="definitely_not_a_real_kb_dir") == []
    load_corpus.cache_clear()


def test_csv_missing_file_raises_clear_error() -> None:
    with pytest.raises(FileNotFoundError):
        load_questions("data/does_not_exist.csv")


def test_csv_skips_malformed_rows(tmp_path) -> None:
    csv_path = tmp_path / "q.csv"
    csv_path.write_text(
        "question_id,category,question\n"
        "Q-1,sla,Valid question?\n"
        ",sla,Missing id\n"
        "Q-2,sla,\n"
        "Q-3,security,Another valid question?\n",
        encoding="utf-8",
    )
    rows = load_questions(str(csv_path))
    assert [r.question_id for r in rows] == ["Q-1", "Q-3"]


def test_aiml_retries_then_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "live")
    monkeypatch.setenv("AIML_ENABLED", "true")
    monkeypatch.setenv("AIML_API_KEY", "test-key")
    monkeypatch.setattr(mc, "_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(mc, "_BACKOFF_SECONDS", 0)  # no real sleeping in tests
    mc.reset_provider_call_counts()

    attempts = {"count": 0}

    def boom(*args, **kwargs):
        attempts["count"] += 1
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(mc.urllib.request, "urlopen", boom)

    assert mc.chat_json("sys", "user") is None
    assert attempts["count"] == 3  # retried up to the cap, then fell back


def test_aiml_does_not_retry_on_bad_json(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "live")
    monkeypatch.setenv("AIML_ENABLED", "true")
    monkeypatch.setenv("AIML_API_KEY", "test-key")
    monkeypatch.setattr(mc, "_BACKOFF_SECONDS", 0)
    mc.reset_provider_call_counts()

    attempts = {"count": 0}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"not-json"

    def once(*args, **kwargs):
        attempts["count"] += 1
        return FakeResponse()

    monkeypatch.setattr(mc.urllib.request, "urlopen", once)

    assert mc.chat_json("sys", "user") is None
    assert attempts["count"] == 1  # malformed responses are not retried
