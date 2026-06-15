export type RiskLevel = "low" | "medium" | "high" | "critical";

export type RFPQuestionState = {
  question_id: string;
  raw_question: string;
  normalized_question: string;
  category: string[];
  risk_level: RiskLevel;
  assigned_agents: string[];
  opinions: AgentOpinion[];
  conflict_detected: boolean;
  conflict_summary: string | null;
  final_answer: string | null;
  status: string;
  approvals: Approval[];
  risk_tags: string[];
};

export type BandGateState = {
  rfp_id: string;
  buyer_name: string;
  vendor_name: string;
  policy_version: string;
  questions: Record<string, RFPQuestionState>;
  promise_ledger: PromiseLedgerEntry[];
  audit_trail: AuditEvent[];
  global_risk_score: number;
};

export type Evidence = {
  source_id: string;
  document_name: string;
  chunk_id: string;
  quote: string;
  confidence: number;
};

export type PolicyViolation = {
  policy_id: string;
  severity: RiskLevel;
  claim: string;
  allowed_position: string;
  recommended_fix: string;
};

export type AgentOpinion = {
  agent_name: string;
  provider: string;
  model_name: string;
  answer: string;
  confidence: number;
  evidence: Evidence[];
  policy_violations: PolicyViolation[];
  risk_tags: string[];
};

export type Approval = {
  approver_role: string;
  approver_name: string | null;
  decision: string;
  comment: string | null;
  timestamp: string;
};

export type PromiseLedgerEntry = {
  commitment_id: string;
  source_question_id: string;
  commitment_text: string;
  owner_department: string;
  delivery_action: string;
  due_stage: string;
  approval_required: boolean;
};

export type AuditEvent = {
  event_id: string;
  timestamp: string;
  actor: string;
  action: string;
  question_id: string | null;
  summary: string;
  payload_hash: string;
};

export type ProviderStatus = {
  band_mode: string;
  featherless_mode: string;
  aiml_mode: string;
  featherless_configured: boolean;
  aiml_configured: boolean;
  band_default_room_id: string | null;
  thenvoi_rest_url: string;
  thenvoi_ws_url: string;
};

export type BandEventRecord = {
  event_type: string;
  rfp_id: string;
  question_id: string | null;
  agent: string;
  summary: string;
  risk_level: string | null;
  requires_human_approval: boolean;
  provider_mode: string;
  timestamp: string;
};
