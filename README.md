# BandGate

> **The multi-agent promise gate for cybersecurity and government RFPs.**

BandGate stops cybersecurity vendors from accidentally making unsupported, unsafe, or
contractually risky promises in government RFPs. Sales, Security, Legal, Product, Compliance,
and Delivery agents collaborate **before** an answer leaves the company. The system drafts
answers, checks every material claim against approved evidence or policy, blocks unsafe
language, red-teams the result for hallucination and prompt injection, escalates risky answers
to a human, and exports a **Promise Ledger** so delivery teams inherit every commitment.

> The RFP is only the container. The real product is **commitment control**.

- **Hackathon:** Band of Agents Hackathon
- **Track:** Track 1 — Internal Enterprise Workflows
- **Stack:** Python (FastAPI) backend · Next.js frontend · Docker Compose
- **Required visible integrations:** Band · Featherless · AI/ML API

See [PLAN.md](PLAN.md) for the full product spec and day-by-day build plan.

---

## Team

- **Ishita Bhattacharyya**
- **Soham Das**

---

## The problem

Enterprise RFPs and security questionnaires are not paperwork. **They are promises.** One
unsupported answer can silently become an SLA, a privacy obligation, a security disclosure, or
a delivery commitment the company cannot honor.

Cybersecurity and public-sector RFPs are the sharpest version of this problem:

- Vendors receive high-volume security questionnaires with rich, conflicting evidence (SOC 2,
  ISO 27001, FedRAMP, GDPR, HIPAA, PCI DSS, encryption, incident response, subprocessors, data
  residency).
- The conflicts are real and demo-friendly:
  - Sales wants to say **yes** to 99.99% uptime.
  - Legal blocks uncapped SLA or liability language.
  - Security refuses to share pentest reports without an NDA.
  - Compliance prevents FedRAMP overclaims.
- Government buyers demand auditability, approved wording, and evidence-backed answers.

Generic RFP tools are weakest exactly where it matters most: when answers must be
**policy-enforced and citation-gated**.

---

## What BandGate is (and is not)

BandGate is a Band-visible internal workflow for risky RFP commitments. It is a policy-aware
review system that drafts an answer, verifies it against approved evidence and policy, blocks or
rewrites unsafe language, escalates anything risky to a human, and records the whole trail. In
short, it is a human-approved promise gate for cybersecurity and government sales.

It is not a generic RFP response engine, and it does not replace Legal, Security, or Compliance.
It cannot answer any RFP on its own, and it never approves contractual language by itself — a
human always stays in the loop for risky commitments.

---

## How it works

```mermaid
flowchart TD
    RFP["📄 Government RFP / Security Questionnaire"] --> INTAKE

    subgraph INGEST [" "]
        INTAKE["🛡️ RFP Intake Agent<br/><i>prompt-injection scan on untrusted text</i>"]
        STATE[("🗂️ Canonical local state<br/>output/state.json")]
        INTAKE --> STATE
    end

    STATE --> BAND["📡 Band Room · visible event stream"]

    subgraph AGENTS ["Agent collaboration"]
        SALES["💬 Sales Engineer<br/><i>optimistic draft</i>"]
        SEC["🔐 Security &amp; Compliance RAG<br/><i>evidence + citations</i>"]
        PROD["🧩 Product Capability<br/><i>GA vs roadmap vs scoping</i>"]
        LEGAL["⚖️ Legal / Commitment Guard<br/><i>what we may promise</i>"]
        ADV["🚨 Featherless Adversarial Review<br/><i>red team + hallucination check</i>"]
    end

    STATE --> SALES & SEC & PROD & LEGAL & ADV
    SALES & SEC & PROD & LEGAL & ADV --> ORCH["🔁 Workflow Orchestrator"]
    ORCH --> HUMAN{"🙋 Human Approval Gate"}
    HUMAN --> OUT["✅ Final Response · Audit Trail · Promise Ledger"]
```

The flow per question: **draft → retrieve evidence → policy review → adversarial review →
human review → approved → finalized.** A claim only survives into the final answer if it is
supported by approved evidence or by the commitment policy.

