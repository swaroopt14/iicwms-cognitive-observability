# IICWMS – Agent Responsibilities

## Overview

All agents follow these principles:
- **Stateless** - Can be re-run at any time
- **No direct communication** - Use SharedState only
- **Evidence-backed** - Every claim points to data
- **Single responsibility** - One clear purpose

---

## 1. Workflow Agent

**Purpose:** Monitor workflow execution for anomalies.

### Input
- Workflow events from Observation Layer
- Expected step durations (from definitions)

### Detects
- **WORKFLOW_DELAY** - Step exceeds SLA
- **MISSING_STEP** - Step was skipped
- **SEQUENCE_VIOLATION** - Out-of-order execution

### Output
```json
{
  "type": "WORKFLOW_DELAY",
  "workflow_id": "wf_12",
  "evidence": ["step_DEPLOY exceeded SLA"]
}
```

### Design Notes
- Tracks active workflows in memory
- Compares actual vs expected durations
- High confidence for skipped steps (0.95)

---

## 2. Resource Agent

**Purpose:** Monitor resource conditions and trends.

### Input
- Resource metrics (time-windowed)

### Detects
- **SUSTAINED_RESOURCE_CRITICAL** - Multiple readings at critical level
- **SUSTAINED_RESOURCE_WARNING** - Multiple readings at elevated level
- **RESOURCE_DRIFT** - Consistent upward trend

### Important Rules
- **Single spikes ≠ anomaly**
- Trend slope matters more than absolute values
- Requires sustained window of readings (3+)

### Output
```json
{
  "type": "SUSTAINED_RESOURCE_CRITICAL",
  "resource_id": "vm_web_01",
  "evidence": ["cpu_percent at 95% for 3 readings"]
}
```

---

## 3. Compliance Agent

**Purpose:** Check events against policy definitions.

### Input
- Events from Observation Layer
- Static policy definitions

### Detects
- **SILENT** violations - Events that violate policy without raising alerts

### Policies Implemented
| Policy | Checks |
|--------|--------|
| NO_AFTER_HOURS_WRITE | WRITE operations outside 9-18 |
| NO_UNUSUAL_LOCATION | Access from untrusted networks |
| NO_UNCONTROLLED_SENSITIVE_ACCESS | Sensitive resources without workflow |
| NO_SVC_ACCOUNT_WRITE | Service account direct writes |
| NO_SKIP_APPROVAL | Skipped approval steps |

### Output
```json
{
  "policy_id": "NO_AFTER_HOURS_WRITE",
  "event_id": "evt_001",
  "violation_type": "SILENT"
}
```

---

## 4. Risk Forecast Agent

**Purpose:** Predict risk trajectory, NOT exact failure.

### Risk States
```
NORMAL → DEGRADED → AT_RISK → VIOLATION → INCIDENT
```

### Input
- Anomalies from other agents
- Policy hits from Compliance Agent

### Output
```json
{
  "entity": "wf_12",
  "current_state": "DEGRADED",
  "projected_state": "AT_RISK",
  "confidence": 0.67,
  "time_horizon": "10–15 min"
}
```

### Design Notes
- Only signals when risk is **escalating**
- Provides time horizons, not exact times
- This is how we predict BEFORE it happens

---

## 5. Causal Agent

**Purpose:** Identify cause-effect relationships.

### Input
- Anomalies
- Risk signals
- Policy hits

### Method
- **Temporal precedence** - Cause must precede effect
- **Dependency patterns** - Known cause-effect relationships
- **Correlation strength** - Closer events = higher confidence

### Known Patterns
| Cause | Effect | Confidence |
|-------|--------|------------|
| SUSTAINED_RESOURCE_CRITICAL | WORKFLOW_DELAY | 0.85 |
| RESOURCE_DRIFT | WORKFLOW_DELAY | 0.60 |
| MISSING_STEP | SILENT (policy) | 0.90 |

### Output
```json
{
  "cause": "NETWORK_LATENCY",
  "effect": "WORKFLOW_DELAY",
  "confidence": 0.81
}
```

### Design Notes
- **No ML required**
- Temporal + dependency reasoning is sufficient
- Adjusts confidence based on temporal distance

---

## 6. Master Agent (Coordinator)

**Purpose:** Orchestrate the reasoning cycle.

### Responsibilities
1. Trigger agents (async/parallel)
2. Collect outputs to SharedState
3. Rank severity
4. Trigger explanation generation

### Forbidden
- No deep reasoning (delegates to specialized agents)
- No LLM usage
- No direct event creation

### Reasoning Cycle
```
1. Start cycle
2. Get observations
3. Run specialized agents (parallel)
4. Run risk forecast
5. Run causal analysis
6. Generate recommendations
7. Complete cycle
```

---

## Recommendation Logic

The Master Agent maps causes to recommendations (NOT invented):

| Cause | Action | Urgency |
|-------|--------|---------|
| Resource saturation | Throttle jobs | HIGH |
| SLA pressure | Pre-notify admins | MEDIUM |
| Missing step | Temporary access guard | HIGH |
| Sequence violation | Enforce ordering | MEDIUM |

**Never auto-apply recommendations.**
