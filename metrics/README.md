# chronos-risk-engine

> **Service 6** — System Risk Index (Health Tracking)

## Purpose

Tracks a **composite risk score (0-100)** across the entire system — like an "S&P 500 for operational risk." Every movement is traceable to specific agent contributions and evidence IDs.

## Weighted Components

| Component | Weight | Scoring |
|-----------|--------|---------|
| **Workflow Risk** | 35% | MISSING_STEP=+25, DELAY=+15, SEQUENCE=+10 |
| **Resource Risk** | 35% | CRITICAL=+30, WARNING=+15, DRIFT=+20 |
| **Compliance Risk** | 30% | +20 per policy violation |

## Risk States

```
NORMAL (0-30) → DEGRADED (30-50) → AT_RISK (50-70) → CRITICAL (70-90) → VIOLATION/INCIDENT (90+)
```

## Interface

| Method | Purpose |
|--------|---------|
| `record_cycle()` | Process completed reasoning cycle |
| `get_current()` | Current risk state + component breakdown |
| `get_history()` | Risk over time (last 100 cycles) |
| `get_trend()` | increasing / decreasing / stable |

## Configuration

- **Baseline:** 20.0 (never 0 in real systems)
- **History depth:** 100 cycles
- **Trend window:** Last 10 data points

## Technology

- **Language:** Python 3.10+
- **Models:** Pydantic v2
- **Storage:** In-memory with cycle-level snapshots
