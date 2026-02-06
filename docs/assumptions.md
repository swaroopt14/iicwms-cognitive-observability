# IICWMS – Assumptions & Constraints

This document explicitly lists all assumptions made for Round-1 evaluation, as required by PS-08.

---

## 1. Data Assumptions

- All IT events, workflows, and metrics are **simulated**.
- No real enterprise or customer data is used.
- Event distributions are intentionally controlled to demonstrate anomalies and violations.

This allows focus on **architecture and reasoning**, not data acquisition.

---

## 2. Detection Assumptions

- Anomaly detection is **heuristic-based**, not ML-trained.
- Baselines are computed from recent simulated windows.
- Detection accuracy is secondary to **explainability**.

This aligns with PS-08 guidance prioritizing reasoning over precision.

---

## 3. Graph Assumptions

- Neo4j is treated as the **authoritative system state**.
- Graph structure is intentionally minimal.
- Advanced graph algorithms (GDS, Graph ML) are not used in Round-1.

Graph traversal is used for **traceability**, not prediction.

---

## 4. Causality Assumptions

- The system infers **probable causes**, not mathematically proven causality.
- PyRCA is used only for **root-cause hypothesis ranking** within a predefined causal graph.
- Final insights are framed as **decision support**, not ground truth.

---

## 5. AI / LLM Usage

- LLMs are used **only** for:
  - Natural-language explanation
  - Executive summary generation
- LLMs do **not**:
  - Detect anomalies
  - Enforce policies
  - Modify system state

This ensures deterministic system behavior.

---

## 6. System Scope Limitations

Not included in Round-1:
- Production deployment
- Real-time streaming infrastructure
- User authentication
- Adaptive learning loops
- Automated remediation execution

These are explicitly marked as **future scope**.

---

## 7. Evaluation Alignment

This implementation is designed to satisfy Round-1 evaluation priorities:

- Modular multi-agent architecture  
- Coordinated reasoning  
- Clear observe → reason → explain flow  
- Explicit assumptions and constraints  

---

## 8. Transparency Statement

All limitations, assumptions, and simplifications are documented intentionally to ensure:
- Judge clarity  
- Architectural honesty  
- Defensible evaluation  

This project emphasizes **understanding systems**, not overstating capabilities.
