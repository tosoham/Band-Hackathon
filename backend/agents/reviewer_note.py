"""Shared handling for human-gate reviewer notes (@mention instructions).

When a human reviewer tags an agent at the gate, their message is forwarded to
that agent as a trusted steering instruction. The live model applies it
directly. The deterministic fallback cannot rewrite its templated answer, so it
records the note as a *pending* steer rather than claiming a completed revision.
"""

from __future__ import annotations

# Marker phrase prefixing the deterministic annotation. Kept as a constant so
# the wording stays consistent across agents and is easy to assert in tests.
_NOTE_MARKER = "Reviewer note — applied in live mode"


def normalize_reviewer_note(human_note: str | None) -> str | None:
    """Trim a reviewer note to a non-empty string, or ``None`` when blank."""
    return (human_note or "").strip() or None


def append_reviewer_note(answer: str, note: str | None) -> str:
    """Annotate a deterministic answer with a pending reviewer note.

    Returns ``answer`` unchanged when there is no note. The annotation is framed
    as a pending steer (not a completed revision) because the deterministic path
    cannot actually rewrite the templated text — only the live model can.
    """
    if not note:
        return answer
    return f"{answer}\n\n({_NOTE_MARKER}: {note})"
