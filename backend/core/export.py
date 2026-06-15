import json
from pathlib import Path

from core.schemas import BandGateState


def write_outputs(state: BandGateState, output_dir: str = "output") -> None:
    path = Path(output_dir)
    path.mkdir(exist_ok=True)
    (path / "state.json").write_text(state.model_dump_json(indent=2), encoding="utf-8")
    (path / "audit_trail.json").write_text(
        json.dumps([event.model_dump(mode="json") for event in state.audit_trail], indent=2),
        encoding="utf-8",
    )
    (path / "promise_ledger.json").write_text(
        json.dumps([entry.model_dump(mode="json") for entry in state.promise_ledger], indent=2),
        encoding="utf-8",
    )
    (path / "final_response.md").write_text(_final_response_markdown(state), encoding="utf-8")


def _final_response_markdown(state: BandGateState) -> str:
    lines = [
        "# BandGate Final RFP Response",
        "",
        f"Buyer: {state.buyer_name}",
        f"Vendor: {state.vendor_name}",
        f"Policy version: {state.policy_version}",
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
                f"**Final answer:** {question.final_answer}",
                "",
            ]
        )
    return "\n".join(lines)
