# IICWMS – Cognitive Observability Platform

### Intelligent IT Compliance & Workflow Monitoring System (PS-08)

> **Moving beyond monitoring into Cognitive Observability** — a multi-agent, reasoning-driven intelligence system that explains *why* things happen, not just *what* happened.

---

## Problem Overview

Modern IT systems operate through complex workflows involving users, services, resources, and policies. As scale increases, traditional monitoring tools fail to provide **understanding** — they surface metrics and alerts but do not explain *why* failures happen or *what actions should be taken*.

This leads to:
- Silent workflow anomalies going undetected
- Compliance violations discovered only during audits
- Resource inefficiencies compounding over time
- Delayed incident response due to lack of causal reasoning

---

## Our Solution: Cognitive Observability

**IICWMS** is a **multi-agent, reasoning-driven intelligence system** that observes simulated IT operations to produce **auditable, traceable, retryable, and explainable insights**.

Instead of answering *"What is broken?"*, the system answers:
- **Why did this happen?** — Causal analysis with evidence chains
- **What is the most probable root cause?** — Temporal correlation + dependency reasoning
- **What ripple effects does this create?** — Blast radius and downstream impact analysis
- **What action should be taken next?** — Prioritized, confidence-scored recommendations

### Core Principle

> "If we can't explain why something matters, it doesn't matter."

---

## High-Level Architecture

```
┌─────────────────────────┐
│   Simulation Engine     │   ← generates realistic IT events
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│   Observation Layer     │   ← raw facts only (events + metrics)
└───────────┬─────────────┘
            ↓
┌──────────────────────────────────────┐
│   Multi-Agent Reasoning Layer        │
│                                      │
│   ┌──────────────┐  ┌─────────────┐ │
│   │ WorkflowAgent│  │ResourceAgent│ │
│   └──────────────┘  └─────────────┘ │
│   ┌──────────────┐  ┌─────────────┐ │
│   │ComplianceAgent│ │ CausalAgent │ │
│   └──────────────┘  └─────────────┘ │
│   ┌──────────────┐  ┌─────────────┐ │
│   │RiskForecast  │  │ Adaptive    │ │
│   │Agent         │  │ Baseline    │ │
│   └──────────────┘  └─────────────┘ │
│   ┌──────────────┐  ┌─────────────┐ │
│   │ MasterAgent  │  │ScenarioInj. │ │
│   └──────────────┘  └─────────────┘ │
│                                      │
│   ┌──────────────────────────────┐   │
│   │  Shared State (Blackboard)   │   │
│   └──────────────────────────────┘   │
└───────────┬──────────────────────────┘
            ↓
┌──────────────────────────────────────┐
│   Explanation Engine (LLM-backed)    │   ← human-readable output
└───────────┬──────────────────────────┘
            ↓
┌──────────────────────────────────────┐
│   Frontend Dashboard (11 pages)      │   ← Next.js cognitive UI
└──────────────────────────────────────┘
```

### Key Architectural Principles

1. **Reality is generated, not inferred** — Only the Simulation Engine creates events
2. **Observe ≠ Reason ≠ Explain** — These are separate layers
3. **Agents do not talk to each other** — All coordination through shared state (Blackboard)
4. **LLMs are forbidden for detection** — LLMs ONLY for explanation wording
5. **Every claim must point to evidence** — If it cannot be traced, it does not exist

---

## Multi-Agent System (9 Agents)

| Agent | Purpose | Detects |
|-------|---------|---------|
| **WorkflowAgent** | Monitors workflow execution | Delays, missing steps, sequence violations |
| **ResourceAgent** | Monitors resource conditions | Sustained CPU/memory spikes, network latency |
| **ComplianceAgent** | Checks policy compliance | Silent violations, after-hours access, policy breaches |
| **RiskForecastAgent** | Predicts risk trajectory | NORMAL → DEGRADED → AT_RISK → VIOLATION → INCIDENT |
| **CausalAgent** | Identifies cause-effect chains | Temporal correlations + dependency-based reasoning |
| **AdaptiveBaselineAgent** | Learns normal behavior | Drift detection before static thresholds trigger |
| **MasterAgent** | Coordinates reasoning cycles | Triggers agents, ranks severity, produces insights |
| **ScenarioInjectionAgent** | Stress testing | Injects disruption scenarios for agent evaluation |
| **QueryAgent (RAG)** | Answers questions | Agentic RAG over blackboard state |

---

## Shared State (Blackboard)

Agents communicate through a shared, immutable blackboard ledger:

```json
{
  "cycle_id": "cycle_104",
  "facts": ["...observed events and metrics..."],
  "anomalies": ["...agent-detected anomalies with confidence..."],
  "policy_hits": ["...compliance violations with evidence..."],
  "risk_signals": ["...risk state transitions..."],
  "hypotheses": ["...probable causes ranked by confidence..."],
  "causal_links": ["...cause → effect with statistical basis..."],
  "recommendations": ["...prioritized actions with expected impact..."]
}
```

---

