# chronos-rag

> **Service 7** — Reasoning-Augmented Generation (Query Engine)

## Purpose

A **reasoning query interface** (not a chatbot) that answers natural language questions by reasoning over agent outputs, not raw logs. Powers the "Ask Chronos AI" feature.

## Query Pipeline

```
User Question → Decompose → Route to Agents → Retrieve Evidence → Synthesize Answer
```

## Supported Query Types

| Type | Example | Routes To |
|------|---------|-----------|
| `RISK_STATUS` | "What is the current risk level?" | Risk signals, anomalies |
| `CAUSAL_ANALYSIS` | "Why is vm_api_01 slow?" | Causal links, anomalies |
| `COMPLIANCE_CHECK` | "Are there any violations?" | Policy hits, compliance |
| `WORKFLOW_HEALTH` | "Which workflows are delayed?" | Workflow anomalies |
| `RESOURCE_STATUS` | "What's the CPU status?" | Resource metrics, anomalies |
| `PREDICTION` | "What will happen next?" | Risk signals, trends |
| `GENERAL` | "Give me a system summary" | All agents |

## Response Format

```json
{
  "answer": "Evidence-backed answer",
  "supporting_evidence": ["evt_042", "anom_015"],
  "confidence": 0.85,
  "uncertainty": "Based on last 5 reasoning cycles",
  "query_decomposition": { "type": "CAUSAL_ANALYSIS", "agents": ["causal", "resource"] }
}
```

## Key Differentiator

Reasons over **agent outputs** (anomalies, causal links, risk signals) — not raw logs. Every answer is backed by evidence from the Blackboard.

## Technology

- **Language:** Python 3.10+
- **Mode 1:** Pattern-matching RAG (deterministic)
- **Mode 2:** CrewAI-powered (optional, `ENABLE_CREWAI=true`)
