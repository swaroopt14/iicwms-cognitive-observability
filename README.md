# IICWMS – Chronos AI: Cognitive Observability Platform

### Intelligent IT Compliance & Workflow Monitoring System | PS-08

> **10 Microservices | 9 Reasoning Agents | 40+ API Endpoints | 10 Dashboard Pages**

> *"If we can't explain why something matters, it doesn't matter."*

---

## Problem

IT teams lose **$1.2M/year** to alert fatigue, silent compliance violations, and reactive monitoring. Dashboards show *what* is broken — never *why* it happened or *what to do next*.

## Solution

**Chronos AI** is a **multi-agent cognitive observability system** that observes, reasons, and explains — producing **auditable, traceable, retryable, and explainable insights** with full evidence chains.

```
═══════════════════════════════════════════════════════════════════════════════
 OBSERVE (raw facts) → REASON (9 agents) → EXPLAIN (evidence-backed insights)
═══════════════════════════════════════════════════════════════════════════════
```

---

## Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    chronos-dashboard (frontend/)                        │
│            Next.js 16 │ React 19 │ Tailwind CSS 4 │ :3000             │
│     10 Pages: Overview │ Workflows │ Resources │ Compliance            │
│              Anomalies │ Causal │ Insights │ Ask AI │ Scenarios │ Risk │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ REST API (JSON)
┌──────────────────────────────┴──────────────────────────────────────────┐
│                    chronos-gateway (api/)                               │
│              FastAPI │ Uvicorn │ 40+ endpoints │ :8000                  │
└───┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬────────────────────┘
    │      │      │      │      │      │      │      │
    ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐
