import Link from "next/link";

import LiveRoomPanel from "../../../components/LiveRoomPanel";
import RoomChatList, { type ChatItem } from "../../../components/RoomChatList";
import { fetchState } from "../../../lib/api";
import type { AgentOpinion } from "../../../lib/types";

function riskClass(risk: string) {
  return `risk risk-${risk}`;
}

const RISK_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

type Params = { questionId: string };

export default async function ReviewPage({ params }: { params: Promise<Params> }) {
  const { questionId } = await params;
  const state = await fetchState();
  const question = state?.questions?.[questionId];
  const publicBackendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "";

  if (!question) {
    return (
      <>
        <main className="appShell">
          <header className="appHeader">
            <h1>{questionId}</h1>
          </header>
          <p className="emptyState">
            Question not found. <Link href="/intake">Return to intake</Link>.
          </p>
        </main>
      </>
    );
  }

  const rfpId = state?.rfp_id ?? "";
  const chatItems: ChatItem[] = Object.values(state?.questions ?? {})
    .map((q) => ({
      id: q.question_id,
      question: q.raw_question,
      status: q.status,
      risk: q.risk_level,
      tags: q.risk_tags,
    }))
    .sort((a, b) => (RISK_ORDER[a.risk] ?? 9) - (RISK_ORDER[b.risk] ?? 9));

  return (
    <>
      <main className="appShell reviewShell">
        <header className="appHeader">
          <div>
            <p className="eyebrow">{rfpId} · Review workspace</p>
            <h1>{question.question_id}</h1>
            <p className="subtitle">{question.raw_question}</p>
          </div>
          <div className="metaPills">
            <span className={riskClass(question.risk_level)}>{question.risk_level}</span>
            <span>status: {question.status}</span>
            <span>{question.risk_tags.join(", ") || "no tags"}</span>
          </div>
        </header>

        <div className="roomLayout">
          <RoomChatList items={chatItems} activeId={question.question_id} />
          <section className="reviewLayout">
            <aside className="reviewAside">
            <article className="reviewPanel">
              <h3>Conflict</h3>
              <p>{question.conflict_summary ?? "No conflict yet."}</p>
            </article>
            <article className="reviewPanel">
              <h3>Final Answer</h3>
              <p>{question.final_answer ?? "Not finalized."}</p>
            </article>
            <article className="reviewPanel">
              <h3>Agent Opinions ({question.opinions.length})</h3>
              <ol className="opinionList">
                {question.opinions.map((opinion: AgentOpinion, index) => (
                  <li key={`${opinion.agent_name}-${index}`}>
                    <strong>{opinion.agent_name.replaceAll("_", " ")}</strong>
                    <p>{opinion.answer}</p>
                    <small>
                      {opinion.provider} · {Math.round(opinion.confidence * 100)}% confidence
                      {opinion.evidence.length
                        ? ` · ${opinion.evidence.length} citation${opinion.evidence.length === 1 ? "" : "s"}`
                        : ""}
                    </small>
                  </li>
                ))}
                {question.opinions.length === 0 ? <li>No opinions yet.</li> : null}
              </ol>
            </article>
            <article className="reviewPanel">
              <h3>Evidence</h3>
              <ul className="evidenceList">
                {question.opinions
                  .flatMap((opinion) => opinion.evidence)
                  .slice(0, 6)
                  .map((evidence) => (
                    <li key={`${evidence.source_id}-${evidence.chunk_id}`}>
                      <strong>{evidence.document_name}</strong>
                      <p>{evidence.quote}</p>
                    </li>
                  ))}
                {question.opinions.flatMap((opinion) => opinion.evidence).length === 0 ? (
                  <li>No supporting evidence yet.</li>
                ) : null}
              </ul>
            </article>
            <article className="reviewPanel">
              <h3>Approvals</h3>
              <ul>
                {question.approvals.map((approval, idx) => (
                  <li key={idx}>
                    <strong>{approval.decision.replaceAll("_", " ")}</strong> · {approval.approver_role}
                    {approval.comment ? <p>{approval.comment}</p> : null}
                  </li>
                ))}
                {question.approvals.length === 0 ? <li>No approvals yet.</li> : null}
              </ul>
            </article>
          </aside>
            <LiveRoomPanel
              questionId={question.question_id}
              rfpId={rfpId}
              publicBackendUrl={publicBackendUrl}
              initialStatus={question.status}
            />
          </section>
        </div>
      </main>
    </>
  );
}
