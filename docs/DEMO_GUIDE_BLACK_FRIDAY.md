# Chronos AIOps Demo Guide (Judge-Level, Detailed)

Last updated: 2026-02-16

---

## 1) Industry Problem Statement (Mapped to PS-08)

### Industry reality
- Large enterprises run:
  - Multiple projects
  - Multiple environments (`dev/staging/prod`)
  - Multiple teams and ownership layers
  - Multiple observability tools (Datadog, Prometheus, GitHub, K8s audit, custom webhooks)
- During peak traffic (for example Black Friday), failures are rarely single-cause.
- Traditional monitoring answers:
  - "What is red?"
- It often does **not** answer:
  - "Why did it happen?"
  - "What will happen in next 10–60 minutes?"
  - "What should each team do now?"
  - "Can we prove this in audit/postmortem?"

### Our PS-08 mapping
Chronos solves:
- Adaptive intelligence
- Predictive/proactive risk analysis
- Scenario injection (stress tests)
- Cross-agent reasoning
- Explainability and transparency

---

## 2) Our Solution (What We Built)

Chronos is a local-first cognitive observability platform:

`Observe -> Multi-Agent Reason -> Explain -> Act`

Core principles:
- Deterministic detection logic (not prompt magic)
- Evidence-first reasoning (every output linked to IDs/events)
- Append-only audit trail (blackboard cycles)
- Optional LLM only for wording/query polish; **not for scoring**

---

## 3) Data Sources (Where Data Comes From)

### Ingestion endpoints (API)
- `POST /ingest/envelope`
- `POST /ingest/github/webhook`
- `POST /observe/event`
- `POST /observe/metric`

### Typical source systems represented
- GitHub webhooks (`pull_request`, `workflow_run`)
- Prometheus-style metrics
- Datadog-style events/log-like signals
- K8s audit-like events
- Generic webhook/client/server signals

### Important clarification
In this demo build, many streams are simulated/normalized locally.  
We do **not** claim live paid vendor API pulling in this path. We ingest structured events and metrics into the Observation Layer.

---

## 4) How Logs/Events Are Fetched and Processed

### Source -> Observation
1. Source sends event/metric to ingestion endpoint.
2. Observation layer stores:
   - Events (`observe_event`)
   - Metrics (`observe_metric`)
3. Data is append-only for cycle processing.

### Observation -> Reasoning
MasterAgent pulls recent windows:
- events
- metrics

Then runs agents by phases:
- Phase 1 (parallel): workflow/resource/compliance/adaptive/code
- Phase 2 (sequential): risk forecast -> causal
- Phase 3: severity + recommendations

### Reasoning -> Explain
Explanation engine converts cycle artifacts into:
- summary
- why it matters
- impact if ignored
- recommended actions

---

## 5) Risk Classification (High/Medium/Low etc.)

There are two complementary layers:

### A) Risk state trajectory (RiskForecastAgent)
Risk states:
- `NORMAL`
- `DEGRADED`
- `AT_RISK`
- `VIOLATION`
- `INCIDENT`

Exact logic:
- `total_issues = anomaly_count + (2 * policy_violation_count)`
- `0 -> NORMAL`, `<=1 -> DEGRADED`, `<=3 -> AT_RISK`, `<=5 -> VIOLATION`, `>5 -> INCIDENT`
- Confidence:
  - `confidence = min(0.95, 0.5 + min(0.3, anomaly_count*0.1) + min(0.2, policy_violation_count*0.1))`

### B) Severity scoring (SeverityEngineAgent)
Score range: `0-10`, mapped to:
- `None`
- `Low`
- `Medium`
- `High`
- `Critical`

Formula style:
- Base score from issue type + confidence
- Context multipliers (asset/data/time/role/repetition/blast/module)
- Weighted delta, bounded and clamped

Exact equation:
- `weighted_delta = clamp(sum(weight_i * (factor_i - 1)), -0.4, +0.6)`
- `final_score = clamp(base_score * (1 + weighted_delta), 0, 10)`

This is deterministic numeric logic, not LLM prompt output.

---

## 6) Confidence Scoring (How and Why)

Confidence is computed by module-specific deterministic math:

### ResourceAgent
- Sustained threshold windows (for example 3 consecutive points)
- Critical/warning thresholds by metric

### AdaptiveBaselineAgent
- Rolling baseline
- Sigma deviation (`DEVIATION_THRESHOLD = 2.5`)

### RiskForecastAgent
- Base + issue volume increments
- Confidence rises with more corroborating anomalies/policy hits

### CausalAgent
- Pattern base confidence
- Temporal distance factor
- Final confidence adjusted by timing proximity

### SeverityEngineAgent
- Deterministic score composition and clamping to `0..10`

### RecommendationEngineAgent
- `confidence = 0.5 * base_rule + 0.2 * severity_norm + 0.3 * context_match`

### Query confidence
- Based on evidence confidence average + bounded evidence-volume bonus

Exact query confidence formula:
- `avg = mean(top10 evidence confidences clamped to 0..1)`
- `bonus = min(0.08, 0.01 * max(0, evidence_count - 3))`
- `query_confidence = min(1.0, avg + bonus)`

