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

export default async function AuditPage() {
  const events = await fetchAudit();
  const recent = events.slice(-200).reverse();

  return (
    <>
      <main className="appShell">
        <header className="appHeader">
          <div>
            <p className="eyebrow">Audit Trail</p>
            <h1>{events.length} events</h1>
            <p className="subtitle">
              Every agent opinion, policy check, adversarial finding, and human decision lands here with a
              payload hash for tamper detection.
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
