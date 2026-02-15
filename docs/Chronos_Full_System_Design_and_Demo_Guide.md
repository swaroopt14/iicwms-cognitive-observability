# Chronos AI Full System Design and Demo Guide

## 1) Executive Summary
Chronos AI is a cognitive observability platform that converts raw operational signals into explainable, evidence-backed actions.

Core loop:
`Observe -> Detect -> Forecast -> Reason -> Explain -> Act -> Learn`

This document answers:
- How anomalies are sent from input systems
- What input sources exist
- How ingestion, event creation, de-duplication, categorization, scoring, and tracking work
- How adaptive, predictive, proactive, and cross-agent reasoning are implemented
- How results are shown in UI and escalated to Slack
- How to run everything locally (no paid cloud required)

---

## 2) What Exists Today vs What We Add Next

### 2.1 Implemented in current repo
- Ingestion APIs:
  - `POST /observe/event`
  - `POST /observe/metric`
  - `POST /ingest/envelope` (strict enterprise telemetry contract + DLQ)
  - `POST /ingest/github/webhook` (demo mode: PR/CI ingestion for pre-deploy prediction)
- Observation layer stores raw events/metrics append-only
- Multi-agent reasoning cycle (parallel + sequential phases)
- Adaptive baseline detection
- Risk forecasting
- Causal link generation
- Explanation engine with confidence and uncertainty
- Query agent (RAG over Blackboard + recent observations)
- Scenario injection API for stress tests
- Dashboard pages for anomalies, causal links, compliance, risk, search, trends
- Persistence in SQLite (`data/chronos.db`) and optional Neo4j graph integration
 - Workflow Timeline now supports a `code` lane (PR/CI + predictive anomalies)

### 2.2 Not yet implemented, but required for production-grade demo
- Kafka broker-based ingest bus
- Webhook receiver + connector workers (GitHub/Jira/CloudTrail/K8s/etc.)
- Slack alert dispatcher with severity policies
- Strong idempotency key store for multi-source dedup at ingress
- Fully local Docker Compose stack with Kafka + Redis + Neo4j + API + frontend + workers

This document includes both the current behavior and production extension design.

---

## 3) Input Sources: How Anomalies Enter the System

### 3.1 Current input sources (implemented)
1. Simulation Engine (`simulator/engine.py`)
- Generates workflow, access, config, and resource events
- Produces metrics (`cpu_percent`, `memory_percent`, `network_latency_ms`)

2. Scenario Injection Agent (`agents/scenario_injection_agent.py`)
- Injects stress scenarios directly into observation layer:
  - `LATENCY_SPIKE`
  - `COMPLIANCE_BREACH`
  - `WORKLOAD_SURGE`
  - `CASCADING_FAILURE`
  - `RESOURCE_DRIFT`

3. Manual/API source
- External systems (or scripts) can call:
  - `POST /observe/event`
  - `POST /observe/metric`
  - `POST /ingest/envelope` (recommended for enterprise context + dedup)

4. GitHub PR/CI webhook (implemented, demo mode)
- `POST /ingest/github/webhook`
- Purpose: bring pre-deploy signals (PR/review/CI) into the same evidence chain as deploy/runtime.
- Correlation: events carry `enterprise_context.deployment_id` and `trace_id=trace_<deployment_id>`.

### 3.2 Production source expansion (recommended)
Add connector workers for:
- Webhooks: GitHub, GitLab, Jira, ServiceNow, PagerDuty
- Log shippers: Fluent Bit / Vector
- Infra telemetry: Prometheus exporters, OpenTelemetry collectors
- Cloud/security feeds: CloudTrail, GuardDuty, Kubernetes audit, IAM logs
- Cost feeds: billing exports, Kubernetes usage metrics, FinOps tools

---

## 4) Event Ingestion and Event Creation

### 4.1 Current implemented pipeline
1. Raw event/metric arrives at API.
2. API validates schema (`EventInput`, `MetricInput`).
3. Observation layer writes append-only:
- In-memory bounded buffer (fast reads)
- JSONL backup
- SQLite primary persistence
4. Reasoning loop periodically reads recent windows and starts a cycle.

### 4.2 Enterprise envelope ingest (implemented)
`POST /ingest/envelope` enforces:
- schema version gate (`v1.x`)
- idempotency (duplicates quarantined to DLQ)
- timestamp skew quarantine
- category-specific payload checks