```mermaid
stateDiagram-v2
    direction LR
    [*] --> open
    open --> drafting
    drafting --> evidence_review
    evidence_review --> policy_review
    policy_review --> adversarial_review
    adversarial_review --> human_review
    human_review --> approved
    approved --> finalized
    finalized --> [*]
```

---

## The agents

Six logical agents plus one human gate. Some are implemented as deterministic backend functions
first (reliable for the demo), then upgraded to model calls where they add value.

| Agent | Role |
|---|---|
| **RFP Intake** | Parses CSV/PDF-like data into structured questions; classifies category; tags risk; assigns agents; **scans raw RFP text for prompt injection** (treats buyer content as untrusted). |
| **Sales Engineer** | Drafts buyer-friendly, optimistic answers. May include assumptions. Never finalizes commitments. |
| **Security & Compliance RAG** | Answers only from approved security/compliance evidence (SOC 2, ISO 27001, FedRAMP, encryption, incident response, access control, vuln management, retention, subprocessors). Every answer carries citations or is marked unsupported. |
| **Product Capability** | Distinguishes *generally available* vs *architecturally possible* vs *roadmap only* vs *requires custom scoping* vs *contractually approved*. |
| **Legal / Commitment Guard** | Enforces what the company may promise: SLA limits, liability caps, indemnity, DPA/residency language, NDA requirements, AI-training commitments, and human-approval routing. Deterministic rules with an opt-in provider path. |
| **Featherless Adversarial Reviewer** | Independent red team: prompt-injection detection, unsupported-claim detection, cross-answer contradiction detection, sensitive-disclosure detection, hallucination risk scoring. **The model that drafts the answer does not approve itself.** |
| **Human Approval Gate** | Required for high-risk commitments. Approve · approve with edits · escalate to Legal/Security · mark unsupported · reject. Human approval is a feature, not a weakness. |

---

## Policy and hallucination enforcement

### The hard rule

> **No final answer may contain a material claim unless it is supported by approved evidence
> or the commitment policy.**

If a claim is unsupported, BandGate blocks it, rewrites it to approved language, or escalates it
to a human.

### Claim support levels

| Level | Meaning |
|---|---|
| `supported_by_evidence` | Final answer may include the claim **with citation**. |
| `supported_by_policy` | Final answer may include approved policy wording. |
| `unsupported` | Block or escalate. |
| `contradicted_by_policy` | Block and rewrite. |
| `requires_human_approval` | Hold finalization until approved. |

### Deterministic conflict rules

Checked **before** relying on any LLM reasoning (see `backend/core/conflict.py`):

- SLA above the policy max without approval **blocks** finalization.
- `"FedRAMP authorized"` **blocks** unless policy says authorized.
- `"EU-only"` **blocks** when operational telemetry may be processed globally.
- Customer-data-training claims **block** when policy forbids them.
- Sensitive artifacts (SOC 2 report, pentest report, architecture diagram) **escalate** when an
  NDA is required.
- Buyer instructions to "ignore policy" are **prompt injection** and are ignored as untrusted
  input (see `backend/core/injection.py`).

### Commitment policy

The single source of truth for what the company may promise lives in
[`knowledge_base/policies/commitment_policy.yaml`](knowledge_base/policies/commitment_policy.yaml)
— SLA limits, privacy/residency stance, security-artifact NDA requirements, compliance status,
liability caps, and implementation timelines.

---

## Architecture

```mermaid
flowchart LR
    USER([👤 Reviewer]) -->|browser| FE

    subgraph DOCKER ["🐳 Docker Compose"]
        direction TB
        FE["🖥️ Frontend<br/>Next.js · :3000<br/><i>queue · timeline · approvals · ledger</i>"]
        BE["⚙️ Backend<br/>FastAPI · :8000<br/><i>state · RAG · policy · orchestration · exports</i>"]
        FE -->|GET /state| BE
    end

    BE --> KB[("📚 Knowledge Base<br/>markdown + commitment_policy.yaml")]
    BE --> OUT[("🗂️ output/*.json + *.md<br/>canonical state · audit · ledger")]

    BE -.->|visible events| BAND["📡 Band"]
    BE -.->|adversarial review| FEATHER["🚨 Featherless"]
    BE -.->|structured intake / draft / policy| AIML["🧠 AI/ML API"]

    classDef provider stroke-dasharray: 5 5;
    class BAND,FEATHER,AIML provider;
```

