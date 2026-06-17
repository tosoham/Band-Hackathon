"""In-memory mutable state store.

The boot path is intentionally light: it runs intake only (question parsing,
risk evaluation, injection scan), without the answer pipeline or the demo
orchestrator's policy/adversarial sweep. The LiveOrchestrator drives every
agent opinion lazily, per question, when ``/deliberate/{qid}`` is hit. This
keeps backend startup fast even with hundreds of live AI/ML calls in play.

Set ``BANDGATE_BOOT_MODE=demo`` to fall back to the legacy ``build_demo_state``
boot path used by the v1 dashboard.
"""

import os

from agents.intake import build_initial_state
from agents.orchestrator import build_demo_state
from core.schemas import BandGateState

_state: BandGateState | None = None


def _boot() -> BandGateState:
    if os.getenv("BANDGATE_BOOT_MODE", "lazy").lower() == "demo":
        return build_demo_state(post_band_events=False)
    return build_initial_state()


def get_state() -> BandGateState:
    global _state
    if _state is None:
        _state = _boot()
    return _state


def reset_state() -> BandGateState:
    global _state
    _state = _boot()
    return _state
