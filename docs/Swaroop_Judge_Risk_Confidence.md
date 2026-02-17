# Swaroop Judge Notes (Chronos / IICWMS)

## How Confidence and Risk Scores Are Calculated (Deterministic, Explainable)

This is the core question judges will ask.

Chronos does **not** rely on "LLM intuition" for risk. Scoring is engineered, repeatable math:
- deterministic inputs (events, metrics, anomalies, policy hits)
- deterministic formulas (documented weights and clamps)
- traceable outputs (every score links to evidence IDs)

---

# 1) Define "Risk" in Chronos

Risk is **not severity**.

Risk means:

> Likelihood of operational damage × potential impact magnitude, adjusted by context.

Chronos expresses this as:

```text
RiskScore = ProbabilityFactor × ImpactFactor × ContextMultiplier
```

Everything in the platform feeds one of these three buckets.

---

# 2) Confidence Score (0–100): What It Means and Why It Changes

**Confidence** answers:

> "How strongly do we believe this causal link / forecast / insight is true given current evidence?"

Confidence is **evidence reliability**, not "probability the AI is correct".

## 2.1 Confidence in the current implementation (RiskForecastAgent)

Chronos forecasts risk states per entity (workflow/policy/resource) and computes a deterministic confidence.

Inputs:
- `anomaly_count`
- `policy_violation_count` (policy hits are weighted more)

Exact formula:

```text
confidence = min(0.95,
  0.5
  + min(0.3, anomaly_count * 0.1)
  + min(0.2, policy_violation_count * 0.1)
)
```

Interpretation:
- more independent signals in recent cycles → higher confidence
- confidence is capped (never 100%) to avoid false certainty

## 2.2 What judges should see in UI output

Every confidence value is accompanied by:
- evidence IDs (anomaly IDs, policy hit IDs)
- reasoning string (what signals increased confidence)

---

# 3) Risk Scoring (0–100): Fully Deterministic

Chronos produces **risk trajectory**, not "magic predictions".

There are two layers:
1. **Risk State** (NORMAL → DEGRADED → AT_RISK → VIOLATION → INCIDENT)
2. **Risk Index / Risk Score** (0–100) for dashboards and trend charts

## 3.1 ProbabilityFactor (how likely it escalates)

ProbabilityFactor is computed from **observable recurrence signals**.

In the current implementation, probability is represented by:
- anomaly accumulation (`anomaly_count`)
- policy breach accumulation (`policy_violation_count`, weighted 2x)

The escalation driver:

```text
total_issues = anomaly_count + (2 * policy_violation_count)
```

Projected risk state mapping:

```text
if total_issues == 0  -> NORMAL
if total_issues <= 1  -> DEGRADED
if total_issues <= 3  -> AT_RISK
if total_issues <= 5  -> VIOLATION
else                  -> INCIDENT
```

This is deterministic: same inputs → same state.

## 3.2 ImpactFactor (how bad it could be)

Impact is derived from **graph context and metadata** (what is affected and how far it propagates), such as:
- workflow criticality (deployments weighted higher)
- dependency depth / blast radius (more downstream nodes = higher impact)
- policy sensitivity (security/compliance impacts carry higher weight)

Judges can validate this because:
- the affected nodes/workflows are visible in Root Cause Explorer
- evidence IDs tie back to specific workflow events/metrics/policy hits

## 3.3 ContextMultiplier (when/where it happens)

ContextMultiplier adjusts risk based on operational context:
- production vs non-production
- off-hours vs business hours
- maintenance window / change window

This multiplier is documented and configurable (no hidden model).

## 3.4 Final RiskScore (0–100)

Conceptually:

```text
RiskScore = (ProbabilityFactor × ImpactFactor) × ContextMultiplier
RiskScoreFinal = clamp(0, 100, round(RiskScore * 100))
```

In the current demo build, dashboards also express risk as a **risk index** derived from risk states:

```text
NORMAL   -> 0–20 (baseline)
DEGRADED -> ~25
AT_RISK  -> ~55
VIOLATION-> ~80
INCIDENT -> ~95
```

This makes the risk trend chart stable, interpretable, and judge-friendly.

---

# 4) Worked Example (Judge-Friendly)

Scenario:
Unapproved deployment by an admin at 11:45 PM triggers sustained CPU pressure and workflow delay.

Signals:
- anomalies detected (workflow delay, resource sustained breach)
- policy hit detected (approval skipped)

Deterministic forecast:
- `anomaly_count` increases
- `policy_violation_count` increases
- `total_issues = anomaly_count + 2*policy_violation_count` crosses thresholds
- projected risk state moves: DEGRADED → AT_RISK → VIOLATION
- confidence increases with signal volume (bounded at 0.95)

Output shown to judges:

```text
Risk: 80 (VIOLATION)
Confidence: 0.90

Evidence:
- anom_xxx (workflow delay)
- anom_yyy (sustained CPU)
- hit_zzz  (policy approval skip)

Why:
- repeated anomalies + weighted policy hit escalated projected_state
```

---

# 5) Transparency Output (Non-Negotiable)

Chronos always shows a breakdown so judges never ask "how did you get 80?".

Required fields:
- `risk_state` and/or `risk_score`
- `confidence`
- top contributors (anomalies, policy hits, blast radius)
- evidence IDs

---

# 6) What You Must Never Say (Judge Safety)

Do not say:
- "AI calculates the risk"
- "the model decides severity"
- "it learns over time"

Say:
- "Risk and confidence are deterministic formulas over observed signals and graph context."
- "Every output is traceable to evidence IDs and repeatable with the same inputs."

