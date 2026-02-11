# chronos-graph

> **Service 8** — Graph Database (Knowledge Store)

## Purpose

Neo4j graph database integration for persistent storage of entities, relationships, and causal knowledge. Neo4j serves as the **authoritative system state** for complex graph queries.

## Graph Schema

### Node Types

| Node | Properties |
|------|-----------|
| `Workflow` | id, type, status, started_at |
| `Resource` | id, type, metrics |
| `Agent` | name, type, last_active |
| `Policy` | id, severity, condition |
| `Event` | id, type, timestamp, actor |
| `Anomaly` | id, type, confidence, evidence |

### Relationship Types

| Relationship | From → To | Purpose |
|-------------|-----------|---------|
| `CAUSED_BY` | Anomaly → Event | Causal attribution |
| `DETECTED_BY` | Anomaly → Agent | Agent attribution |
| `VIOLATES` | Event → Policy | Compliance linking |
| `IMPACTS` | Resource → Workflow | Dependency mapping |

## Files

| File | Purpose |
|------|---------|
| `neo4j_client.py` | Connection manager, CRUD operations, query execution |
| `schema.cypher` | Node/relationship definitions, constraints, indexes |
| `queries.cypher` | Pre-built Cypher queries for reasoning |

## Status

- **Round-1:** In-memory SharedState (Blackboard)
- **Round-2:** Neo4j as persistent graph store

## Technology

- **Language:** Python 3.10+
- **Database:** Neo4j (Aura or local)
- **Query Language:** Cypher
- **Driver:** `neo4j` Python driver