Solid arrows are the canonical local path that always works; dashed arrows are the external
provider integrations, each with a mocked fallback so a flaky API never breaks the demo.

---

## Tech stack

- **Backend:** Python 3.12, FastAPI, Uvicorn, Pydantic v2, PyYAML, pytest.
- **Frontend:** Next.js 16 (App Router, React 19, standalone output), TypeScript.
- **Infra:** Docker + Docker Compose.
- **Providers:** Band (visible agent collaboration), Featherless (adversarial review), AI/ML API
  (structured intake/draft/policy).

---

## Provider integrations

All three required integrations are designed to be **visible** in the demo while keeping local
state canonical, so a flaky API never breaks the run. Configure keys in `.env`:

| Variable | Used by | Purpose |
|---|---|---|
| `FEATHERLESS_API_KEY` | Adversarial reviewer | Independent red-team / hallucination scoring. |
| `FEATHERLESS_BASE_URL` | Adversarial reviewer | OpenAI-compatible Featherless endpoint; default `https://api.featherless.ai/v1`. |
| `FEATHERLESS_MODEL` | Adversarial reviewer | Featherless model name; default `Qwen/Qwen2.5-7B-Instruct`. |
| `AIML_API_KEY` | Intake + drafting + policy | Structured extraction and structured policy decisions, currently disabled by default. |
| `AIML_ENABLED` | Intake + drafting + policy | Must be `true` before AI/ML API calls are allowed; keep `false` until credits are available. |
| `AIML_BASE_URL` | Intake + drafting + policy | OpenAI-compatible AI/ML endpoint; default `https://api.aimlapi.com/v1`. |
| `AIML_MODEL` | Intake + drafting + policy | Low-cost default from AI/ML quickstart: `google/gemma-3-4b-it`. |
| `AIML_NORMALIZE_LIVE_LIMIT` | Intake | Max live AI/ML normalization calls per process; default `2`. |
| `AIML_SALES_LIVE_LIMIT` | Sales draft | Max live AI/ML sales-draft calls per process; default `2`. |
| `AIML_DRIFT_LIVE_LIMIT` | Drift control | Max live AI/ML drift-classification calls per process; default `6`. |
| `AIML_DRIFT_ENABLE_LIVE` | Drift control | If `true`, use AI/ML to enrich deterministic drift findings; default `false` for fast recording. |
| `AIML_DRIFT_SCAN_ALL` | Drift control | If `true`, ask AI/ML to review every room message; default `false` for faster demos. |
| `AIML_INTAKE_RISK_LIVE_LIMIT` | Intake | Max live AI/ML risk-enrichment calls per process; default `6`. |
| `AIML_REPORT_LIVE_LIMIT` | Demo report | Max live AI/ML chat-report summary calls per process; default `2`. |
| `FEATHERLESS_REVIEW_LIVE_LIMIT` | Adversarial reviewer | Max live Featherless red-team calls per process; default `3`. |
| `BAND_MODE` | Band client | `mock`, `lite`, or `live`; use `lite` while SDK/API quota is constrained. |
| `FEATHERLESS_MODE` | Adversarial reviewer | `mock`, `lite`, or `live`; use `lite` for the free trial tier. |
| `AIML_MODE` | Intake + drafting + policy | `mock`, `lite`, or `live`; use `lite` for the free tier. |
| `BAND_REST_URL` | Band SDK | REST base URL, default `https://app.band.ai/`. |
| `BAND_WS_URL` | Band SDK | WebSocket URL, default `wss://app.band.ai/api/v1/socket/websocket`. |
| `BAND_DEFAULT_ROOM_ID` | Band SDK | Optional existing room ID for demo routing. |
| `DEMO_MODE` | All providers | `mock` runs fully offline with deterministic fallbacks; set to live mode to exercise real provider calls. |

> AI/ML is disabled unless `AIML_ENABLED=true`. A key in `.env` is not enough to trigger calls.

For sparse live testing, set only the provider you are actively demonstrating to `live`. Live
calls are capped by the per-task limit env vars above, and every provider call falls back to
deterministic local guardrails if quota, rate limits, or JSON parsing fail.

Run a one-shot provider smoke test before the full demo:

