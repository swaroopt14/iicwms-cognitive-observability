"""
IICWMS Causal Agent
===================
Identifies causal relationships.

INPUT:
- Anomalies
- Risk signals
- Policy hits

OUTPUT:
{
  "cause": "NETWORK_LATENCY",
  "effect": "WORKFLOW_DELAY",
  "confidence": 0.81
}

NO ML REQUIRED.
Temporal + dependency reasoning is enough.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import threading

from blackboard import (
    SharedState, CausalLink,
    Anomaly, PolicyHit, RiskSignal
)
from .langgraph_runtime import run_linear_graph, is_langgraph_enabled


# Known causal patterns (dependency reasoning)
CAUSAL_PATTERNS = {
    # Resource issues → Workflow effects
    ("SUSTAINED_RESOURCE_CRITICAL", "WORKFLOW_DELAY"): {
        "confidence": 0.85,
        "reasoning": "Resource saturation directly impacts workflow execution time"
    },
    ("SUSTAINED_RESOURCE_WARNING", "WORKFLOW_DELAY"): {
        "confidence": 0.7,
        "reasoning": "Elevated resource usage may contribute to workflow slowdown"
    },
    ("RESOURCE_DRIFT", "WORKFLOW_DELAY"): {
        "confidence": 0.6,
        "reasoning": "Resource drift suggests degrading conditions affecting performance"
    },
    
    # Missing steps → Policy violations
    ("MISSING_STEP", "SILENT"): {
        "confidence": 0.9,
        "reasoning": "Skipped steps often bypass compliance checkpoints"
    },
    
    # Sequence violations → Risk escalation
    ("SEQUENCE_VIOLATION", "AT_RISK"): {
        "confidence": 0.75,
        "reasoning": "Out-of-order execution indicates process breakdown"
    }
}


@dataclass
class CausalCandidate:
    """A potential causal link to evaluate."""
    cause_type: str
    cause_entity: str
    effect_type: str
    effect_entity: str
    temporal_distance: timedelta
    evidence_ids: List[str]


class CausalAgent:
    """
    Causal Agent
    
    Identifies causal relationships using:
    - Temporal precedence (cause must precede effect)
    - Dependency patterns (known cause-effect relationships)
    - Correlation strength
    
    NO ML REQUIRED. Temporal + dependency reasoning is enough.
    
    Agents do NOT communicate directly.
    All output goes to SharedState + Neo4j (if enabled).
    """
    
    AGENT_NAME = "CausalAgent"
    
    def __init__(self):
        self._identified_links: List[str] = []  # Track for dedup
        self._graph = None
        self._use_langgraph = is_langgraph_enabled()
    
    def _get_graph(self):
        """Lazy-init Neo4j client."""
        if self._graph is None:
            from graph import get_neo4j_client
            self._graph = get_neo4j_client()
        return self._graph
    
    def analyze(
        self,
        anomalies: List[Anomaly],
        policy_hits: List[PolicyHit],
        risk_signals: List[RiskSignal],
        state: SharedState
    ) -> List[CausalLink]:
        if self._use_langgraph:
            graph_state = run_linear_graph(
                {
                    "anomalies": anomalies,
                    "policy_hits": policy_hits,
                    "risk_signals": risk_signals,
                    "state": state,
                    "candidates": [],
                    "links": [],
                },
                [
                    ("find_candidates", self._graph_find_candidates),
                    ("evaluate_candidates", self._graph_evaluate_candidates),
                ],
            )
            return graph_state.get("links", [])
        return self._analyze_core(anomalies, policy_hits, risk_signals, state)

    def _analyze_core(
        self,
        anomalies: List[Anomaly],
        policy_hits: List[PolicyHit],
        risk_signals: List[RiskSignal],
        state: SharedState
    ) -> List[CausalLink]:
        """
        Analyze patterns to identify causal links.
        
        Returns causal links found (also written to state).
        """
        links = []
        
        # Find candidates based on temporal proximity
        candidates = self._find_candidates(anomalies, policy_hits, risk_signals)
        
        # Evaluate each candidate
        for candidate in candidates:
            link = self._evaluate_candidate(candidate, state)
            if link:
                links.append(link)
        
        return links

    def _graph_find_candidates(self, graph_state: Dict[str, Any]) -> Dict[str, Any]:
        graph_state["candidates"] = self._find_candidates(
            graph_state["anomalies"], graph_state["policy_hits"], graph_state["risk_signals"]
        )
        return graph_state

    def _graph_evaluate_candidates(self, graph_state: Dict[str, Any]) -> Dict[str, Any]:
        links: List[CausalLink] = []
        state = graph_state["state"]
        for candidate in graph_state.get("candidates", []):
            link = self._evaluate_candidate(candidate, state)
            if link:
                links.append(link)
        graph_state["links"] = links
        return graph_state
    
    def _find_candidates(
        self,
        anomalies: List[Anomaly],
        policy_hits: List[PolicyHit],
        risk_signals: List[RiskSignal]
    ) -> List[CausalCandidate]:
        """Find causal candidates based on temporal proximity."""
        candidates = []
        
        # Sort all items by timestamp
        all_items = []
        
        for a in anomalies:
            all_items.append(("anomaly", a.type, a.anomaly_id, a.timestamp, a))
        
        for p in policy_hits:
            all_items.append(("policy", p.violation_type, p.hit_id, p.timestamp, p))
        
        for r in risk_signals:
            all_items.append(("risk", r.projected_state.value, r.signal_id, r.timestamp, r))
        
        all_items.sort(key=lambda x: x[3])
        
        # Look for temporal patterns (items within 60 seconds of each other)
        for i, (type1, subtype1, id1, ts1, item1) in enumerate(all_items):
            for j in range(i + 1, len(all_items)):
                type2, subtype2, id2, ts2, item2 = all_items[j]
                
                distance = ts2 - ts1
                if distance > timedelta(seconds=60):
                    break  # Too far apart
                
                # Check if this matches a known pattern
                pattern_key = (subtype1, subtype2)
                if pattern_key in CAUSAL_PATTERNS:
                    cause_entity = self._extract_entity(item1)
                    effect_entity = self._extract_entity(item2)
                    
                    candidates.append(CausalCandidate(
                        cause_type=subtype1,
                        cause_entity=cause_entity,
                        effect_type=subtype2,
                        effect_entity=effect_entity,
                        temporal_distance=distance,
                        evidence_ids=[id1, id2]
                    ))
        
        return candidates
    
    def _extract_entity(self, item: Any) -> str:
        """Extract entity identifier from an item."""
        if hasattr(item, 'description'):
            desc = item.description
            # Look for common entity patterns
            for word in desc.split():
                if word.startswith(("wf_", "vm_", "storage_")):
                    return word.rstrip(",.")
        
        if hasattr(item, 'entity'):
            return item.entity
        
        if hasattr(item, 'anomaly_id'):
            return item.anomaly_id
        
        return "unknown"
    
    def _evaluate_candidate(
        self,
        candidate: CausalCandidate,
        state: SharedState
    ) -> Optional[CausalLink]:
        """Evaluate a causal candidate and create link if valid."""
        pattern_key = (candidate.cause_type, candidate.effect_type)
        
        if pattern_key not in CAUSAL_PATTERNS:
            return None
        
        pattern = CAUSAL_PATTERNS[pattern_key]
        
        # Dedup check
        link_key = f"{candidate.cause_type}:{candidate.cause_entity}->{candidate.effect_type}:{candidate.effect_entity}"
        if link_key in self._identified_links:
            return None
        
        self._identified_links.append(link_key)
        
        # Adjust confidence based on temporal distance
        base_confidence = pattern["confidence"]
        time_factor = 1.0 - (candidate.temporal_distance.total_seconds() / 60)  # Closer = higher
        adjusted_confidence = base_confidence * max(0.5, time_factor)
        
        reasoning = self._build_friendly_reasoning(
            cause_type=candidate.cause_type,
            effect_type=candidate.effect_type,
            temporal_distance=candidate.temporal_distance,
            base_reason=pattern["reasoning"],
        )

        # Create causal link in blackboard
        link = state.add_causal_link(
            cause=candidate.cause_type,
            effect=candidate.effect_type,
            cause_entity=candidate.cause_entity,
            effect_entity=candidate.effect_entity,
            confidence=adjusted_confidence,
            reasoning=reasoning,
            evidence_ids=candidate.evidence_ids
        )
        
        # Write to Neo4j knowledge graph (fire-and-forget in background thread)
        def _write():
            try:
                self._get_graph().write_causal_link(
                    cause=candidate.cause_type,
                    effect=candidate.effect_type,
                    cause_entity=candidate.cause_entity,
                    effect_entity=candidate.effect_entity,
                    confidence=adjusted_confidence,
                    reasoning=reasoning,
                )
            except Exception:
                pass
        threading.Thread(target=_write, daemon=True).start()
        
        return link
    
    def get_causal_chain(self, entity: str) -> List[CausalLink]:
        """
        Get causal chain for an entity.
        
        Traces back through causes to find root.
        """
        # Would query state for all links involving entity
        # For now, return empty (would implement with graph queries)
        return []

    def _build_friendly_reasoning(
        self,
        cause_type: str,
        effect_type: str,
        temporal_distance: timedelta,
        base_reason: str,
    ) -> str:
        """
        Plain-English explanation for UI and audits.
        Avoids overly statistical language for operators.
        """
        secs = int(max(1, temporal_distance.total_seconds()))
        cause = cause_type.replace("_", " ").title()
        effect = effect_type.replace("_", " ").title()
        return (
            f"Observed sequence: {cause} happened before {effect} "
            f"(~{secs}s gap). Likely link: {base_reason}. "
            "Use linked evidence IDs to validate and act."
        )
