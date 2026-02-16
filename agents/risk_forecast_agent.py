"""
IICWMS Risk Forecast Agent
==========================
Predicts risk trajectory, NOT exact failure.

PURPOSE:
Predict risk BEFORE it happens.

RISK STATES:
NORMAL → DEGRADED → AT_RISK → VIOLATION → INCIDENT

OUTPUT:
{
  "entity": "wf_12",
  "current_state": "DEGRADED",
  "projected_state": "AT_RISK",
  "confidence": 0.67,
  "time_horizon": "10–15 min"
}

This is how you predict BEFORE it happens.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from blackboard import (
    SharedState, RiskSignal, RiskState,
    Anomaly, PolicyHit
)
from .langgraph_runtime import run_linear_graph, is_langgraph_enabled


@dataclass
class EntityRiskProfile:
    """Tracks risk state for an entity."""
    entity: str
    entity_type: str  # "workflow", "resource"
    current_state: RiskState = RiskState.NORMAL
    anomaly_count: int = 0
    policy_violation_count: int = 0
    last_updated: Optional[datetime] = None
    
    def compute_projected_state(self) -> RiskState:
        """Project where risk is heading based on indicators."""
        # Risk escalation logic
        total_issues = self.anomaly_count + (self.policy_violation_count * 2)  # Policy violations weigh more
        
        if total_issues == 0:
            return RiskState.NORMAL
        elif total_issues <= 1:
            return RiskState.DEGRADED
        elif total_issues <= 3:
            return RiskState.AT_RISK
        elif total_issues <= 5:
            return RiskState.VIOLATION
        else:
            return RiskState.INCIDENT
    
    def compute_confidence(self) -> float:
        """Compute confidence in prediction."""
        # More data = higher confidence
        base = 0.5
        if self.anomaly_count > 0:
            base += min(0.3, self.anomaly_count * 0.1)
        if self.policy_violation_count > 0:
            base += min(0.2, self.policy_violation_count * 0.1)
        return min(0.95, base)


class RiskForecastAgent:
    """
    Risk Forecast Agent
    
    Predicts risk trajectory, not exact failure.
    
    This is PREDICTION WITHOUT BS:
    - We predict where things are heading
    - We DO NOT predict exact failure time
    - We provide confidence and time horizons
    
    Agents do NOT communicate directly.
    All output goes to SharedState.
    """
    
    AGENT_NAME = "RiskForecastAgent"
    
    def __init__(self):
        # Track risk profiles: entity -> profile
        self._profiles: Dict[str, EntityRiskProfile] = {}
        self._use_langgraph = is_langgraph_enabled()
    
    def analyze(
        self,
        anomalies: List[Anomaly],
        policy_hits: List[PolicyHit],
        state: SharedState
    ) -> List[RiskSignal]:
        if self._use_langgraph:
            graph_state = run_linear_graph(
                {
                    "anomalies": anomalies,
                    "policy_hits": policy_hits,
                    "state": state,
                    "signals": [],
                },
                [
                    ("accumulate_anomalies", self._graph_accumulate_anomalies),
                    ("accumulate_policy_hits", self._graph_accumulate_policy_hits),
                    ("emit_risk_signals", self._graph_emit_risk_signals),
                ],
            )
            return graph_state.get("signals", [])
        return self._analyze_core(anomalies, policy_hits, state)

    def _analyze_core(
        self,
        anomalies: List[Anomaly],
        policy_hits: List[PolicyHit],
        state: SharedState
    ) -> List[RiskSignal]:
        """
        Analyze anomalies and policy hits to forecast risk.
        
        Returns risk signals (also written to state).
        """
        signals = []
        
        # Update profiles from anomalies
        for anomaly in anomalies:
            entity = self._extract_entity(anomaly)
            if not entity:
                continue
            
            entity_type = self._determine_entity_type(entity)
            
            if entity not in self._profiles:
                self._profiles[entity] = EntityRiskProfile(
                    entity=entity,
                    entity_type=entity_type
                )
            
            profile = self._profiles[entity]
            profile.anomaly_count += 1
            profile.last_updated = datetime.utcnow()
        
        # Update profiles from policy hits
        for hit in policy_hits:
            # Try to extract entity from event_id or policy context
            entity = self._extract_entity_from_hit(hit)
            if not entity:
                continue
            
            entity_type = self._determine_entity_type(entity)
            
            if entity not in self._profiles:
                self._profiles[entity] = EntityRiskProfile(
                    entity=entity,
                    entity_type=entity_type
                )
            
            profile = self._profiles[entity]
            profile.policy_violation_count += 1
            profile.last_updated = datetime.utcnow()
        
        # Generate risk signals for entities with elevated risk
        for entity, profile in self._profiles.items():
            projected = profile.compute_projected_state()
            
            # Only signal if risk is escalating
            if self._state_rank(projected) > self._state_rank(profile.current_state):
                signal = state.add_risk_signal(
                    entity=entity,
                    entity_type=profile.entity_type,
                    current_state=profile.current_state,
                    projected_state=projected,
                    confidence=profile.compute_confidence(),
                    time_horizon=self._compute_time_horizon(profile, projected),
                    reasoning=self._generate_reasoning(profile, projected),
                    evidence_ids=self._gather_evidence_ids(profile, anomalies, policy_hits)
                )
                signals.append(signal)
                
                # Update current state
                profile.current_state = projected
        
        return signals

    def _graph_accumulate_anomalies(self, graph_state: Dict[str, Any]) -> Dict[str, Any]:
        for anomaly in graph_state["anomalies"]:
            entity = self._extract_entity(anomaly)
            if not entity:
                continue
            entity_type = self._determine_entity_type(entity)
            if entity not in self._profiles:
                self._profiles[entity] = EntityRiskProfile(entity=entity, entity_type=entity_type)
            profile = self._profiles[entity]
            profile.anomaly_count += 1
            profile.last_updated = datetime.utcnow()
        return graph_state

    def _graph_accumulate_policy_hits(self, graph_state: Dict[str, Any]) -> Dict[str, Any]:
        for hit in graph_state["policy_hits"]:
            entity = self._extract_entity_from_hit(hit)
            if not entity:
                continue
            entity_type = self._determine_entity_type(entity)
            if entity not in self._profiles:
                self._profiles[entity] = EntityRiskProfile(entity=entity, entity_type=entity_type)
            profile = self._profiles[entity]
            profile.policy_violation_count += 1
            profile.last_updated = datetime.utcnow()
        return graph_state

    def _graph_emit_risk_signals(self, graph_state: Dict[str, Any]) -> Dict[str, Any]:
        signals: List[RiskSignal] = []
        anomalies = graph_state["anomalies"]
        policy_hits = graph_state["policy_hits"]
        state = graph_state["state"]
        for entity, profile in self._profiles.items():
            projected = profile.compute_projected_state()
            if self._state_rank(projected) > self._state_rank(profile.current_state):
                signal = state.add_risk_signal(
                    entity=entity,
                    entity_type=profile.entity_type,
                    current_state=profile.current_state,
                    projected_state=projected,
                    confidence=profile.compute_confidence(),
                    time_horizon=self._compute_time_horizon(profile, projected),
                    reasoning=self._generate_reasoning(profile, projected),
                    evidence_ids=self._gather_evidence_ids(profile, anomalies, policy_hits),
                )
                signals.append(signal)
                profile.current_state = projected
        graph_state["signals"] = signals
        return graph_state
    
    def _state_rank(self, state: RiskState) -> int:
        """Get numeric rank of risk state."""
        ranks = {
            RiskState.NORMAL: 0,
            RiskState.DEGRADED: 1,
            RiskState.AT_RISK: 2,
            RiskState.VIOLATION: 3,
            RiskState.INCIDENT: 4
        }
        return ranks.get(state, 0)
    
    def _extract_entity(self, anomaly: Anomaly) -> Optional[str]:
        """Extract entity from anomaly."""
        # Parse from description or evidence
        desc = anomaly.description
        
        # Look for workflow IDs
        if "wf_" in desc:
            for word in desc.split():
                if word.startswith("wf_"):
                    return word.rstrip(",.")
        
        # Look for resource IDs
        if "Resource " in desc:
            parts = desc.split("Resource ")
            if len(parts) > 1:
                entity = parts[1].split()[0].rstrip(",.")
                return entity
        
        # Check evidence
        if anomaly.evidence:
            for ev in anomaly.evidence:
                if "/" in ev:
                    return ev.split("/")[0]
        
        return None
    
    def _extract_entity_from_hit(self, hit: PolicyHit) -> Optional[str]:
        """Extract entity from policy hit."""
        # Use policy ID as entity for now
        # In real system, would trace back to affected entity
        return f"policy_context_{hit.policy_id}"
    
    def _determine_entity_type(self, entity: str) -> str:
        """Determine entity type."""
        if entity.startswith("wf_"):
            return "workflow"
        elif entity.startswith("vm_") or entity.startswith("storage_"):
            return "resource"
        elif entity.startswith("policy_"):
            return "policy"
        return "unknown"
    
    def _compute_time_horizon(self, profile: EntityRiskProfile, projected: RiskState) -> str:
        """Compute time horizon for risk projection."""
        # Based on velocity of risk escalation
        total = profile.anomaly_count + profile.policy_violation_count
        
        if total <= 2:
            return "15-30 min"
        elif total <= 4:
            return "10-15 min"
        else:
            return "5-10 min"
    
    def _generate_reasoning(self, profile: EntityRiskProfile, projected: RiskState) -> str:
        """Generate reasoning for risk signal."""
        parts = []
        
        if profile.anomaly_count > 0:
            parts.append(f"{profile.anomaly_count} anomalies detected")
        
        if profile.policy_violation_count > 0:
            parts.append(f"{profile.policy_violation_count} policy violations")
        
        reasoning = f"Entity {profile.entity} shows risk escalation: " + ", ".join(parts)
        reasoning += f". Projected to reach {projected.value} state."
        
        return reasoning
    
    def _gather_evidence_ids(
        self,
        profile: EntityRiskProfile,
        anomalies: List[Anomaly],
        policy_hits: List[PolicyHit]
    ) -> List[str]:
        """Gather evidence IDs for this entity."""
        evidence = []
        
        for anomaly in anomalies:
            if profile.entity in anomaly.description:
                evidence.append(anomaly.anomaly_id)
        
        for hit in policy_hits:
            evidence.append(hit.hit_id)
        
        return evidence[:10]  # Limit
    
    def get_risk_profile(self, entity: str) -> Optional[EntityRiskProfile]:
        """Get risk profile for an entity."""
        return self._profiles.get(entity)
    
    def get_all_at_risk_entities(self) -> List[EntityRiskProfile]:
        """Get all entities at elevated risk."""
        return [
            p for p in self._profiles.values()
            if self._state_rank(p.current_state) >= self._state_rank(RiskState.AT_RISK)
        ]
