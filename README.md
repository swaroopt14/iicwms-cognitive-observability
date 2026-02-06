# IICWMS – Cognitive Observability Platform  
### Intelligent IT Compliance & Workflow Monitoring System (PS-08)

> **Moving beyond monitoring into Cognitive Observability**

---

## 🚩 Problem Overview

Modern IT systems operate through complex workflows involving users, services, resources, and policies.  
As scale increases, traditional monitoring tools fail to provide **understanding** — they surface metrics and alerts but do not explain *why* failures happen or *what actions should be taken*.

This leads to:
- Silent workflow anomalies  
- Undetected compliance violations  
- Resource inefficiencies  
- Delayed incident response  

---

## 🧠 Our Solution: Cognitive Observability

**IICWMS** is a **multi-agent, graph-driven intelligence system** that reasons over simulated IT operations to produce **auditable, traceable, retryable, and explainable insights**.

Instead of answering *"What is broken?"*, the system answers:

- **Why did this happen?**
- **What is the most probable root cause?**
- **What ripple effects does this create across the system?**
- **What action should be taken next?**

---

## 🏗️ High-Level Architecture

The system is built around a **coordinated multi-agent architecture** with a shared **Evidence Blackboard** and a **graph-based system model**.

Core components:
- Simulated IT environment & event generator  
- Specialized analytical agents (workflow, policy, resource, RCA)  
- Evidence Blackboard (immutable hypothesis ledger)  
- Neo4j Knowledge Graph (system state & dependencies)  
- Sovereign Orchestrator (master reasoning agent)  
- Minimal interpretability-focused UI  

> The system follows the **Observe → Reason → Explain** paradigm mandated by PS-08.

---

## 🤖 Multi-Agent Design

### Implemented Agents (Round-1)
- **Workflow Deviation Agent** – detects missing steps & invisible delays  
- **Policy Combination Agent** – detects high-risk policy intersections  
- **Resource Correlation Agent** – correlates resource spikes with workflows  
- **RCA Hypothesis Agent (PyRCA)** – ranks probable root causes (scoped)  
- **Sovereign Orchestrator** – synthesizes insights & explanations  

### Designed (Future Scope)
- Drift / baseline evolution agent  
- Consistency & confidence validation agent  

---

## 🧩 Graph-Based Reasoning

The IT environment is modeled as a **dynamic knowledge graph** in Neo4j:

- Nodes: Users, Events, Workflows, Resources, Policies, StateChanges  
- Edges: PERFORMED, PART_OF, RESULTED_IN, AFFECTED, VIOLATED  

This enables **path-based reasoning**, such as tracing a policy violation back to the exact user action and system state change that caused it.

---

## 🧾 Explainability & ATRE Principles

Every insight produced by the system is:

- **Auditable** – backed by immutable evidence entries  
- **Traceable** – linked to graph paths and event UUIDs  
- **Retryable** – agents are stateless and re-runnable  
- **Explainable** – insights cite evidence, not intuition  

LLMs are used **only** for narrative explanation, never for detection or enforcement.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-----|-----------|
| Backend | Python 3.10, FastAPI, Pydantic v2 |
| Graph | Neo4j Aura (Community / Free Tier) |
| Agents | Stateless Python functions |
| RCA | PyRCA (Salesforce) – scoped usage |
| Blackboard | JSONL Evidence Ledger |
| AI | Gemini 1.5 Pro / GPT-4o (explanations only) |
| Frontend | React + react-force-graph |
| Simulation | Faker + Scenario Generator |

---

## ▶️ Running the System (Local)

```bash
# Backend
pip install -r requirements.txt
uvicorn api.server:app --reload

# Frontend
cd frontend/dashboard
npm install
npm run dev
```

Neo4j Aura credentials are configured via `.env`.

---

## 🎥 Demo Video

📺 **Demo Video Link**: *(to be added before submission)*

The video demonstrates:
- Scenario injection
- Agent hypothesis generation
- Graph-based reasoning
- Explainable executive insight synthesis

---

## 🚀 Future Scope

- Adaptive baseline learning  
- Confidence arbitration across agents  
- Predictive compliance simulation  
- Extended causal graph reasoning  

> **Round-1 focuses on architectural validation and reasoning flow, not production completeness.**

---

## 📜 License

MIT License
