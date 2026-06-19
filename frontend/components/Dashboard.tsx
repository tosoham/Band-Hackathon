"use client";

import { useEffect, useState } from "react";
import Icon, { type IconName } from "./Icon";
import { type Decision } from "./ApprovalControls";
import BandTimeline from "./BandTimeline";
import BandRoom from "./BandRoom";
import RiskDashboard from "./RiskDashboard";
import ExportBar from "./ExportBar";
import DemoReset from "./DemoReset";
import PipelineControl from "./PipelineControl";
import PolicyDecisionPanel from "./PolicyDecisionPanel";
import AdversarialReviewPanel from "./AdversarialReviewPanel";
import PromiseLedger from "./PromiseLedger";
import LiveRoomPanel from "./LiveRoomPanel";
import RfpUpload from "./RfpUpload";
import { Logo } from "./Logo";
import type {
  AgentOpinion,
  BandEventRecord,
  BandGateState,
  QuestionStatus,
  RFPQuestionState,
  Evidence,
} from "../lib/types";

type StateSource = "live" | "fallback" | "demo";
type View = "overview" | "intake" | "triage" | "review" | "bandroom" | "risk" | "ledger" | "audit" | "exports";
type SubTab = "agents" | "evidence" | "policy" | "adversarial" | "band" | "liveroom";

const RISK_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
const RISK_WEIGHT: Record<string, number> = { critical: 1, high: 0.7, medium: 0.4, low: 0.15 };

function postureBand(score: number): { tag: string; color: string } {
  if (score >= 67) return { tag: "Elevated", color: "var(--r-high)" };
  if (score >= 34) return { tag: "Guarded", color: "var(--r-medium)" };
  return { tag: "Contained", color: "var(--r-low)" };
}

const AGENT_CODE: Record<string, string> = {
  sales_engineer: "SE",
  security_compliance: "SC",
  product_capability: "PC",
  legal_commitment_guard: "LG",
  adversarial_reviewer: "AR",
};

function agentCode(name: string) {
  return AGENT_CODE[name] ?? name.slice(0, 2).toUpperCase();
}

function agentLabel(name: string) {
  return name.replaceAll("_", " ");
}

function riskClass(risk: string) {
  return `risk risk-${risk}`;
}

const DELIBERATING = ["drafting", "evidence_review", "policy_review", "adversarial_review"];

function statusLabel(question: RFPQuestionState) {
  const s = question.status;
  const last = question.approvals[question.approvals.length - 1];
  if (s === "finalized" || s === "approved") return "Approved";
  if (s === "rejected") return "Rejected";
  if (s === "human_review") return last?.decision === "rejected" ? "Rejected" : "At human gate";
  if (DELIBERATING.includes(s)) return "Deliberating";
  return "Queued";
}

function statusKind(question: RFPQuestionState) {
  const s = question.status;
  const last = question.approvals[question.approvals.length - 1];
  if (s === "finalized" || s === "approved") return "ok";
  if (s === "rejected" || (s === "human_review" && last?.decision === "rejected")) return "attack";
  if (s === "human_review") return "review";
  if (DELIBERATING.includes(s)) return "review";
  return "queued";
}

function confidencePct(value: number) {
  return `${Math.round(value * 100)}%`;
}

