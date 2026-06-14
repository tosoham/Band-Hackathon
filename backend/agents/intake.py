from core.conflict import evaluate_question
from core.rfp_parser import load_questions
from core.schemas import BandGateState, RFPQuestionState


def build_initial_state() -> BandGateState:
    questions: dict[str, RFPQuestionState] = {}

    for row in load_questions("data/sample_questionnaire.csv"):
        evaluation = evaluate_question(row.question, row.category)
        questions[row.question_id] = RFPQuestionState(
            question_id=row.question_id,
            raw_question=row.question,
            normalized_question=row.question.strip(),
            category=[part.strip() for part in row.category.split("|") if part.strip()],
            risk_level=evaluation.risk_level,
            assigned_agents=evaluation.assigned_agents,
            status="open",
            conflict_detected=evaluation.conflict_detected,
            conflict_summary=evaluation.summary,
            risk_tags=evaluation.risk_tags,
        )

    return BandGateState(
        rfp_id="RFP-GOV-001",
        buyer_name="Public Sector Cybersecurity Review Board",
        vendor_name="SentinelAI Security Platform",
        policy_version="2026.06",
        questions=questions,
        global_risk_score=0.0,
    )
