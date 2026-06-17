import { NavShell } from "../../components/NavShell";
import { backendUrl } from "../../lib/api";
import type { PromiseLedgerEntry } from "../../lib/types";

async function fetchLedger(): Promise<PromiseLedgerEntry[]> {
  const base = backendUrl();
  if (!base) return [];
  try {
    const res = await fetch(`${base}/exports/promise-ledger`, { cache: "no-store" });
    if (!res.ok) return [];
    return (await res.json()) as PromiseLedgerEntry[];
  } catch {
    return [];
  }
}

export default async function LedgerPage() {
  const ledger = await fetchLedger();

  return (
    <>
      <NavShell active="/ledger" />
      <main className="appShell">
        <header className="appHeader">
          <div>
            <p className="eyebrow">Promise Ledger</p>
            <h1>{ledger.length} commitments</h1>
            <p className="subtitle">
              Every approved RFP answer that creates a delivery obligation lands here. Delivery, Customer
              Success, Security, and Legal inherit ownership before contracting.
            </p>
          </div>
        </header>
        <table className="ledgerTable">
          <thead>
            <tr>
              <th>ID</th>
              <th>Commitment</th>
              <th>Owner</th>
              <th>Due stage</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {ledger.map((entry) => (
              <tr key={entry.commitment_id}>
                <td>{entry.commitment_id}</td>
                <td>
                  <strong>{entry.commitment_text}</strong>
                  <p>{entry.delivery_action}</p>
                </td>
                <td>{entry.owner_department}</td>
                <td>{entry.due_stage}</td>
                <td>{entry.source_question_id}</td>
              </tr>
            ))}
            {ledger.length === 0 ? (
              <tr>
                <td colSpan={5} className="emptyRow">
                  No commitments yet. Approve an RFP answer to populate the ledger.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </main>
    </>
  );
}
