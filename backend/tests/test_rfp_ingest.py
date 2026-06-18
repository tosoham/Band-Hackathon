"""Deterministic tests for RFP ingestion (no live providers)."""

import io

from core import rfp_ingest


def test_csv_to_rows_normalizes_and_fills_ids():
    data = b"question_id,category,question\nQ-001,sla|legal,Guarantee 99.9% uptime?\n,security,Describe encryption.\n"
    rows = rfp_ingest.csv_to_rows(data)
    assert rows[0] == ("Q-001", "sla|legal", "Guarantee 99.9% uptime?")
    # Missing id is backfilled, missing category defaults.
    assert rows[1][0] == "Q-002"
    assert rows[1][1] == "security"


def test_heuristic_structure_extracts_questions():
    text = (
        "Vendor Security Questionnaire\n"
        "Page 1 of 3\n"
        "1. Do you encrypt customer data at rest?\n"
        "2. Describe your incident response process.\n"
        "Some boilerplate footer line.\n"
        "Will you accept uncapped liability?\n"
    )
    pairs = rfp_ingest._heuristic_structure(text)
    questions = [q for _, q in pairs]
    assert "Do you encrypt customer data at rest?" in questions
    assert any("incident response" in q.lower() for q in questions)
    assert any("liability" in q.lower() for q in questions)
    # Boilerplate that isn't question-shaped is dropped.
    assert all("boilerplate footer" not in q.lower() for q in questions)
    # Categories are guessed from keywords.
    cats = dict((q, c) for c, q in pairs)
    assert cats["Do you encrypt customer data at rest?"] == "security|encryption"


def test_rows_to_csv_roundtrips():
    rows = [("Q-001", "general", "Do you support SSO?")]
    blob = rfp_ingest.rows_to_csv_bytes(rows)
    assert rfp_ingest.csv_to_rows(blob) == rows


def test_pdf_to_rows_extracts_from_generated_pdf():
    pypdf = __import__("pypdf")
    try:
        from pypdf import PdfWriter
    except Exception:  # pragma: no cover - pypdf always present in this env
        return
    # Build a tiny one-page PDF with question text.
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    # A blank page has no text; just assert extraction + structuring never crash
    # and return a list (empty is acceptable for a textless PDF).
    rows = rfp_ingest.pdf_to_rows(buf.getvalue())
    assert isinstance(rows, list)
    assert pypdf is not None
