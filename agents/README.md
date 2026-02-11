# chronos-reasoning

> **Service 3** — Multi-Agent Reasoning Layer (9 Specialized Agents)

## Purpose

The reasoning engine of Chronos AI. Nine specialized agents analyze observations independently and write findings to the shared Blackboard. **Agents never communicate directly** — all coordination happens through SharedState.

## Agent Registry

| # | Agent | Type | Detects / Does |
|---|-------|------|----------------|
| 1 | `WorkflowAgent` | Detection | Delays, missing steps, sequence violations |
| 2 | `ResourceAgent` | Detection | Sustained spikes, drift trends |
| 3 | `ComplianceAgent` | Detection | Silent policy violations (5 policies) |
| 4 | `AdaptiveBaselineAgent` | Detection | Sigma deviations from learned normal |
| 5 | `RiskForecastAgent` | Prediction | NORMAL → DEGRADED → AT_RISK → VIOLATION → INCIDENT |
| 6 | `CausalAgent` | Reasoning | Cause-effect chains with confidence scores |
| 7 | `MasterAgent` | Coordinator | Orchestrates cycles, ranks severity, maps recommendations |
| 8 | `QueryAgent` | Interface | Agentic RAG — answers natural language queries |
| 9 | `ScenarioInjectionAgent` | Testing | Injects 5 stress scenarios for demos |

## Execution Phases

```
Phase 1 (Parallel):   Workflow + Resource + Compliance + Baseline
Phase 2 (Sequential): Risk Forecast (reads Phase 1 outputs)
Phase 3 (Sequential): Causal Agent (reads all previous)
```

## I/O Contracts

| Agent | Reads | Writes |
|-------|-------|--------|
| WorkflowAgent | ObservationLayer (workflow events) | Blackboard → `anomalies[]` |
| ResourceAgent | ObservationLayer (resource metrics) | Blackboard → `anomalies[]` |
| ComplianceAgent | ObservationLayer (all events), Policies | Blackboard → `policy_hits[]` |
| AdaptiveBaselineAgent | ObservationLayer (metrics) | Blackboard → `anomalies[]` |
| RiskForecastAgent | Blackboard (anomalies, policy_hits) | Blackboard → `risk_signals[]` |
| CausalAgent | Blackboard (anomalies, policy_hits, risk_signals) | Blackboard → `causal_links[]` |
| MasterAgent | ObservationLayer, Blackboard (all) | Blackboard → `recommendations[]` |

## Technology

- **Language:** Python 3.10+
- **Concurrency:** `ThreadPoolExecutor` (max_workers=4)
- **Optional:** CrewAI integration for query pipeline
