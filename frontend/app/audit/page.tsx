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
        <ol className="auditList">
          {recent.map((event) => (
            <li key={event.event_id}>
              <header>
                <strong>{event.actor.replaceAll("_", " ")}</strong>
                <span>{event.action.replaceAll("_", " ")}</span>
                <time>{new Date(event.timestamp).toLocaleString()}</time>
              </header>
              <p>{event.summary}</p>
              <small>
                {event.question_id ? `${event.question_id} · ` : ""}hash:{" "}
                <code>{event.payload_hash.slice(0, 16)}…</code>
              </small>
            </li>
          ))}
          {recent.length === 0 ? <li className="emptyState">No audit events yet.</li> : null}
        </ol>
      </main>
    </>
  );
}
