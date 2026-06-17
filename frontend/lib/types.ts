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
  aiml_enabled: boolean;
  featherless_live_ready: boolean;
  aiml_model: string;
  aiml_embedding_model?: string;
  featherless_model: string;
  aiml_live_limits: Record<string, number>;
  featherless_live_limits: Record<string, number>;
  band_default_room_id: string | null;
  band_rest_url: string;
  band_ws_url: string;
};

export type BandEventRecord = {
  event_type: string;
  rfp_id: string;
  question_id: string | null;
  agent: string;
  summary: string;
  risk_level: string | null;
  requires_human_approval: boolean;
  payload?: Record<string, unknown> | null;
  provider_mode: string;
  timestamp: string;
};

export type RfpQuestionSummary = {
  question_id: string;
  raw_question: string;
  normalized_question: string;
  category: string[];
  risk_level: RiskLevel;
  risk_tags: string[];
  status: string;
  conflict_summary: string | null;
  has_final_answer: boolean;
};

export type RfpListResponse = {
  rfp_id: string;
  buyer_name: string;
  vendor_name: string;
  policy_version: string;
  question_count: number;
  questions: RfpQuestionSummary[];
};

export type HumanGateAction =
  | "comment"
  | "approve"
  | "approve_with_edits"
  | "push_back"
  | "escalate"
  | "reject";

export type HumanMessagePayload = {
  question_id: string;
  content: string;
  action: HumanGateAction;
  mentions?: string[];
  final_answer?: string;
  approver_role?: string;
  approver_name?: string;
};
