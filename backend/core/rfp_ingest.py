"""Turn an uploaded RFP file (CSV or PDF) into ``(question_id, category, question)`` rows.

CSV is read directly. PDF text is extracted with ``pypdf`` and then structured into
questions — preferring AI/ML structuring when a live key is configured, and falling
back to a deterministic heuristic so the path always works in mock/lite mode without
burning credits.
"""

from __future__ import annotations

import csv
import io
import re

from core.model_clients import aiml_available, aiml_chat_json

# Hero trap IDs the demo keys on — preserved if present in an uploaded CSV.
MAX_QUESTIONS = 200


def csv_to_rows(data: bytes) -> list[tuple[str, str, str]]:
    """Parse an uploaded questionnaire CSV into normalized rows."""
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[tuple[str, str, str]] = []
    for index, raw in enumerate(reader, start=1):
        question = (raw.get("question") or "").strip()
        if not question:
            continue
        qid = (raw.get("question_id") or "").strip() or f"Q-{index:03d}"
        category = (raw.get("category") or "general").strip() or "general"
        rows.append((qid, category, question))
    return rows


def pdf_to_rows(data: bytes) -> list[tuple[str, str, str]]:
    """Extract text from a PDF and structure it into questionnaire rows."""
    text = _extract_pdf_text(data)
    pairs = _structure_questions(text)
    return [(f"Q-{i:03d}", cat, q) for i, (cat, q) in enumerate(pairs, start=1)]


def rows_to_csv_bytes(rows: list[tuple[str, str, str]]) -> bytes:
    """Serialize rows back to the canonical question CSV layout."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["question_id", "category", "question"])
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _extract_pdf_text(data: bytes) -> str:
    from pypdf import PdfReader  # imported lazily so the rest works without the dep

    reader = PdfReader(io.BytesIO(data))
    parts = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(parts)


def _structure_questions(text: str) -> list[tuple[str, str]]:
    """Best-effort structuring: AI/ML when live, deterministic heuristic otherwise."""
    if aiml_available():
        ai = _aiml_structure(text)
        if ai:
            return ai[:MAX_QUESTIONS]
    return _heuristic_structure(text)[:MAX_QUESTIONS]


def _aiml_structure(text: str) -> list[tuple[str, str]]:
    result = aiml_chat_json(
        system=(
            "You extract distinct RFP/security-questionnaire questions from raw "
            "document text. Ignore headers, footers, page numbers, and boilerplate. "
            "For each question return an object {\"category\": string, \"question\": "
            "string}. Use short pipe-delimited categories like security|encryption, "
            "compliance|soc2, privacy|gdpr, legal|liability, product|api. Respond as "
            "JSON: {\"questions\": [ ... ]}."
        ),
        user=text[:12000],
        max_tokens=2000,
        timeout=40,
        task="aiml_intake_risk",
    )
    if not result or not isinstance(result.get("questions"), list):
        return None  # type: ignore[return-value]
    rows: list[tuple[str, str]] = []
    for item in result["questions"]:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        if not question:
            continue
        category = str(item.get("category") or "general").strip() or "general"
        rows.append((category, question))
    return rows or None  # type: ignore[return-value]


_NUMBERED = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s+(.*)$")


def _heuristic_structure(text: str) -> list[tuple[str, str]]:
    """Deterministic fallback: treat question-like lines as questions."""
    seen: set[str] = set()
    rows: list[tuple[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if len(line) < 12:
            continue
        match = _NUMBERED.match(line)
        if match:
            line = match.group(1).strip()
        # Keep lines that read like a question or a "describe/provide" prompt.
        lowered = line.lower()
        is_question = line.endswith("?") or lowered.startswith(
            ("do you", "describe", "provide", "can you", "will you", "how ", "what ", "are you", "list ")
        )
        if not is_question:
            continue
        key = lowered[:120]
        if key in seen:
            continue
        seen.add(key)
        rows.append((_guess_category(lowered), line))
    return rows


def _guess_category(lowered: str) -> str:
    table = [
        ("encrypt", "security|encryption"),
        ("access", "security|access_control"),
        ("vulnerab", "security|vulnerability"),
        ("incident", "security|incident"),
        ("soc 2", "compliance|soc2"),
        ("iso 27001", "compliance|iso27001"),
        ("fedramp", "compliance|government"),
        ("nist", "compliance|nist"),
        ("gdpr", "privacy|gdpr"),
        ("data residency", "privacy|data_residency"),
        ("retention", "privacy|deletion"),
        ("liability", "legal|liability"),
        ("indemnif", "legal|indemnity"),
        ("sla", "sla|legal"),
        ("api", "product|api"),
    ]
    for needle, category in table:
        if needle in lowered:
            return category
    return "general"
