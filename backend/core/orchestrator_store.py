"""Singleton hook for the live orchestrator so request handlers can share it."""

from __future__ import annotations

from agents.live_orchestrator import LiveOrchestrator
from core.state_store import get_state

_ORCHESTRATOR: LiveOrchestrator | None = None


def get_orchestrator() -> LiveOrchestrator:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = LiveOrchestrator(get_state())
    return _ORCHESTRATOR


def reset_orchestrator() -> None:
    global _ORCHESTRATOR
    _ORCHESTRATOR = None