On success it writes a single Observation event and (optionally) a metric, embedding:
- `enterprise_context` (org/project/env/service/deployment_id/workflow_id)
- `actor_context` (role/team/auth)
- `source_signature` (tool attribution)
- `normalized_event` (category/type/severity/confidence_initial)
- `trace_id` and `tenant_key`

### 4.3 GitHub webhook ingest (implemented, demo mode)
`POST /ingest/github/webhook` accepts GitHub events and writes Observation events with:
- `source_signature.tool_name=github`
- `enterprise_context.deployment_id` (explicit or derived from repo+sha)
- `normalized_event.event_category=code|cicd`
- raw `event_payload` stored for audit proof

Security note:
- Signature verification is not implemented; do not expose publicly.

### 4.2 Event identity and normalization (recommended)
At ingress, standardize each item to:
- `event_id` (source-native or generated)
- `source_system` (github/cloudtrail/k8s/etc.)
- `event_type`
- `entity_id`, `entity_type`
- `timestamp` (normalized UTC)
- `metadata` (JSON)
- `fingerprint` (for dedup)

---

## 5) Deduplication / Duplicate Recheck

### 5.1 Existing dedup behavior
- Compliance agent avoids repeated policy hit per `policy_id:event_id` in memory.
- SQLite uses `INSERT OR IGNORE` on primary keys for several tables.

### 5.2 Production dedup design (required)
Use two-level dedup:
1. Ingress idempotency key (5 to 30 minute TTL):
- Key: `source_system + source_event_id` or hash fingerprint
- Store in Redis/SQLite idempotency table

2. Semantic duplicate check:
- If no source_event_id, compare `{entity, type, time_bucket, normalized_payload_hash}`
- Mark as `duplicate_of` instead of discarding silently

Outcome:
- Prevent alert storms from retried webhooks or repeated poll responses
- Maintain lineage for audit

---

## 6) How Anomalies Are Created and Categorized

### 6.1 Detection agents and anomaly types (implemented)
- WorkflowAgent:
  - `WORKFLOW_DELAY`
  - `MISSING_STEP`
  - `SEQUENCE_VIOLATION`
- ResourceAgent:
  - `SUSTAINED_RESOURCE_CRITICAL`
  - `SUSTAINED_RESOURCE_WARNING`
  - `RESOURCE_DRIFT`
- AdaptiveBaselineAgent:
  - `BASELINE_DEVIATION` (sigma-based)
- ComplianceAgent:
  - policy hits (`SILENT` violation type)

### 6.2 Enterprise anomaly taxonomy (recommended complete list)
1. Workflow / Process
- step skipped, delay, stuck state, unauthorized override

2. Infrastructure
- sustained CPU/memory saturation, latency surge, packet loss, node pressure

3. Application / Code
- deploy failure spike, error-rate jump, latency regression, dependency timeout

4. Compliance / Governance
- after-hours write, approval bypass, SoD violation, encryption policy breach

5. Security / Data leakage
- unusual location access, secret access anomaly, exfiltration pattern, privilege escalation

6. Cost / FinOps
- cloud spend spike, idle over-provisioning, inefficient workload placement, storage bloat

7. Data quality / pipeline
- schema drift, null surge, freshness SLA breach, reconciliation mismatch

Each anomaly must include:
- `type`, `severity`, `confidence`, `evidence_ids`, `agent`, `description`, `timestamp`

---

## 7) How Events Are Tracked End-to-End

Tracking unit: `reasoning cycle`

Per cycle:
- raw inputs consumed
- anomalies and policy hits appended
- risk signals forecasted
- causal links generated
- recommendations mapped
- insights produced

Persistence:
- SQLite tables for events, metrics, cycles, anomalies, policy_hits, risk_history, insights, recommendations
- Optional Neo4j for relationship traversal (causal chain, ripple effects)

Auditability:
- Every claim references evidence IDs
- Query answers include supporting evidence + confidence + uncertainty

---

## 8) Predictive and Proactive Analysis

### 8.1 Current prediction implementation
RiskForecastAgent projects trajectory:
`NORMAL -> DEGRADED -> AT_RISK -> VIOLATION -> INCIDENT`