## Frontend Dashboard (11 Pages)

The frontend is a modern Next.js application providing cognitive observability across 11 specialized views:

| Page | Description |
|------|-------------|
| **Overview** | System health, stats, cost trends, anomaly rates, critical insights |
| **Workflow Timeline** | Interactive confidence-tracked event timeline with lane visualization |
| **Anomaly Center** | All detected anomalies with evidence chain drill-down |
| **Causal Analysis** | Interactive graph of cause-effect relationships with snapshot export |
| **Compliance** | Policy monitoring, violation tracking, audit readiness scoring |
| **Insight Feed** | Executive-level AI-generated insights with recommended actions |
| **Resource & Cost** | Resource utilization, cost trends, predictive cost analysis |
| **System Risk Graph** | Stock-market-style risk trajectory with agent contribution breakdown |
| **Scenarios** | Stress testing with real-time agent response visualization |
| **Chronos AI (Search)** | Agentic RAG — ask questions, get evidence-backed answers |
| **System Graph** | Risk index with component comparison and contribution analysis |

### Frontend Features
- Real-time data with React Query
- Custom canvas-rendered charts (no chart library dependency)
- Evidence chain drill-down from any anomaly/insight
- Cross-page navigation (Jump to Graph, View Causal Analysis, etc.)
- Scenario injection with live agent-by-agent response animation
- Chronos AI with multi-stage thinking visualization (4-5s reasoning)
- Extract Snapshot — export causal analysis state as JSON
- Fully responsive modern UI with dark accents

---

## Explainability & ATRE Principles

Every insight produced by the system is:

- **Auditable** — backed by immutable evidence entries in the blackboard
- **Traceable** — linked to specific event IDs, metric readings, and agent reasoning
- **Retryable** — agents are stateless and re-runnable on the same data
- **Explainable** — insights cite evidence chains, not intuition

**LLMs are used ONLY for narrative explanation, never for detection or enforcement.**

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.10+, FastAPI, Pydantic v2, Uvicorn |
| Simulation | Custom engine with emergent behavior patterns |
| Agents | 9 stateless Python agent modules |
| Blackboard | In-memory shared state with JSONL persistence |
| AI/LLM | Google Gemini (explanation only), CrewAI orchestration |
| RAG | Custom query engine over blackboard state |
| Frontend | Next.js 16, React 19, TypeScript, TailwindCSS 4 |
| Charts | Custom HTML Canvas rendering (zero chart library deps) |
| Data Fetching | TanStack React Query with auto-refresh |

---

## Running the System

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm

### Backend

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run API server
uvicorn api.server:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # Development (port 3000)

# OR for production build:
npm run build
npx next start -p 3000
```

### Seed Demo Data (Optional)

```bash
# With backend running, seed rich data for all pages
python scripts/seed_demo_data.py
```

### Environment Variables

```bash
GOOGLE_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini/gemini-2.0-flash
ENABLE_CREWAI=true
```

---

## Project Structure

```
iicwms-cognitive-observability/
├── agents/                    # 9 AI agents (stateless modules)
│   ├── workflow_agent.py
│   ├── resource_agent.py
│   ├── compliance_agent.py
│   ├── causal_agent.py
│   ├── risk_forecast_agent.py
│   ├── adaptive_baseline_agent.py
│   ├── master_agent.py
│   ├── scenario_injection_agent.py
│   └── query_agent.py
├── api/                       # FastAPI server + endpoints
│   └── server.py
├── blackboard/                # Shared state management
│   └── state.py
├── explanation/               # LLM-backed explanation engine
│   ├── engine.py
│   └── crew.py
├── frontend/                  # Next.js dashboard (11 pages)
│   └── src/
│       ├── app/               # Page routes
│       ├── components/        # Shared UI components
│       └── lib/               # API client, mock data, utils
├── metrics/                   # Risk index calculation
├── observation/               # Observation layer (facts only)
├── rag/                       # RAG query engine
├── scripts/                   # Utility scripts
├── simulator/                 # Simulation engine
├── docs/                      # Architecture documentation
├── requirements.txt
└── README.md
```

---

## Success Criteria (All Achieved)

- [x] Workflow degradation detected and explained
- [x] Silent compliance violations identified with evidence
- [x] Risk predicted BEFORE violation occurs
- [x] Root cause explained with causal chains
- [x] Preventive actions suggested with confidence scores
- [x] 9 agents working through shared blackboard
- [x] 11-page frontend with real-time data visualization
- [x] Agentic RAG for natural language system queries
- [x] Scenario injection with live agent response tracking
- [x] Full evidence traceability across all insights

---

## Design Principles (Failure Modes Avoided)

- **No "LLM detected anomaly"** — Detection is rule-based and statistical
- **No scripted demo data** — Simulation engine generates emergent behavior
- **No agents calling each other** — All coordination via shared blackboard
- **No auto-fixing systems** — Recommendations only, humans decide
- **No dashboards without reasoning** — Every metric has an explanation

---

## License

MIT License
