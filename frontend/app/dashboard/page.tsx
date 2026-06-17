import { mockState } from "../../lib/mockState";
import { NavShell } from "../../components/NavShell";
import type { BandEventRecord, BandGateState, ProviderStatus, RFPQuestionState } from "../../lib/types";

async function getState(): Promise<BandGateState> {
  const baseUrl = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_BACKEND_URL;
  if (!baseUrl) return mockState;
  try {
    const response = await fetch(`${baseUrl}/state`, { cache: "no-store" });
    if (!response.ok) return mockState;
    return (await response.json()) as BandGateState;
  } catch {
    return mockState;
  }
}

async function getProviders(): Promise<ProviderStatus | null> {
  const baseUrl = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_BACKEND_URL;
  if (!baseUrl) return null;
  try {
    const response = await fetch(`${baseUrl}/providers`, { cache: "no-store" });
    if (!response.ok) return null;
    return (await response.json()) as ProviderStatus;
  } catch {
    return null;
  }
}

async function getBandEvents(): Promise<BandEventRecord[]> {
  const baseUrl = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_BACKEND_URL;
  if (!baseUrl) return [];
  try {
    const response = await fetch(`${baseUrl}/band/events`, { cache: "no-store" });
    if (!response.ok) return [];
    return (await response.json()) as BandEventRecord[];
  } catch {
    return [];
  }
}

async function getBandChatReport(): Promise<string> {
  const baseUrl = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_BACKEND_URL;
  if (!baseUrl) return "";
  try {
    const response = await fetch(`${baseUrl}/exports/band-chat-report`, { cache: "no-store" });
    if (!response.ok) return "";
    return await response.text();
  } catch {
    return "";
  }
}

function riskClass(risk: string) {
  return `risk risk-${risk}`;
}

function statusLabel(question: RFPQuestionState) {
  if (question.risk_tags.includes("prompt_injection")) return "Attack detected";
  if (question.conflict_detected) return "Needs review";
  return "Open";
}

