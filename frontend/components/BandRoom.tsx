import Icon, { type IconName } from "./Icon";
import type { BandEventRecord } from "../lib/types";

type EventMeta = { label: string; icon: IconName; kind: string };

// Maps Soham's backend event_type values onto the revamp's timeline vocabulary
// (the be-* node colors already defined for BandTimeline).
const EVENT_META: Record<string, EventMeta> = {
  assignment: { label: "Assignment", icon: "agents", kind: "assignment" },
  policy_blocked: { label: "Policy block", icon: "block", kind: "block" },
  adversarial_finding: { label: "Adversarial finding", icon: "shield", kind: "adversarial" },
  human_approval: { label: "Human gate", icon: "approve", kind: "approval" },
  drift_control_finding: { label: "Drift finding", icon: "alert", kind: "block" },
  collaboration_report: { label: "Collaboration report", icon: "review", kind: "final" },
};

function eventMeta(type: string): EventMeta {
  return EVENT_META[type] ?? { label: type.replaceAll("_", " "), icon: "band", kind: "output" };
}

function agentLabel(name: string) {
  return name.replaceAll("_", " ");
}

export default function BandRoom({ events, report }: { events: BandEventRecord[]; report: string }) {
  const drift = events.filter((event) => event.event_type === "drift_control_finding");
  const blocks = events.filter((event) => event.event_type === "policy_blocked");
  const agents = Array.from(new Set(events.map((event) => event.agent).filter(Boolean)));
  const backendUrl = (process.env.NEXT_PUBLIC_BACKEND_URL ?? "").replace(/\/+$/, "");
  const reportPreview = report ? report.split("\n").slice(0, 40).join("\n") : "";

  if (events.length === 0) {
    return (
      <section className="bandRoom" aria-label="Band Room">
        <article className="reviewPanel bandRoomEmpty">
          <Icon name="band" size={30} />
          <h3>No deliberation yet</h3>
          <p>
            Upload a questionnaire on the Intake tab to start the pipeline — the six agents&apos;
            live conversation will stream here.
          </p>
        </article>
      </section>
    );
  }

  return (
    <section className="bandRoom" aria-label="Band Room">
      <section className="metrics" aria-label="Band room metrics">
        <div className="stat stat-total">
          <span className="statValue">{events.length}</span>
          <span className="statLabel">Events</span>
        </div>
        <div className="stat stat-guard">
          <span className="statValue">{blocks.length}</span>
          <span className="statLabel">Policy blocks</span>
        </div>
        <div className="stat stat-high">
          <span className="statValue">{drift.length}</span>
          <span className="statLabel">Drift findings</span>
        </div>
        <div className="stat stat-crit">
          <span className="statValue">{agents.length}</span>
          <span className="statLabel">Agents</span>
        </div>
      </section>

      <article className="reviewPanel">
        <h3>
          <Icon name="agents" size={15} /> Agents in the room
        </h3>
        <div className="bandRoster">
          {agents.map((agent) => (
            <span key={agent} className="rosterChip">
              <span className="dot" />
              {agentLabel(agent)}
            </span>
          ))}
        </div>
      </article>

      {drift.length > 0 && (
        <article className="reviewPanel">
          <h3>
            <Icon name="alert" size={15} /> Drift Control <span className="countPill">{drift.length}</span>
          </h3>
          <p className="advTagline">AI/ML drift detections held for human approval before anything ships.</p>
          <ul className="advList">
            {drift.map((event, index) => (
              <li key={`${event.timestamp}-drift-${index}`} className="advItem adv-hallucination">
                <div className="advItemHead">
                  <span className="advCat">
                    <Icon name="alert" size={14} /> {agentLabel(event.agent)}
                  </span>
                  <span className={`risk risk-${event.risk_level ?? "high"}`}>{event.risk_level ?? "high"}</span>
                </div>
                <p className="advDetail">{event.summary}</p>
                {event.requires_human_approval && <span className="bandTag">human approval required</span>}
              </li>
            ))}
          </ul>
        </article>
      )}

      <article className="reviewPanel">
        <h3>
          <Icon name="band" size={15} /> Six-Agent Collaboration Stream{" "}
          <span className="countPill">{events.length}</span>
        </h3>
        <ul className="bandLog">
          {events.map((event, index) => {
            const meta = eventMeta(event.event_type);
            return (
              <li key={`${event.timestamp}-${index}`} className={`bandEvent be-${meta.kind}`}>
                <span className="bandNode" aria-hidden />
                <div className="bandBody">
                  <div className="bandHead">
                    <span className="bandTitle">
                      {meta.label} · {agentLabel(event.agent)}
                    </span>
                    <span className="bandTag">{event.question_id ?? "global"}</span>
                  </div>
                  <p className="bandDetail">{event.summary}</p>
                </div>
              </li>
            );
          })}
        </ul>
      </article>

      <article className="reviewPanel">
        <h3>
          <Icon name="export" size={15} /> Band Chat Report
        </h3>
        {reportPreview ? (
          <>
            <pre className="reportPreview">{reportPreview}</pre>
            {backendUrl && (
              <a className="reportLink" href={`${backendUrl}/exports/band-chat-report`} target="_blank" rel="noreferrer">
                <Icon name="export" size={15} /> Open full report
              </a>
            )}
          </>
        ) : (
          <p>The report builds automatically as questions are finalized.</p>
        )}
      </article>
    </section>
  );
}