Projection input:
- anomaly count
- policy violation count (higher weight)
- historical entity risk profile

Output includes:
- projected state
- confidence
- time horizon (`5-10`, `10-15`, `15-30 min`)

### 8.2 Proactive actions
Master agent maps detected causes to recommendations using rule map (not hallucinated LLM actions), for example:
- resource saturation -> throttle/scale
- missing workflow step -> temporary guard + audit
- workflow delay -> pre-notify SLA stakeholders

### 8.3 Pre-deploy prediction (implemented)
CodeAgent uses GitHub PR/CI webhook evidence to emit anomalies like:
- `HIGH_CHURN_PR`
- `LOW_TEST_COVERAGE`
- `HIGH_COMPLEXITY_HINT`
- `HOTSPOT_FILE_CHANGE`

These predictive anomalies are:
- written to Blackboard as anomalies (evidence-backed)
- surfaced into the Workflow Timeline `code` lane in demo mode
- correlated to deploy/runtime using `deployment_id`

---

## 9) Confidence Score Logic

### 9.1 Current confidence behavior
- Resource anomalies: fixed rule confidence (e.g., 0.9 critical sustained)
- Workflow anomalies: rule confidence (0.85 to 0.95)
- Baseline deviations: `0.5 + sigma*0.1` capped
- Risk forecasts: confidence from issue density
- Causal links: pattern base confidence adjusted by temporal proximity
- Insight confidence: blended average + max from cycle evidence

### 9.2 Recommended confidence contract for judges
Publish confidence as:
- `signal_confidence`: detector-level certainty
- `causal_confidence`: link certainty
- `action_confidence`: expected remedy impact confidence

Also show uncertainty note:
- data quality constraints
- missing telemetry sources
- simulated vs real source mode

---

## 10) Remedy Recommendation with Confidence

Remedy object format:
- `action`
- `cause`
- `priority`
- `expected_impact`
- `action_confidence`
- `rollback_hint`

Example:
- Action: "Throttle non-critical background jobs on vm_api_01"
- Cause: `SUSTAINED_RESOURCE_CRITICAL -> WORKFLOW_DELAY`
- Priority: `critical`
- Action confidence: `0.82`
- Rollback hint: "Restore previous worker pool after latency < 200ms for 3 windows"

---

## 11) Kafka in Docker (System View, Ecommerce-style)

### 11.1 Why Kafka
Kafka decouples producers (input systems) from consumers (detectors, enrichers, alerting), enabling resilient, replayable, scalable streams.

### 11.2 Topic model
- `raw.events` - normalized operational events
- `raw.metrics` - telemetry metrics
- `enriched.events` - normalized + classified + dedup metadata
- `anomalies.detected` - detector outputs
- `risk.signals` - forecast outputs
- `insights.generated` - explainability outputs
- `alerts.high` - alert-ready critical findings

### 11.3 Consumer groups
- `ingestion-normalizer`
- `dedup-enricher`
- `agent-detectors`
- `risk-causal-engine`
- `insight-engine`
- `slack-notifier`

### 11.4 Flow (ecommerce analogy)
Like ecommerce:
- `order_placed` -> inventory/payment/shipping consumers

Here:
- `raw.events` -> normalize/dedup -> anomaly detectors -> risk/causal -> insights -> alerts

### 11.5 Local Docker deployment components
- `zookeeper` (or KRaft mode)
- `kafka`
- `kafka-ui` (optional)
- `chronos-api`
- `chronos-workers`
- `frontend`
- `sqlite volume`
- `neo4j` local container
- `redis` (idempotency/cache)

No paid cloud service required.

---

## 12) Log Visibility: Sources and Count

### 12.1 Current log visibility
Currently shown in platform from:
1. Observation events stream
2. Observation metrics stream
3. Derived reasoning artifacts (anomalies, policy hits, risk signals, causal links)

### 12.2 Production expanded log sources (target)
At least 8 categories:
1. Application logs
2. Infrastructure metrics/logs
3. Workflow engine logs
4. CI/CD and deployment events
5. Security and IAM logs
6. Compliance/policy audit logs
7. Cost and usage records
8. Data pipeline quality logs

---

## 13) Webhooks and Other Ingestion Methods

