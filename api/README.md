# chronos-gateway

> **Service 9** — API Gateway (FastAPI REST Service)

## Purpose

The REST API gateway serving **40+ endpoints** across 12 route groups. Connects the frontend dashboard to all backend services — observation, reasoning, explanation, risk index, and RAG.

## Route Groups (40+ Endpoints)

| Group | Endpoints | Purpose |
|-------|-----------|---------|
| **Observation** | `POST /observe/event`, `POST /observe/metric`, `GET /events` | Event/metric ingestion |
| **System Health** | `GET /system/health`, `GET /signals/summary`, `GET /overview/stats` | Dashboard health data |
| **Insights** | `GET /insights`, `GET /insight/{id}` | AI-generated insights |
| **Anomalies** | `GET /anomalies`, `GET /anomalies/summary`, `GET /anomalies/trend` | Detection results |
| **Compliance** | `GET /policies`, `GET /policy/violations`, `GET /compliance/*` | Policy monitoring |
| **Workflows** | `GET /workflows`, `GET /workflow/{id}/timeline` | Workflow tracking |
| **Resources** | `GET /resources`, `GET /resources/trend`, `GET /cost/trend` | Resource monitoring |
| **Causal** | `GET /causal/links`, `GET /graph/path/{id}` | Cause-effect data |
| **Risk** | `GET /risk/index`, `GET /risk/current` | Risk trajectory |
| **Query/RAG** | `POST /query`, `POST /rag/query`, `GET /rag/examples` | NL query interface |
| **Scenarios** | `GET /scenarios`, `POST /scenarios/inject` | Stress testing |
| **Baselines** | `GET /baselines`, `GET /baselines/deviations` | Adaptive baselines |

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `API_HOST` | `0.0.0.0` | Bind address |
| `API_PORT` | `8000` | Listen port |

## Running

```bash
uvicorn api.server:app --reload --port 8000
```

## Technology

- **Language:** Python 3.10+
- **Framework:** FastAPI (async, OpenAPI auto-docs)
- **Server:** Uvicorn (ASGI)
- **Validation:** Pydantic v2
- **Port:** 8000
