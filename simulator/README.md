# chronos-simulator

> **Service 1** — Simulation Engine (Reality Generation)

## Purpose

Generates simulated IT operations — workflows, resource metrics, access events — with emergent behavior from probabilistic rules. This is the **source of truth** for the entire system.

## What It Generates

| Domain | Events |
|--------|--------|
| **Workflows** | `WORKFLOW_START`, `STEP_START`, `STEP_COMPLETE`, `STEP_SKIP`, `COMPLETE` |
| **Access** | `ACCESS_READ`, `ACCESS_WRITE`, `ACCESS_DELETE` |
| **Resources** | `RESOURCE_ALLOCATE`, `RESOURCE_RELEASE` |
| **System** | `CONFIG_CHANGE`, `CREDENTIAL_ACCESS`, `LOGIN`, `LOGOUT` |

## Architectural Constraints

- No knowledge of policies
- No knowledge of agents
- No scripted scenarios
- Creates **reality**, not alerts
- Emergent anomalies from probabilistic rules

## Key Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Tick interval | 5 seconds | Simulation time unit |
| Workflow start probability | 10% per tick | New workflow creation |
| Step skip probability | 15% | Creates detectable anomalies |
| Unusual location probability | 10% | Compliance stress |

## Technology

- **Language:** Python 3.10+
- **Dependencies:** None (standalone module)
- **Interface:** `SimulationEngine.tick()` → events + metrics