Recommended ingestion modes:
1. Push: webhook receiver (`/ingest/webhook/{source}`)
2. Pull: connector scheduler for APIs
3. Stream: Kafka producer from collectors
4. Batch: CSV/JSON bulk import (for backfill)

Each event receives:
- source attribution
- schema version
- ingestion timestamp
- trace/correlation id

---

## 14) Raw Data to Actionable Insight

Transformation layers:
1. Raw facts (Observation)
2. Structured detections (agents)
3. Forecast and causality (risk + causal)
4. Explainability synthesis (explanation engine)
5. Prioritized actions and alerts

Interpretability rule:
No UI card without evidence chain and confidence display.

---

## 15) AI Query Coverage: "Ask Anything About Events"

Current capability:
- QueryAgent + RAG decomposes user question
- Retrieves evidence from Blackboard and recent observations
- Returns answer, confidence, uncertainty, evidence details, recommended actions, follow-up queries

Production extension:
- Add semantic index for long history
- Add source filters (`from=security`, `from=cost`)
- Add "why not" answers when evidence is insufficient

---

## 16) Special Cases: Code Errors, Cloud Cost, Data Leakage

### 16.1 Code error anomalies
- error rate spike post deployment
- regression in endpoint latency
- failing job retries crossing threshold

### 16.2 Nuisance cloud cost anomalies
- sudden spend burst on specific resource group
- sustained idle > threshold
- overprovisioned node pools

### 16.3 Data leakage anomalies
- unusual high-volume read/export
- access to sensitive stores without workflow context
- anomalous external location credential access

Each must map to:
- severity policy
- confidence score
- recommended remediation playbook

---

## 17) UI and Slack High Alerts

### 17.1 UI presentation (implemented)
Frontend pages already show:
- anomaly center
- causal analysis
- compliance dashboard
- risk trends
- insights feed
- search/ask-ai view

### 17.2 High alert pipeline (recommended)
Trigger Slack alert when:
- severity `CRITICAL`, or
- projected risk is `VIOLATION/INCIDENT`, or
- compliance breach with sensitive resource

Slack payload:
- summary
- affected entity
- top evidence IDs
- confidence
- suggested action
- deep link to UI detail

---

## 18) Database Persistence: What and Why

### 18.1 SQLite (current source of truth)
Persists:
- raw events + metrics
- cycles
- anomalies
- policy hits
- recommendations
- risk history
- insights

Why:
- restart-safe history
- trend analytics
- audit and judge demonstration

### 18.2 Neo4j (optional graph layer)
Persists relationships:
- anomaly `CAUSED_BY` anomaly
- workflow topology and ripple links
- entity relationships for graph traversal

---

## 19) Real-Time Dashboard Mechanics

Real-time behavior today:
- background reasoning loop executes periodically
- frontend polls API endpoints for fresh cycle outputs
- charts are generated from cycle history and trend endpoints

For stricter real-time UX (recommended):
- SSE/WebSocket channel for push updates
- event-driven card refresh based on topic type

---

## 20) Agent Communication and Flow

### 20.1 Agents and output roles
- `WorkflowAgent`: workflow anomalies
- `ResourceAgent`: sustained resource stress + drift
- `ComplianceAgent`: policy hits
- `AdaptiveBaselineAgent`: learned-normal deviations
- `RiskForecastAgent`: risk trajectory signals
- `CausalAgent`: cause-effect links
- `MasterAgent`: orchestration, severity synthesis, recommendation mapping
- `QueryAgent`: cross-artifact retrieval and answer synthesis
- `ScenarioInjectionAgent`: stress test injections

### 20.2 Parallel + sequential execution
- Phase 1 (parallel): workflow/resource/compliance/adaptive
- Phase 2 (sequential): risk forecast
- Phase 3 (sequential): causal reasoning
- Phase 4: recommendation synthesis + explanation generation

### 20.3 Cross-agent reasoning
- Agents do not directly call each other
- They exchange through shared Blackboard state
- Downstream agents consume upstream artifacts, refining conclusions

This is the key to non-isolated reasoning.

---

## 21) Adaptive Intelligence, Predictive, Scenario Injection, Cross-Agent, Explainability

### 21.1 Adaptive intelligence
Implemented:
- rolling baselines per entity+metric
- sigma-based deviation
- threshold adaptation rate to avoid immediate contamination

