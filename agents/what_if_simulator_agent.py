"""
What-If Simulator Agent
=======================
Deterministic counterfactual simulator over latest system snapshot.
"""

from __future__ import annotations

from typing import Any, Dict, List

from blackboard import SharedState, ScenarioRun, RiskState
from .langgraph_runtime import run_linear_graph, is_langgraph_enabled


class WhatIfSimulatorAgent:
    AGENT_NAME = "WhatIfSimulatorAgent"
    _RISK_STATE_RANK = {
        RiskState.NORMAL: 0,
        RiskState.DEGRADED: 25,
        RiskState.AT_RISK: 55,
        RiskState.VIOLATION: 80,
        RiskState.INCIDENT: 95,
    }

    _SCENARIO_DEFAULTS = {
        "LATENCY_SPIKE": {"magnitude": 0.5, "duration_minutes": 15},
        "WORKLOAD_SURGE": {"multiplier": 2.0, "duration_minutes": 15},
        "COMPLIANCE_RELAX": {"minutes_extension": 180, "duration_minutes": 30},
    }

    def __init__(self):
        self._use_langgraph = is_langgraph_enabled()

    def run(
        self,
        scenario_type: str,
        parameters: Dict[str, Any],
        state: SharedState,
    ) -> ScenarioRun:
        computed = self.compute(
            scenario_type=scenario_type,
            parameters=parameters,
            state=state,
        )

        latest_cycle_id = state._completed_cycles[-1].cycle_id if state._completed_cycles else None
        return state.add_scenario_run(
            scenario_type=computed["scenario_type"],
            parameters=computed["parameters"],
            baseline=computed["baseline"],
            simulated=computed["simulated"],
            impact_score=computed["impact_score"],
            assumptions=computed["assumptions"],
            confidence=computed["confidence"],
            confidence_reason=computed["confidence_reason"],
            related_cycle_id=latest_cycle_id,
        )

    def compute(
        self,
        scenario_type: str,
        parameters: Dict[str, Any],
        state: SharedState,
    ) -> Dict[str, Any]:
        if self._use_langgraph:
            graph_state = run_linear_graph(
                {
                    "scenario_type": scenario_type,
                    "parameters": parameters,
                    "state": state,
                    "scenario": "",
                    "normalized": {},
                    "baseline": {},
                    "simulated": {},
                    "trace": [],
                },
                [
                    ("normalize", self._graph_normalize),
                    ("baseline", self._graph_baseline),
                    ("simulate", self._graph_simulate),
                    ("context", self._graph_context),
                    ("finalize", self._graph_finalize),
                ],
            )
            return graph_state["result"]
        return self._compute_core(scenario_type, parameters, state)

    def _compute_core(
        self,
        scenario_type: str,
        parameters: Dict[str, Any],
        state: SharedState,
    ) -> Dict[str, Any]:
        """
        Compute a deterministic what-if result without persisting.
        Useful for sandbox/dry-run mode.
        """
        scenario = scenario_type.upper()
        defaults = dict(self._SCENARIO_DEFAULTS.get(scenario, {}))
        defaults.update(parameters or {})
        p = self._normalize_parameters(defaults)

        baseline = self._baseline_metrics(state)
        simulated = dict(baseline)
        explain_trace: List[str] = []

        if scenario == "LATENCY_SPIKE":
            magnitude = float(p.get("magnitude", 0.5))
            simulated["sla_violations"] += max(1.0, 4.0 * magnitude)
            simulated["compliance_violations"] += max(0.0, 1.0 * magnitude)
            simulated["risk_index"] = min(100.0, baseline["risk_index"] + 25.0 * magnitude)
            explain_trace.append(f"LATENCY_SPIKE magnitude {magnitude:.2f} -> risk +{25.0 * magnitude:.2f}")
        elif scenario == "WORKLOAD_SURGE":
            mult = float(p.get("multiplier", 2.0))
            simulated["sla_violations"] += max(1.0, (mult - 1.0) * 6.0)
            simulated["compliance_violations"] += max(0.0, (mult - 1.0) * 1.5)
            simulated["risk_index"] = min(100.0, baseline["risk_index"] + (mult - 1.0) * 18.0)
            explain_trace.append(f"WORKLOAD_SURGE multiplier {mult:.2f} -> risk +{(mult - 1.0) * 18.0:.2f}")
        elif scenario == "COMPLIANCE_RELAX":
            ext = float(p.get("minutes_extension", 180))
            simulated["sla_violations"] += 0.5
            simulated["compliance_violations"] += min(6.0, ext / 90.0)
            simulated["risk_index"] = min(100.0, baseline["risk_index"] + min(20.0, ext / 18.0))
            explain_trace.append(f"COMPLIANCE_RELAX extension {ext:.0f}m -> risk +{min(20.0, ext / 18.0):.2f}")
        else:
            simulated["sla_violations"] += 0.5
            simulated["risk_index"] = min(100.0, baseline["risk_index"] + 5.0)
            explain_trace.append("UNKNOWN scenario fallback -> risk +5.00")

        self._apply_context_modifiers(simulated, p, explain_trace)

        impact = self._impact_score(baseline, simulated)
        assumptions = [
            "Read-only simulation: no writes to Observation layer",
            "Uses deterministic rules; not probabilistic forecasting",
            "Impact is delta vs latest observed baseline",
            *explain_trace[:5],
        ]
        confidence, reason = self._confidence(scenario, p)
        return {
            "scenario_type": scenario,
            "parameters": p,
            "baseline": baseline,
            "simulated": simulated,
            "impact_score": impact,
            "assumptions": assumptions,
            "confidence": confidence,
            "confidence_reason": reason,
        }

    def _graph_normalize(self, graph_state: Dict[str, Any]) -> Dict[str, Any]:
        scenario = graph_state["scenario_type"].upper()
        defaults = dict(self._SCENARIO_DEFAULTS.get(scenario, {}))
        defaults.update(graph_state.get("parameters") or {})
        graph_state["scenario"] = scenario
        graph_state["normalized"] = self._normalize_parameters(defaults)
        graph_state["trace"] = []
        return graph_state

    def _graph_baseline(self, graph_state: Dict[str, Any]) -> Dict[str, Any]:
        baseline = self._baseline_metrics(graph_state["state"])
        graph_state["baseline"] = baseline
        graph_state["simulated"] = dict(baseline)
        return graph_state

    def _graph_simulate(self, graph_state: Dict[str, Any]) -> Dict[str, Any]:
        scenario = graph_state["scenario"]
        p = graph_state["normalized"]
        baseline = graph_state["baseline"]
        simulated = graph_state["simulated"]
        explain_trace = graph_state["trace"]

        if scenario == "LATENCY_SPIKE":
            magnitude = float(p.get("magnitude", 0.5))
            simulated["sla_violations"] += max(1.0, 4.0 * magnitude)
            simulated["compliance_violations"] += max(0.0, 1.0 * magnitude)
            simulated["risk_index"] = min(100.0, baseline["risk_index"] + 25.0 * magnitude)
            explain_trace.append(f"LATENCY_SPIKE magnitude {magnitude:.2f} -> risk +{25.0 * magnitude:.2f}")
        elif scenario == "WORKLOAD_SURGE":
            mult = float(p.get("multiplier", 2.0))
            simulated["sla_violations"] += max(1.0, (mult - 1.0) * 6.0)
            simulated["compliance_violations"] += max(0.0, (mult - 1.0) * 1.5)
            simulated["risk_index"] = min(100.0, baseline["risk_index"] + (mult - 1.0) * 18.0)
            explain_trace.append(f"WORKLOAD_SURGE multiplier {mult:.2f} -> risk +{(mult - 1.0) * 18.0:.2f}")
        elif scenario == "COMPLIANCE_RELAX":
            ext = float(p.get("minutes_extension", 180))
            simulated["sla_violations"] += 0.5
            simulated["compliance_violations"] += min(6.0, ext / 90.0)
            simulated["risk_index"] = min(100.0, baseline["risk_index"] + min(20.0, ext / 18.0))
            explain_trace.append(f"COMPLIANCE_RELAX extension {ext:.0f}m -> risk +{min(20.0, ext / 18.0):.2f}")
        else:
            simulated["sla_violations"] += 0.5
            simulated["risk_index"] = min(100.0, baseline["risk_index"] + 5.0)
            explain_trace.append("UNKNOWN scenario fallback -> risk +5.00")

        return graph_state

    def _graph_context(self, graph_state: Dict[str, Any]) -> Dict[str, Any]:
        self._apply_context_modifiers(graph_state["simulated"], graph_state["normalized"], graph_state["trace"])
        return graph_state

    def _graph_finalize(self, graph_state: Dict[str, Any]) -> Dict[str, Any]:
        scenario = graph_state["scenario"]
        p = graph_state["normalized"]
        baseline = graph_state["baseline"]
        simulated = graph_state["simulated"]
        explain_trace = graph_state["trace"]
        impact = self._impact_score(baseline, simulated)
        assumptions = [
            "Read-only simulation: no writes to Observation layer",
            "Uses deterministic rules; not probabilistic forecasting",
            "Impact is delta vs latest observed baseline",
            *explain_trace[:5],
        ]
        confidence, reason = self._confidence(scenario, p)
        graph_state["result"] = {
            "scenario_type": scenario,
            "parameters": p,
            "baseline": baseline,
            "simulated": simulated,
            "impact_score": impact,
            "assumptions": assumptions,
            "confidence": confidence,
            "confidence_reason": reason,
        }
        return graph_state

    def _baseline_metrics(self, state: SharedState) -> Dict[str, float]:
        if not state._completed_cycles:
            return {"sla_violations": 0.0, "compliance_violations": 0.0, "risk_index": 10.0}

        latest = state._completed_cycles[-1]
        sla_viol = float(sum(1 for a in latest.anomalies if a.type in ("WORKFLOW_DELAY", "MISSING_STEP", "SEQUENCE_VIOLATION")))
        comp_viol = float(len(latest.policy_hits))

        max_rank = 0
        for r in latest.risk_signals:
            max_rank = max(max_rank, self._RISK_STATE_RANK.get(r.projected_state, 0))

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

    def _normalize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        p = dict(parameters)
        p["magnitude"] = max(0.0, min(2.0, float(p.get("magnitude", 0.5))))
        p["multiplier"] = max(1.0, min(6.0, float(p.get("multiplier", 2.0))))
        p["minutes_extension"] = max(0.0, min(720.0, float(p.get("minutes_extension", 180.0))))
        p["time_window"] = str(p.get("time_window", "business_hours")).lower()
        p["affected_module"] = str(p.get("affected_module", "general")).lower()
        p["actor_role"] = str(p.get("actor_role", "service")).lower()
        return p

    def _apply_context_modifiers(self, simulated: Dict[str, float], p: Dict[str, Any], trace: List[str]) -> None:
        risk_boost = 0.0

        if p.get("time_window") in ("after_hours", "weekend"):
            risk_boost += 4.0
            trace.append("Context time_window after_hours/weekend -> risk +4.00")

        module = str(p.get("affected_module", "general"))
        if module in ("auth", "payment", "approval", "compliance"):
            risk_boost += 6.0
            simulated["compliance_violations"] += 0.6
            trace.append(f"Context affected_module {module} -> risk +6.00")

        role = str(p.get("actor_role", "service"))
        if role in ("admin", "security"):
            risk_boost += 3.0
            trace.append(f"Context actor_role {role} -> risk +3.00")

        simulated["risk_index"] = min(100.0, simulated["risk_index"] + risk_boost)