│simul-││obser-││reaso-││black-││expla-││risk- ││rag   ││graph │
│ator  ││ver   ││ning  ││board ││iner  ││engine││      ││      │
│      ││      ││(9 ag)││      ││      ││      ││      ││(Neo4j│
└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘
 SVC 1   SVC 2   SVC 3   SVC 4   SVC 5   SVC 6  SVC 7   SVC 8
```

---

## Service Registry

| # | Service | Directory | Technology | Description |
|---|---------|-----------|------------|-------------|
| 1 | **chronos-simulator** | `simulator/` | Python 3.10 | Probabilistic event/metric generation with emergent behavior |
| 2 | **chronos-observer** | `observation/` | Python 3.10 + JSONL | Append-only raw fact ingestion & windowed queries |
| 3 | **chronos-reasoning** | `agents/` | Python 3.10 (9 agents) | Multi-agent detection, compliance, risk, causal analysis |
| 4 | **chronos-blackboard** | `blackboard/` | Python 3.10 + JSONL | Shared reasoning state — inter-agent communication hub |
| 5 | **chronos-explainer** | `explanation/` | Python 3.10 + Gemini | 3-tier insight generation (Template → LLM → CrewAI) |
| 6 | **chronos-risk-engine** | `metrics/` | Python 3.10 | Composite risk index (0-100) with weighted scoring |
| 7 | **chronos-rag** | `rag/` | Python 3.10 | Reasoning-augmented query engine (7 query types) |
| 8 | **chronos-graph** | `graph/` | Python 3.10 + Neo4j | Graph database for causal knowledge (Round-2) |
| 9 | **chronos-gateway** | `api/` | FastAPI + Uvicorn | REST API gateway — 40+ endpoints, 12 route groups |
| 10 | **chronos-dashboard** | `frontend/` | Next.js 16 + React 19 | 10-page cognitive observability frontend |

> See [`SERVICES.md`](SERVICES.md) for full service architecture with data flow diagrams.

---

## Multi-Agent Reasoning (9 Agents)

| Agent | Type | Detects / Does |
|-------|------|----------------|
| **WorkflowAgent** | Detection | Delays, missing steps, sequence violations |
| **ResourceAgent** | Detection | Sustained CPU/memory spikes, network drift |
| **ComplianceAgent** | Detection | Silent policy violations (5 policies) |
| **AdaptiveBaselineAgent** | Detection | Sigma deviations from learned normal |
| **RiskForecastAgent** | Prediction | NORMAL → DEGRADED → AT_RISK → VIOLATION → INCIDENT |
| **CausalAgent** | Reasoning | Cause-effect chains with confidence scores |
| **MasterAgent** | Coordinator | Orchestrates cycles, ranks severity, maps actions |
| **QueryAgent** | Interface | Agentic RAG — answers natural language questions |
| **ScenarioInjectionAgent** | Testing | Injects 5 stress scenarios for demos |

**Coordination:** Agents never communicate directly. All via Blackboard (SharedState).

```
Phase 1 (Parallel):   Workflow + Resource + Compliance + Baseline
Phase 2 (Sequential): Risk Forecast → Causal Analysis
Phase 3:              Recommendations + Explanations
```

---

## Project Structure

```
iicwms-cognitive-observability/
│
├── .env.example                         # Environment config (Gemini, CrewAI, ports)
├── .gitignore
├── LICENSE
├── README.md                            # This file
├── SERVICES.md                          # Full service architecture manifest
├── requirements.txt                     # Python 3.10+ dependencies
├── guards.py                            # Runtime architectural boundary enforcement
│
├── docs/                                # Documentation & judge-facing materials
│   ├── IICWMS_End_To_End_Document.md    #   End-to-end system document (for judges)
│   ├── architecture.md                  #   System architecture & data model
│   ├── agent_responsibilities.md        #   Agent I/O contracts & boundaries
│   ├── assumptions.md                   #   Explicit assumptions & limitations
│   └── demo_flow.md                     #   Demo script & talking points
│
├── scripts/                             # Operational scripts
│   └── seed_demo_data.py                #   Per-page demo data generator
│
│  ─── BACKEND SERVICES ─────────────────────────────────────────────────
│
├── simulator/                           # SVC 1: chronos-simulator
│   ├── README.md                        #   Service documentation
│   ├── __init__.py                      #   Exports: SimulationEngine
│   └── engine.py                        #   Probabilistic simulation engine
│
├── observation/                         # SVC 2: chronos-observer
│   ├── README.md                        #   Service documentation
│   ├── __init__.py                      #   Exports: ObservationLayer
│   └── layer.py                        #   Append-only event/metric store
│
├── agents/                              # SVC 3: chronos-reasoning (9 agents)
│   ├── README.md                        #   Service documentation
│   ├── __init__.py                      #   Agent registry & exports
│   ├── master_agent.py                  #   Coordinator — orchestrates cycles
│   ├── workflow_agent.py                #   Detection — workflow anomalies
│   ├── resource_agent.py                #   Detection — resource spikes & drift
│   ├── compliance_agent.py              #   Detection — 5 policy violations
│   ├── adaptive_baseline_agent.py       #   Detection — learned baseline deviations
│   ├── risk_forecast_agent.py           #   Prediction — risk trajectory
│   ├── causal_agent.py                  #   Reasoning — cause-effect chains
│   ├── query_agent.py                   #   Interface — agentic RAG
│   ├── query_crew.py                    #   CrewAI — optional LLM pipeline
│   └── scenario_injection_agent.py      #   Testing — 5 stress scenarios
│
├── blackboard/                          # SVC 4: chronos-blackboard
│   ├── README.md                        #   Service documentation
│   ├── __init__.py                      #   Exports: SharedState, data models
│   └── state.py                         #   Cycle-based shared reasoning state
│
├── explanation/                         # SVC 5: chronos-explainer
│   ├── README.md                        #   Service documentation
│   ├── __init__.py                      #   Exports: ExplanationEngine
│   ├── engine.py                        #   3-tier pipeline (Template→LLM→CrewAI)
│   └── crew.py                          #   CrewAI crew definition
│
├── metrics/                             # SVC 6: chronos-risk-engine
│   ├── README.md                        #   Service documentation
│   ├── __init__.py                      #   Exports: RiskIndexTracker
│   └── risk_index.py                    #   Composite risk score (0-100)
│
├── rag/                                 # SVC 7: chronos-rag
│   ├── README.md                        #   Service documentation
│   ├── __init__.py                      #   Exports: AgenticRAGEngine
│   └── query_engine.py                  #   Query decomposition → synthesis
│
├── graph/                               # SVC 8: chronos-graph (Round-2)
│   ├── README.md                        #   Service documentation
│   ├── __init__.py                      #   Exports: Neo4jClient
│   ├── neo4j_client.py                  #   Neo4j connection & operations
│   ├── schema.cypher                    #   Graph schema definition
│   └── queries.cypher                   #   Pre-built Cypher queries
│
├── api/                                 # SVC 9: chronos-gateway
│   ├── README.md                        #   Service documentation
│   ├── __init__.py                      #   Exports: app
│   └── server.py                        #   FastAPI — 40+ endpoints
│
│  ─── FRONTEND SERVICE ─────────────────────────────────────────────────
│
└── frontend/                            # SVC 10: chronos-dashboard
    ├── README.md                        #   Service documentation
    ├── package.json                     #   React 19, Tailwind 4, TanStack Query
    ├── next.config.ts                   #   Next.js 16 configuration
    ├── tsconfig.json                    #   TypeScript 5 strict mode
    ├── postcss.config.mjs               #   PostCSS + Tailwind pipeline
    ├── eslint.config.mjs                #   ESLint 9 rules
    ├── public/                          #   Static assets
    └── src/
        ├── components/                  #   Sidebar, Header, Charts, Providers
        │   └── Charts.tsx               #   Custom canvas charts (zero deps)
        └── app/                         #   Next.js App Router — 10 pages
            ├── overview/                #   System health dashboard
            ├── workflow-map/            #   Workflow execution timeline
            ├── resource-cost/           #   Resource & cost intelligence
            ├── compliance/              #   Compliance intelligence
            ├── anomaly-center/          #   Anomaly detection hub
            ├── causal-analysis/         #   Causal reasoning visualization
            ├── insight-feed/            #   Executive intelligence feed
            ├── search/                  #   Ask Chronos AI (agentic RAG)
            ├── scenarios/               #   Scenario lab (stress testing)
            └── system-graph/            #   System risk index
```

---

## Quick Start

### Prerequisites

- Python 3.10+ (recommended: 3.12+)
- Node.js 18+ and npm

### Backend (Services 1-9)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Gemini API key (optional — system works without it)

# Start API server
uvicorn api.server:app --reload --port 8000
```

### Frontend (Service 10)

```bash
cd frontend
npm install
npm run dev          # Development → http://localhost:3000
```

### Seed Demo Data

```bash
# With backend running — seeds all 10 frontend pages
python3 scripts/seed_demo_data.py
```

### Health Checks / Smoke Tests

```bash
# Backend up?
curl -s http://localhost:8000/system/health | head

# OpenAPI docs
open http://localhost:8000/docs   # macOS

# Frontend up?
curl -I http://localhost:3000 | head
```

### Demo Flows (No Cloud Required)

```bash
# 1) Trigger one reasoning cycle (agents run + blackboard cycle created)
curl -s -X POST http://localhost:8000/analysis/cycle | jq .

# 2) Ingest a GitHub PR webhook (pre-deploy code signal)
curl -s -X POST http://localhost:8000/ingest/github/webhook \\
  -H 'Content-Type: application/json' \\
  -H 'X-GitHub-Event: pull_request' \\
  -H 'X-GitHub-Delivery: demo-1' \\
  --data '{"action":"opened","deployment_id":"deploy_demo_001","repository":{"full_name":"paytm/payment-api"},"sender":{"login":"ravi"},"pull_request":{"number":847,"title":"Fix payment timeout regex","changed_files":6,"additions":47,"deletions":12,"head":{"sha":"abc123def456"}},"metadata":{"churn_lines":59,"complexity":8.2,"hotspot_files":["payment_regex.py"]}}' | jq .

# 3) Ingest a GitHub Actions workflow_run webhook (CI signal like coverage)
curl -s -X POST http://localhost:8000/ingest/github/webhook \\
  -H 'Content-Type: application/json' \\
  -H 'X-GitHub-Event: workflow_run' \\
  -H 'X-GitHub-Delivery: demo-2' \\
  --data '{"action":"completed","deployment_id":"deploy_demo_001","repository":{"full_name":"paytm/payment-api"},"sender":{"login":"github-actions[bot]"},"workflow_run":{"id":9991,"name":"paytm-cd.yml","conclusion":"success","head_sha":"abc123def456"},"metadata":{"test_coverage":0.62}}' | jq .

# 4) Run another cycle so CodeAgent emits predictive anomalies
curl -s -X POST http://localhost:8000/analysis/cycle | jq .

# 5) View the workflow timeline (now includes a Code & CI lane)
open http://localhost:3000/workflow-map   # macOS
```

> `jq` is optional; remove it if you don't have it installed.

### Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `GEMINI_API_KEY` | No | — | LLM for explanation engine (optional) |
| `ENABLE_CREWAI` | No | `false` | CrewAI multi-agent explanations |
| `API_HOST` | No | `0.0.0.0` | Server bind address |
| `API_PORT` | No | `8000` | Server port |
| `SQLITE_DB_PATH` | No | `data/chronos.db` | SQLite operational store path |
| `ENABLE_NEO4J` | No | `false` | Enable Neo4j graph (optional) |
| `NEO4J_URI` | If Neo4j enabled | — | Neo4j connection URI |
| `NEO4J_USERNAME` | If Neo4j enabled | — | Neo4j username |
| `NEO4J_PASSWORD` | If Neo4j enabled | — | Neo4j password |
| `ENABLE_SLACK_ALERTS` | No | `false` | Enable Slack notifications |
| `SLACK_WEBHOOK_URL` | If Slack enabled | — | Slack Incoming Webhook URL |
| `FRONTEND_BASE_URL` | No | `http://localhost:3000` | Used in Slack message deep-links |

### Data Persistence (Local)

- SQLite: `data/chronos.db` (created automatically on first run)
- Observation JSONL (backup): `observation/events.jsonl`
- Blackboard cycles JSONL (backup): `blackboard/cycles.jsonl`

Neo4j is optional. If `ENABLE_NEO4J=false`, the backend runs with a graceful NullGraphClient.

### Common Troubleshooting (DevOps)

- Backend starts but shows Slack errors:
  - Set `ENABLE_SLACK_ALERTS=false` in `.env` or provide a valid `SLACK_WEBHOOK_URL`.
- Frontend shows mock data:
  - Ensure backend is up on `http://localhost:8000` and `NEXT_PUBLIC_API_URL` is correct.
- Port conflict:
  - Change `API_PORT` or run `uvicorn ... --port <new>` and update `NEXT_PUBLIC_API_URL`.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Languages** | Python 3.10+, TypeScript 5 |
| **Backend** | FastAPI, Uvicorn, Pydantic v2 |
| **Frontend** | Next.js 16, React 19, Tailwind CSS 4, TanStack React Query v5 |
| **AI/LLM** | Google Gemini (explanation only), CrewAI (optional) |
| **Agents** | 9 stateless Python modules with Blackboard coordination |
| **Storage** | In-memory state + JSONL persistence |
| **Charts** | Custom HTML Canvas rendering (zero chart library deps) |
| **Data Fetching** | Axios (frontend), httpx (backend) |
| **Guards** | Runtime architectural enforcement via Python decorators |
| **Graph DB** | Neo4j + Cypher (Round-2) |

---

## ATRE Principles

Every insight is:

- **Auditable** — Immutable blackboard cycles with JSONL persistence
- **Traceable** — Every claim links to specific event IDs and metric readings
- **Retryable** — Agents are stateless — same input produces same output
- **Explainable** — Full reasoning chain from observation to insight

---

## Architectural Guards (Runtime Enforcement)

| Guard | Prevents |
|-------|----------|
| `@agents_cannot_emit_events` | Agents creating events (only simulation can) |
| `@llm_cannot_write_state` | LLM modifying shared state |
| `@simulation_cannot_read_policies` | Simulation knowing about policies |
| `validate_insight_has_evidence()` | Insights without evidence chains |
| `validate_anomaly_has_evidence()` | Anomalies without event references |

---

## Success Criteria (All Achieved)

- [x] Workflow degradation detected and explained with evidence
- [x] Silent compliance violations identified before audit
- [x] Risk predicted BEFORE violation occurs
- [x] Root cause explained with causal chains and confidence
- [x] Preventive actions suggested with urgency levels
- [x] 9 agents coordinated through shared blackboard
- [x] 10-page frontend with real-time cognitive visualization
- [x] Agentic RAG for natural language system queries
- [x] Scenario injection with live agent response tracking
- [x] Full evidence traceability across all insights

---

## Codebase Metrics

| Metric | Count |
|--------|-------|
| Total services | 10 |
| Total files | ~74 |
| Python modules | 30+ |
| TypeScript modules | 16 |
| REST API endpoints | 40+ |
| Specialized agents | 9 |
| Frontend pages | 10 |
| Chart components | 6 (custom, zero deps) |
| Policy rules | 5 |
| Injection scenarios | 5 |
| Causal patterns | 5 |

---

## Documentation

| Document | Purpose |
|----------|---------|
| [`SERVICES.md`](SERVICES.md) | Full service architecture, data flow, guard registry |
| [`docs/IICWMS_End_To_End_Document.md`](docs/IICWMS_End_To_End_Document.md) | Comprehensive end-to-end system document (for judges) |
| [`docs/architecture.md`](docs/architecture.md) | System architecture & data model specification |
| [`docs/agent_responsibilities.md`](docs/agent_responsibilities.md) | Agent I/O contracts & boundaries |
| [`docs/assumptions.md`](docs/assumptions.md) | Explicit assumptions & limitations |
| [`docs/demo_flow.md`](docs/demo_flow.md) | Demo script & talking points |

Each service directory also contains its own `README.md` with interface contracts, configuration, and technology details.

---


#  Phase 1 – Foundation & Architecture

### 1️⃣ Initial Project Scaffold

```
feat: initialize IICWMS Chronos AI monorepo structure

- Created 10-service architecture layout
- Added backend service directories (simulator → graph)
- Added frontend Next.js 16 scaffold
- Added docs/, scripts/, guards.py
- Established modular microservice boundaries
```

---


## License

MIT License