### 21.2 Predictive/proactive
Implemented:
- risk trajectory projection + time horizon
- recommendation mapping before incident state

### 21.3 Scenario injection
Implemented:
- five stress scenarios to show resilience and response quality

### 21.4 Cross-agent reasoning
Implemented:
- causal links built from anomalies + policy + risk signals in temporal window

### 21.5 Explainability and transparency
Implemented:
- evidence IDs on outputs
- confidence + uncertainty
- deterministic template fallback when LLM unavailable

---

## 22) Workflow Monitoring in Backend and Frontend

### 22.1 Backend monitoring
- health endpoint for component liveness
- MCP brain endpoints (`/mcp/brain`, `/mcp/pulse`)
- agent activity endpoint (`/agents/activity`)
- DB stats endpoint (`/db/stats`)

### 22.2 Frontend monitoring
- workflow map
- anomaly center
- compliance and resource pages
- causal graph and insight feed

---

## 23) Compliance and Policy Setup by Team Manager (Target Design)

Add policy management APIs:
- `POST /policies` create
- `PUT /policies/{id}` update
- `PUT /teams/{team_id}/policy-profile`

Policy model:
- policy id, rule expression, severity, owner team, escalation channel, exemptions

Manager capabilities:
- set policy strictness by team
- define business hours per region
- set alert thresholds and escalation ladder

---

## 24) End-to-End Resource Usage Analysis

From ingestion to Slack:
1. receive metric/event
2. normalize + dedup
3. detect anomaly
4. link causal chain
5. forecast risk trajectory
6. compute confidence
7. generate insight + remedy
8. render in dashboard
9. push high-priority Slack alert
10. persist all artifacts for audit replay

---

## 25) How to Present to Judges (Demo Storyline)

1. Start with normal pulse (`/mcp/pulse`).
2. Inject `CASCADING_FAILURE` scenario.
3. Run one cycle and open anomaly center.
4. Show risk moved from normal to at-risk/violation trajectory.
5. Open causal analysis and point to confidence-labeled links.
6. Open insight feed and show recommendations + evidence IDs.
7. Ask query: "What will happen if ignored?" and show structured answer.
8. Show DB stats and graph relation endpoints for persistence proof.
9. Show local Docker architecture (no cloud dependency).

Judge-ready message:
- Not a dashboard clone
- Not only alerting
- It reasons, predicts, explains, and recommends with traceability

---

## 26) Competitive Differentiation

Compared to typical observability tools:
- We do cross-agent reasoning, not isolated threshold alerts
- We produce causal + predictive narratives, not just charts
- We expose confidence + uncertainty, not opaque decisions
- We keep evidence lineage for every recommendation
- We support adaptive baseline logic and scenario stress tests

---

## 27) Main Question: "How are we going to do this?"

Answer in one plan:
1. Keep current deterministic multi-agent core as reliability layer.
2. Add Kafka + webhook connectors for real enterprise inputs.
3. Add robust dedup/idempotency and source attribution.
4. Add policy management for team-level compliance setup.
5. Add Slack escalation service with confidence-aware routing.
6. Keep explainability strict: every output must have evidence + confidence + uncertainty.
7. Demonstrate all five judging themes live:
- adaptive
- predictive/proactive
- scenario injection
- cross-agent reasoning
- explainability/transparency

---

## 28) Implementation Backlog (Priority Order)

P0
- Kafka topics + worker consumers
- webhook ingestion endpoints + connectors
- Redis/SQLite idempotency dedup keys
- Slack notifier service

P1
- Team policy management APIs and UI
- Source-wise dashboards (security/cost/code/data)
- confidence decomposition (`signal`, `causal`, `action`)

P2
- WebSocket/SSE real-time push
- richer anomaly taxonomy and playbooks
- automated remediation guardrails (approval-based)

---

## 29) Final Architecture Statement
Chronos AI is an explainable cognitive observability system where:
- raw telemetry is ingested and normalized,
- specialized agents detect anomalies,
- risk and causal engines predict and reason across agents,
- explanation engine converts noisy data into interpretable action,
- alerts and dashboards deliver confidence-backed decisions,
- and all artifacts are persisted locally for audit and replay.

This is how we turn raw data junk into actionable insight with clarity and interpretability.