function eventTime(ts: string) {
  const d = new Date(ts);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function auditKind(action: string): "approved" | "alert" | "decision" | "neutral" {
  const a = action.toLowerCase();
  if (a.includes("finalize") || a.includes("approve") || a.includes("ledger")) return "approved";
  if (a.includes("reject") || a.includes("escalat") || a.includes("block") || a.includes("violation") || a.includes("injection"))
    return "alert";
  if (a.includes("decision") || a.includes("human") || a.includes("gate")) return "decision";
  return "neutral";
}

const ROOM_AGENTS = [
  { keys: ["intake", "intake_coordinator", "intake_risk"], label: "Intake", role: "Triages & routes risk", defaultProvider: "aiml" },
  { keys: ["sales_engineer"], label: "Sales", role: "Drafts the answer", defaultProvider: "aiml" },
  { keys: ["security_compliance"], label: "Security", role: "Cites controls & evidence", defaultProvider: "aiml" },
  { keys: ["product_capability"], label: "Product", role: "Validates capabilities", defaultProvider: "aiml" },
  { keys: ["legal_commitment_guard"], label: "Legal", role: "Guards commitments", defaultProvider: "aiml" },
  { keys: ["adversarial_reviewer"], label: "Adversarial", role: "Red-teams every claim", defaultProvider: "featherless" },
] as const;

type AnswerState = { label: string; kind: "attack" | "conflict" | "ok"; detail: string; icon: IconName };

function answerState(question: RFPQuestionState): AnswerState {
  if (question.risk_tags.includes("prompt_injection")) {
    return {
      label: "Prompt injection blocked",
      kind: "attack",
      icon: "block",
      detail: "Buyer text tried to override internal policy and was quarantined as untrusted input.",
    };
  }
  if (question.conflict_detected) {
    return {
      label: "Conflict — policy review",
      kind: "conflict",
      icon: "alert",
      detail:
        question.conflict_summary ??
        "The optimistic draft conflicts with approved evidence and must be reviewed before finalization.",
    };
  }
  return {
    label: "Evidence-backed draft",
    kind: "ok",
    icon: "approve",
    detail: "The draft is supported by retrieved evidence and is ready for policy sign-off.",
  };
}

function dedupeEvidence(opinions: AgentOpinion[]): Evidence[] {
  const seen = new Set<string>();
  const all: Evidence[] = [];
  for (const opinion of opinions) {
    for (const evidence of opinion.evidence) {
      if (!seen.has(evidence.chunk_id)) {
        seen.add(evidence.chunk_id);
        all.push(evidence);
      }
    }
  }
  return all.sort((a, b) => b.confidence - a.confidence);
}

function recommendedAnswer(question: RFPQuestionState): string {
  const evidenceBacked = question.opinions.find(
    (opinion) => opinion.risk_tags.includes("supported_by_evidence") && opinion.evidence.length > 0,
  );
  return evidenceBacked?.answer ?? question.opinions[0]?.answer ?? "";
}

function NavItem({
  icon,
  label,
  active,
  onClick,
}: {
  icon: IconName;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button type="button" className={`navItem${active ? " navActive" : ""}`} onClick={onClick} aria-current={active}>
      <span className="navIcon">
        <Icon name={icon} size={17} />
      </span>
      <span className="navLabel">{label}</span>
    </button>
  );
}

function QueueRow({
  question,
  selected,
  compact,
  onClick,
}: {
  question: RFPQuestionState;
  selected: boolean;
  compact?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={`questionRow${compact ? " compact" : ""}${selected ? " isSelected" : ""}`}
      onClick={onClick}
      aria-pressed={selected}
    >
      <div className="qrMain">
        <div className="qrTop">
          <span className="questionId">{question.question_id}</span>
          <span className={riskClass(question.risk_level)}>{question.risk_level}</span>
        </div>
        <h3>{question.raw_question}</h3>
        <div className="qrBottom">
          <span className={`status status-${statusKind(question)}`}>
            <span className="dot" />
            {statusLabel(question)}
          </span>
          {!compact &&
            question.category.slice(0, 2).map((cat) => (
              <span className="chip" key={cat}>
                {cat.replaceAll("_", " ")}
              </span>
            ))}
        </div>
      </div>
      {!compact && (
        <span className="qrArrow" aria-hidden>
          <Icon name="chevron" size={18} />
        </span>
      )}
    </button>
  );
}

function OpinionCard({ opinion }: { opinion: AgentOpinion }) {
  return (
    <li className="tlItem">
      <span className="avatar" aria-hidden>
        {agentCode(opinion.agent_name)}
      </span>
      <article className="opinion">
        <div className="opinionHead">
          <span className="opinionAgent">{agentLabel(opinion.agent_name)}</span>
          <span className={`sourceTag source-${opinion.provider === "aiml" ? "aiml" : "local"}`}>
            {opinion.provider === "aiml" ? "AI/ML API" : "deterministic"}
          </span>
        </div>
        <p className="opinionAnswer">{opinion.answer}</p>
        <div className="opinionFoot">
          <span className="confidence">
            <span className="confidenceBar" aria-hidden>
              <span style={{ width: confidencePct(opinion.confidence) }} />
            </span>
            <span className="confidenceVal">{confidencePct(opinion.confidence)}</span>
          </span>
          <span className="evidenceCount">
            {opinion.evidence.length} citation{opinion.evidence.length === 1 ? "" : "s"}
          </span>
        </div>
        {opinion.risk_tags.length > 0 && (
          <div className="tagLine">
            {opinion.risk_tags.map((tag) => (
              <span key={tag}>{tag.replaceAll("_", " ")}</span>
            ))}
          </div>
        )}
      </article>
    </li>
  );
}

export default function Dashboard({
  state,
  source,
  bandEvents = [],
  bandReport = "",
  publicBackendUrl = "",
}: {
  state: BandGateState;
  source: StateSource;
  bandEvents?: BandEventRecord[];
  bandReport?: string;
  publicBackendUrl?: string;
}) {
  const [live, setLive] = useState<BandGateState>(state);
  const [byId, setById] = useState<Record<string, RFPQuestionState>>(state.questions);
  const [view, setView] = useState<View>("overview");
  const [subTab, setSubTab] = useState<SubTab>("agents");

  // The pipeline runs server-side; poll /state so question statuses, the Promise
  // Ledger, the Audit Trail, and recorded decisions stay live (and survive
  // navigating between questions).
  useEffect(() => {
    if (!publicBackendUrl) return;
    let alive = true;
    const tick = async () => {
      try {
        const res = await fetch(`${publicBackendUrl.replace(/\/+$/, "")}/state`, { cache: "no-store" });
        if (!res.ok || !alive) return;
        const fresh = (await res.json()) as BandGateState;
        if (!alive) return;
        setLive(fresh);
        setById(fresh.questions);
      } catch {
        /* transient — keep last known state */
      }
    };
    tick();
    const id = setInterval(tick, 3000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [publicBackendUrl]);

  const questions = Object.values(byId).sort(
    (a, b) => (RISK_ORDER[a.risk_level] ?? 9) - (RISK_ORDER[b.risk_level] ?? 9),
  );

  const defaultId =
    questions.find((question) => question.risk_tags.includes("sla_overcommitment"))?.question_id ??
    questions[0]?.question_id;
  const [selectedId, setSelectedId] = useState(defaultId);

  const selected = questions.find((question) => question.question_id === selectedId) ?? questions[0];

  function openReview(id: string) {
    setSelectedId(id);
    setSubTab("agents");
    setView("review");
  }

  async function decide(decision: Decision, role: string, finalAnswer?: string) {
    if (!selected) return;
    const current = byId[selected.question_id];
    if (!current) return;

    const nextFinal =
      decision === "rejected"
        ? null
        : finalAnswer ?? (decision === "approved" ? recommendedAnswer(current) : current.final_answer);
    const status: QuestionStatus =
      decision === "approved" || decision === "approved_with_edits" ? "approved" : "human_review";

    const updated: RFPQuestionState = {
      ...current,
      status,
      final_answer: nextFinal,
      approvals: [
        ...current.approvals,
        {
          approver_role: role,
          approver_name: null,
          decision,
          comment: null,
          timestamp: new Date().toISOString(),
        },
      ],
    };
    setById({ ...byId, [current.question_id]: updated });

    const backendUrl = (process.env.NEXT_PUBLIC_BACKEND_URL ?? "").replace(/\/+$/, "");
    if (backendUrl) {
      try {
        await fetch(`${backendUrl}/questions/${current.question_id}/decision`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ decision, approver_role: role, final_answer: nextFinal }),
        });
      } catch {
        /* ignore — local state already reflects the decision */
      }
    }
  }

  const total = questions.length;
  const highRisk = questions.filter((q) => q.risk_level === "high").length;
  const criticalRisk = questions.filter((q) => q.risk_level === "critical").length;
  const blocked = questions.filter((q) => q.conflict_detected).length;
  const finalized = questions.filter((q) => q.status === "approved" || q.status === "finalized").length;
  const evidence = selected ? dedupeEvidence(selected.opinions) : [];
  const liveProvider = live.provider_mode !== "mock";
  const stateInfo = selected ? answerState(selected) : null;

  const derivedRisk =
    total > 0 ? questions.reduce((sum, q) => sum + (RISK_WEIGHT[q.risk_level] ?? 0), 0) / total : 0;
  const rawScore = live.global_risk_score > 0 ? live.global_risk_score : derivedRisk;
  const score = Math.round(rawScore <= 1 ? rawScore * 100 : rawScore);
  const posture = postureBand(score);

  // ---- Overview: agent roster, AI activity, and live room preview ----
  const allOpinions = questions.flatMap((q) => q.opinions);
  function agentStat(keys: readonly string[]) {
    const ops = allOpinions.filter((o) => keys.includes(o.agent_name));
    return { count: ops.length, provider: ops.find((o) => o.provider)?.provider };
  }
  let aimlCalls = 0;
  let featherlessCalls = 0;
  let evidenceCalls = 0;
  for (const o of allOpinions) {
    const p = (o.provider ?? "").toLowerCase();
    if (o.agent_name === "adversarial_reviewer" || p.includes("featherless")) featherlessCalls += 1;
    else if (p.includes("aiml")) aimlCalls += 1;
    evidenceCalls += o.evidence.length;
  }
  const roomTurns = bandEvents.length;
  const recentEvents = [...bandEvents].slice(-4).reverse();

  const NAV_TOP: { id: View; label: string; icon: IconName }[] = [
    { id: "overview", label: "Overview", icon: "home" },
  ];
  const NAV: { id: View; label: string; icon: IconName }[] = [
    { id: "intake", label: "Intake", icon: "queue" },
    { id: "triage", label: "Triage", icon: "queue" },
    { id: "review", label: "Review", icon: "review" },
    { id: "bandroom", label: "Band Room", icon: "band" },
  ];
  const NAV_ANALYSIS: { id: View; label: string; icon: IconName }[] = [
    { id: "risk", label: "Risk Dashboard", icon: "risk" },
    { id: "ledger", label: "Promise Ledger", icon: "ledger" },
    { id: "audit", label: "Audit Trail", icon: "policy" },
    { id: "exports", label: "Exports", icon: "export" },
  ];

  const HEAD: Record<View, { eyebrow: string; title: string; subtitle: string }> = {
    overview: {
      eyebrow: "Band of Agents · Track 1",
      title: "Overview",
      subtitle: "Portfolio posture and entry point.",
    },
    intake: {
      eyebrow: "Band of Agents · Track 1",
      title: "Intake",
      subtitle: "Upload an RFP questionnaire and load its questions.",
    },
    triage: {
      eyebrow: "Band of Agents · Track 1",
      title: "Triage Queue",
      subtitle: `${state.vendor_name} responding to ${state.buyer_name}`,
    },
    review: {
      eyebrow: `${selected?.question_id ?? "—"} · Review`,
      title: "Question Review",
      subtitle: "Draft, evidence, policy, adversarial check, and human sign-off.",
    },
    bandroom: {
      eyebrow: "Band of Agents · Track 1",
      title: "Band Room",
      subtitle: "Live six-agent collaboration, policy blocks, drift control, and the chat report.",
    },
    risk: { eyebrow: "Portfolio", title: "Risk Dashboard", subtitle: "Exposure across the full questionnaire." },
    ledger: {
      eyebrow: "Delivery",
      title: "Promise Ledger",
      subtitle: "Every approved commitment becomes a delivery obligation.",
    },
    audit: {
      eyebrow: "Audit",
      title: "Audit Trail",
      subtitle: "Every agent opinion, policy check, decision, and finalize — hashed and timestamped.",
    },
    exports: { eyebrow: "Audit", title: "Exports", subtitle: "Final response, audit trail, and Promise Ledger." },
  };

  const subTabs: { id: SubTab; label: string; icon: IconName; count?: number }[] = [
    { id: "agents", label: "Agents", icon: "agents", count: selected?.opinions.length ?? 0 },
    { id: "evidence", label: "Evidence", icon: "evidence", count: evidence.length },
    { id: "policy", label: "Policy", icon: "policy" },
    { id: "adversarial", label: "Adversarial", icon: "shield" },
    { id: "band", label: "Band feed", icon: "band" },
    { id: "liveroom", label: "Live Room", icon: "band" },
  ];

  const head = HEAD[view];

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brandMark">
            <Logo size={24} />
          </span>
          <div>
            <span className="brandName">BandGate</span>
            <span className="brandTag">Promise Gate</span>
          </div>
        </div>

        <nav className="nav">
          {NAV_TOP.map((item) => (
            <NavItem
              key={item.id}
              icon={item.icon}
              label={item.label}
              active={view === item.id}
              onClick={() => setView(item.id)}
            />
          ))}
          <span className="navHeading">Workflow</span>
          {NAV.map((item) => (
            <NavItem
              key={item.id}
              icon={item.icon}
              label={item.label}
              active={view === item.id}
              onClick={() => setView(item.id)}
            />
          ))}
          <span className="navHeading">Analysis</span>
          {NAV_ANALYSIS.map((item) => (
            <NavItem
              key={item.id}
              icon={item.icon}
              label={item.label}
              active={view === item.id}
              onClick={() => setView(item.id)}
            />
          ))}
        </nav>

        <div className="sidebarFoot">
          <span className={`providerPill ${liveProvider ? "provider-live" : "provider-mock"}`}>
            <span className="dot" /> AI/ML · {liveProvider ? state.provider_mode : "mock"}
          </span>
          <span className="policyVer">policy v{state.policy_version}</span>
          <form action="/api/auth/logout" method="post" className="navLogout">
            <button type="submit">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              Sign out
            </button>
          </form>
        </div>
      </aside>

      <div className="content">
        <header className="topbar">
          {view === "overview" ? (
            <div className="topSpacer" />
          ) : (
            <div>
              <p className="eyebrow">{head.eyebrow}</p>
              <h1>{head.title}</h1>
              <p className="subtitle">{head.subtitle}</p>
            </div>
          )}
          <div className="headChips">
            <span className="idChip">{live.rfp_id}</span>
            {source !== "live" && <span className="demoChip">demo data</span>}
            <PipelineControl publicBackendUrl={publicBackendUrl} />
            <DemoReset />
          </div>
        </header>

        {source === "fallback" && (
          <div className="banner banner-warn" role="status">
            Backend unreachable — showing bundled demo data. Start the backend to load live state.
          </div>
        )}

        {view === "overview" && (
          <>
            <section className="hero">
              <div>
                <p className="eyebrow">Band of Agents · Track 1 · {state.rfp_id}</p>
                <h1 className="heroTitle">
                  Every answer is a <em>promise.</em>
                </h1>
                <p className="heroLede">
                  <strong>{state.vendor_name}</strong> is responding to <strong>{state.buyer_name}</strong>.
                  BandGate reviews each answer before it ships — blocking unsafe commitments, gating every claim
                  to approved evidence, and routing real risk to a human.
                </p>
                <button type="button" className="heroCta" onClick={() => setView("triage")}>
                  Open triage queue <Icon name="chevron" size={16} />
                </button>
              </div>

              <aside className="posture">
                <div className="postureRow">
                  <span className="postureScore">
                    {score}
                    <span>/100</span>
                  </span>
                  <span
                    className="postureTag"
                    style={{
                      color: posture.color,
                      background: `color-mix(in srgb, ${posture.color} 13%, transparent)`,
                    }}
                  >
                    {posture.tag}
                  </span>
                </div>
                <div className="postureMeter">
                  <i style={{ width: `${Math.max(6, score)}%` }} />
                </div>
                <p className="postureFoot">
                  Portfolio risk posture across {total} questions · {blocked} blocked for rewrite · {finalized} finalized.
                </p>
              </aside>
            </section>

            <section className="metrics" aria-label="Overview metrics">
              <div className="stat stat-total">
                <span className="statValue">{total}</span>
                <span className="statLabel">Questions</span>
              </div>
              <div className="stat stat-guard">
                <span className="statValue">{blocked}</span>
                <span className="statLabel">Guarded</span>
              </div>
              <div className="stat stat-high">
                <span className="statValue">{highRisk}</span>
                <span className="statLabel">High risk</span>
              </div>
              <div className="stat stat-crit">
                <span className="statValue">{criticalRisk}</span>
                <span className="statLabel">Critical</span>
              </div>
            </section>

            <section className="roomRoster" aria-label="Agent room">
              <div className="sectionTitle">
                <h2>The Room</h2>
                <span>Six agents · AI/ML proposes, policy disposes</span>
              </div>
              <div className="roster">
                {ROOM_AGENTS.map((a) => {
                  const stat = agentStat(a.keys);
                  const provider = (stat.provider ?? a.defaultProvider).toLowerCase();
                  const tag = provider.includes("featherless") ? "featherless" : "aiml";
                  const active = stat.count > 0;
                  return (
                    <div key={a.label} className="agentCard">
                      <div className="agentCardHead">
                        <span className={`agentDot${active ? " agentDotLive" : ""}`} />
                        <span className="agentName">{a.label}</span>
                      </div>
                      <p className="agentRole">{a.role}</p>
                      <div className="agentMeta">
                        <span className={`provBadge prov-${tag}`}>{tag}</span>
                        {active && (
                          <span className="agentCalls">
                            {stat.count} {stat.count === 1 ? "turn" : "turns"}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            <div className="overviewSplit">
              <section className="livePreviewCard" aria-label="Live deliberation">
                <div className="sectionTitle">
                  <h2>Live deliberation</h2>
                  <button type="button" className="linkCta" onClick={() => setView("bandroom")}>
                    View live room <Icon name="chevron" size={14} />
                  </button>
                </div>
                {recentEvents.length > 0 ? (
                  <ul className="liveFeed">
                    {recentEvents.map((ev, i) => (
                      <li key={`${ev.timestamp}-${i}`} className="liveFeedItem">
                        <span className="feedAvatar">{agentCode(ev.agent)}</span>
                        <div className="feedBody">
                          <div className="feedTop">
                            <span className="feedAgent">{agentLabel(ev.agent)}</span>
                            {ev.risk_level && <span className={riskClass(ev.risk_level)}>{ev.risk_level}</span>}
                            <span className="feedTime" suppressHydrationWarning>{eventTime(ev.timestamp)}</span>
                          </div>
                          <p className="feedSummary">{ev.summary}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="emptyState">
                    No room activity yet. Run a deliberation to watch the agents talk here.
                  </p>
                )}
              </section>

              <section className="aiUsageCard" aria-label="AI activity">
                <div className="sectionTitle">
                  <h2>AI activity</h2>
                  <span className={`providerPill ${liveProvider ? "provider-live" : "provider-mock"}`}>
                    <span className="dot" /> {liveProvider ? state.provider_mode : "mock"}
                  </span>
                </div>
                <div className="usageGrid">
                  <div className="usageStat">
                    <span className="usageValue">{aimlCalls}</span>
                    <span className="usageLabel">AI/ML reasoning</span>
                  </div>
                  <div className="usageStat">
                    <span className="usageValue">{featherlessCalls}</span>
                    <span className="usageLabel">Adversarial reviews</span>
                  </div>
                  <div className="usageStat">
                    <span className="usageValue">{evidenceCalls}</span>
                    <span className="usageLabel">Evidence retrieved</span>
                  </div>
                  <div className="usageStat">
                    <span className="usageValue">{roomTurns}</span>
                    <span className="usageLabel">Room turns</span>
                  </div>
                </div>
              </section>
            </div>
          </>
        )}

        {view === "intake" && (
          <>
            <RfpUpload />
            <section className="queueWide" aria-label="Loaded questions">
              <div className="sectionTitle">
                <h2>Loaded Questions</h2>
                <span>{total} items</span>
              </div>
              <div className="questionList">
                {questions.map((question) => (
                  <QueueRow
                    key={question.question_id}
                    question={question}
                    selected={question.question_id === selected.question_id}
                    onClick={() => openReview(question.question_id)}
                  />
                ))}
                {total === 0 ? (
                  <p className="intakeEmpty">No questions loaded yet — upload a CSV or PDF above.</p>
                ) : null}
              </div>
            </section>
          </>
        )}

        {view === "triage" && (
          <>
            <section className="metrics" aria-label="Risk overview">
              <div className="stat stat-total">
                <span className="statValue">{total}</span>
                <span className="statLabel">Questions</span>
              </div>
              <div className="stat stat-guard">
                <span className="statValue">{blocked}</span>
                <span className="statLabel">Guarded</span>
              </div>
              <div className="stat stat-high">
                <span className="statValue">{highRisk}</span>
                <span className="statLabel">High risk</span>
              </div>
              <div className="stat stat-crit">
                <span className="statValue">{criticalRisk}</span>
                <span className="statLabel">Critical</span>
              </div>
            </section>

            <section className="queueWide" aria-label="Question queue">
              <div className="sectionTitle">
                <h2>Question Queue</h2>
                <span>{total} items · sorted by risk</span>
              </div>
              <div className="questionList">
                {questions.map((question) => (
                  <QueueRow
                    key={question.question_id}
                    question={question}
                    selected={question.question_id === selected.question_id}
                    onClick={() => openReview(question.question_id)}
                  />
                ))}
              </div>
            </section>
          </>
        )}

        {view === "review" && !selected && (
          <p className="intakeEmpty">No question selected — upload a questionnaire and pick a question to review.</p>
        )}
        {view === "review" && selected && (
          <section className="reviewLayout" aria-label="Question review">
            <div className="queueRail">
              <span className="railHead">Queue · {total}</span>
              {questions.map((question) => (
                <QueueRow
                  key={question.question_id}
                  question={question}
                  selected={question.question_id === selected.question_id}
                  compact
                  onClick={() => {
                    setSelectedId(question.question_id);
                    setSubTab("agents");
                  }}
                />
              ))}
            </div>

            <div className="reviewDetail">
              <article className={`reviewPanel answerState answer-${stateInfo?.kind}`}>
                <span className="answerIcon" aria-hidden>
                  <Icon name={stateInfo?.icon ?? "alert"} size={20} />
                </span>
                <div>
                  <span className="answerStateLabel">{stateInfo?.label}</span>
                  <p>{stateInfo?.detail}</p>
                </div>
              </article>

              <article className="reviewPanel">
                <h3>Buyer Question</h3>
                <p className="buyerQ">{selected.raw_question}</p>
              </article>

              <nav className="subTabs" aria-label="Review sections">
                {subTabs.map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    className={`subTab${subTab === tab.id ? " subTabActive" : ""}`}
                    onClick={() => setSubTab(tab.id)}
                    aria-current={subTab === tab.id}
                  >
                    <Icon name={tab.icon} size={15} />
                    {tab.label}
                    {tab.count !== undefined && tab.count > 0 && <span className="count">{tab.count}</span>}
                  </button>
                ))}
              </nav>

              {subTab === "agents" && (
                <article className="reviewPanel">
                  <h3>
                    <Icon name="agents" size={15} /> Agent Timeline
                  </h3>
                  {selected.opinions.length > 0 ? (
                    <ul className="timeline">
                      {selected.opinions.map((opinion) => (
                        <OpinionCard key={opinion.agent_name} opinion={opinion} />
                      ))}
                    </ul>
                  ) : (
                    <p>No agent opinions yet for this question.</p>
                  )}
                </article>
              )}

              {subTab === "evidence" && (
                <article className="reviewPanel">
                  <h3>
                    <Icon name="evidence" size={15} /> Evidence &amp; Citations{" "}
                    <span className="countPill">{evidence.length}</span>
                  </h3>
                  {evidence.length > 0 ? (
                    <ul className="evidenceList">
                      {evidence.map((item) => (
                        <li key={item.chunk_id} className="evidenceItem">
                          <div className="evidenceHead">
                            <span className="evidenceDoc">{item.document_name}</span>
                            <span className="evidenceConf">{confidencePct(item.confidence)}</span>
                          </div>
                          <p className="evidenceQuote">{item.quote}</p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>No supporting evidence retrieved — any claim here is unsupported.</p>
                  )}
                </article>
              )}

              {subTab === "policy" && <PolicyDecisionPanel question={selected} />}
              {subTab === "adversarial" && <AdversarialReviewPanel question={selected} />}
              {subTab === "band" && <BandTimeline question={selected} />}
              {subTab === "liveroom" && (
                <LiveRoomPanel
                  key={selected.question_id}
                  questionId={selected.question_id}
                  rfpId={live.rfp_id}
                  publicBackendUrl={publicBackendUrl}
                  onDecide={decide}
                  recommended={recommendedAnswer(selected)}
                  initialStatus={selected.status}
                />
              )}

              {subTab !== "liveroom" && (
                <p className="gateHint">
                  Open the <strong>Live Room</strong> tab to comment, @mention agents, and record the
                  human-gate decision (approve / escalate / reject).
                </p>
              )}
            </div>
          </section>
        )}

        {view === "bandroom" && <BandRoom events={bandEvents} report={bandReport} />}
        {view === "risk" && <RiskDashboard state={live} />}
        {view === "ledger" && <PromiseLedger state={live} />}
        {view === "audit" && (
          <section className="auditPanel" aria-label="Audit trail">
            <div className="sectionTitle">
              <h2>Audit Trail</h2>
              <span>{live.audit_trail.length} events · hashed &amp; timestamped</span>
            </div>
            {live.audit_trail.length === 0 ? (
              <p className="intakeEmpty">
                No audit events yet — they accrue as the agents deliberate and answers finalize.
              </p>
            ) : (
              <ul className="auditList">
                {[...live.audit_trail].reverse().map((event) => (
                  <li key={event.event_id} className={`auditRow audit-${auditKind(event.action)}`}>
                    <span className="auditDot" aria-hidden />
                    <div className="auditBody">
                      <div className="auditHead">
                        <span className="auditActor">{event.actor.replaceAll("_", " ")}</span>
                        <span className="auditAction">{event.action.replaceAll("_", " ")}</span>
                        {event.question_id ? <span className="auditQ">{event.question_id}</span> : null}
                        <span className="auditTime" suppressHydrationWarning>
                          {eventTime(event.timestamp)}
                        </span>
                      </div>
                      {event.summary ? <p className="auditSummary">{event.summary}</p> : null}
                      <code className="auditHash" title="payload hash (integrity)">
                        {event.payload_hash.slice(0, 16)}
                      </code>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
        {view === "exports" && <ExportBar state={live} />}
      </div>
    </div>
  );
}
