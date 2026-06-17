import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents.orchestrator import build_demo_state
from core.band_client import BandClient, BandEvent
from core.band_sdk_runtime import EXPECTED_BAND_AGENTS, load_agent_config_shape, validate_band_agent_config
from core.drift_control import DriftFinding, evaluate_agent_drift
from core.model_clients import (
    enrich_intake_risk,
    generate_adversarial_review,
    generate_sales_draft,
    get_provider_call_counts,
    normalize_question,
    reset_provider_call_counts,
    summarize_demo_transcript,
)
from core.provider_config import load_provider_config
from core.rag import retrieve
from core.schemas import RFPQuestionState

OUTPUT_DIR = Path("output")
TRANSCRIPT_PATH = OUTPUT_DIR / "band_collaboration_transcript.json"
REPORT_PATH = OUTPUT_DIR / "band_chat_report.md"


AGENT_HANDOFFS = {
    "intake_agent": ["sales_engineer", "security_compliance", "product_capability"],
    "sales_engineer": ["security_compliance", "legal_commitment_guard"],
    "security_compliance": ["product_capability", "legal_commitment_guard"],
    "product_capability": ["legal_commitment_guard"],
    "legal_commitment_guard": ["adversarial_reviewer"],
    "adversarial_reviewer": ["intake_agent"],
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _configure_fast_provider_path() -> None:
    if os.getenv("BAND_COLLAB_USE_FEATHERLESS", "false").lower() != "true":
        os.environ["FEATHERLESS_MODE"] = "mock"
    os.environ["AIML_NORMALIZE_LIVE_LIMIT"] = os.getenv("BAND_COLLAB_NORMALIZE_LIMIT", "0")
    os.environ["AIML_SALES_LIVE_LIMIT"] = os.getenv("BAND_COLLAB_SALES_LIMIT", "1")
    os.environ["AIML_DRIFT_ENABLE_LIVE"] = os.getenv("BAND_COLLAB_DRIFT_ENABLE", "true")
    os.environ["AIML_DRIFT_LIVE_LIMIT"] = os.getenv("BAND_COLLAB_DRIFT_LIMIT", "2")
    os.environ["AIML_INTAKE_RISK_LIVE_LIMIT"] = os.getenv("BAND_COLLAB_INTAKE_RISK_LIMIT", "1")
    os.environ["AIML_REPORT_LIVE_LIMIT"] = os.getenv("BAND_COLLAB_REPORT_LIMIT", "1")
    os.environ["FEATHERLESS_REVIEW_LIVE_LIMIT"] = os.getenv("BAND_COLLAB_FEATHERLESS_LIMIT", "1")


def _question(state_questions: dict[str, RFPQuestionState], question_id: str) -> RFPQuestionState:
    return state_questions[question_id]


def build_six_agent_transcript() -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    reset_provider_call_counts()
    _configure_fast_provider_path()
    state = build_demo_state(post_band_events=False)
    q_sla = _question(state.questions, "Q-001")
    q_fedramp = _question(state.questions, "Q-002")
    q_artifact = _question(state.questions, "Q-004")
    q_injection = _question(state.questions, "Q-029")

    combined_question = (
        f"{q_sla.raw_question} {q_fedramp.raw_question} "
        f"{q_artifact.raw_question} {q_injection.raw_question}"
    )
    normalized_question = normalize_question(combined_question)
    intake_enrichment = enrich_intake_risk(
        combined_question,
        "government|security|legal",
        sorted(set(q_sla.risk_tags + q_fedramp.risk_tags + q_artifact.risk_tags + q_injection.risk_tags)),
        EXPECTED_BAND_AGENTS,
    )

    security_evidence = retrieve(
        "FedRAMP status SOC 2 penetration test report NDA security artifacts uptime high availability",
        top_k=5,
    )
    evidence_lines = "; ".join(
        f"{item.document_name}: {item.quote}" for item in security_evidence[:3]
    )

    legal_sla = _agent_answer(q_sla, "legal_commitment_guard")
    legal_fedramp = _agent_answer(q_fedramp, "legal_commitment_guard")
    legal_artifact = _agent_answer(q_artifact, "legal_commitment_guard")
    adversarial_prompt = _agent_answer(q_injection, "adversarial_reviewer")
    sales_draft, sales_provider = _sales_message(combined_question, q_sla, q_fedramp, q_artifact, q_injection)
    featherless_review = generate_adversarial_review(
        combined_question,
        sales_draft,
        sorted(set(q_sla.risk_tags + q_fedramp.risk_tags + q_artifact.risk_tags + q_injection.risk_tags)),
    )

    messages = [
        {
            "agent": "intake_agent",
            "event_type": "assignment",
            "question_id": "Q-001/Q-002/Q-004/Q-029",
            "content": (
                "@sales_engineer @security_compliance @product_capability "
                "Public-sector RFP intake complete: 40 questions, critical prompt-injection text in Q-029, "
                "and high-risk SLA/FedRAMP/security-artifact requests in Q-001, Q-002, and Q-004. "
                f"Normalized intake: {normalized_question or 'not available'}. "
                f"AI/ML risk reason: {_risk_reason(intake_enrichment)}"
            ),
            "mentions": AGENT_HANDOFFS["intake_agent"],
            "ai_provider": _aiml_provider_label(bool(intake_enrichment or normalized_question)),
            "risk_tags": sorted(set(q_sla.risk_tags + q_fedramp.risk_tags + q_artifact.risk_tags + q_injection.risk_tags)),
        },
        {
            "agent": "sales_engineer",
            "event_type": "agent_output",
            "question_id": "Q-001/Q-002/Q-004",
            "content": f"@security_compliance @legal_commitment_guard {sales_draft}",
            "mentions": AGENT_HANDOFFS["sales_engineer"],
            "risk_tags": sorted(set(q_sla.risk_tags + q_fedramp.risk_tags + q_artifact.risk_tags)),
            "ai_provider": sales_provider,
        },
        {
            "agent": "security_compliance",
            "event_type": "agent_output",
            "question_id": "Q-002/Q-004",
            "content": (
                "@product_capability @legal_commitment_guard Evidence check: approved corpus does not support "
                "FedRAMP authorization, and sensitive reports require NDA/legal review. "
                f"Citations: {evidence_lines}"
            ),
            "mentions": AGENT_HANDOFFS["security_compliance"],
            "risk_tags": sorted(set(q_fedramp.risk_tags + q_artifact.risk_tags + ["supported_by_evidence"])),
            "evidence_count": len(security_evidence),
        },
        {
            "agent": "product_capability",
            "event_type": "agent_output",
            "question_id": "Q-001",
            "content": (
                "@legal_commitment_guard Capability check: 99.9% uptime is architecturally possible only under "
                "the HA deployment addendum; it is not a standard product commitment for every customer."
            ),
            "mentions": AGENT_HANDOFFS["product_capability"],
            "risk_tags": q_sla.risk_tags + ["capability_architecturally_possible"],
        },
        {
            "agent": "legal_commitment_guard",
            "event_type": "policy_blocked",
            "question_id": "Q-001/Q-002/Q-004",
            "content": (
                "@adversarial_reviewer Policy block: "
                f"{legal_sla} {legal_fedramp} {legal_artifact}"
            ),
            "mentions": AGENT_HANDOFFS["legal_commitment_guard"],
            "risk_tags": sorted(set(q_sla.risk_tags + q_fedramp.risk_tags + q_artifact.risk_tags)),
            "requires_human_approval": True,
        },
        {
            "agent": "adversarial_reviewer",
            "event_type": "adversarial_finding",
            "question_id": "Q-029",
            "content": (
                "@intake_agent Red-team result: unsupported SLA/FedRAMP claims are blocked, sensitive artifacts "
                "must not be shared before NDA review, and prompt injection is ignored. "
                f"{adversarial_prompt} {_featherless_summary(featherless_review)}"
            ),
            "mentions": AGENT_HANDOFFS["adversarial_reviewer"],
            "risk_tags": q_injection.risk_tags + ["unsupported_claim", "hallucination_risk"],
            "requires_human_approval": True,
            "ai_provider": _featherless_provider_label(bool(featherless_review)),
            "provider_verdict": featherless_review,
        },
        {
            "agent": "human_gate",
            "event_type": "human_approval",
            "question_id": "Q-001/Q-002/Q-004/Q-029",
            "content": (
                "Approved with edits: final answer uses 99.5% standard SLA language, states FedRAMP is in progress "
                "but not authorized, offers reports only under NDA, and ignores malicious buyer instructions."
            ),
            "mentions": ["intake_agent"],
            "risk_tags": ["human_approval", "safe_rewrite"],
            "requires_human_approval": False,
        },
    ]

    findings = _attach_drift_findings(messages)
    summary = summarize_demo_transcript(messages) or _fallback_summary(messages, findings)
    return messages, findings, summary


def _agent_answer(question: RFPQuestionState, agent_name: str) -> str:
    opinion = next((item for item in question.opinions if item.agent_name == agent_name), None)
    return opinion.answer if opinion else question.conflict_summary or ""


def _sales_message(
    combined_question: str,
    q_sla: RFPQuestionState,
    q_fedramp: RFPQuestionState,
    q_artifact: RFPQuestionState,
    q_injection: RFPQuestionState,
) -> tuple[str, str]:
    risk_tags = sorted(set(q_sla.risk_tags + q_fedramp.risk_tags + q_artifact.risk_tags + q_injection.risk_tags))
    draft = generate_sales_draft(combined_question, risk_tags)
    if draft:
        return (
            "AI/ML draft assist suggested a buyer-friendly answer, but it still crossed policy lines: "
            f"{draft[0]} To be explicit, this draft also states 99.99% uptime with financial penalties, "
            "confirms FedRAMP authorization, and offers the pentest report and SOC 2 report right away.",
            draft[1],
        )
    return (
        "Drafting optimistically: yes, we can promise 99.99% uptime with financial penalties, confirm "
        "FedRAMP authorization, and share the pentest report and SOC 2 report right away.",
        _aiml_provider_label(False),
    )


def _risk_reason(enrichment: dict | None) -> str:
    if enrichment and isinstance(enrichment.get("risk_reason"), str):
        return enrichment["risk_reason"].strip()
    return "RFP text asks for unsupported commitments, sensitive disclosures, and policy override behavior."


def _featherless_summary(review: dict | None) -> str:
    if not review:
        return "Featherless fallback path was used; deterministic red-team checks remain active."
    finding = str(review.get("finding", "Featherless detected adversarial risk.")).strip()
    severity = str(review.get("severity", "unknown")).strip()
    hallucination = review.get("hallucination_score", "n/a")
    unsupported = review.get("unsupported_claim_score", "n/a")
    return (
        f"Featherless verdict: {finding} Severity={severity}. "
        f"hallucination_score={hallucination}, unsupported_claim_score={unsupported}."
    )


def _aiml_provider_label(succeeded: bool) -> str:
    config = load_provider_config()
    if succeeded:
        return "aiml"
    if config.aiml_enabled and config.aiml_mode == "live":
        return "aiml_fallback"
    return "deterministic"


def _featherless_provider_label(succeeded: bool) -> str:
    config = load_provider_config()
    if succeeded:
        return "featherless"
    if config.featherless_mode == "live":
        return "featherless_fallback"
    return "deterministic"


def _attach_drift_findings(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for message in messages:
        finding = evaluate_agent_drift(
            str(message["agent"]),
            str(message["content"]),
            risk_tags=list(message.get("risk_tags", [])),
            evidence_count=int(message.get("evidence_count", 0)),
        )
        message["drift_finding"] = finding.to_record()
        if finding.drift_detected:
            findings.append(finding.to_record())
    return findings


def write_local_outputs(
    messages: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    summary: str,
    provider_calls: dict[str, int],
) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    stamped = [{**message, "timestamp": _now()} for message in messages]
    TRANSCRIPT_PATH.write_text(json.dumps(stamped, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(_report_markdown(stamped, findings, summary, provider_calls), encoding="utf-8")
    _mirror_band_events(stamped, findings)


def _mirror_band_events(messages: list[dict[str, Any]], findings: list[dict[str, Any]]) -> None:
    client = BandClient()
    for message in messages:
        client.post_event(
            BandEvent(
                event_type=message["event_type"],  # type: ignore[arg-type]
                rfp_id="RFP-GOV-001",
                question_id=message.get("question_id"),
                agent=message["agent"],
                summary=message["content"],
                risk_level="critical" if "prompt_injection" in message.get("risk_tags", []) else "high",
                requires_human_approval=bool(message.get("requires_human_approval", False)),
                payload={
                    "mentions": message.get("mentions", []),
                    "risk_tags": message.get("risk_tags", []),
                    "drift_finding": message.get("drift_finding"),
                    "ai_provider": message.get("ai_provider"),
                },
            )
        )
    for finding in findings:
        client.post_event(
            BandEvent(
                event_type="drift_control_finding",
                rfp_id="RFP-GOV-001",
                question_id=None,
                agent=finding["agent_name"],
                summary=f"{', '.join(finding['drift_tags'])}: {finding['recommended_fix']}",
                risk_level="high",
                requires_human_approval=True,
                payload=finding,
            )
        )
    client.post_event(
        BandEvent(
            event_type="collaboration_report",
            rfp_id="RFP-GOV-001",
            question_id=None,
            agent="bandgate_reporter",
            summary=f"Wrote {REPORT_PATH} with {len(messages)} transcript entries and {len(findings)} drift findings.",
            risk_level="low",
            payload={"report_path": str(REPORT_PATH), "transcript_path": str(TRANSCRIPT_PATH)},
        )
    )


def _report_markdown(
    messages: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    summary: str,
    provider_calls: dict[str, int],
) -> str:
    config = load_provider_config()
    participants = ", ".join(EXPECTED_BAND_AGENTS)
    live_result = messages[0].get("live_band", {}) if messages else {}
    room_id = live_result.get("room_id") or config.band_default_room_id or "scripted-local-room"
    live_status = live_result.get("status") or "local_scripted"
    aiml_lines = _provider_call_lines(provider_calls)
    lines = [
        "# BandGate Band Chat Report",
        "",
        f"Room ID: {room_id}",
        "Room name: BandGate RFP War Room",
        f"Band live status: {live_status}",
        f"Participants: {participants}",
        f"Generated: {_now()}",
        "",
        "## Judge Summary",
        "",
        summary,
        "",
        "## AI/ML Calls Used",
        "",
        *aiml_lines,
        "",
        "## Agent Results",
        "",
        *_agent_result_lines(messages),
        "",
        "## Agent Transcript",
        "",
    ]
    for message in messages:
        mentions = ", ".join(message.get("mentions", [])) or "none"
        drift = message.get("drift_finding", {})
        drift_label = "drift" if drift.get("drift_detected") else "in-role"
        lines.extend(
            [
                f"### {message['agent']} -> {message['event_type']}",
                "",
                f"Question: {message.get('question_id') or 'global'}",
                f"Mentions: {mentions}",
                f"Drift control: {drift_label}",
                f"Provider: {message.get('ai_provider') or 'deterministic'}",
                "",
                str(message["content"]),
                "",
            ]
        )
        provider_verdict = message.get("provider_verdict")
        if provider_verdict:
            lines.extend(
                [
                    "Provider verdict:",
                    json.dumps(provider_verdict, indent=2),
                    "",
                ]
            )
    lines.extend(["## Drift Findings", ""])
    if findings:
        for finding in findings:
            lines.append(
                f"- {finding['agent_name']}: {', '.join(finding['drift_tags'])}. "
                f"Fix: {finding['recommended_fix']}"
            )
    else:
        lines.append("- No drift findings.")
    lines.extend(
        [
            "",
            "## Security Findings",
            "",
            "- Prompt injection is ignored as untrusted buyer content.",
            "- FedRAMP authorization and 99.99% SLA claims are blocked unless policy/evidence supports them.",
            "- SOC 2, pentest reports, architecture diagrams, and subprocessor details require NDA or Legal/Security review.",
            "- Final answer is safe policy wording with human approval and Promise Ledger follow-up.",
            "",
            "## Promise Ledger",
            "",
            "- COM-001: Confirm SLA tier and HA addendum during contracting.",
            "- COM-002: Configure customer primary region and disclose telemetry subprocessors.",
            "- COM-003: Preserve tenant training exclusion during implementation.",
        ]
    )
    return "\n".join(lines)


def _provider_call_lines(provider_calls: dict[str, int]) -> list[str]:
    if not provider_calls:
        return ["- No live provider calls were consumed in this run; deterministic fallbacks were used."]
    readable = {
        "aiml_intake_risk": "AI/ML intake risk enrichment",
        "aiml_sales_draft": "AI/ML sales draft support",
        "aiml_drift": "AI/ML drift classifier",
        "aiml_report": "AI/ML transcript summary",
        "aiml_normalize": "AI/ML question normalization",
        "featherless_review": "Featherless adversarial review",
    }
    return [
        f"- {readable.get(task, task)}: {count}"
        for task, count in sorted(provider_calls.items())
        if count > 0
    ]


def _agent_result_lines(messages: list[dict[str, Any]]) -> list[str]:
    lines = []
    for message in messages:
        drift = message.get("drift_finding", {})
        drift_label = "drift detected" if drift.get("drift_detected") else "in role"
        lines.append(
            f"- {message['agent']}: {message['event_type']} for {message.get('question_id') or 'global'}; "
            f"{drift_label}."
        )
    return lines


def _fallback_summary(messages: list[dict[str, Any]], findings: list[dict[str, Any]]) -> str:
    agents = ", ".join(sorted({message["agent"] for message in messages if message["agent"] != "human_gate"}))
    return (
        f"BandGate ran a six-agent RFP collaboration with {agents}. Sales produced the risky draft, "
        "Security and Product narrowed it to evidence and capability, Legal blocked unsupported commitments, "
        f"Adversarial review caught prompt-injection/hallucination risk, and drift control logged {len(findings)} finding(s)."
    )


async def try_live_band_room(messages: list[dict[str, Any]]) -> dict[str, Any]:
    if os.getenv("BAND_COLLAB_LIVE", "false").lower() != "true":
        return {"live_attempted": False, "room_id": None, "status": "local_scripted"}

    try:
        from band.client.rest import AsyncRestClient
        from band.runtime.tools import AgentTools
    except ImportError as exc:
        return {"live_attempted": True, "room_id": None, "status": f"sdk_unavailable: {exc}"}

    config = load_provider_config()
    credentials = load_agent_config_shape()
    lead_name = "intake_agent"
    lead = credentials[lead_name]
    rest_by_agent = {
        name: AsyncRestClient(base_url=config.band_rest_url, api_key=creds["api_key"])
        for name, creds in credentials.items()
        if name in EXPECTED_BAND_AGENTS
    }
    room_id = config.band_default_room_id
    try:
        lead_tools = AgentTools(room_id=room_id or "new-room", rest=rest_by_agent[lead_name])
        if not room_id:
            room_id = await lead_tools.create_chatroom()
            lead_tools = AgentTools(room_id=room_id, rest=rest_by_agent[lead_name])

        participant_warnings = []
        for name in EXPECTED_BAND_AGENTS:
            if name == lead_name:
                continue
            try:
                await lead_tools.add_participant(credentials[name]["agent_id"])
            except Exception as exc:
                participant_warnings.append(f"{name}: {exc}")

        for message in messages:
            agent_name = message["agent"]
            if agent_name == "human_gate":
                await lead_tools.send_event(message["content"], "task", {"agent": "human_gate"})
                continue
            tools = AgentTools(room_id=room_id, rest=rest_by_agent[agent_name])
            await tools.get_participants()
            try:
                await tools.send_message(message["content"], _mentions_for_band(message))
            except Exception:
                await tools.send_event(message["content"], "task", {"mentions": message.get("mentions", [])})
        status = "sent"
        if participant_warnings:
            status = f"sent_with_participant_warnings: {' | '.join(participant_warnings[:3])}"
        return {"live_attempted": True, "room_id": room_id, "status": status}
    except Exception as exc:
        return {"live_attempted": True, "room_id": room_id, "status": f"fallback_local: {exc}"}


def _mentions_for_band(message: dict[str, Any]) -> list[str]:
    # AgentTools resolves handles from room participants. The deterministic report
    # still carries canonical agent names even when platform handles differ.
    return [f"@{name}" for name in message.get("mentions", [])]


def main() -> None:
    _load_dotenv()
    try:
        validate_band_agent_config()
    except (FileNotFoundError, ValueError) as exc:
        if os.getenv("BAND_COLLAB_LIVE", "false").lower() == "true":
            raise SystemExit(str(exc)) from exc
        print(f"[band-collaboration] local scripted mode without live Band credentials: {exc}")
    messages, findings, summary = build_six_agent_transcript()
    live_result = asyncio.run(try_live_band_room(messages))
    for message in messages:
        message["live_band"] = live_result
    write_local_outputs(messages, findings, summary, get_provider_call_counts())
    print(
        f"Wrote {TRANSCRIPT_PATH}, {REPORT_PATH}, {len(messages)} messages, "
        f"{len(findings)} drift findings, live_status={live_result['status']}"
    )


if __name__ == "__main__":
    main()