export default async function Dashboard() {
  const state = await getState();
  const providers = await getProviders();
  const bandEvents = await getBandEvents();
  const bandChatReport = await getBandChatReport();
  const questions = Object.values(state.questions);
  const highRisk = questions.filter((q) => q.risk_level === "high").length;
  const criticalRisk = questions.filter((q) => q.risk_level === "critical").length;
  const blocked = questions.filter((q) => q.conflict_detected).length;
  const finalized = questions.filter((q) => q.status === "finalized").length;
  const driftEvents = bandEvents.filter((e) => e.event_type === "drift_control_finding");
  const publicBackendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.BACKEND_URL ?? "";
  const reportPreview = bandChatReport.split("\n").slice(0, 22).join("\n");
  const selected =
    questions.find((q) => q.risk_tags.includes("sla_overcommitment")) ?? questions[0];

  return (
    <>
      <NavShell active="/dashboard" />
      <main>
        <header className="topbar">
          <div>
            <p className="eyebrow">Band of Agents Hackathon · Track 1</p>
            <h1>BandGate</h1>
          </div>
          <div className="meta">
            <span>{state.rfp_id}</span>
            <span>{state.buyer_name}</span>
          </div>
        </header>

        <section className="metrics" aria-label="Risk overview">
          <div>
            <span className="metricValue">{questions.length}</span>
            <span className="metricLabel">Questions</span>
          </div>
          <div>
            <span className="metricValue">{finalized}</span>
            <span className="metricLabel">Finalized</span>
          </div>
          <div>
            <span className="metricValue">{highRisk}</span>
            <span className="metricLabel">High risk</span>
          </div>
          <div>
            <span className="metricValue">{criticalRisk}</span>
            <span className="metricLabel">Critical</span>
          </div>
          <div>
            <span className="metricValue">{blocked}</span>
            <span className="metricLabel">Blocked</span>
          </div>
          <div>
            <span className="metricValue">{driftEvents.length}</span>
            <span className="metricLabel">Drift findings</span>
          </div>
        </section>

        <section className="providerStrip" aria-label="Provider modes">
          <span>Band: {providers?.band_mode ?? "mock"}</span>
          <span>
            AI/ML API:{" "}
            {providers?.aiml_enabled
              ? `${providers.aiml_mode} · ${providers.aiml_model}`
              : "disabled"}
          </span>
          <span>
            Featherless:{" "}
            {providers?.featherless_live_ready
              ? `${providers.featherless_mode} · ${providers.featherless_model}`
              : "lite"}
          </span>
          <span>Ledger: {state.promise_ledger.length} commitments</span>
          <span>Audit: {state.audit_trail.length} events</span>
          <span>
            Six-agent room:{" "}
            {bandEvents.some((e) => e.event_type === "collaboration_report") ? "scripted" : "pending"}
          </span>
        </section>

        <section className="workspace">
          <div className="queue" aria-label="Question queue">
            <div className="sectionTitle">
              <h2>Question Queue</h2>
              <span>{state.vendor_name}</span>
            </div>
            <div className="questionList">
              {questions.slice(0, 12).map((question) => (
                <article className="questionRow" key={question.question_id}>
                  <div>
                    <span className="questionId">{question.question_id}</span>
                    <h3>{question.raw_question}</h3>
                    <p>{question.conflict_summary}</p>
                    {question.final_answer ? <p className="answerPreview">{question.final_answer}</p> : null}
                  </div>
                  <div className="rowBadges">
                    <span className={riskClass(question.risk_level)}>{question.risk_level}</span>
                    <span className="status">{statusLabel(question)}</span>
                  </div>
                </article>
              ))}
            </div>
          </div>

          {selected ? (
            <div className="review" aria-label="Review detail">
              <div className="sectionTitle">
                <h2>{selected.question_id} Review</h2>
                <span className={riskClass(selected.risk_level)}>{selected.risk_level}</span>
              </div>

              <article className="reviewPanel">
                <h3>Buyer Question</h3>
                <p>{selected.raw_question}</p>
              </article>

              <article className="reviewPanel">
                <h3>Agent Timeline</h3>
                <ol className="timeline">
                  {selected.opinions.map((opinion) => (
                    <li key={opinion.agent_name}>
                      <span>{opinion.agent_name.replaceAll("_", " ")}</span>
                      <p>{opinion.answer}</p>
                      <small>
                        {opinion.provider} · {Math.round(opinion.confidence * 100)}% confidence
                      </small>
                    </li>
                  ))}
                </ol>
              </article>

              <article className="reviewPanel">
                <h3>Policy Decision</h3>
                <p>
                  {selected.opinions.find((o) => o.agent_name === "legal_commitment_guard")?.answer ??
                    selected.conflict_summary}
                </p>
                <div className="tagLine">
                  {selected.risk_tags.map((tag) => (
                    <span key={tag}>{tag.replaceAll("_", " ")}</span>
                  ))}
                </div>
              </article>

              <article className="reviewPanel">
                <h3>Evidence</h3>
                {selected.opinions.flatMap((o) => o.evidence).length ? (
                  <ul className="evidenceList">
                    {selected.opinions.flatMap((o) => o.evidence).map((evidence) => (
                      <li key={`${evidence.source_id}-${evidence.chunk_id}`}>
                        <strong>{evidence.document_name}</strong>
                        <p>{evidence.quote}</p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>No supporting evidence attached yet.</p>
                )}
              </article>

              <article className="reviewPanel">
                <h3>Final Answer</h3>
                <p>{selected.final_answer ?? "No final answer generated yet."}</p>
                {selected.approvals.length ? (
                  <p className="approval">{selected.approvals[0].decision.replaceAll("_", " ")}</p>
                ) : null}
              </article>

              <article className="reviewPanel">
                <h3>Six-Agent Band Room</h3>
                {bandEvents.length ? (
                  <ol className="timeline">
                    {bandEvents.slice(-8).map((event, index) => (
                      <li key={`${event.timestamp}-${index}`}>
                        <span>{event.event_type.replaceAll("_", " ")}</span>
                        <p>
                          {event.agent}: {event.summary}
                        </p>
                        <small>
                          {event.question_id ?? "global"} · {event.provider_mode}
                        </small>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p>No Band events recorded yet. Run the demo pipeline or reset the backend state.</p>
                )}
              </article>
            </div>
          ) : null}
        </section>

        <section className="reportGrid" aria-label="Band chat report and drift control">
          <article className="reviewPanel">
            <div className="sectionTitle">
              <h2>Drift Control</h2>
              <span>{driftEvents.length} findings</span>
            </div>
            {driftEvents.length ? (
              <ol className="timeline">
                {driftEvents.slice(-5).map((event, index) => (
                  <li key={`${event.timestamp}-drift-${index}`}>
                    <span>{event.agent.replaceAll("_", " ")}</span>
                    <p>{event.summary}</p>
                    <small>{event.risk_level ?? "high"} · human approval required</small>
                  </li>
                ))}
              </ol>
            ) : (
              <p>Run the six-agent collaboration script to generate drift findings.</p>
            )}
          </article>

          <article className="reviewPanel">
            <div className="sectionTitle">
              <h2>Band Chat Report</h2>
              {publicBackendUrl ? (
                <a className="exportLink" href={`${publicBackendUrl}/exports/band-chat-report`}>
                  Open report
                </a>
              ) : (
                <span>pending</span>
              )}
            </div>
            <pre className="reportPreview">
              {reportPreview || "Run python backend/scripts/run_band_collaboration.py to generate the report."}
            </pre>
          </article>
        </section>
      </main>
    </>
  );
}
