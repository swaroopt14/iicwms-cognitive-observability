# chronos-blackboard

> **Service 4** — Shared Reasoning State (Blackboard Pattern)

## Purpose

The **central communication hub** between all agents. Agents never talk to each other directly — they read from and write to the Blackboard. This ensures all reasoning is **inspectable**, **auditable**, and **debuggable**.

## Data Models

| Model | Fields | Written By |
|-------|--------|-----------|
| `ReasoningCycle` | cycle_id, started_at, completed_at | MasterAgent |
| `Fact` | claim, evidence_ids, source_agent | Any agent |
| `Anomaly` | type, entity, confidence, evidence_ids, agent | Detection agents |
| `PolicyHit` | policy_id, event_id, violation_type, agent | ComplianceAgent |
| `RiskSignal` | entity, current_state, projected_state, confidence | RiskForecastAgent |
| `CausalLink` | cause → effect, confidence, reasoning, evidence_ids | CausalAgent |
| `Hypothesis` | claim, confidence, supporting/counter evidence | QueryAgent |
| `Recommendation` | cause, action, urgency, rationale | MasterAgent |

## Cycle Lifecycle

```
start_cycle() → agents append findings → complete_cycle() → persist to JSONL
```

## Constraints

- Each agent appends **only** to its own section
- No overwrites within the same cycle
- No deletions within the same cycle
- Cycles are **immutable** once completed
- All entries must include `evidence_ids`

## Storage

- **Format:** JSONL persistence (`blackboard/cycles.jsonl`)
- **In-Memory:** Fast access during active cycle
- **History:** Last 100 cycles retained

## Technology

- **Language:** Python 3.10+
- **Models:** Pydantic v2 dataclasses
- **Persistence:** JSONL file store
