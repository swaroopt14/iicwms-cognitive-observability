# IICWMS – Assumptions & Constraints

This document explicitly lists all assumptions made for Phase-1 evaluation, as required by PS-08.

---

## 1. Data Assumptions

- All IT events, workflows, and metrics are **simulated**
- No real enterprise or customer data is used
- Event distributions are intentionally controlled to demonstrate anomalies
- Simulation generates emergent behavior, not scripted scenarios

This allows focus on **architecture and reasoning**, not data acquisition.

---

## 2. Detection Assumptions

- Anomaly detection is **heuristic-based**, not ML-trained
- Baselines are computed from recent simulated windows
- Detection accuracy is secondary to **explainability**
- Single spikes are NOT anomalies - sustained patterns matter

This aligns with PS-08 guidance prioritizing reasoning over precision.

---

## 3. Agent Assumptions

- Agents are stateless and re-runnable
- Agents do NOT communicate directly with each other
- All coordination happens through SharedState (Blackboard)
- Each agent has clearly defined boundaries

---

## 4. Causality Assumptions

- The system infers **probable causes**, not mathematically proven causality
- Causal reasoning uses temporal precedence + dependency patterns
- No ML required - temporal + dependency reasoning is sufficient
- Final insights are framed as **decision support**, not ground truth

---

## 5. AI / LLM Usage

**LLMs are used ONLY for:**
- Natural-language explanation
- Executive summary generation

**LLMs do NOT:**
- Detect anomalies
- Enforce policies
- Modify system state
- Make decisions

This ensures **deterministic system behavior**.

---

## 6. System Scope Limitations

**Not included in Phase-1:**
- Production deployment
- Real-time streaming infrastructure
- User authentication
- Adaptive learning loops
- Automated remediation execution
- Graph database (Neo4j) - using in-memory state

These are explicitly marked as **future scope**.

---

## 7. Observation Layer

- Append-only storage
- Time-ordered events
- No aggregation at observation level
- Raw facts only, no interpretation

---

## 8. Risk Forecast

- Predicts risk trajectory, not exact failure time
- Uses risk states: NORMAL → DEGRADED → AT_RISK → VIOLATION → INCIDENT
- Provides confidence scores and time horizons
- Based on accumulated evidence, not speculation

---

## 9. Common Failure Modes (Explicitly Avoided)

❌ "LLM detected anomaly"  
❌ Scripted demo data  
❌ Agents calling each other  
❌ Auto-fixing systems  
❌ Dashboards without reasoning  

---

## 10. Evaluation Alignment

This implementation is designed to satisfy Round-1 evaluation priorities:

- Modular multi-agent architecture
- Coordinated reasoning through shared state
- Clear observe → reason → explain flow
- Explicit assumptions and constraints

---

## 11. Transparency Statement

All limitations, assumptions, and simplifications are documented intentionally to ensure:

- Judge clarity
- Architectural honesty
- Defensible evaluation

This project emphasizes **understanding systems**, not overstating capabilities.
