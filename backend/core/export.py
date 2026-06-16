import json
from pathlib import Path

from core.schemas import BandGateState


def write_outputs(state: BandGateState, output_dir: str = "output") -> None:
    path = Path(output_dir)
    path.mkdir(exist_ok=True)
    (path / "state.json").write_text(state.model_dump_json(indent=2), encoding="utf-8")
    (path / "audit_trail.json").write_text(json.dumps(audit_trail_records(state), indent=2), encoding="utf-8")
    (path / "promise_ledger.json").write_text(json.dumps(promise_ledger_records(state), indent=2), encoding="utf-8")
    (path / "final_response.md").write_text(final_response_markdown(state), encoding="utf-8")


def audit_trail_records(state: BandGateState) -> list[dict]:
    return [event.model_dump(mode="json") for event in state.audit_trail]


def promise_ledger_records(state: BandGateState) -> list[dict]:
    return [entry.model_dump(mode="json") for entry in state.promise_ledger]


def final_response_markdown(state: BandGateState) -> str:
    lines = [
        "# BandGate Final RFP Response",
        "",
        f"Buyer: {state.buyer_name}",
        f"Vendor: {state.vendor_name}",
        f"Policy version: {state.policy_version}",
        f"Global risk score: {state.global_risk_score}",
        "",
    ]
    for question in state.questions.values():
        if question.status != "finalized":
            continue
        lines.extend(
            [
                f"## {question.question_id}",
                "",
                f"**Question:** {question.raw_question}",
                "",
                f"**Risk:** {question.risk_level}",
                "",
                f"**Decision:** {question.conflict_summary or 'No conflict detected.'}",
                "",
                f"**Final answer:** {question.final_answer}",
                "",
            ]
        )
        evidence = [item for opinion in question.opinions for item in opinion.evidence]
        if evidence:
            lines.append("**Evidence:**")
            lines.extend(f"- {item.document_name}: {item.quote}" for item in evidence)
            lines.append("")
        approvals = question.approvals
        if approvals:
            lines.append("**Approval trail:**")
            lines.extend(
                f"- {approval.decision} by {approval.approver_name or approval.approver_role}: {approval.comment or 'No comment'}"
                for approval in approvals
            )
            lines.append("")
    return "\n".join(lines)
