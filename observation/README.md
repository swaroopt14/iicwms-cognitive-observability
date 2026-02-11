# chronos-observer

> **Service 2** — Observation Layer (Raw Fact Ingestion)

## Purpose

Append-only, time-ordered storage of raw events and metrics. The Observation Layer is the **single source of facts** — no aggregation, no interpretation, no reasoning.

## Interface

| Method | Input | Output |
|--------|-------|--------|
| `observe_event()` | Raw event from simulation | Persisted `ObservedEvent` |
| `observe_metric()` | Raw metric from simulation | Persisted `ObservedMetric` |
| `get_event_window()` | Time range, type, workflow | Filtered events |
| `get_metric_window()` | Time range, resource, metric | Filtered metrics |
| `get_recent_events(n)` | Count | Latest N events |
| `get_recent_metrics(n)` | Count | Latest N metrics |

## Storage

- **Format:** JSONL (JSON Lines)
- **Location:** `observation/events.jsonl`
- **Mode:** Append-only (immutable once written)
- **Concurrency:** Thread-safe with locks

## Architectural Constraints

- No aggregation at observation level
- No interpretation or scoring
- No reasoning or intelligence
- Pure fact storage only

## Technology

- **Language:** Python 3.10+
- **Persistence:** JSONL file store
- **Thread Safety:** `threading.Lock`
