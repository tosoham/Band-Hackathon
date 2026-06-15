import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from core.schemas import AuditEvent


def make_audit_event(actor: str, action: str, question_id: str | None, summary: str, payload: dict[str, Any]) -> AuditEvent:
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return AuditEvent(
        event_id=hashlib.sha256(f"{actor}:{action}:{question_id}:{serialized}".encode()).hexdigest()[:16],
        timestamp=datetime.now(UTC).isoformat(),
        actor=actor,
        action=action,
        question_id=question_id,
        summary=summary,
        payload_hash=hashlib.sha256(serialized.encode()).hexdigest(),
    )