```bash
PYTHONPATH=backend python backend/scripts/probe_providers.py
```

Run the harder live-pressure suite when you want judge-visible `AI/ML` plus `Featherless`
usage on tougher buyer traps:

```bash
PYTHONPATH=backend python backend/scripts/run_hardening_suite.py
```

### Band SDK setup

Band uses the `band-sdk` package and the `band` Python module. The SDK connects Remote
Agents to Band over REST + WebSocket. Each running agent needs credentials from the Band
platform:

1. In Band, create one **Remote Agent** for each BandGate role you want visible: Intake, Sales,
   Security, Product, Legal Guard, and Adversarial Reviewer.
2. Copy each Remote Agent's **Agent UUID** and one-time **API key** into `agent_config.yaml`.
   Start from `agent_config.yaml.example`; do not commit the real file.
3. Rooms are for collaboration and routing. A room does not issue every agent's credentials;
   each Remote Agent has its own UUID/API key and joins or is added to rooms through the SDK's
   room/participant tools.
4. The SDK exposes tools such as `band_send_message`, `band_send_event`,
   `band_add_participant`, `band_get_participants`, and `band_create_chatroom`.

The backend `BandClient` adapter records the same event payloads in `mock`/`lite` mode. Live
mode should run the six Remote Agents with `band-sdk[langgraph]` once `agent_config.yaml` and an
approved LLM adapter are filled. The official SDK docs describe `Agent.create(...)` plus
`await agent.run()` as the point where the WebSocket subscriptions stay active.

Band SDK v1.0.0 removed the old `thenvoi-sdk` / `thenvoi.*` import path. BandGate now documents
`BAND_REST_URL` and `BAND_WS_URL` as the canonical env vars, while still accepting the legacy
`THENVOI_*` names as compatibility fallbacks so older local `.env` files keep working.

---

## Getting started

**Prerequisites:** Docker and Docker Compose.

```bash
# 1. Configure environment (provider keys optional in mock mode)
cp .env.example .env

# 2. Build and start backend + frontend
docker compose up -d --build
```

Then open:

- **Frontend dashboard:** http://localhost:3000
- **Backend health:** http://localhost:8000/health
- **Backend state (JSON):** http://localhost:8000/state

Run the demo pipeline and tests inside the backend container:

```bash
# Process the questionnaire and write output/*.json + output/final_response.md
docker compose run --rm backend python run_demo.py

# Run backend tests
docker compose run --rm backend pytest

# Validate local Band agent credentials without making live WebSocket calls
docker compose run --rm -v ./agent_config.yaml:/app/agent_config.yaml:ro backend python scripts/verify_band_agents.py

# Sparse provider smoke test
docker compose run --rm backend python scripts/probe_providers.py

# Generate the six-agent Band collaboration transcript and chat report
docker compose run --rm backend python scripts/run_band_collaboration.py

# Pressure-test harder cybersecurity traps with AI/ML + Featherless
docker compose run --rm backend python scripts/run_hardening_suite.py

# Fast deterministic report for recording rehearsals
docker compose run --rm -e BAND_COLLAB_SALES_LIMIT=0 -e BAND_COLLAB_INTAKE_RISK_LIMIT=0 -e BAND_COLLAB_REPORT_LIMIT=0 backend python scripts/run_band_collaboration.py

# Optional: keep the Band lite/mock event stream service running
docker compose --profile band up -d band-service
```

---

## Local development without Docker

Useful for fast iteration. Relative paths (`data/`, `knowledge_base/`, `output/`) resolve from
the **repository root**, so always run backend commands from the repo root.

### Backend

```bash
# From repo root
python3 -m venv backend/.venv
backend/.venv/bin/pip install -e "backend[dev]"

# Run the demo pipeline
PYTHONPATH=backend backend/.venv/bin/python backend/run_demo.py

# Run the API (cwd must be repo root so data/ and knowledge_base/ resolve)
backend/.venv/bin/uvicorn app:app --app-dir backend --reload

# Run tests (from backend/ so pytest picks up pyproject config)
cd backend && .venv/bin/python -m pytest -q
```

### Frontend

```bash
cd frontend
npm install

# The UI falls back to lib/mockState.ts when no backend is reachable, so it
# renders standalone. Point it at the backend with BACKEND_URL when available.
BACKEND_URL=http://localhost:8000 npm run dev

# Type-check / production build
npx tsc --noEmit
npm run build
```

