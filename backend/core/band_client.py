import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from core.provider_config import ProviderConfig, load_provider_config

BandEventType = Literal[
    "assignment",
    "agent_output",
    "policy_blocked",
    "adversarial_finding",
    "aiml_enrichment",
    "drift_control_finding",
    "human_approval",
    "final_export",
    "room_message",
    "collaboration_report",
    "round_start",
    "round_complete",
    "deliberation_started",
    "deliberation_finalized",
    "human_message",
]


@dataclass(frozen=True)
class BandEvent:
    event_type: BandEventType
    rfp_id: str
    question_id: str | None
    agent: str
    summary: str
    risk_level: str | None = None
    requires_human_approval: bool = False
    payload: dict[str, Any] | None = None
    timestamp: str = ""

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["timestamp"] = self.timestamp or datetime.now(UTC).isoformat()
        return record


class BandClient:
    """Band integration seam.

    In ``mock``/``lite`` mode this writes JSONL only. In ``live`` mode it
    delegates to :class:`core.band_publisher.BandPublisher`, which still
    writes JSONL first and then attempts a REST post as the right agent
    identity. JSONL is always the source of truth for the SSE stream.
    """

    def __init__(self, config: ProviderConfig | None = None, event_log: str = "output/band_events.jsonl") -> None:
        self.config = config or load_provider_config()
        self.event_log = Path(event_log)
        self._publisher = None  # lazy

    def post_event(self, event: BandEvent) -> dict[str, Any]:
        record = self._write_local_event(event)
        if self.config.band_mode == "live":
            try:
                asyncio.run(self._publish_live(event))
            except RuntimeError:
                # Already inside an event loop (e.g. orchestrator); the caller
                # should use BandPublisher directly. JSONL is already written.
                pass
        return record

    async def _publish_live(self, event: BandEvent) -> None:
        from core.band_publisher import BandPublisher

        if self._publisher is None:
            self._publisher = BandPublisher(self.config, event_log=str(self.event_log))
        await self._publisher.ensure_room(event.rfp_id)
        await self._publisher.post(
            event.agent,
            event.summary,
            rfp_id=event.rfp_id,
            question_id=event.question_id,
            event_type=event.event_type,
            mentions=(event.payload or {}).get("mentions", []),
            risk_level=event.risk_level,
            requires_human_approval=event.requires_human_approval,
            payload=event.payload,
        )

    def _write_local_event(self, event: BandEvent) -> dict[str, Any]:
        self.event_log.parent.mkdir(parents=True, exist_ok=True)
        record = event.to_record()
        record["provider_mode"] = self.config.band_mode
        self.event_log.open("a", encoding="utf-8").write(json.dumps(record) + "\n")
        return record
