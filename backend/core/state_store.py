"""In-memory mutable state store.

The answer pipeline builds state deterministically; once built we keep a single
mutable copy in memory so write actions (human approvals) persist across
requests within a run. ``reset`` rebuilds it for a clean demo.
"""

from agents.orchestrator import build_demo_state
from core.schemas import BandGateState

_state: BandGateState | None = None


def get_state() -> BandGateState:
    global _state
    if _state is None:
        _state = build_demo_state()
    return _state


def reset_state() -> BandGateState:
    global _state
    _state = build_demo_state()
    return _state
