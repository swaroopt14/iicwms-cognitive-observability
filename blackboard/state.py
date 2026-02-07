"""
IICWMS Shared State (Blackboard)
================================
Makes reasoning INSPECTABLE and DEBUGGABLE.

PURPOSE:
- Shared state between agents
- Each agent appends its own section
- No overwrites, no deletions in same cycle

CANONICAL STRUCTURE:
{
  "cycle_id": "cycle_104",
  "facts": [...],
  "anomalies": [],
  "policy_hits": [],
  "risk_signals": [],
  "hypotheses": [],
  "causal_links": [],
  "recommendations": []
}
"""

import json
import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path
from enum import Enum
import threading


class RiskState(Enum):
    """Risk trajectory states."""
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    AT_RISK = "AT_RISK"
    VIOLATION = "VIOLATION"
    INCIDENT = "INCIDENT"


@dataclass
class Fact:
    """A derived fact from observation."""
    fact_id: str
    source: str  # Which agent derived this
    claim: str
    evidence_ids: List[str]  # Event IDs
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Anomaly:
    """An anomaly detected by an agent."""
    anomaly_id: str
    type: str  # WORKFLOW_DELAY, RESOURCE_SPIKE, etc.
    agent: str
    evidence: List[str]  # What observations led to this
    description: str
    confidence: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PolicyHit:
    """A policy violation detected."""
    hit_id: str
    policy_id: str
    event_id: str
    violation_type: str  # SILENT, DIRECT, COMBINATION
    agent: str
    description: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RiskSignal:
    """A risk forecast from the Risk Agent."""
    signal_id: str
    entity: str  # What is at risk (workflow, resource)
    entity_type: str  # "workflow", "resource"
    current_state: RiskState
    projected_state: RiskState
    confidence: float
    time_horizon: str  # "10-15 min"
    reasoning: str
    evidence_ids: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Hypothesis:
    """A hypothesis from any agent."""
    hypothesis_id: str
    agent: str
    claim: str
    evidence_ids: List[str]
    confidence: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CausalLink:
    """A causal link identified by the Causal Agent."""
    link_id: str
    cause: str  # e.g., "NETWORK_LATENCY"
    effect: str  # e.g., "WORKFLOW_DELAY"
    cause_entity: str  # e.g., "vm_api_01"
    effect_entity: str  # e.g., "wf_deploy_abc123"
    confidence: float
    reasoning: str
    evidence_ids: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Recommendation:
    """A recommended action."""
    rec_id: str
    cause: str
    action: str
    urgency: str  # LOW, MEDIUM, HIGH, CRITICAL
    rationale: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReasoningCycle:
    """
    A complete reasoning cycle.
    
    Each cycle is immutable once completed.
    """
    cycle_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    facts: List[Fact] = field(default_factory=list)
    anomalies: List[Anomaly] = field(default_factory=list)
    policy_hits: List[PolicyHit] = field(default_factory=list)
    risk_signals: List[RiskSignal] = field(default_factory=list)
    hypotheses: List[Hypothesis] = field(default_factory=list)
    causal_links: List[CausalLink] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "cycle_id": self.cycle_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "facts": [asdict(f) | {"timestamp": f.timestamp.isoformat()} for f in self.facts],
            "anomalies": [asdict(a) | {"timestamp": a.timestamp.isoformat()} for a in self.anomalies],
            "policy_hits": [asdict(p) | {"timestamp": p.timestamp.isoformat()} for p in self.policy_hits],
            "risk_signals": [
                asdict(r) | {
                    "timestamp": r.timestamp.isoformat(),
                    "current_state": r.current_state.value,
                    "projected_state": r.projected_state.value
                } for r in self.risk_signals
            ],
            "hypotheses": [asdict(h) | {"timestamp": h.timestamp.isoformat()} for h in self.hypotheses],
            "causal_links": [asdict(c) | {"timestamp": c.timestamp.isoformat()} for c in self.causal_links],
            "recommendations": [asdict(r) | {"timestamp": r.timestamp.isoformat()} for r in self.recommendations],
        }


