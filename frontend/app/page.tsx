import { mockState } from "../lib/mockState";
import type { BandGateState, RFPQuestionState } from "../lib/types";

async function getState(): Promise<BandGateState> {
  const baseUrl = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_BACKEND_URL;

  if (!baseUrl) {
    return mockState;
  }

  try {
    const response = await fetch(`${baseUrl}/state`, { cache: "no-store" });
    if (!response.ok) {
      return mockState;
    }
    return (await response.json()) as BandGateState;
  } catch {
    return mockState;
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

export default async function Home() {
  const state = await getState();
  const questions = Object.values(state.questions);
  const highRisk = questions.filter((question) => question.risk_level === "high").length;
  const criticalRisk = questions.filter((question) => question.risk_level === "critical").length;
  const blocked = questions.filter((question) => question.conflict_detected).length;
  const selected = questions.find((question) => question.risk_tags.includes("sla_overcommitment")) ?? questions[0];

  return (
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
          <span className="metricValue">{blocked}</span>
          <span className="metricLabel">Guarded</span>
        </div>
        <div>
          <span className="metricValue">{highRisk}</span>
          <span className="metricLabel">High risk</span>
        </div>
        <div>
          <span className="metricValue">{criticalRisk}</span>
          <span className="metricLabel">Critical</span>
        </div>
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
                </div>
                <div className="rowBadges">
                  <span className={riskClass(question.risk_level)}>{question.risk_level}</span>
                  <span className="status">{statusLabel(question)}</span>
                </div>
              </article>
            ))}
          </div>
        </div>

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
              {selected.assigned_agents.map((agent) => (
                <li key={agent}>
                  <span>{agent.replaceAll("_", " ")}</span>
                  <p>{agent === "legal_commitment_guard" ? "Policy review required before final answer." : "Assigned for Day 1 intake review."}</p>
                </li>
              ))}
            </ol>
          </article>

          <article className="reviewPanel">
            <h3>Policy Decision</h3>
            <p>{selected.conflict_summary}</p>
            <div className="tagLine">
              {selected.risk_tags.map((tag) => (
                <span key={tag}>{tag.replaceAll("_", " ")}</span>
              ))}
            </div>
          </article>

          <article className="reviewPanel">
            <h3>Evidence</h3>
            <p>SLA, FedRAMP, data residency, artifact sharing, and AI data usage claims must resolve against approved corpus entries before finalization.</p>
          </article>
        </div>
      </section>
    </main>
  );
}
