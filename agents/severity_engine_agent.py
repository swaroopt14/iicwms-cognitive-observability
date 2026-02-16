"""
Context-Aware Severity Engine
=============================
Deterministic severity translator (0-10) with explicit context multipliers.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Dict, List, Tuple

from blackboard import SharedState, Anomaly, PolicyHit, SeverityScore


class SeverityEngineAgent:
    AGENT_NAME = "SeverityEngineAgent"

    _WEIGHTS = {
        "asset": 0.28,
        "data": 0.22,
        "time": 0.15,
        "role": 0.10,
        "repetition": 0.15,
        "blast": 0.10,
    }

    def analyze(
        self,
        anomalies: List[Anomaly],
        policy_hits: List[PolicyHit],
        state: SharedState,
    ) -> List[SeverityScore]:
        repetition = Counter([a.type for a in anomalies])
        scores: List[SeverityScore] = []

        for a in anomalies:
            base = self._base_score_for_anomaly(a)
            ctx = self._context_factors(issue_type=a.type, repetition_count=repetition[a.type], description=a.description)
            final = self._final_score(base, ctx)
            sev = state.add_severity_score(
                source_type="anomaly",
                source_id=a.anomaly_id,
                issue_type=a.type,
                base_score=base,
                final_score=final,
                label=self._label(final),
                vector=self._vector(base, ctx),
                escalation_state=self._escalation_state(final, repetition[a.type]),
                context_factors=ctx,
                evidence_ids=list(a.evidence),
            )
            scores.append(sev)

        for p in policy_hits:
            issue = f"POLICY_{p.policy_id}"
            base = 7.0 if p.violation_type.upper() == "SILENT" else 5.5
            ctx = self._context_factors(issue_type=issue, repetition_count=1, description=p.description)
            final = self._final_score(base, ctx)
            sev = state.add_severity_score(
                source_type="policy_hit",
                source_id=p.hit_id,
                issue_type=issue,
                base_score=base,
                final_score=final,
                label=self._label(final),
                vector=self._vector(base, ctx),
                escalation_state=self._escalation_state(final, 1),
                context_factors=ctx,
                evidence_ids=[p.event_id],
            )
            scores.append(sev)

        return scores

    def _base_score_for_anomaly(self, a: Anomaly) -> float:
        t = a.type
        c = max(0.0, min(1.0, float(a.confidence)))
        if t == "WORKFLOW_DELAY":
            return 4.0 + 4.0 * c
        if t == "SUSTAINED_RESOURCE_CRITICAL":
            return 5.0 + 5.0 * c
        if t == "SUSTAINED_RESOURCE_WARNING":
            return 3.5 + 3.0 * c
        if t == "MISSING_STEP":
            return 7.0 + 2.0 * c
        if t == "SEQUENCE_VIOLATION":
            return 5.5 + 2.5 * c
        if t in ("LOW_TEST_COVERAGE", "HIGH_CHURN_PR", "HIGH_COMPLEXITY_HINT", "HOTSPOT_FILE_CHANGE"):
            return 5.0 + 3.0 * c
        return 4.0 + 3.0 * c

    def _context_factors(self, issue_type: str, repetition_count: int, description: str) -> Dict[str, float]:
        issue = issue_type.upper()
        desc = (description or "").lower()
        hour = datetime.utcnow().hour

        asset = 1.4 if any(k in issue for k in ("MISSING_STEP", "POLICY_", "WORKFLOW_DELAY")) else 1.2
        data = 1.3 if ("sensitive" in desc or "credential" in desc or "policy" in issue) else 1.0
        time = 1.2 if (hour < 7 or hour > 21) else 1.0
        role = 1.1 if ("svc" in desc or "service account" in desc) else 1.0
        repetition = min(1.3, 1.0 + max(0, repetition_count - 1) * 0.1)
        blast = 1.2 if "resource_critical" in issue.lower() else 1.0

        return {
            "asset": round(asset, 3),
            "data": round(data, 3),
            "time": round(time, 3),
            "role": round(role, 3),
            "repetition": round(repetition, 3),
            "blast": round(blast, 3),
        }

    def _final_score(self, base: float, ctx: Dict[str, float]) -> float:
        delta = 0.0
        for k, w in self._WEIGHTS.items():
            delta += w * (ctx.get(k, 1.0) - 1.0)
        delta = max(-0.4, min(0.6, delta))
        score = base * (1.0 + delta)
        return round(max(0.0, min(10.0, score)), 3)

    def _label(self, score: float) -> str:
        if score == 0:
            return "None"
        if score <= 3.9:
            return "Low"
        if score <= 6.9:
            return "Medium"
        if score <= 8.9:
            return "High"
        return "Critical"

    def _escalation_state(self, score: float, repetition_count: int) -> str:
        if score >= 9.0 or repetition_count >= 4:
            return "INCIDENT"
        if score >= 8.5:
            return "VIOLATION"
        if score >= 7.0:
            return "AT_RISK"
        if score >= 4.0:
            return "DEGRADED"
        if score > 0:
            return "NORMAL"
        return "INFO"

    def _vector(self, base: float, ctx: Dict[str, float]) -> str:
        return (
            f"B{base:.1f}/AS{ctx['asset']:.1f}/DS{ctx['data']:.1f}/"
            f"T{ctx['time']:.1f}/R{ctx['role']:.1f}/REP{ctx['repetition']:.1f}/BL{ctx['blast']:.1f}"
        )