### Risk index (0-100) formula used for trend
- `risk_score = 0.35*workflow_risk + 0.35*resource_risk + 0.30*compliance_risk`
- Base for each component starts at `20`.
- Workflow impacts: `MISSING_STEP=25`, `WORKFLOW_DELAY=15`, `SEQUENCE_VIOLATION=20` (scaled by anomaly confidence)
- Resource impacts: `SUSTAINED_RESOURCE_CRITICAL=30`, `SUSTAINED_RESOURCE_WARNING=15`, `RESOURCE_DRIFT=10` (scaled by anomaly confidence)
- Compliance impact: `+20` per policy violation

### Explicit non-claim
We do **not** assign confidence "because LLM answered strongly."  
Confidence is produced by coded formulas + evidence quality.

---

## 7) How the System Adapts Over Time

Adaptive behavior is implemented in `AdaptiveBaselineAgent`:
- Rolling window (`WINDOW_SIZE = 50`)
- Baseline activation after minimum samples (`MIN_SAMPLES = 10`)
- Adaptive threshold smoothing (`ADAPTATION_RATE = 0.1`)

Meaning:
- The system learns normal resource behavior
- It reduces false positives from static thresholds
- It flags true baseline deviation using sigma logic

---

## 8) Black Friday Demo Scenario (Recommended Walkthrough)

### Story
During Black Friday traffic, checkout/onboarding volume surges:
- latency increases
- retries increase
- CPU saturates
- workflow steps miss SLA
- policy risk grows as teams attempt manual overrides

### Suggested demo flow
1. Start system and open dashboard.
2. Inject scenario:
   - `WORKLOAD_SURGE` and/or `PAYTM_HOTFIX_FAIL`
3. Run analysis cycle.
4. Show:
   - anomalies
   - risk trajectory
   - causal links
   - recommendations
5. Open Ask Chronos:
   - "Given projected_state=VIOLATION and impact_score=64, what should DevOps do in next 15 minutes?"
6. Show checklist response + evidence links.
7. Show audit timeline/export trail.

### Expected chain (example)
- Traffic/workload surge -> resource saturation -> workflow delays -> compliance pressure -> risk escalation

---

## 9) "Who Built What" Contribution Matrix

Use this table in presentation. Replace owner placeholders with names.

| Module | What was built | Logic behind it | Owner |
|---|---|---|---|
| Observation Layer | Event/metric ingestion and append-only storage | Preserve raw facts before reasoning | `<name>` |
| Workflow Agent | Delay/missing/sequence anomaly detection | SLA and step-order integrity checks | `<name>` |
| Resource Agent | Sustained spike + drift detection | Avoid single-spike noise; trend-aware detection | `<name>` |
| Compliance Agent | Policy violation detection | Catch silent governance failures | `<name>` |
| Adaptive Baseline | Rolling baseline + sigma deviations | Self-adapting normal behavior model | `<name>` |
| Risk Forecast | Risk-state trajectory | Predict escalation window, not only current state | `<name>` |
| Causal Agent | Cause-effect linkage | Temporal + known pattern reasoning | `<name>` |
| Severity Engine | Context-aware severity score | Deterministic 0-10 risk translation | `<name>` |
| Recommendation Engine | Action generation + confidence | Rule-based runbook with explainable confidence | `<name>` |
| Query/Chronos AI | Evidence-backed NL interface | Compact answers + actionable checklist | `<name>` |
| Frontend (Overview/Compliance/Resource/etc.) | Real-time visual storytelling | Make reasoning interpretable for ops + judges | `<name>` |
| API + Integrations + Slack | Endpoints, simulation, alerts | End-to-end usable workflow | `<name>` |

---

## 10) Demo Script (What to Say)

### 10-second opener
"Traditional monitoring tells us what is red. Chronos shows what failed, why it failed, what happens next, and what each team should do now, with evidence."

### Scoring transparency line
"All risk and confidence values come from deterministic formulas in code. LLM is optional for phrasing, not for anomaly/risk scoring."

### Business line
"In Black Friday conditions, the value is reducing MTTD/MTTR and avoiding silent compliance drift while traffic is peaking."

---

## 11) Commands (Quick)

Backend:
```bash
source .venv/bin/activate
ENABLE_LANGGRAPH=true ENABLE_LANGGRAPH_AGENTS=true ENABLE_VECTOR_STORE=false uvicorn api.server:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm run dev
```

Health checks:
```bash
curl http://localhost:8000/system/health
curl http://localhost:8000/risk/current
curl http://localhost:8000/alerts/slack/status
```

---

## 12) Judge Q&A (Short Answers)

### "Is this LLM scoring?"
No. Detection, risk, severity, and recommendation confidence are deterministic code paths. LLM is not used for core scoring.

### "Can you prove why alert fired?"
Yes. Evidence IDs and cycle artifacts are retained and linked in blackboard/insight outputs.

### "Can it adapt?"
Yes. Adaptive baseline updates thresholds from rolling behavior and sigma deviations.

### "Can it test future changes safely?"
Yes. What-if sandbox/simulation paths are read-only and produce impact deltas with confidence reasons.