class SharedState:
    """
    The Shared State (Blackboard).
    
    Rules:
    - Each agent appends its own section
    - No overwrites
    - No deletions in same cycle
    """
    
    def __init__(self, storage_path: str = "blackboard/cycles.jsonl"):
        self._storage_path = Path(storage_path)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._current_cycle: Optional[ReasoningCycle] = None
        self._completed_cycles: List[ReasoningCycle] = []
        self._lock = threading.Lock()
        
        self._load_history()
    
    def _load_history(self):
        """Load completed cycles from storage."""
        if not self._storage_path.exists():
            return
        
        # For now, just ensure the file exists
        # Full deserialization can be implemented if needed
    
    # ─────────────────────────────────────────────────────────────────────────────
    # CYCLE MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────────
    
    def start_cycle(self) -> str:
        """Start a new reasoning cycle."""
        with self._lock:
            cycle_id = f"cycle_{uuid.uuid4().hex[:8]}"
            self._current_cycle = ReasoningCycle(
                cycle_id=cycle_id,
                started_at=datetime.utcnow()
            )
            return cycle_id
    
    def complete_cycle(self) -> Optional[ReasoningCycle]:
        """Complete the current cycle and persist it."""
        with self._lock:
            if not self._current_cycle:
                return None
            
            self._current_cycle.completed_at = datetime.utcnow()
            self._persist_cycle(self._current_cycle)
            self._completed_cycles.append(self._current_cycle)
            
            completed = self._current_cycle
            self._current_cycle = None
            
            return completed
    
    def _persist_cycle(self, cycle: ReasoningCycle):
        """Persist a cycle to storage."""
        with open(self._storage_path, 'a') as f:
            f.write(json.dumps(cycle.to_dict()) + '\n')
    
    @property
    def current_cycle(self) -> Optional[ReasoningCycle]:
        return self._current_cycle
    
    # ─────────────────────────────────────────────────────────────────────────────
    # AGENT APPEND APIs (Each agent appends its own section)
    # ─────────────────────────────────────────────────────────────────────────────
    
    def add_fact(self, source: str, claim: str, evidence_ids: List[str]) -> Fact:
        """Add a fact (any agent)."""
        with self._lock:
            if not self._current_cycle:
                raise RuntimeError("No active cycle")
            
            fact = Fact(
                fact_id=f"fact_{uuid.uuid4().hex[:8]}",
                source=source,
                claim=claim,
                evidence_ids=evidence_ids
            )
            self._current_cycle.facts.append(fact)
            return fact
    
    def add_anomaly(
        self,
        type: str,
        agent: str,
        evidence: List[str],
        description: str,
        confidence: float
    ) -> Anomaly:
        """Add an anomaly (Workflow/Resource agents)."""
        with self._lock:
            if not self._current_cycle:
                raise RuntimeError("No active cycle")
            
            anomaly = Anomaly(
                anomaly_id=f"anom_{uuid.uuid4().hex[:8]}",
                type=type,
                agent=agent,
                evidence=evidence,
                description=description,
                confidence=confidence
            )
            self._current_cycle.anomalies.append(anomaly)
            return anomaly
    
    def add_policy_hit(
        self,
        policy_id: str,
        event_id: str,
        violation_type: str,
        agent: str,
        description: str
    ) -> PolicyHit:
        """Add a policy violation (Compliance Agent)."""
        with self._lock:
            if not self._current_cycle:
                raise RuntimeError("No active cycle")
            
            hit = PolicyHit(
                hit_id=f"hit_{uuid.uuid4().hex[:8]}",
                policy_id=policy_id,
                event_id=event_id,
                violation_type=violation_type,
                agent=agent,
                description=description
            )
            self._current_cycle.policy_hits.append(hit)
            return hit
    
    def add_risk_signal(
        self,
        entity: str,
        entity_type: str,
        current_state: RiskState,
        projected_state: RiskState,
        confidence: float,
        time_horizon: str,
        reasoning: str,
        evidence_ids: List[str]
    ) -> RiskSignal:
        """Add a risk signal (Risk Forecast Agent)."""
        with self._lock:
            if not self._current_cycle:
                raise RuntimeError("No active cycle")
            
            signal = RiskSignal(
                signal_id=f"risk_{uuid.uuid4().hex[:8]}",
                entity=entity,
                entity_type=entity_type,
                current_state=current_state,
                projected_state=projected_state,
                confidence=confidence,
                time_horizon=time_horizon,
                reasoning=reasoning,
                evidence_ids=evidence_ids
            )
            self._current_cycle.risk_signals.append(signal)
            return signal
    
    def add_hypothesis(
        self,
        agent: str,
        claim: str,
        evidence_ids: List[str],
        confidence: float
    ) -> Hypothesis:
        """Add a hypothesis (any agent)."""
        with self._lock:
            if not self._current_cycle:
                raise RuntimeError("No active cycle")
            
            hypothesis = Hypothesis(
                hypothesis_id=f"hyp_{uuid.uuid4().hex[:8]}",
                agent=agent,
                claim=claim,
                evidence_ids=evidence_ids,
                confidence=confidence
            )
            self._current_cycle.hypotheses.append(hypothesis)
            return hypothesis
    
    def add_causal_link(
        self,
        cause: str,
        effect: str,
        cause_entity: str,
        effect_entity: str,
        confidence: float,
        reasoning: str,
        evidence_ids: List[str]
    ) -> CausalLink:
        """Add a causal link (Causal Agent)."""
        with self._lock:
            if not self._current_cycle:
                raise RuntimeError("No active cycle")
            
            link = CausalLink(
                link_id=f"cause_{uuid.uuid4().hex[:8]}",
                cause=cause,
                effect=effect,
                cause_entity=cause_entity,
                effect_entity=effect_entity,
                confidence=confidence,
                reasoning=reasoning,
                evidence_ids=evidence_ids
            )
            self._current_cycle.causal_links.append(link)
            return link
    
    def add_recommendation(
        self,
        cause: str,
        action: str,
        urgency: str,
        rationale: str
    ) -> Recommendation:
        """Add a recommendation (Master Agent)."""
        with self._lock:
            if not self._current_cycle:
                raise RuntimeError("No active cycle")
            
            rec = Recommendation(
                rec_id=f"rec_{uuid.uuid4().hex[:8]}",
                cause=cause,
                action=action,
                urgency=urgency,
                rationale=rationale
            )
            self._current_cycle.recommendations.append(rec)
            return rec
    
    # ─────────────────────────────────────────────────────────────────────────────
    # QUERY APIs
    # ─────────────────────────────────────────────────────────────────────────────
    
    def get_current_anomalies(self) -> List[Anomaly]:
        """Get anomalies from current cycle."""
        if not self._current_cycle:
            return []
        return list(self._current_cycle.anomalies)
    
    def get_current_policy_hits(self) -> List[PolicyHit]:
        """Get policy hits from current cycle."""
        if not self._current_cycle:
            return []
        return list(self._current_cycle.policy_hits)
    
    def get_current_risk_signals(self) -> List[RiskSignal]:
        """Get risk signals from current cycle."""
        if not self._current_cycle:
            return []
        return list(self._current_cycle.risk_signals)
    
    def get_recent_cycles(self, count: int = 10) -> List[ReasoningCycle]:
        """Get most recent completed cycles."""
        return self._completed_cycles[-count:]


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton access
# ═══════════════════════════════════════════════════════════════════════════════

_instance: Optional[SharedState] = None


def get_shared_state() -> SharedState:
    """Get the singleton shared state instance."""
    global _instance
    if _instance is None:
        _instance = SharedState()
    return _instance
