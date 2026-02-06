# IICWMS Agent Responsibilities

This document details each agent's purpose, inputs, outputs, and detection methods.

---

## Agent Design Principles

All agents follow these principles:

1. **Stateless**: No internal state between invocations
2. **Graph-First**: Query Neo4j for context, don't maintain local state
3. **Opinion-Based**: Output structured opinions with confidence scores
4. **Explainable**: Every opinion includes human-readable explanation
5. **Auditable**: All outputs logged to Blackboard

---

## Workflow Agent

### Purpose
Detect anomalies in workflow execution: skipped steps, out-of-order execution, incomplete workflows.

### Input
| Input | Type | Description |
|-------|------|-------------|
| workflow_id | string | ID of workflow to analyze |
| events | List[Event] | Events associated with this workflow |

### Output
```python
Opinion(
    opinion_type: "STEP_SKIPPED" | "OUT_OF_ORDER" | "INCOMPLETE_WORKFLOW",
    confidence: float,  # 0.0 - 1.0
    evidence: {
        "workflow_id": str,
        "skipped_step_id": str,  # if applicable
        "expected_sequence": List[str],
        "actual_sequence": List[str],
        "detection_method": "graph_query"
    },
    explanation: str
)
```

### Detection Methods

#### Skipped Step Detection
```cypher
MATCH (w:Workflow {id: $workflow_id})-[:HAS_STEP]->(s:Step {mandatory: true})
WHERE NOT EXISTS((s)<-[:OCCURRED_IN_STEP]-(:Event {event_type: 'WORKFLOW_STEP_COMPLETE'}))
RETURN s
```

#### Out-of-Order Detection
Compares timestamps of step completion events against expected sequence from graph.

#### Incomplete Workflow Detection
Counts completed steps vs total steps, flags if ratio < 1.0 and no completion event.

### When This Agent Fires
- On workflow completion events
- On periodic workflow audits
- When explicitly triggered via API

---

## Policy Agent

### Purpose
Check compliance against policies encoded in the graph.

### Input
| Input | Type | Description |
|-------|------|-------------|
| events | List[Event] | Events to check |
| scope | Dict | Optional scope (workflow_id, resource_id) |

### Output
```python
PolicyOpinion(
    opinion_type: "POLICY_VIOLATION" | "POLICY_WARNING" | "COMPLIANCE_VERIFIED",
    confidence: float,
    policy_id: str,
    policy_name: str,
    severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
    evidence: {
        "workflow_id": str,
        "step_id": str,
        "required_event": str,
        "found_events": List[str]
    },
    explanation: str
)
```

### Detection Methods

#### Approval Policy Check
```cypher
MATCH (p:Policy {type: 'APPROVAL_REQUIRED'})-[:APPLIES_TO]->(s:Step)
WHERE NOT EXISTS((s)<-[:OCCURRED_IN_STEP]-(:Event {event_type: 'APPROVAL_GRANTED'}))
RETURN p, s
```

#### Access Pattern Check
Compares credential access events against baseline patterns stored in metadata.

#### Time Window Check
Verifies critical operations occur within allowed time windows.

### Policy Types Supported
| Policy Type | Description |
|-------------|-------------|
| APPROVAL_REQUIRED | Step requires approval event before completion |
| ACCESS_BASELINE | Access must match normal patterns |
| TIME_WINDOW | Operations restricted to certain hours |
| RESOURCE_LIMIT | Resource usage must stay within bounds |

---

## Resource Agent

### Purpose
Monitor resource consumption and detect anomalies.

### Input
| Input | Type | Description |
|-------|------|-------------|
| events | List[Event] | Resource metric events |
| resource_id | string | Optional filter for specific resource |

### Output
```python
ResourceOpinion(
    opinion_type: "THRESHOLD_BREACH" | "TREND_ANOMALY" | "CORRELATION_ALERT",
    confidence: float,
    resource_id: str,
    metric_type: str,
    evidence: {
        "metric_value": float,
        "threshold": float,
        "overage_percent": float,
        "trend_data": List[Dict]  # for trend anomalies
    },
    explanation: str
)
```

### Detection Methods

#### Threshold Breach
```python
if metric_value > threshold:
    generate_opinion(THRESHOLD_BREACH)
```

#### Trend Detection
Compares average of first third vs last third of observations:
```python
if last_third_avg > first_third_avg * 1.3:  # 30% increase
    generate_opinion(TREND_ANOMALY)
```

#### Correlation Detection
When multiple resources breach thresholds simultaneously:
```python
if len(breaching_resources) >= 2:
    generate_opinion(CORRELATION_ALERT)
```

