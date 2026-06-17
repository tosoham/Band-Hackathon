import asyncio
import json
from pathlib import Path

from core.band_publisher import BandPublisher
from core.provider_config import ProviderConfig


def _config(mode: str = "lite") -> ProviderConfig:
    return ProviderConfig(
        band_mode=mode,  # type: ignore[arg-type]
        featherless_mode="lite",
        aiml_mode="lite",
        featherless_api_key=None,
        aiml_api_key=None,
        band_default_room_id=None,
        band_rest_url="https://app.band.ai/",
        band_ws_url="wss://app.band.ai/api/v1/socket/websocket",
    )


def test_publisher_writes_jsonl_in_lite_mode(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    pub = BandPublisher(_config("lite"), event_log=str(log))
    result = asyncio.run(
        pub.post(
            "sales_engineer",
            "Yes, our SLA is 99.9% with credits.",
            rfp_id="RFP-1",
            question_id="Q-001",
            event_type="agent_output",
            mentions=["legal_commitment_guard"],
            risk_level="high",
            payload={"round_no": 1},
        )
    )
    assert result.posted_to_jsonl is True
    assert result.posted_to_band is False
    rec = json.loads(log.read_text(encoding="utf-8").strip())
    assert rec["agent"] == "sales_engineer"
    assert rec["payload"]["mentions"] == ["legal_commitment_guard"]
    assert rec["payload"]["round_no"] == 1


def test_publisher_live_mode_degrades_without_band_sdk(tmp_path: Path, monkeypatch) -> None:
    log = tmp_path / "events.jsonl"
    pub = BandPublisher(_config("live"), event_log=str(log))

    async def fake_ensure_room(rfp_id: str) -> str | None:
        pub._sdk_failure = "sdk_unavailable: test"
        return None

    monkeypatch.setattr(pub, "ensure_room", fake_ensure_room)
    result = asyncio.run(
        pub.post(
            "intake_agent",
            "Triage start.",
            rfp_id="RFP-1",
            question_id="Q-001",
        )
    )
    assert result.posted_to_jsonl is True
    assert result.posted_to_band is False
    assert "sdk_unavailable" in (result.error or "")
    saved = json.loads(log.read_text(encoding="utf-8").strip())
    assert saved["agent"] == "intake_agent"
