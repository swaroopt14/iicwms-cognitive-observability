# IICWMS — Chronos AI: Service Architecture

> 10 Microservices | 9 Agents | 40+ API Endpoints | 10 Dashboard Pages

---

## Service Map

```
═══════════════════════════════════════════════════════════════════════════════
                       CHRONOS AI — SERVICE ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

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
  └──────┘└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘└──────┘
   SVC 1   SVC 2   SVC 3   SVC 4   SVC 5   SVC 6  SVC 7   SVC 8
```

---

## Service Registry

| # | Service Name | Directory | Technology | Port | Description |
|---|-------------|-----------|------------|------|-------------|
| 1 | **chronos-simulator** | `simulator/` | Python 3.10 | — | Probabilistic event/metric generation with emergent behavior |
| 2 | **chronos-observer** | `observation/` | Python 3.10 + JSONL | — | Append-only raw fact ingestion & windowed queries |
| 3 | **chronos-reasoning** | `agents/` | Python 3.10 (9 agents) | — | Multi-agent detection, compliance, risk, causal analysis |
| 4 | **chronos-blackboard** | `blackboard/` | Python 3.10 + JSONL | — | Shared reasoning state — inter-agent communication hub |
| 5 | **chronos-explainer** | `explanation/` | Python 3.10 + Gemini | — | 3-tier insight generation (Template → LLM → CrewAI) |
| 6 | **chronos-risk-engine** | `metrics/` | Python 3.10 | — | Composite risk index (0-100) with weighted scoring |
| 7 | **chronos-rag** | `rag/` | Python 3.10 | — | Reasoning-augmented query engine (7 query types) |
| 8 | **chronos-graph** | `graph/` | Python 3.10 + Neo4j | 7687 | Graph database for causal knowledge (Round-2) |
| 9 | **chronos-gateway** | `api/` | FastAPI + Uvicorn | 8000 | REST API gateway — 40+ endpoints, 12 route groups |
| 10 | **chronos-dashboard** | `frontend/` | Next.js 16 + React 19 | 3000 | 10-page cognitive observability frontend |

---

## Data Flow Between Services

```
chronos-simulator ──events/metrics──→ chronos-observer
                                           │
                                    ┌──────┴──────┐
                                    ▼              ▼
                              chronos-reasoning    chronos-reasoning
                              (Phase 1: parallel)  (Phase 2: sequential)
                                    │              │
                                    └──────┬───────┘
                                           ▼
                                    chronos-blackboard
                                           │
                              ┌────────────┼────────────┐
                              ▼            ▼            ▼
                       chronos-explainer  chronos-risk  chronos-rag
                              │            │            │
                              └────────────┼────────────┘
                                           ▼
                                    chronos-gateway
                                           │
                                           ▼
                                    chronos-dashboard
```

---

## Architectural Guards (Runtime Enforcement)

| Guard | Prevents | Enforced On |
|-------|----------|-------------|
| `@agents_cannot_emit_events` | Agents creating events | chronos-reasoning |
| `@llm_cannot_write_state` | LLM modifying shared state | chronos-explainer |
| `@simulation_cannot_read_policies` | Simulation knowing policies | chronos-simulator |
| `validate_event_has_no_severity()` | Events having pre-labels | chronos-observer |
| `validate_insight_has_evidence()` | Insights without evidence | chronos-explainer |
| `validate_anomaly_has_evidence()` | Anomalies without evidence | chronos-reasoning |

---

## Quick Start

```bash
# Backend (Services 1-9)
pip install -r requirements.txt
uvicorn api.server:app --reload --port 8000

# Frontend (Service 10)
cd frontend && npm install && npm run dev

# Seed demo data (all 10 pages)
python3 scripts/seed_demo_data.py
```

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
