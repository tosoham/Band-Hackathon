"""Band publisher: one Band room, six agent identities, JSONL-first writes.

The live Band integration in v1 was a one-shot fire-and-forget call from
``run_band_collaboration.py``. v2 needs the same six agents posting into the
same Band room across many rounds while the LiveOrchestrator coordinates,
and it needs every event mirrored to ``output/band_events.jsonl`` so the
SSE stream the frontend subscribes to keeps flowing even when REST is slow
or the room is unavailable.

Design rules:
- JSONL first, REST second. The orchestrator's loop never blocks on Band.
- If ``BAND_MODE`` is not ``live`` or ``agent_config.yaml`` is missing, all
  posts degrade silently to JSONL-only — the UI still sees a "simulated"
  room with full chat flow.
- Per-agent ``AsyncRestClient`` instances mirror the pattern proven in
  ``run_band_collaboration.try_live_band_room``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.band_sdk_runtime import EXPECTED_BAND_AGENTS, load_agent_config_shape
from core.provider_config import ProviderConfig, load_provider_config

DEFAULT_EVENT_LOG = "output/band_events.jsonl"


@dataclass
class PublishResult:
    posted_to_jsonl: bool
    posted_to_band: bool
    band_room_id: str | None
    error: str | None = None


class BandPublisher:
    """Multi-identity Band publisher with offline mirror.

    Use :meth:`ensure_room` once per RFP, then call :meth:`post` for every
    deliberation turn. The publisher caches REST clients and the room id.
    """

    def __init__(
        self,
        config: ProviderConfig | None = None,
        event_log: str = DEFAULT_EVENT_LOG,
    ) -> None:
        self.config = config or load_provider_config()
        self.event_log = Path(event_log)
        self.event_log.parent.mkdir(parents=True, exist_ok=True)
        self._room_id: str | None = self.config.band_default_room_id
        self._lead_tools = None  # AgentTools | None
        self._rest_by_agent: dict[str, Any] = {}
        self._tools_by_agent: dict[str, Any] = {}
        self._credentials: dict[str, dict[str, str]] | None = None
        self._sdk_failure: str | None = None

    @property
    def live_target(self) -> bool:
        """Whether the publisher will try a live REST post."""
        return self.config.band_mode == "live"

    @property
    def room_id(self) -> str | None:
        return self._room_id

    # ----- offline mirror -----

    def write_event(
        self,
        event_type: str,
        rfp_id: str,
        question_id: str | None,
        agent: str,
        summary: str,
        *,
        risk_level: str | None = None,
        requires_human_approval: bool = False,
        payload: dict[str, Any] | None = None,
        timestamp: str | None = None,
        provider_mode: str | None = None,
    ) -> dict[str, Any]:
        record = {
            "event_type": event_type,
            "rfp_id": rfp_id,
            "question_id": question_id,
            "agent": agent,
            "summary": summary,
            "risk_level": risk_level,
            "requires_human_approval": requires_human_approval,
            "payload": payload or {},
            "timestamp": timestamp or datetime.now(UTC).isoformat(),
            "provider_mode": provider_mode or self.config.band_mode,
        }
        with self.event_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        return record

    # ----- live Band path -----

    async def ensure_room(self, rfp_id: str) -> str | None:
        if not self.live_target:
            return self._room_id
        if self._lead_tools is not None:
            return self._room_id
        try:
            self._credentials = load_agent_config_shape()
        except FileNotFoundError as exc:
            self._sdk_failure = f"agent_config_missing: {exc}"
            return None
        except Exception as exc:  # noqa: BLE001 - defensive
            self._sdk_failure = f"agent_config_error: {exc}"
            return None

        try:
            from band.client.rest import AsyncRestClient  # type: ignore
            from band.runtime.tools import AgentTools  # type: ignore
        except ImportError as exc:
            self._sdk_failure = f"sdk_unavailable: {exc}"
            return None

        lead_name = "intake_agent"
        self._rest_by_agent = {
            name: AsyncRestClient(base_url=self.config.band_rest_url, api_key=creds["api_key"])
            for name, creds in self._credentials.items()
            if name in EXPECTED_BAND_AGENTS
        }

        try:
            lead_tools = AgentTools(room_id=self._room_id or "new-room", rest=self._rest_by_agent[lead_name])
            if not self._room_id:
                self._room_id = await lead_tools.create_chatroom()
                lead_tools = AgentTools(room_id=self._room_id, rest=self._rest_by_agent[lead_name])
            self._lead_tools = lead_tools
            for name in EXPECTED_BAND_AGENTS:
                if name == lead_name or name not in self._credentials:
                    continue
                try:
                    await lead_tools.add_participant(self._credentials[name]["agent_id"])
                except Exception as exc:  # noqa: BLE001 - non-fatal
                    self._sdk_failure = f"add_participant_warning[{name}]: {exc}"
            for name, rest in self._rest_by_agent.items():
                self._tools_by_agent[name] = AgentTools(room_id=self._room_id, rest=rest)
        except Exception as exc:  # noqa: BLE001 - defensive
            self._sdk_failure = f"room_init_failed: {exc}"
            return None
        return self._room_id

    async def post(
        self,
        agent_name: str,
        content: str,
        *,
        rfp_id: str,
        question_id: str | None,
        event_type: str = "room_message",
        mentions: list[str] | None = None,
        risk_level: str | None = None,
        requires_human_approval: bool = False,
        payload: dict[str, Any] | None = None,
    ) -> PublishResult:
        """Post a turn into the room. Always mirrors to JSONL first."""
        merged_payload = {"mentions": mentions or [], **(payload or {})}
        self.write_event(
            event_type=event_type,
            rfp_id=rfp_id,
            question_id=question_id,
            agent=agent_name,
            summary=content[:600],
            risk_level=risk_level,
            requires_human_approval=requires_human_approval,
            payload=merged_payload,
        )

        if not self.live_target:
            return PublishResult(posted_to_jsonl=True, posted_to_band=False, band_room_id=self._room_id)

        room_id = await self.ensure_room(rfp_id)
        if not room_id or not self._tools_by_agent or self._sdk_failure:
            return PublishResult(
                posted_to_jsonl=True,
                posted_to_band=False,
                band_room_id=room_id,
                error=self._sdk_failure,
            )

        # human_gate is not a Band Remote Agent; route it through the lead's events.
        if agent_name == "human_gate" and self._lead_tools is not None:
            try:
                await self._lead_tools.send_event(content, "task", {"agent": "human_gate"})
                return PublishResult(posted_to_jsonl=True, posted_to_band=True, band_room_id=room_id)
            except Exception as exc:  # noqa: BLE001
                return PublishResult(posted_to_jsonl=True, posted_to_band=False, band_room_id=room_id, error=str(exc))

        tools = self._tools_by_agent.get(agent_name)
        if tools is None:
            return PublishResult(
                posted_to_jsonl=True,
                posted_to_band=False,
                band_room_id=room_id,
                error=f"unknown_agent: {agent_name}",
            )
        try:
            band_mentions = [f"@{name}" for name in (mentions or [])]
            try:
                await tools.send_message(content, band_mentions)
            except Exception:
                await tools.send_event(content, "task", {"mentions": band_mentions})
            return PublishResult(posted_to_jsonl=True, posted_to_band=True, band_room_id=room_id)
        except Exception as exc:  # noqa: BLE001
            return PublishResult(
                posted_to_jsonl=True,
                posted_to_band=False,
                band_room_id=room_id,
                error=str(exc),
            )

    async def close(self) -> None:
        """Close cached REST clients if any."""
        for rest in self._rest_by_agent.values():
            close = getattr(rest, "aclose", None) or getattr(rest, "close", None)
            if callable(close):
                try:
                    maybe_coro = close()
                    if hasattr(maybe_coro, "__await__"):
                        await maybe_coro
                except Exception:
                    pass
        self._rest_by_agent.clear()
        self._tools_by_agent.clear()
        self._lead_tools = None
