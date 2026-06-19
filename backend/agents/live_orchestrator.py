"""LiveOrchestrator: bounded multi-round Band deliberation.

For each question the orchestrator runs up to ``max_rounds`` rounds of
agent collaboration in a single Band room:

  Round 1  draft + retrieve + capability + policy (Sales, Security, Product, Legal)
  Round 2  Featherless adversarial reviewer
  Round 3+ challenged agents rebut; reviewer judges again
  Round N  consensus OR escalation to the Human Gate

Each round-turn is posted via :class:`core.band_publisher.BandPublisher`
(JSONL first, REST second when ``BAND_MODE=live``). Human messages routed
through ``register_human_message`` advance an ``asyncio.Event`` per
question so the orchestrator can resume or restart a round.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from agents.adversarial_reviewer import red_team_answer
from agents.ledger import add_ledger_entry_if_new
from agents.legal_commitment_guard import review_commitment
from agents.product_capability import assess_capability
from agents.sales_engineer import draft_answer
from agents.security_compliance import answer_from_evidence
from core.audit import make_audit_event
from core.band_publisher import BandPublisher
from core.policy_loader import load_commitment_policy
from core.schemas import AgentOpinion, Approval, BandGateState, PolicyViolation, RFPQuestionState


DEFAULT_MAX_ROUNDS = 5
HUMAN_GATE = "human_gate"

# Agents that can produce a fresh turn when the adversarial reviewer flags them
# or the human gate directs them with an @mention. intake_agent and
# adversarial_reviewer have no redraft path at the gate, so a mention of either
# is recorded but does not trigger a turn.
REBUTTAL_AGENTS = {
    "sales_engineer",
    "security_compliance",
    "product_capability",
    "legal_commitment_guard",
}


@dataclass
class HumanDecision:
    action: str  # "approve" | "approve_with_edits" | "push_back" | "escalate" | "reject" | "comment"
    content: str
    mentions: list[str] = field(default_factory=list)
    approver_role: str = "Demo Human Reviewer"
    approver_name: str | None = "BandGate Operator"
    final_answer: str | None = None


class LiveOrchestrator:
    """Coordinates multi-round live deliberation for a BandGateState."""

    def __init__(
        self,
        state: BandGateState,
        *,
        publisher: BandPublisher | None = None,
        policy: dict[str, Any] | None = None,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
    ) -> None:
        self.state = state
        self.publisher = publisher or BandPublisher()
        self.policy = policy or load_commitment_policy()
        self.max_rounds = max_rounds
        self._human_signals: dict[str, asyncio.Event] = {}
        # FIFO queue per question — a human can send several messages (e.g. a
        # push-back then an approval) without one overwriting the other.
        self._human_decisions: dict[str, list[HumanDecision]] = {}
        self._active: set[str] = set()
        self._lock = asyncio.Lock()
        self._pipeline_task: asyncio.Task[Any] | None = None

    # ----- human gate plumbing -----

    def register_human_message(self, question_id: str, decision: HumanDecision) -> None:
        """Drop a human message in. Wakes the orchestrator if it is waiting."""
        self._human_decisions.setdefault(question_id, []).append(decision)
        event = self._human_signals.get(question_id)
        if event is not None:
            event.set()

    def is_active(self, question_id: str) -> bool:
        return question_id in self._active

    # ----- public deliberation entry points -----

    async def deliberate(self, question_id: str) -> RFPQuestionState:
        if question_id not in self.state.questions:
            raise KeyError(question_id)
        async with self._lock:
            already_active = question_id in self._active
            self._active.add(question_id)
        if already_active:
            # Another caller is already running this deliberation; just wait
            # until it leaves a finalized status.
            await self._wait_until_finalized(question_id)
            return self.state.questions[question_id]
        try:
            await self.publisher.ensure_room(self.state.rfp_id)
            await self._run_loop(self.state.questions[question_id])
            return self.state.questions[question_id]
        finally:
            self._active.discard(question_id)

    async def run_queue(self, question_ids: list[str]) -> list[RFPQuestionState]:
        results: list[RFPQuestionState] = []
        for qid in question_ids:
            results.append(await self.deliberate(qid))
        return results

    # ----- whole-questionnaire pipeline -----

    _RISK_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    def ordered_question_ids(self) -> list[str]:
        """Every question id, highest-risk first, so the interesting ones stream first."""
        return [
            q.question_id
            for q in sorted(
                self.state.questions.values(),
                key=lambda q: self._RISK_ORDER.get(q.risk_level, 9),
            )
        ]

    def pipeline_running(self) -> bool:
        return self._pipeline_task is not None and not self._pipeline_task.done()

    def start_pipeline(self) -> bool:
        """Kick a background task that deliberates every question sequentially.

        Returns False if a pipeline is already running.
        """
        if self.pipeline_running():
            return False
        self._pipeline_task = asyncio.create_task(self._run_pipeline(self.ordered_question_ids()))
        return True

    def stop_pipeline(self) -> bool:
        if self.pipeline_running():
            self._pipeline_task.cancel()  # type: ignore[union-attr]
            return True
        return False

    async def _run_pipeline(self, question_ids: list[str]) -> None:
        await self.publisher.ensure_room(self.state.rfp_id)
        await self.publisher.post(
            "orchestrator",
            f"Pipeline started · {len(question_ids)} questions queued (highest risk first).",
            rfp_id=self.state.rfp_id,
            question_id=None,
            event_type="pipeline_started",
            payload={"count": len(question_ids), "queue": question_ids[:50]},
        )
        try:
            for index, qid in enumerate(question_ids, start=1):
                await self.publisher.post(
                    "orchestrator",
                    f"Queue {index}/{len(question_ids)} · deliberating {qid}.",
                    rfp_id=self.state.rfp_id,
                    question_id=qid,
                    event_type="pipeline_progress",
                    payload={"index": index, "total": len(question_ids), "question_id": qid},
                )
                await self.deliberate(qid)
        except asyncio.CancelledError:
            await self.publisher.post(
                "orchestrator",
                "Pipeline stopped by operator.",
                rfp_id=self.state.rfp_id,
                question_id=None,
                event_type="pipeline_stopped",
                payload={},
            )
            raise
        else:
            await self.publisher.post(
                "orchestrator",
                "Pipeline complete · all questions processed.",
                rfp_id=self.state.rfp_id,
                question_id=None,
                event_type="pipeline_complete",
                payload={"count": len(question_ids)},
            )

    # ----- inner loop -----

    async def _run_loop(self, question: RFPQuestionState) -> None:
        question.opinions = []
        question.approvals = []
        question.final_answer = None
        question.status = "drafting"

        await self._post(
            "orchestrator",
            f"Deliberation start for {question.question_id}.",
            question=question,
            event_type="deliberation_started",
        )

        adversarial_challenge: str | None = None
        for round_no in range(1, self.max_rounds + 1):
            await self._post(
                "orchestrator",
                f"Round {round_no} start.",
                question=question,
                event_type="round_start",
                payload={"round_no": round_no},
            )
            await self._round_one_if_needed(question, round_no)
            await self._round_challenge_response(question, round_no, adversarial_challenge)

            adversarial = await self._run_adversarial_round(question, round_no)
            consensus = self._consensus_reached(question, adversarial)
            await self._post(
                "orchestrator",
                f"Round {round_no} complete · consensus={consensus}.",
                question=question,
                event_type="round_complete",
                payload={"round_no": round_no, "consensus": consensus},
            )
            if consensus:
                break
            adversarial_challenge = adversarial.answer if adversarial else None

        # The orchestrator only escalates risky answers to the human. Safe ones
        # (consensus, no policy violations, no injection, low risk) auto-approve.
        if self._needs_human_review(question):
            await self._invite_human_gate(question)
            decision = await self._await_human(question)
            await self._apply_human_decision(question, decision)

            if question.status == "human_review":
                # Push-back from the human: rerun deliberation once with the human's
                # message attached as adversarial challenge.
                adversarial_challenge = f"Human reviewer says: {decision.content}"
                await self._round_challenge_response(
                    question,
                    self.max_rounds,
                    adversarial_challenge,
                    mentions=decision.mentions,
                    human_note=decision.content,
                )
                await self._invite_human_gate(question, second_pass=True)
                decision = await self._await_human(question)
                await self._apply_human_decision(question, decision)
        else:
            await self._auto_approve(question)

        await self._finalize(question)

    async def _round_one_if_needed(self, question: RFPQuestionState, round_no: int) -> None:
        if round_no != 1:
            return
        # Sales drafts. Agent calls are synchronous (blocking HTTP to the
        # providers), so run them in a worker thread to keep the event loop
        # responsive while a model is thinking.
        sales = await asyncio.to_thread(draft_answer, question.raw_question, question.risk_tags)
        question.opinions.append(sales)
        await self._post_opinion(question, sales, round_no=1)
        # Security retrieves + reasons.
        security = await asyncio.to_thread(answer_from_evidence, question.normalized_question)
        question.opinions.append(security)
        await self._post_opinion(question, security, round_no=1)
        # Product when assigned, or whenever risk tags imply capability gating.
        if "product_capability" in set(question.assigned_agents) or any(
            tag.startswith("capability_") or tag == "sla_overcommitment"
            for tag in question.risk_tags
        ):
            product = await asyncio.to_thread(assess_capability, question.normalized_question)
            question.opinions.append(product)
            await self._post_opinion(question, product, round_no=1)
        # Legal policy review.
        legal = await asyncio.to_thread(review_commitment, question, self.policy)
        question.opinions.append(legal)
        await self._post_opinion(question, legal, round_no=1)
        question.status = "evidence_review"

    async def _round_challenge_response(
        self,
        question: RFPQuestionState,
        round_no: int,
        adversarial_challenge: str | None,
        *,
        mentions: list[str] | None = None,
        human_note: str | None = None,
    ) -> None:
        if round_no == 1 or not adversarial_challenge:
            return
        # Agents flagged by the adversarial reviewer, plus any the human gate
        # explicitly tagged with an @mention.
        targets = self._flagged_agents(question)
        mentioned = {name for name in (mentions or []) if name in REBUTTAL_AGENTS}
        targets |= mentioned
        if not targets:
            return

        # Only a directly-mentioned agent acts on the human's free-text note.
        # Reviewer-flagged rebuttals stay driven by the adversarial finding.
        def note_for(agent: str) -> str | None:
            return human_note if agent in mentioned else None

        if "sales_engineer" in targets:
            refreshed = await asyncio.to_thread(
                draft_answer,
                question.raw_question,
                question.risk_tags,
                human_note=note_for("sales_engineer"),
            )
            refreshed.risk_tags = sorted(set(refreshed.risk_tags + ["rebuttal"]))
            question.opinions.append(refreshed)
            await self._post_opinion(question, refreshed, round_no=round_no, prefix="Rebuttal")
        if "security_compliance" in targets:
            refreshed = await asyncio.to_thread(
                answer_from_evidence,
                question.normalized_question,
                human_note=note_for("security_compliance"),
            )
            refreshed.risk_tags = sorted(set(refreshed.risk_tags + ["rebuttal"]))
            question.opinions.append(refreshed)
            await self._post_opinion(question, refreshed, round_no=round_no, prefix="Rebuttal")
        if "product_capability" in targets:
            refreshed = await asyncio.to_thread(
                assess_capability,
                question.normalized_question,
                human_note=note_for("product_capability"),
            )
            refreshed.risk_tags = sorted(set(refreshed.risk_tags + ["rebuttal"]))
            question.opinions.append(refreshed)
            await self._post_opinion(question, refreshed, round_no=round_no, prefix="Rebuttal")
        if "legal_commitment_guard" in targets:
            # Legal is the hard policy gate — it re-asserts policy and never
            # bends to a reviewer note, so no human_note is threaded in.
            refreshed = await asyncio.to_thread(review_commitment, question, self.policy)
            refreshed.risk_tags = sorted(set(refreshed.risk_tags + ["rebuttal"]))
            question.opinions.append(refreshed)
            await self._post_opinion(question, refreshed, round_no=round_no, prefix="Rebuttal")

    async def _run_adversarial_round(self, question: RFPQuestionState, round_no: int) -> AgentOpinion:
        question.final_answer = self._choose_final_answer(question)
        question.status = "adversarial_review"
        adversarial = await asyncio.to_thread(red_team_answer, question)
        adversarial.risk_tags = sorted(set(adversarial.risk_tags + [f"round_{round_no}"]))
        question.opinions.append(adversarial)
        await self._post_opinion(question, adversarial, round_no=round_no)
        return adversarial

    def _consensus_reached(self, question: RFPQuestionState, adversarial: AgentOpinion) -> bool:
        # Consensus = adversarial has no critical/high finding AND no agent in this
        # round was flagged as needing rebuttal beyond what's already addressed.
        critical_findings = any(
            violation.severity in {"high", "critical"} for violation in adversarial.policy_violations
        )
        return not critical_findings

    def _flagged_agents(self, question: RFPQuestionState) -> set[str]:
        flagged: set[str] = set()
        adversarial = next(
            (op for op in reversed(question.opinions) if op.agent_name == "adversarial_reviewer"),
            None,
        )
        if not adversarial:
            return flagged
        for violation in adversarial.policy_violations:
            if "unsupported" in violation.policy_id or "contradiction" in violation.policy_id:
                flagged.update({"security_compliance", "legal_commitment_guard"})
            if "prompt_injection" in violation.policy_id:
                flagged.add("legal_commitment_guard")
        # Sales is usually the source of overclaims; redrafts won't help — Legal owns the rewrite.
        return flagged

    def _choose_final_answer(self, question: RFPQuestionState) -> str:
        legal = self._latest_opinion(question, "legal_commitment_guard")
        adversarial = self._latest_opinion(question, "adversarial_reviewer")
        security = self._latest_opinion(question, "security_compliance")

        if adversarial and any(
            v.policy_id == "adversarial.prompt_injection" for v in adversarial.policy_violations
        ):
            return (
                "Malicious buyer instruction ignored. Final answer must be produced "
                "only from approved evidence and policy."
            )
        if legal and legal.policy_violations:
            return legal.answer
        if security and security.evidence:
            return security.answer
        return legal.answer if legal else "No approved final answer generated."

    def _needs_human_review(self, question: RFPQuestionState) -> bool:
        """True when an answer is risky enough to require a human decision.

        Safe answers (consensus, no policy violations, no injection, low risk)
        are auto-approved by the orchestrator and never touch the human gate.
        """
        if question.risk_level in {"high", "critical"}:
            return True
        if question.conflict_detected:
            return True
        if any(tag in question.risk_tags for tag in ("prompt_injection", "sensitive_disclosure")):
            return True
        # Any agent that recorded a concrete policy violation forces a human look.
        for opinion in question.opinions:
            if opinion.policy_violations:
                return True
        return False

    async def _auto_approve(self, question: RFPQuestionState) -> None:
        """Finalize a safe answer on the agents' behalf — no human needed."""
        question.final_answer = question.final_answer or self._choose_final_answer(question)
        question.status = "approved"
        question.approvals.append(
            Approval(
                approver_role="Orchestrator (auto)",
                approver_name="BandGate Orchestrator",
                decision="approved",
                comment="Auto-approved: consensus reached, no policy violations or risk flags.",
                timestamp=datetime.now(UTC).isoformat(),
            )
        )
        await self._post(
            "orchestrator",
            f"Auto-approved {question.question_id} — consensus, no violations, low risk. "
            "No human review needed.",
            question=question,
            event_type="auto_approval",
            payload={"reason": "safe", "risk_level": question.risk_level},
        )

    async def _invite_human_gate(self, question: RFPQuestionState, *, second_pass: bool = False) -> None:
        question.status = "human_review"
        prompt = (
            f"Human gate review for {question.question_id}. "
            f"Final draft: {question.final_answer or '(empty)'} "
            f"Risk tags: {', '.join(question.risk_tags) or 'none'}."
        )
        if second_pass:
            prompt = "Second pass after human push-back. " + prompt
        await self._post(
            HUMAN_GATE,
            prompt,
            question=question,
            event_type="human_approval",
            requires_human_approval=True,
        )

    async def _await_human(self, question: RFPQuestionState) -> HumanDecision:
        qid = question.question_id
        event = self._human_signals.setdefault(qid, asyncio.Event())
        queue = self._human_decisions.setdefault(qid, [])
        if not queue:
            try:
                await asyncio.wait_for(event.wait(), timeout=_human_wait_timeout())
            except asyncio.TimeoutError:
                # Default to a safe escalation if no human responds in time.
                queue.append(
                    HumanDecision(
                        action="escalate",
                        content="No human response within timeout; auto-escalating.",
                    )
                )
        event.clear()
        return queue.pop(0)

    async def _apply_human_decision(self, question: RFPQuestionState, decision: HumanDecision) -> None:
        await self._post(
            HUMAN_GATE,
            decision.content,
            question=question,
            event_type="human_message",
            payload={"action": decision.action, "mentions": decision.mentions},
        )
        question.approvals.append(
            Approval(
                approver_role=decision.approver_role,
                approver_name=decision.approver_name,
                decision=_map_action_to_decision(decision.action),
                comment=decision.content,
                timestamp=datetime.now(UTC).isoformat(),
            )
        )
        if decision.action in {"approve", "approve_with_edits"}:
            question.status = "approved"
            if decision.final_answer:
                question.final_answer = decision.final_answer
        elif decision.action == "reject":
            question.status = "human_review"
            question.final_answer = None
        elif decision.action == "escalate":
            question.status = "human_review"
        elif decision.action == "push_back":
            question.status = "human_review"
        else:
            # comment-only — leave status as-is.
            pass

    async def _finalize(self, question: RFPQuestionState) -> None:
        if question.status not in {"approved", "human_review"}:
            question.status = "finalized"
        elif question.status == "approved":
            question.status = "finalized"
        self.state.audit_trail.append(
            make_audit_event(
                actor="live_orchestrator",
                action="finalize_answer",
                question_id=question.question_id,
                summary=question.final_answer or "",
                payload=question.model_dump(mode="json"),
            )
        )
        entry = add_ledger_entry_if_new(self.state, question)
        if entry is not None:
            await self._post(
                "orchestrator",
                f"Promise Ledger entry {entry.commitment_id} created.",
                question=question,
                event_type="final_export",
                payload={"commitment_id": entry.commitment_id},
            )
        await self._post(
            "orchestrator",
            f"Deliberation finalized for {question.question_id}.",
            question=question,
            event_type="deliberation_finalized",
            payload={"status": question.status},
        )

    # ----- helpers -----

    def _latest_opinion(self, question: RFPQuestionState, agent_name: str) -> AgentOpinion | None:
        for opinion in reversed(question.opinions):
            if opinion.agent_name == agent_name:
                return opinion
        return None

    async def _post_opinion(
        self,
        question: RFPQuestionState,
        opinion: AgentOpinion,
        *,
        round_no: int,
        prefix: str | None = None,
    ) -> None:
        body = opinion.answer
        if prefix:
            body = f"[{prefix}] {body}"
        self.state.audit_trail.append(
            make_audit_event(
                actor=opinion.agent_name,
                action=f"round_{round_no}_opinion",
                question_id=question.question_id,
                summary=body,
                payload=opinion.model_dump(mode="json"),
            )
        )
        mentions = _mentions_for_agent(opinion.agent_name, opinion.policy_violations)
        await self._post(
            opinion.agent_name,
            body,
            question=question,
            event_type="agent_output",
            mentions=mentions,
            payload={
                "round_no": round_no,
                "provider": opinion.provider,
                "model_name": opinion.model_name,
                "confidence": opinion.confidence,
                "risk_tags": opinion.risk_tags,
            },
        )

    async def _post(
        self,
        agent: str,
        summary: str,
        *,
        question: RFPQuestionState,
        event_type: str = "agent_output",
        mentions: list[str] | None = None,
        payload: dict[str, Any] | None = None,
        requires_human_approval: bool = False,
    ) -> None:
        await self.publisher.post(
            agent,
            summary,
            rfp_id=self.state.rfp_id,
            question_id=question.question_id,
            event_type=event_type,
            mentions=mentions,
            risk_level=question.risk_level,
            requires_human_approval=requires_human_approval,
            payload=payload,
        )

    async def _wait_until_finalized(self, question_id: str) -> None:
        for _ in range(300):
            if self.state.questions[question_id].status == "finalized":
                return
            await asyncio.sleep(0.5)


def _mentions_for_agent(agent_name: str, violations: list[PolicyViolation]) -> list[str]:
    if agent_name == "intake_agent":
        return ["sales_engineer", "security_compliance", "product_capability"]
    if agent_name == "sales_engineer":
        return ["legal_commitment_guard", "security_compliance"]
    if agent_name == "security_compliance":
        return ["legal_commitment_guard"]
    if agent_name == "product_capability":
        return ["legal_commitment_guard"]
    if agent_name == "legal_commitment_guard" and violations:
        return ["adversarial_reviewer", "human_gate"]
    if agent_name == "adversarial_reviewer" and violations:
        return ["legal_commitment_guard", "human_gate"]
    return []


def _map_action_to_decision(action: str) -> str:
    return {
        "approve": "approved",
        "approve_with_edits": "approved_with_edits",
        "push_back": "escalated",
        "escalate": "escalated",
        "reject": "rejected",
        "comment": "approved_with_edits",  # benign default for plain comments
    }.get(action, "approved_with_edits")


def _human_wait_timeout() -> float:
    import os

    try:
        return float(os.getenv("BANDGATE_HUMAN_WAIT_SECONDS", "600"))
    except ValueError:
        return 600.0