---

## API reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe — `{"status": "ok", "service": "bandgate-backend"}`. |
| `GET` | `/state` | Full `BandGateState` as JSON (built from the sample questionnaire). |
| `GET` | `/providers` | Current provider modes and whether each key/package is configured. |
| `GET` | `/band/events` | Last 100 recorded Band event payloads from mock/lite/live adapter flow. |
| `GET` | `/exports/final-response` | Final RFP response as Markdown. |
| `GET` | `/exports/audit-trail` | Audit trail records as JSON. |
| `GET` | `/exports/promise-ledger` | Promise Ledger records as JSON. |
| `GET` | `/exports/band-chat-report` | Generated six-agent Band collaboration report as Markdown. |
| `GET` | `/exports/hardening-report` | Generated hardening stress-test report as Markdown. |

The frontend's `page.tsx` reads `${BACKEND_URL}/state` and gracefully falls back to
`lib/mockState.ts` if the backend is unreachable.

---

## Testing

```bash
# Docker
docker compose run backend pytest

# Local
cd backend && .venv/bin/python -m pytest -q
```

Current coverage:

- **Conflict rules** (`test_conflict.py`) — SLA overcommitment, FedRAMP overclaim, EU-only
  residency, and prompt injection are correctly flagged.
- **Band client** (`test_band_client.py`) — mock/lite Band event payloads are recorded without
  exposing credentials or making platform calls.
- **Citation gate** (`test_citation_gate.py`) — unsupported evidence-backed claims are downgraded
  before they can appear in a final answer.
- **Exports** (`test_exports.py`) — final Markdown export, Promise Ledger records, and export
  API routes stay consistent.
- **Orchestrator** (`test_orchestrator.py`) — the demo pipeline keeps 40 questions, finalizes
  hero questions, writes policy/evidence-backed answers, emits audit events, and creates Promise
  Ledger entries.

`run_demo.py` writes:

- `output/state.json`
- `output/audit_trail.json`
- `output/promise_ledger.json`
- `output/final_response.md`
- `output/band_collaboration_transcript.json`
- `output/band_chat_report.md`
- `output/hardening_results.json`
- `output/hardening_report.md`

## Demo runbook

For the most reliable final demo:

1. Start the stack: `docker compose up -d --build`
2. Regenerate canonical output: `docker compose run --rm backend python run_demo.py`
3. Generate the six-agent collaboration report: `docker compose run --rm backend python scripts/run_band_collaboration.py`
4. Verify providers when live mode is enabled: `docker compose run --rm backend python scripts/probe_providers.py`
5. Open the dashboard at `http://localhost:3000`
6. Walk the SLA conflict, prompt-injection example, drift control panel, final export, and Promise Ledger panels

For a one-command freeze check before recording or submitting:

```bash
python backend/scripts/final_demo_check.py
```

## Repo note

GitHub is redirecting pushes from `tosoham/Band-Hackathon` to `tosoham/BandGate`. Updating the
`origin` URL is recommended when you have a minute:

```bash
git remote set-url origin git@github.com:tosoham/BandGate.git
```

---

## Knowledge base

A fictional but internally consistent corpus for **SentinelAI Security Platform**. Each document
includes approved wording, forbidden wording, conditions/exceptions, and an owning department.

RAG is intentionally simple and reliable:

```text
load markdown → chunk by heading → embed → retrieve top_k=4 → generate structured answer → attach citations
```

```text
company/   company_profile.md · approved_answer_library.md
security/  soc2_summary.md · iso27001_controls.md · encryption_policy.md
           incident_response_policy.md · vulnerability_management.md
           access_control_policy.md · fedramp_status.md
privacy/   dpa_summary.md · data_residency.md · subprocessors.md
           data_retention.md · ai_data_usage.md
product/   product_capabilities.md · ha_architecture.md · integrations.md
           implementation_timeline.md
legal/     msa_summary.md · sla_policy.md · liability_policy.md · nda_artifact_policy.md
policies/  commitment_policy.yaml
```

---

*Built for the Band of Agents Hackathon — Track 1: Internal Enterprise Workflows.*
