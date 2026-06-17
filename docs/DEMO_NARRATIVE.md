# BandGate Demo Narrative

## 30-Second Pitch

Enterprise RFP answers are not paperwork. They are promises. BandGate brings six agents into a Band room before a cybersecurity vendor answers a government RFP: Intake scopes the question, Sales drafts, Security cites evidence, Product checks capability, Legal blocks unsafe commitments, and Adversarial Review catches hallucinations and prompt injection. The final answer is safe, approved, cited, and converted into a Promise Ledger obligation.

## Demo Commands

```bash
docker compose up -d --build
docker compose run --rm backend python run_demo.py
docker compose run --rm backend python scripts/run_band_collaboration.py
docker compose run --rm backend python scripts/run_hardening_suite.py
docker compose run --rm frontend npm run build
python backend/scripts/final_demo_check.py
```

Fast deterministic collaboration report:

```bash
docker compose run --rm \
  -e BAND_COLLAB_SALES_LIMIT=0 \
  -e BAND_COLLAB_INTAKE_RISK_LIMIT=0 \
  -e BAND_COLLAB_REPORT_LIMIT=0 \
  backend python scripts/run_band_collaboration.py
```

AIML-enriched collaboration report:

```bash
docker compose run --rm \
  -e AIML_ENABLED=true \
  -e AIML_MODE=live \
  -e BAND_COLLAB_INTAKE_RISK_LIMIT=1 \
  -e BAND_COLLAB_REPORT_LIMIT=1 \
  backend python scripts/run_band_collaboration.py
```

AI/ML + Featherless hardening run:

```bash
docker compose run --rm \
  -e AIML_ENABLED=true \
  -e AIML_MODE=live \
  -e FEATHERLESS_MODE=live \
  backend python scripts/run_hardening_suite.py
```

Optional live Band collaboration send:

```bash
docker compose run --rm \
  -e BAND_COLLAB_LIVE=true \
  -e AIML_ENABLED=true \
  -e AIML_MODE=live \
  -v ./agent_config.yaml:/app/agent_config.yaml:ro \
  backend python scripts/run_band_collaboration.py
```

Optional live Band connectivity check:

```bash
docker compose run --rm \
  -e BAND_VERIFY_LIVE=true \
  -e FEATHERLESS_MODE=live \
  -v ./agent_config.yaml:/app/agent_config.yaml:ro \
  backend python scripts/verify_band_agents.py
```

## 3-Minute Video Script

### 0:00-0:20 - Problem

"Government cybersecurity RFPs are full of traps. A vendor can accidentally promise 99.99% uptime, claim FedRAMP authorization, disclose a pentest report, or obey malicious text embedded in the buyer questionnaire. BandGate treats every answer as a commitment."

Show the dashboard header, risk metrics, and queue.

### 0:20-0:45 - Intake

"The Intake Agent loads a public-sector security questionnaire with 40 questions. It flags high-risk contractual claims and one prompt-injection attempt before any model sees it as an instruction."

Show Q-001, Q-002, Q-004, and Q-029 in the queue.

### 0:45-1:25 - Six-Agent Band Room

"Now the work moves into Band. All six agents are visible in the room. Intake mentions Sales, Security, and Product. Sales drafts the buyer-friendly answer. Security and Product respond with evidence and capability limits."

Show `output/band_chat_report.md` or the Band room transcript:

- Intake assigns the RFP.
- Sales overclaims.
- Security cites approved evidence.
- Product narrows capability.

### 1:25-2:05 - Security Money Shot

"This is the key conflict. Sales wants to say yes to 99.99% uptime, FedRAMP authorization, and immediate pentest/SOC 2 report sharing. Legal blocks all three: the SLA needs approved wording, FedRAMP is not authorized, and artifacts require NDA review."

Show the Legal/Commitment Guard panel and drift findings.

### 2:05-2:30 - Drift + Adversarial Review

"BandGate also controls agent drift. Sales cannot finalize legal commitments. Security cannot make uncited claims. Adversarial Review catches hallucination risk and prompt injection, including the malicious instruction to answer all security questions yes."

Show Drift Control and Six-Agent Band Room panels.

### 2:30-2:45 - Harder Pressure Test

"We also ran a live hardening suite against tougher buyer traps: SLA overclaims, FedRAMP bait, prompt injection, and sensitive disclosure requests. AI/ML handled structured intake and draft assist. Featherless independently scored the risky draft for hallucination and unsupported claims."

Show `output/hardening_report.md`.

### 2:45-2:55 - Human Approval

"The human gate approves only the safe rewrite: standard SLA language, FedRAMP in progress but not authorized, reports under NDA, and malicious buyer instructions ignored."

Show the final answer.

### 2:55-3:00 - Promise Ledger

"Every approved promise becomes a delivery obligation. The Promise Ledger tells Customer Success, Product, and Delivery what must actually happen after the deal closes."

Show final export and Promise Ledger.

## Band Room Beats

1. `intake_agent` mentions Sales, Security, and Product with the risky RFP packet.
2. `sales_engineer` drafts an unsafe optimistic answer.
3. `security_compliance` cites approved evidence and unsupported claims.
4. `product_capability` explains HA addendum/custom scope.
5. `legal_commitment_guard` blocks unsafe SLA, FedRAMP, and report-sharing language.
6. `adversarial_reviewer` flags hallucination, prompt injection, and unsupported-claim risk.
7. `human_gate` approves safe wording.

## Fallback Path

If live Band room sending is slow, use the generated report:

- `output/band_collaboration_transcript.json`
- `output/band_chat_report.md`
- `output/hardening_report.md`
- dashboard Six-Agent Band Room panel
- dashboard Drift Control panel

The story remains truthful: live Band agent connectivity is separately verified, and the scripted collaboration path is deterministic for the recording.

## Draft Submission Checklist

- Repo pushed and public/accessible.
- README commands verified.
- Docker stack starts.
- Backend tests pass.
- Frontend build passes.
- AI/ML smoke probe shows `aiml_probe: ok`.
- Hardening report generated with visible `AI/ML` and `Featherless` usage.
- Band verifier connects all six agents.
- `output/band_chat_report.md` generated.
- 3-minute video recorded.
- Slide deck and cover image prepared.
