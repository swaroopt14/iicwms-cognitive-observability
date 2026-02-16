"""
What-If Simulator Agent
=======================
Deterministic counterfactual simulator over latest system snapshot.
"""

from __future__ import annotations

from typing import Any, Dict, List

from blackboard import SharedState, ScenarioRun, RiskState


class WhatIfSimulatorAgent:
    AGENT_NAME = "WhatIfSimulatorAgent"

    _SCENARIO_DEFAULTS = {
        "LATENCY_SPIKE": {"magnitude": 0.5, "duration_minutes": 15},
        "WORKLOAD_SURGE": {"multiplier": 2.0, "duration_minutes": 15},
        "COMPLIANCE_RELAX": {"minutes_extension": 180, "duration_minutes": 30},
    }

    def run(
        self,
        scenario_type: str,
        parameters: Dict[str, Any],
        state: SharedState,
    ) -> ScenarioRun:
        scenario = scenario_type.upper()
        defaults = dict(self._SCENARIO_DEFAULTS.get(scenario, {}))
        defaults.update(parameters or {})
        p = defaults

        baseline = self._baseline_metrics(state)
        simulated = dict(baseline)

        if scenario == "LATENCY_SPIKE":
            magnitude = float(p.get("magnitude", 0.5))
            simulated["sla_violations"] += max(1.0, 4.0 * magnitude)
            simulated["compliance_violations"] += max(0.0, 1.0 * magnitude)
            simulated["risk_index"] = min(100.0, baseline["risk_index"] + 25.0 * magnitude)
        elif scenario == "WORKLOAD_SURGE":
            mult = float(p.get("multiplier", 2.0))
            simulated["sla_violations"] += max(1.0, (mult - 1.0) * 6.0)
            simulated["compliance_violations"] += max(0.0, (mult - 1.0) * 1.5)
            simulated["risk_index"] = min(100.0, baseline["risk_index"] + (mult - 1.0) * 18.0)
        elif scenario == "COMPLIANCE_RELAX":
            ext = float(p.get("minutes_extension", 180))
            simulated["sla_violations"] += 0.5
            simulated["compliance_violations"] += min(6.0, ext / 90.0)
            simulated["risk_index"] = min(100.0, baseline["risk_index"] + min(20.0, ext / 18.0))
        else:
            # Unknown scenario: conservative small perturbation only.
            simulated["sla_violations"] += 0.5
            simulated["risk_index"] = min(100.0, baseline["risk_index"] + 5.0)

        impact = self._impact_score(baseline, simulated)
        assumptions = [
            "Read-only simulation: no writes to Observation layer",
            "Uses deterministic rules; not probabilistic forecasting",
            "Impact is delta vs latest observed baseline",
        ]
        confidence, reason = self._confidence(scenario, p)

        latest_cycle_id = state._completed_cycles[-1].cycle_id if state._completed_cycles else None
        return state.add_scenario_run(
            scenario_type=scenario,
            parameters=p,
            baseline=baseline,
            simulated=simulated,
            impact_score=impact,
            assumptions=assumptions,
            confidence=confidence,
            confidence_reason=reason,
            related_cycle_id=latest_cycle_id,
        )

    def _baseline_metrics(self, state: SharedState) -> Dict[str, float]:
        if not state._completed_cycles:
            return {"sla_violations": 0.0, "compliance_violations": 0.0, "risk_index": 10.0}

        latest = state._completed_cycles[-1]
        sla_viol = float(sum(1 for a in latest.anomalies if a.type in ("WORKFLOW_DELAY", "MISSING_STEP", "SEQUENCE_VIOLATION")))
        comp_viol = float(len(latest.policy_hits))

        max_rank = 0
        rank = {
            RiskState.NORMAL: 0,
            RiskState.DEGRADED: 25,
            RiskState.AT_RISK: 55,
            RiskState.VIOLATION: 80,
            RiskState.INCIDENT: 95,
        }
        for r in latest.risk_signals:
            max_rank = max(max_rank, rank.get(r.projected_state, 0))

        return {
            "sla_violations": sla_viol,
            "compliance_violations": comp_viol,
            "risk_index": float(max_rank),
        }

    def _impact_score(self, baseline: Dict[str, float], simulated: Dict[str, float]) -> float:
        d_wf = max(0.0, simulated["sla_violations"] - baseline["sla_violations"])
        d_cv = max(0.0, simulated["compliance_violations"] - baseline["compliance_violations"])
        d_rs = max(0.0, simulated["risk_index"] - baseline["risk_index"])

        # deterministic normalized impact score (0-100)
        wf_norm = min(1.0, d_wf / 10.0)
        cv_norm = min(1.0, d_cv / 6.0)
        rs_norm = min(1.0, d_rs / 100.0)
        score = (0.35 * wf_norm + 0.35 * cv_norm + 0.30 * rs_norm) * 100.0
        return round(max(0.0, min(100.0, score)), 3)

    def _confidence(self, scenario: str, parameters: Dict[str, Any]) -> tuple[float, str]:
        if scenario == "WORKLOAD_SURGE" and float(parameters.get("multiplier", 2.0)) > 4.0:
            return 0.5, "Extrapolated surge beyond usual operating range"
        if scenario == "LATENCY_SPIKE" and float(parameters.get("magnitude", 0.5)) > 1.0:
            return 0.7, "High latency perturbation, medium model confidence"
        return 0.9, "Within modeled operating envelope"

