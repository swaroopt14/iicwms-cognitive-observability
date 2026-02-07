"""
IICWMS Risk Index Tracker
=========================
System Health Index / Risk Index over time.

Think: "S&P 500, but for operational risk"

This shows trajectory, not raw metrics.

Every movement must be explainable:
- Which agent contributed
- What signal caused movement
- Evidence IDs
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from collections import deque

from blackboard import (
    ReasoningCycle, RiskState,
    Anomaly, PolicyHit, RiskSignal
)


@dataclass
class RiskContribution:
    """A contribution to the risk index."""
    agent: str
    signal_type: str
    impact: float  # Positive = increases risk, negative = decreases
    evidence_id: str
    description: str


@dataclass
class RiskDataPoint:
    """A single point on the risk index graph."""
    timestamp: str
    cycle_id: str
    risk_score: float  # 0-100
    workflow_risk: float
    resource_risk: float
    compliance_risk: float
    risk_state: str  # NORMAL, DEGRADED, AT_RISK, etc.
    contributions: List[RiskContribution]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "cycle_id": self.cycle_id,
            "risk_score": self.risk_score,
            "workflow_risk": self.workflow_risk,
            "resource_risk": self.resource_risk,
            "compliance_risk": self.compliance_risk,
            "risk_state": self.risk_state,
            "contributions": [asdict(c) for c in self.contributions]
        }


class RiskIndexTracker:
    """
    Tracks system risk index over time.
    
    X-Axis: Time (simulation cycles)
    Y-Axis: Risk Score (0-100)
    
    Overlay Lines:
    - Workflow risk
    - Resource stress
    - Compliance proximity
    """
    
    def __init__(self, max_history: int = 100):
        self._history: deque[RiskDataPoint] = deque(maxlen=max_history)
        self._base_risk = 20.0  # Baseline risk (never 0 in real systems)
    
    def record_cycle(self, cycle: ReasoningCycle) -> RiskDataPoint:
        """
        Record a cycle's contribution to risk index.
        
        Returns the new risk data point.
        """
        contributions = []
        
        # Calculate workflow risk
        workflow_risk = self._calculate_workflow_risk(cycle, contributions)
        
        # Calculate resource risk
        resource_risk = self._calculate_resource_risk(cycle, contributions)
        
        # Calculate compliance risk
        compliance_risk = self._calculate_compliance_risk(cycle, contributions)
        
        # Calculate overall risk score (weighted average)
        risk_score = (
            workflow_risk * 0.35 +
            resource_risk * 0.35 +
            compliance_risk * 0.30
        )
        
        # Determine risk state
        risk_state = self._determine_risk_state(risk_score, cycle)
        
        # Create data point
        data_point = RiskDataPoint(
            timestamp=(cycle.completed_at or datetime.utcnow()).isoformat(),
            cycle_id=cycle.cycle_id,
            risk_score=round(risk_score, 2),
            workflow_risk=round(workflow_risk, 2),
            resource_risk=round(resource_risk, 2),
            compliance_risk=round(compliance_risk, 2),
            risk_state=risk_state,
            contributions=contributions
        )
        
        self._history.append(data_point)
        return data_point
    
    def _calculate_workflow_risk(
        self,
        cycle: ReasoningCycle,
        contributions: List[RiskContribution]
    ) -> float:
        """Calculate workflow risk component."""
        risk = self._base_risk
        
        for anomaly in cycle.anomalies:
            if anomaly.type in ("WORKFLOW_DELAY", "MISSING_STEP", "SEQUENCE_VIOLATION"):
                impact = 0
                
                if anomaly.type == "MISSING_STEP":
                    impact = 25  # High impact
                elif anomaly.type == "WORKFLOW_DELAY":
                    impact = 15
                elif anomaly.type == "SEQUENCE_VIOLATION":
                    impact = 20
                
                risk += impact * anomaly.confidence
                
                contributions.append(RiskContribution(
                    agent=anomaly.agent,
                    signal_type=anomaly.type,
                    impact=impact * anomaly.confidence,
                    evidence_id=anomaly.anomaly_id,
                    description=f"+{impact:.0f} risk due to {anomaly.type.lower().replace('_', ' ')}"
                ))
        
        return min(100, risk)
    
    def _calculate_resource_risk(
        self,
        cycle: ReasoningCycle,
        contributions: List[RiskContribution]
    ) -> float:
        """Calculate resource risk component."""
        risk = self._base_risk
        
        for anomaly in cycle.anomalies:
            if "RESOURCE" in anomaly.type:
                impact = 0
                
                if anomaly.type == "SUSTAINED_RESOURCE_CRITICAL":
                    impact = 30
                elif anomaly.type == "SUSTAINED_RESOURCE_WARNING":
                    impact = 15
                elif anomaly.type == "RESOURCE_DRIFT":
                    impact = 10
                
                risk += impact * anomaly.confidence
                
                contributions.append(RiskContribution(
                    agent=anomaly.agent,
                    signal_type=anomaly.type,
                    impact=impact * anomaly.confidence,
                    evidence_id=anomaly.anomaly_id,
                    description=f"+{impact:.0f} risk due to {anomaly.description[:50]}"
                ))
        
        return min(100, risk)
    
    def _calculate_compliance_risk(
        self,
        cycle: ReasoningCycle,
        contributions: List[RiskContribution]
    ) -> float:
        """Calculate compliance risk component."""
        risk = self._base_risk
        
        for hit in cycle.policy_hits:
            # Each policy violation adds to compliance risk
            impact = 20  # Fixed impact per violation
            risk += impact
            
            contributions.append(RiskContribution(
                agent=hit.agent,
                signal_type="POLICY_VIOLATION",
                impact=impact,
                evidence_id=hit.hit_id,
                description=f"+{impact} risk due to policy '{hit.policy_id}' violation"
            ))
        
        return min(100, risk)
    
    def _determine_risk_state(self, score: float, cycle: ReasoningCycle) -> str:
        """Determine risk state from score and signals."""
        # Check for explicit risk signals
        for signal in cycle.risk_signals:
            if signal.projected_state == RiskState.INCIDENT:
                return "INCIDENT"
            elif signal.projected_state == RiskState.VIOLATION:
                return "VIOLATION"
        
        # Fall back to score-based state
        if score >= 80:
            return "CRITICAL"
        elif score >= 60:
            return "AT_RISK"
        elif score >= 40:
            return "DEGRADED"
        else:
            return "NORMAL"
    
    def get_history(self, limit: int = 50) -> List[RiskDataPoint]:
        """Get recent risk history."""
        history = list(self._history)
        return history[-limit:]
    
    def get_current_risk(self) -> Optional[RiskDataPoint]:
        """Get the most recent risk data point."""
        if not self._history:
            return None
        return self._history[-1]
    
    def get_trend(self, window: int = 5) -> str:
        """Get risk trend over recent window."""
        if len(self._history) < 2:
            return "stable"
        
        recent = list(self._history)[-window:]
        if len(recent) < 2:
            return "stable"
        
        first_avg = sum(p.risk_score for p in recent[:len(recent)//2]) / (len(recent)//2)
        last_avg = sum(p.risk_score for p in recent[len(recent)//2:]) / (len(recent) - len(recent)//2)
        
        diff = last_avg - first_avg
        
        if diff > 5:
            return "increasing"
        elif diff < -5:
            return "decreasing"
        else:
            return "stable"


# Singleton instance
_tracker: Optional[RiskIndexTracker] = None


def get_risk_tracker() -> RiskIndexTracker:
    """Get the singleton risk tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = RiskIndexTracker()
    return _tracker
