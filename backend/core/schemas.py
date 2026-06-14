from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["low", "medium", "high", "critical"]
QuestionStatus = Literal[
    "open",
    "drafting",
    "evidence_review",
    "policy_review",
    "adversarial_review",
    "human_review",
    "approved",
    "finalized",
]


class Evidence(BaseModel):
    source_id: str
    document_name: str
    chunk_id: str
    quote: str
    confidence: float = Field(ge=0.0, le=1.0)


class PolicyViolation(BaseModel):
    policy_id: str
    severity: RiskLevel
    claim: str
    allowed_position: str
    recommended_fix: str


class AgentOpinion(BaseModel):
    agent_name: str
    provider: str = "deterministic"
    model_name: str = "day1-rule"
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = []
    policy_violations: list[PolicyViolation] = []
    risk_tags: list[str] = []


class Approval(BaseModel):
    approver_role: str
    approver_name: str | None = None
    decision: Literal["approved", "approved_with_edits", "rejected", "escalated"]
    comment: str | None = None
    timestamp: str


class RFPQuestionState(BaseModel):
    question_id: str
    raw_question: str
    normalized_question: str
    category: list[str]
    risk_level: RiskLevel
    assigned_agents: list[str]
    opinions: list[AgentOpinion] = []
    conflict_detected: bool = False
    conflict_summary: str | None = None
    final_answer: str | None = None
    status: QuestionStatus = "open"
    approvals: list[Approval] = []
    risk_tags: list[str] = []


class PromiseLedgerEntry(BaseModel):
    commitment_id: str
    source_question_id: str
    commitment_text: str
    owner_department: Literal["Sales", "Security", "Legal", "Product", "Delivery", "Customer Success"]
    delivery_action: str
    due_stage: Literal["pre_contract", "contracting", "implementation", "onboarding", "renewal"]
    approval_required: bool


class AuditEvent(BaseModel):
    event_id: str
    timestamp: str
    actor: str
    action: str
    question_id: str | None
    summary: str
    payload_hash: str


class BandGateState(BaseModel):
    rfp_id: str
    buyer_name: str
    vendor_name: str
    policy_version: str
    questions: dict[str, RFPQuestionState]
    promise_ledger: list[PromiseLedgerEntry] = []
    audit_trail: list[AuditEvent] = []
    global_risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
