import Link from "next/link";

import { NavShell } from "../../components/NavShell";
import { fetchRfpList } from "../../lib/api";
import type { RfpQuestionSummary } from "../../lib/types";

function riskClass(risk: string) {
  return `risk risk-${risk}`;
}

export default async function IntakePage() {
  const data = await fetchRfpList();
  const grouped = groupByCategory(data?.questions ?? []);
  const totalRisk = countRisk(data?.questions ?? []);

  return (
    <>
      <NavShell active="/intake" />
      <main className="appShell">
        <header className="appHeader">
          <div>
            <p className="eyebrow">RFP Intake</p>
            <h1>{data?.rfp_id ?? "RFP-GOV-001"} · {data?.buyer_name ?? "Public Sector Buyer"}</h1>
            <p className="subtitle">
              Vendor: {data?.vendor_name ?? "SentinelAI Security Platform"} · Policy version {data?.policy_version}
            </p>
          </div>
          <div className="metaPills">
            <span>{data?.question_count ?? 0} questions</span>
            <span>{totalRisk.high} high</span>
            <span>{totalRisk.critical} critical</span>
          </div>
        </header>
        <section className="intakeGroups">
          {Object.entries(grouped).map(([category, items]) => (
            <article key={category} className="intakeGroup">
              <h2>{category}</h2>
              <ul>
                {items.map((question) => (
                  <li key={question.question_id}>
                    <Link href={`/review/${encodeURIComponent(question.question_id)}`} className="intakeRow">
                      <div>
                        <span className="questionId">{question.question_id}</span>
                        <h3>{question.raw_question}</h3>
                        <p>{question.conflict_summary ?? "Awaiting deliberation."}</p>
                      </div>
                      <span className={riskClass(question.risk_level)}>{question.risk_level}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </section>
      </main>
    </>
  );
}

function groupByCategory(questions: RfpQuestionSummary[]): Record<string, RfpQuestionSummary[]> {
  const groups: Record<string, RfpQuestionSummary[]> = {};
  for (const q of questions) {
    const cat = q.category[0] ?? "uncategorized";
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(q);
  }
  return groups;
}

function countRisk(questions: RfpQuestionSummary[]) {
  let high = 0;
  let critical = 0;
  for (const q of questions) {
    if (q.risk_level === "high") high += 1;
    if (q.risk_level === "critical") critical += 1;
  }
  return { high, critical };
}
