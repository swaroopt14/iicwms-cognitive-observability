# Chronos Implementation Lock (v2)

## Scope Locked
- Unified enterprise telemetry envelope is mandatory.
- Reasoning execution order is fixed:
  - Phase 1 parallel: Workflow, Resource, Compliance, Adaptive, Code
  - Phase 2 sequential: RiskForecast
  - Phase 3 sequential: Causal
  - Coordinator: Master
  - On-demand: Query, Scenario
- Blackboard is append-only with evidence mandatory for each output.

## Delivered In This Slice
- Added strict ingestion endpoint: `POST /ingest/envelope`
- Added ingestion status endpoint: `GET /ingest/status`
- Added GitHub webhook ingest endpoint (demo mode): `POST /ingest/github/webhook`
- Added CodeAgent (predictive pre-deploy signals) and a `code` lane in workflow timeline.
- Implemented:
  - schema version gate (`v1.x`)
  - idempotency duplicate quarantine
  - timestamp skew quarantine
  - category-specific payload checks
  - tenant key generation (`org:project:env`)
  - normalization into observation event + metric

## Envelope Contract (Current)
- Required top-level:
  - `schema_version`
  - `event_id`
  - `idempotency_key`
  - `trace_id`
  - `event_source_ts`
  - `enterprise_context`
  - `actor_context`
  - `source_signature`
  - `normalized_event`
- Optional:
  - `span_id`, `parent_span_id`, `ingested_ts`, `processed_ts`
  - `data_classification`, `pii_present`
  - `metrics_payload`, `event_payload`, `log_payload`

## DLQ Reason Codes (Current)
- `SCHEMA_INVALID`
- `DUPLICATE`
- `LATE_EVENT`

## Immediate Next Steps (Build Order)
1. Persist DLQ and idempotency in SQLite (not in-memory only).
2. Add `events_raw` and `events_normalized` tables with indexes on tenant/time.
3. Add policy lifecycle tables and APIs:
   - draft/validate/activate/rollback
4. Add confidence component persistence per agent output.
5. Add strict query grounding checks (`no evidence => no claim`).
6. Add replay determinism tests and performance SLO tests.
7. Add webhook signature verification (GitHub `X-Hub-Signature-256`) before any public exposure.

## Acceptance Criteria
- Duplicate events do not create duplicate observations.
- Invalid envelope is quarantined with explicit reason code.
- Every agent output has evidence IDs.
- End-to-end: ingest -> cycle -> risk -> causal -> recommendation -> audit timeline.
- Pre-deploy: PR/CI webhook -> CodeAgent anomalies -> timeline `code` lane (evidence-backed).
