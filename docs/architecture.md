# IICWMS – System Architecture

## 1. Architectural Philosophy

IICWMS is designed as an **intelligence layer**, not a monitoring dashboard.

Key principles:
- **Reality is generated, not inferred** - Only Simulation Engine creates events
- **Observe ≠ Reason ≠ Explain** - Separate layers with clear boundaries
- **Agents do not talk to each other** - Coordination through SharedState
- **LLMs forbidden for detection** - Only for explanation wording
- **Every claim must point to evidence** - No untraceable reasoning

---

## 2. System Layout

```
┌────────────────────┐
│ Simulation Engine  │   ← generates reality
└─────────┬──────────┘
          ↓
┌────────────────────┐
│ Observation Layer  │   ← raw facts only
└─────────┬──────────┘
          ↓
┌───────────────────────────────┐
│ Multi-Agent Reasoning Layer   │
│  • Workflow Agent             │
│  • Resource Agent             │
│  • Compliance Agent           │
│  • Risk Forecast Agent        │
│  • Causal Agent               │
│  • Master Agent               │
└─────────┬─────────────────────┘
          ↓
┌────────────────────┐
│ Explanation Engine │   ← human output
└────────────────────┘
```

---

## 3. Module Responsibilities

| Module | Can Read | Can Write | Forbidden |
|--------|----------|-----------|-----------|
| Simulation Engine | Internal state | Events | Policies |
| Observation Layer | Events | DB | Reasoning |
| Agents | Observation + State | State | Events |
| LLM | State | Text only | Decisions |

---

## 4. Data Model

### 4.1 Event (Immutable Fact)

```json
{
  "event_id": "evt_001",
  "type": "ACCESS_WRITE",
  "workflow_id": "wf_12",
  "actor": "user_42",
  "resource": "repo_A",
  "timestamp": "2026-02-06T22:14:12Z",
  "metadata": {}
}
```

**Rules:**
- No interpretation
- No severity
- No intelligence

### 4.2 Resource Metric

```json
{
  "resource_id": "vm_3",
  "metric": "network_latency_ms",
  "value": 420,
  "timestamp": "2026-02-06T22:14:15Z"
}
```

### 4.3 Policy (Static Definition)

```json
{
  "policy_id": "NO_AFTER_HOURS_WRITE",
  "condition": "WRITE && hour(timestamp) NOT IN [9..18]",
  "severity": "HIGH",
  "rationale": "Reduces audit and breach risk"
}
```

---

## 5. Shared State (Blackboard)

Agents communicate through a shared blackboard:

```json
{
  "cycle_id": "cycle_104",
  "facts": [...],
  "anomalies": [],
  "policy_hits": [],
  "risk_signals": [],
  "hypotheses": [],
  "causal_links": [],
  "recommendations": []
}
```

**Rules:**
- Each agent appends its own section
- No overwrites
- No deletions in same cycle

---

## 6. Agent Definitions

### Workflow Agent
- **Input:** Workflow events, expected durations
- **Detects:** Delays, missing steps, sequence violations

### Resource Agent
- **Input:** Resource metrics (time-windowed)
- **Detects:** Sustained spikes, drift trends
- **Important:** Single spikes ≠ anomaly, trend slope matters

### Compliance Agent
- **Input:** Events, policy definitions
- **Detects:** Silent violations

### Risk Forecast Agent
- **Purpose:** Predict risk trajectory (not exact failure)
- **States:** NORMAL → DEGRADED → AT_RISK → VIOLATION → INCIDENT

### Causal Agent
- **Input:** Anomalies, risk signals, policy hits
- **Output:** Cause-effect links with confidence
- **Method:** Temporal + dependency reasoning (no ML required)

### Master Agent (Coordinator)
- **Responsibilities:** Trigger agents, collect outputs, rank severity
- **Forbidden:** No deep reasoning, no LLM usage

---

## 7. Reasoning Cycle (Mandatory Flow)

```
Simulation Tick
      ↓
Observation ingest
      ↓
Master Agent starts cycle
      ↓
Agents run in parallel
      ↓
State populated
      ↓
Causal synthesis
      ↓
Explanation generation
```

**If this loop breaks → system fails.**

---

## 8. Explanation Engine

**Purpose:** Translate reasoning artifacts into human insight.

**Input:**
- Causal links
- Risk state
- Policy violations

**Output (LLM Allowed):**
```json
{
  "summary": "...",
  "why_it_matters": "...",
  "what_will_happen_if_ignored": "...",
  "recommended_actions": [...],
  "confidence": 0.72,
  "uncertainty": "Simulated environment"
}
```

---

## 9. Solution / Recommendation Logic

Solutions are **mapped, not invented**.

| Cause | Recommendation |
|-------|----------------|
| Resource saturation | Throttle jobs |
| SLA pressure | Pre-notify admins |
| Override risk | Temporary access guard |

**Never auto-apply.**

---

## 10. Phase-1 Success Criteria

✅ One workflow degrades  
✅ One silent compliance violation detected  
✅ Risk is predicted BEFORE violation  
✅ Cause is explained  
✅ Preventive action is suggested