### Default Thresholds
| Metric | Warning | Critical |
|--------|---------|----------|
| memory_usage | 75% | 90% |
| cpu_usage | 70% | 85% |
| disk_usage | 80% | 95% |
| network_latency | 100ms | 500ms |

---

## RCA Agent (Root Cause Analysis)

### Purpose
Build causal hypotheses from anomalies and events.

### Input
| Input | Type | Description |
|-------|------|-------------|
| anomalies | List[Opinion] | Anomalies from other agents |
| events | List[Event] | Timeline of events |
| graph_context | Dict | Additional graph state |

### Output
```python
RCAOpinion(
    opinion_type: "ROOT_CAUSE_HYPOTHESIS" | "CAUSAL_CHAIN" | "CONTRIBUTING_FACTOR",
    confidence: float,
    anomaly_id: str,
    hypothesis: str,
    causal_chain: List[str],  # ordered list of events/anomalies
    evidence: {
        "analysis_method": "temporal_proximity" | "graph_traversal" | "chain_analysis",
        "preceding_events": List[Dict],
        "workflow_structure": List[Dict]  # if applicable
    },
    explanation: str
)
```

### Analysis Methods

#### Temporal Correlation
Finds events that occurred shortly before the anomaly:
```python
preceding_events = [e for e in events if e.timestamp < anomaly.timestamp]
```

#### Structural Causality (Graph-Based)
Traces dependencies in the graph:
```cypher
MATCH (w:Workflow)-[:HAS_STEP]->(s:Step)-[:REQUIRES]->(prereq:Step)
RETURN s, prereq
```

#### Causal Chain Building
Orders anomalies by timestamp and constructs a narrative chain.

### Important Notes

> "PyRCA usage is scoped to specific anomaly types"

Full PyRCA integration (Bayesian networks, etc.) is future work. Current implementation uses:
- Temporal proximity heuristics
- Graph structure traversal
- Simple chain construction

> "Probable causal relationships, not formal proof"

All RCA outputs are labeled as hypotheses, not definitive causes.

---

## Master Agent

### Purpose
Orchestrate specialized agents and synthesize insights.

### Input
| Input | Type | Description |
|-------|------|-------------|
| events | List[Event] | All events to analyze |
| context | Dict | Scope (workflow_id, resource_id, etc.) |

### Output
```python
Insight(
    category: "COMPLIANCE_VIOLATION" | "WORKFLOW_ANOMALY" | "RESOURCE_ISSUE" | "SECURITY_CONCERN",
    severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO",
    title: str,
    summary: str,
    confidence: float,  # Aggregated from contributing opinions
    contributing_opinions: List[str],  # Opinion IDs
    evidence_chain: List[Dict],
    recommended_actions: List[str],
    explanation: str
)
```

### Orchestration Flow

1. **Collect Opinions**: Run all specialized agents
2. **Log to Blackboard**: Record all opinions
3. **Run RCA**: Analyze detected anomalies
4. **Group Opinions**: By category (workflow, policy, resource)
5. **Synthesize Insights**: Aggregate confidence, determine severity
6. **Generate Recommendations**: Based on category

### Confidence Aggregation
```python
avg_confidence = sum(confidences) / len(confidences)
max_confidence = max(confidences)
aggregate = (avg_confidence + max_confidence) / 2
```

### Severity Determination
Based on:
- Category (policy violations default HIGH)
- Confidence level
- Explicit severity in opinions

---

## Agent Interaction Diagram

```
                    ┌─────────────────┐
                    │  Master Agent   │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │   Workflow   │ │    Policy    │ │   Resource   │
    │    Agent     │ │    Agent     │ │    Agent     │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                │                 │
           │                │                 │
           ▼                ▼                 ▼
    ┌─────────────────────────────────────────────────┐
    │              BLACKBOARD (Evidence Store)         │
    │                                                  │
    │  All opinions logged with:                       │
    │  • UUID                                          │
    │  • Timestamp                                     │
    │  • Agent ID                                      │
    │  • Evidence                                      │
    │  • Explanation                                   │
    └──────────────────────┬──────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  RCA Agent   │
                    │  (Analyzes   │
                    │   opinions)  │
                    └──────────────┘
```

---

## Adding New Agents

To add a new agent:

1. Create `agents/new_agent.py` following the pattern:
```python
class NewAgent:
    def __init__(self, neo4j_client):
        self.neo4j_client = neo4j_client
        self.agent_name = "new_agent"
    
    def analyze(self, events, context) -> List[Opinion]:
        # Query graph
        # Detect anomalies
        # Return opinions
        pass
```

2. Add to `agents/__init__.py`
3. Register in `MasterAgent.__init__`
4. Document in this file
