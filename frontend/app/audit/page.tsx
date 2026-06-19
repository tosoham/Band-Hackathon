import { backendUrl } from "../../lib/api";
import type { AuditEvent } from "../../lib/types";

async function fetchAudit(): Promise<AuditEvent[]> {
  const base = backendUrl();
  if (!base) return [];
  try {
    const res = await fetch(`${base}/exports/audit-trail`, { cache: "no-store" });
    if (!res.ok) return [];
    return (await res.json()) as AuditEvent[];
  } catch {
    return [];
  }
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
  if (a.includes("reject") || a.includes("escalat") || a.includes("block") || a.includes("violation") || a.includes("injection")) {
    return "alert";
  }
  if (a.includes("decision") || a.includes("human") || a.includes("gate")) return "decision";
  return "neutral";
}

function auditActionLabel(event: AuditEvent): string | null {
  const action = event.action.toLowerCase();
  const summary = event.summary.toLowerCase();
  const actor = event.actor.toLowerCase();

  if (action.includes("finalize")) return "Final answer locked";
  if (action.includes("ledger")) return "Promise ledger entry";
  if (action.includes("reject")) return "Rejection recorded";
  if (action.includes("escalat")) return "Escalation recorded";
  if (action.includes("approve") || summary.includes("approved")) return "Approval recorded";
  if (action.includes("decision") || action.includes("human") || action.includes("gate")) return "Human decision";
  if (action.includes("injection") || summary.includes("prompt injection")) return "Prompt injection finding";
  if (actor.includes("legal_commitment_guard")) return "Policy check";
  if (actor.includes("adversarial_reviewer")) return "Adversarial finding";
  if (action.includes("violation") || action.includes("block")) return "Policy finding";
  if (action.includes("round") || action.includes("opinion")) return null;
  return event.action.replaceAll("_", " ");
}

function auditDisplayEvents(events: AuditEvent[]): AuditEvent[] {
  const collapsed = new Map<string, AuditEvent>();

  for (const event of events) {
    const label = auditActionLabel(event);
    if (!label) continue;
    const key = [event.question_id ?? "global", event.actor, label, event.summary.trim().toLowerCase()].join("|");
    collapsed.set(key, { ...event, action: label });
  }

  return [...collapsed.values()].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

export default async function AuditPage() {
  const events = await fetchAudit();
  const recent = auditDisplayEvents(events).slice(0, 200);

  return (
    <>
      <main className="appShell">
        <header className="appHeader">
          <div>
            <p className="eyebrow">Audit Trail</p>
            <h1>{recent.length} events</h1>
            <p className="subtitle">
              Material findings, policy checks, human decisions, and finalization records with payload hashes
              for tamper detection.
            </p>
          </div>
        </header>
        <ol className="auditList auditListStandalone">
          {recent.map((event) => (
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
          {recent.length === 0 ? <li className="emptyState">No audit events yet.</li> : null}
        </ol>
      </main>
    </>
  );
}
