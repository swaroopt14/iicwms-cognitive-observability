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
| **Alerts** | `GET /alerts/slack/status`, `POST /alerts/slack/test` | Slack integration |
| **Audit** | `GET /audit/*`, `POST /audit/export` | Post-mortem forensics |

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `API_HOST` | `0.0.0.0` | Bind address |
| `API_PORT` | `8000` | Listen port |
| `ENABLE_SLACK_ALERTS` | `false` | Enable Slack notifications |
| `SLACK_WEBHOOK_URL` | `` | Slack incoming webhook URL |
| `SLACK_ALERT_MIN_SEVERITY` | `HIGH` | Alert threshold by severity |
| `SLACK_ALERT_MIN_RISK_STATE` | `VIOLATION` | Alert threshold by risk state |

## Running

```bash
uvicorn api.server:app --reload --port 8000
```

## DevOps Runbook

### Prereqs

- Python 3.10+
- `pip install -r requirements.txt`
- Optional: copy `.env.example` to `.env` in repo root

### Health + Docs

```bash
curl -s http://localhost:8000/system/health | head
open http://localhost:8000/docs    # macOS
```

### Data Stores (Local)

- SQLite operational DB: `data/chronos.db` (auto-created)
- Observation append-only backup: `observation/events.jsonl`
- Blackboard append-only backup: `blackboard/cycles.jsonl`

Neo4j is optional (graph features gracefully degrade when disabled).

### Key Demo Endpoints

```bash
# Run one reasoning cycle (Phase1 parallel + Phase2 sequential)
curl -s -X POST http://localhost:8000/analysis/cycle

# Ingest enterprise envelope (strict validation + idempotency + DLQ)
curl -s -X POST http://localhost:8000/ingest/envelope -H 'Content-Type: application/json' --data '{}'

# Ingest GitHub webhook (PR/CI) — demo mode
curl -s -X POST http://localhost:8000/ingest/github/webhook \\
  -H 'Content-Type: application/json' \\
  -H 'X-GitHub-Event: pull_request' \\
  --data '{\"action\":\"opened\",\"deployment_id\":\"deploy_demo_001\",\"repository\":{\"full_name\":\"paytm/payment-api\"},\"sender\":{\"login\":\"ravi\"},\"pull_request\":{\"number\":847,\"title\":\"Fix payment timeout\"}}'
```

### Slack (Optional)

Set in `.env`:

- `ENABLE_SLACK_ALERTS=true`
- `SLACK_WEBHOOK_URL=<incoming webhook>`
- `FRONTEND_BASE_URL=http://localhost:3000`

Check status:

```bash
curl -s http://localhost:8000/alerts/slack/status
curl -s -X POST http://localhost:8000/alerts/slack/test
```

## Technology

- **Language:** Python 3.10+
- **Framework:** FastAPI (async, OpenAPI auto-docs)
- **Server:** Uvicorn (ASGI)
- **Validation:** Pydantic v2
- **Port:** 8000
