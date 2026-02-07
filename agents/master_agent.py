"""
IICWMS Master Agent (Sovereign Orchestrator)
============================================
COORDINATOR ONLY.

RESPONSIBILITIES:
- Trigger agents (async)
- Collect outputs
- Rank severity
- Trigger explanation

FORBIDDEN:
- No deep reasoning (delegates to specialized agents)
- No LLM usage (only Explanation Engine uses LLM)
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import concurrent.futures

from observation import ObservationLayer, ObservedEvent, ObservedMetric
from blackboard import (
    SharedState, ReasoningCycle,
    Anomaly, PolicyHit, RiskSignal, CausalLink, Recommendation
)
from .workflow_agent import WorkflowAgent
from .resource_agent import ResourceAgent
from .compliance_agent import ComplianceAgent
from .risk_forecast_agent import RiskForecastAgent
from .causal_agent import CausalAgent
from .adaptive_baseline_agent import AdaptiveBaselineAgent


# Solution mapping (solutions are mapped, not invented)
SOLUTION_MAP = {
    "SUSTAINED_RESOURCE_CRITICAL": {
        "action": "Throttle jobs or scale resources",
        "urgency": "HIGH",
        "rationale": "Resource saturation will cause cascading failures"
    },
    "SUSTAINED_RESOURCE_WARNING": {
        "action": "Monitor closely, prepare scaling plan",
        "urgency": "MEDIUM",
        "rationale": "Early intervention prevents escalation"
    },
    "RESOURCE_DRIFT": {
        "action": "Investigate root cause of resource growth",
        "urgency": "LOW",
        "rationale": "Drift indicates potential leak or inefficiency"
    },
    "WORKFLOW_DELAY": {
        "action": "Pre-notify admins of SLA pressure",
        "urgency": "MEDIUM",
        "rationale": "Delays compound and affect downstream processes"
    },
    "MISSING_STEP": {
        "action": "Apply temporary access guard and audit",
        "urgency": "HIGH",
        "rationale": "Skipped steps may bypass critical controls"
    },
    "SEQUENCE_VIOLATION": {
        "action": "Review workflow execution and enforce ordering",
        "urgency": "MEDIUM",
        "rationale": "Out-of-order execution indicates process breakdown"
    },
    "SILENT": {  # Policy violation
        "action": "Flag for compliance review",
        "urgency": "HIGH",
        "rationale": "Silent violations accumulate audit risk"
    }
}


@dataclass
class CycleResult:
    """Result of a reasoning cycle."""
    cycle_id: str
    anomaly_count: int
    policy_hit_count: int
    risk_signal_count: int
    causal_link_count: int
    recommendation_count: int
    duration_ms: float


class MasterAgent:
    """
    Master Agent (Sovereign Orchestrator)
    
    Coordinates specialized agents. Does NOT perform deep reasoning.
    
    Reasoning Cycle Flow:
    1. Observation ingest
    2. Master Agent starts cycle
    3. Agents run in parallel
    4. State populated
    5. Causal synthesis
    6. Recommendations generated
    
    If this loop breaks → system fails.
    """
    
    AGENT_NAME = "MasterAgent"
    
    def __init__(
        self,
        observation: ObservationLayer,
        state: SharedState
    ):
        self._observation = observation
        self._state = state
        
        # Initialize specialized agents
        self._workflow_agent = WorkflowAgent()
        self._resource_agent = ResourceAgent()
        self._compliance_agent = ComplianceAgent()
        self._risk_forecast_agent = RiskForecastAgent()
        self._causal_agent = CausalAgent()
        self._adaptive_baseline_agent = AdaptiveBaselineAgent()
    
    def run_cycle(self) -> CycleResult:
        """
        Execute one complete reasoning cycle.
        
        This is the MANDATORY FLOW:
        1. Start cycle
        2. Get observations
        3. Run specialized agents (parallel)
        4. Run risk forecast
        5. Run causal analysis
        6. Generate recommendations
        7. Complete cycle
        """
        start_time = datetime.utcnow()
        
        # 1. Start cycle
        cycle_id = self._state.start_cycle()
        
        # 2. Get recent observations
        events = self._observation.get_recent_events(count=100)
        metrics = self._observation.get_recent_metrics(count=100)
        
        # 3. Run specialized agents in parallel
        anomalies = []
        policy_hits = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Submit parallel tasks
            workflow_future = executor.submit(
                self._workflow_agent.analyze, events, self._state
            )
            resource_future = executor.submit(
                self._resource_agent.analyze, metrics, self._state
            )
            compliance_future = executor.submit(
                self._compliance_agent.analyze, events, self._state
            )
            baseline_future = executor.submit(
                self._adaptive_baseline_agent.analyze, metrics, self._state
            )
            
            # Collect results
            anomalies.extend(workflow_future.result())
            anomalies.extend(resource_future.result())
            policy_hits.extend(compliance_future.result())
            anomalies.extend(baseline_future.result())  # Baseline deviations
        
        # 4. Run risk forecast (depends on anomalies & policy hits)
        risk_signals = self._risk_forecast_agent.analyze(
            anomalies, policy_hits, self._state
        )
        
        # 5. Run causal analysis (depends on all previous)
        causal_links = self._causal_agent.analyze(
            anomalies, policy_hits, risk_signals, self._state
        )
        
        # 6. Generate recommendations (mapped, not invented)
        recommendations = self._generate_recommendations(
            anomalies, policy_hits, causal_links
        )
        
        # 7. Complete cycle
        cycle = self._state.complete_cycle()
        
        end_time = datetime.utcnow()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        return CycleResult(
            cycle_id=cycle_id,
            anomaly_count=len(anomalies),
            policy_hit_count=len(policy_hits),
            risk_signal_count=len(risk_signals),
            causal_link_count=len(causal_links),
            recommendation_count=len(recommendations),
            duration_ms=duration_ms
        )
    
    def _generate_recommendations(
        self,
        anomalies: List[Anomaly],
        policy_hits: List[PolicyHit],
        causal_links: List[CausalLink]
    ) -> List[Recommendation]:
        """
        Generate recommendations based on findings.
        
        Solutions are MAPPED, not invented.
        Never auto-apply.
        """
        recommendations = []
        seen_causes = set()
        
        # From anomalies
        for anomaly in anomalies:
            if anomaly.type in SOLUTION_MAP and anomaly.type not in seen_causes:
                solution = SOLUTION_MAP[anomaly.type]
                rec = self._state.add_recommendation(
                    cause=anomaly.type,
                    action=solution["action"],
                    urgency=solution["urgency"],
                    rationale=solution["rationale"]
                )
                recommendations.append(rec)
                seen_causes.add(anomaly.type)
        
        # From policy hits
        for hit in policy_hits:
            if hit.violation_type in SOLUTION_MAP and hit.violation_type not in seen_causes:
                solution = SOLUTION_MAP[hit.violation_type]
                rec = self._state.add_recommendation(
                    cause=f"Policy:{hit.policy_id}",
                    action=solution["action"],
                    urgency=solution["urgency"],
                    rationale=solution["rationale"]
                )
                recommendations.append(rec)
                seen_causes.add(hit.violation_type)
        
        # From causal links (address root causes)
        for link in causal_links:
            if link.cause in SOLUTION_MAP and link.cause not in seen_causes:
                solution = SOLUTION_MAP[link.cause]
                rec = self._state.add_recommendation(
                    cause=f"Root:{link.cause}",
                    action=solution["action"],
                    urgency="HIGH",  # Root causes are high priority
                    rationale=f"Root cause: {solution['rationale']}"
                )
                recommendations.append(rec)
                seen_causes.add(link.cause)
        
        return recommendations
    
    # ─────────────────────────────────────────────────────────────────────────────
    # QUERY APIs (for external use)
    # ─────────────────────────────────────────────────────────────────────────────
    
    @property
    def adaptive_baseline_agent(self) -> AdaptiveBaselineAgent:
        """Expose adaptive baseline agent for API queries."""
        return self._adaptive_baseline_agent

    def get_current_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state."""
        return {
            "cycle": self._state.current_cycle.cycle_id if self._state.current_cycle else None,
            "anomalies": len(self._state.get_current_anomalies()),
            "policy_hits": len(self._state.get_current_policy_hits()),
            "risk_signals": len(self._state.get_current_risk_signals())
        }
