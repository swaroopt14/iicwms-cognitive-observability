# IICWMS – System Architecture

## 1. Architectural Philosophy

IICWMS is designed as an **intelligence layer**, not a monitoring dashboard.

Key principles:
- Modular, agent-oriented design  
- Event-driven reasoning  
- Graph-based system representation  
- Evidence-first explainability  

The architecture intentionally prioritizes **reasoning clarity** over raw detection accuracy.

---

## 2. High-Level Architecture Diagram (Logical)

```
[ Scenario Generator ]
        |
        v
[ Event Stream ]
        |
        v
[ Evidence Blackboard ] <--------------------+
        |                                    |
        v                                    |
[ Specialized Agents ]                       |
(Workflow / Policy / Resource / RCA)         |
        |                                    |
        +------------ Hypotheses ------------+
        |
        v
[ Sovereign Orchestrator ]
        |
        v
[ Insights API ]
        |
        v
[ Frontend UI ]
```

---

## 3. Knowledge Graph Layer (Neo4j)

The IT environment is modeled as a **dynamic knowledge graph**.

### Node Types
- `User`
- `Event`
- `Workflow`
- `StateChange`
- `Resource`
- `Policy`

### Relationship Types
- `(User)-[:PERFORMED]->(Event)`
- `(Event)-[:PART_OF]->(Workflow)`
- `(Event)-[:RESULTED_IN]->(StateChange)`
- `(StateChange)-[:AFFECTED]->(Resource)`
- `(Event)-[:VIOLATED]->(Policy)`

This structure enables backward and forward traversal for **ripple-effect analysis**.

---

## 4. Evidence Blackboard

Agents do not communicate directly.

Instead, each agent writes an immutable **Hypothesis object** to a shared Evidence Blackboard.

```json
{
  "agent": "ResourceAgent",
  "claim": "CPU spike correlated with deployment",
  "evidence_ids": ["evt-21", "evt-22"],
  "confidence": 0.82
}
```

This design ensures:
- Full audit trail
- Deterministic replay
- No hidden reasoning paths

---

## 5. Sovereign Orchestrator

The Orchestrator:
- Reads all hypotheses
- Queries Neo4j for dependency paths
- Incorporates PyRCA root-cause rankings
- Generates a structured executive insight

It does not perform detection itself.

---

## 6. Causality & Reasoning Model

The system infers **probable causal relationships**, based on:
- Temporal precedence
- Graph path dependencies
- Correlation strength
- Root-cause ranking heuristics

**Formal causal proof is explicitly out of scope for Round-1.**

---

## 7. Observability vs Cognitive Observability

| Aspect | Traditional Monitoring | IICWMS |
|--------|----------------------|--------|
| Signal | Metrics & alerts | Evidence-backed insights |
| Logic | Thresholds | Multi-agent reasoning |
| Traceability | Logs | Graph paths |
| Outcome | Awareness | Understanding |

---

## 8. Extensibility

New agents can be added by:
- Reading from the same Evidence Blackboard
- Writing compatible Hypothesis objects

No changes to existing agents are required.

---

## 9. Round-1 Scope Clarification

**Implemented:**
- Core agents
- Graph reasoning
- Evidence ledger
- Insight synthesis

**Designed:**
- Adaptive learning
- Agent arbitration
- Predictive compliance

This aligns with PS-08 Round-1 evaluation criteria.
