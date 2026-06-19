import os

from agents.answer_pipeline import run_answer_pipeline
from core.conflict import evaluate_question
from core.injection import scan_text
from core.model_clients import normalize_question, provider_mode
from core.paths import find_resource
from core.rfp_parser import load_questions
from core.schemas import BandGateState, RFPQuestionState

_CSV_CANDIDATES = (
    "data/uploaded_rfp.csv",
    "data/rfp_questions_v2.csv",
    "data/sample_questionnaire.csv",
)


def _resolve_questionnaire_path() -> str:
    for candidate in _CSV_CANDIDATES:
        if find_resource(candidate).is_file():
            return candidate
    return _CSV_CANDIDATES[-1]


def build_initial_state(require_upload: bool = False) -> BandGateState:
    questions: dict[str, RFPQuestionState] = {}

    # Authentic start: with require_upload (live boot), the workspace stays empty
    # until the user actually uploads a questionnaire — no preloaded sample.
    has_upload = find_resource("data/uploaded_rfp.csv").is_file()
    rows = [] if (require_upload and not has_upload) else load_questions(_resolve_questionnaire_path())

    for row in rows:
        # The RFP is untrusted input: scan raw buyer text before anything
        # downstream can treat it as an instruction.
        injection = scan_text(row.question)
        if injection.detected:
            print(
                f"[intake] prompt-injection detected in {row.question_id}: "
                f"{injection.matched_patterns}"
            )

        # Structured intake: prefer an AI/ML-normalized restatement, but only for
        # text that is not a detected injection. Falls back to a trimmed string.
        normalized = None
        if not injection.detected:
            normalized = normalize_question(row.question)

        evaluation = evaluate_question(row.question, row.category)
        questions[row.question_id] = RFPQuestionState(
            question_id=row.question_id,
            raw_question=row.question,
            normalized_question=normalized or row.question.strip(),
            category=[part.strip() for part in row.category.split("|") if part.strip()],
            risk_level=evaluation.risk_level,
            assigned_agents=evaluation.assigned_agents,
            status="open",
            conflict_detected=evaluation.conflict_detected,
            conflict_summary=evaluation.summary,
            risk_tags=evaluation.risk_tags,
        )

    # RFP identity is configurable via env (no hardcoded buyer/vendor) — defaults
    # keep the demo populated, override with BANDGATE_RFP_ID / _BUYER_NAME / _VENDOR_NAME.
    return BandGateState(
        rfp_id=os.getenv("BANDGATE_RFP_ID", "RFP-GOV-001"),
        buyer_name=os.getenv("BANDGATE_BUYER_NAME", "Public Sector Cybersecurity Review Board"),
        vendor_name=os.getenv("BANDGATE_VENDOR_NAME", "SentinelAI Security Platform"),
        policy_version="2026.06",
        provider_mode=provider_mode(),
        questions=questions,
        global_risk_score=0.0,
    )


def build_state() -> BandGateState:
    """Intake plus the answer-half pipeline: questions with agent opinions."""
    return run_answer_pipeline(build_initial_state())
