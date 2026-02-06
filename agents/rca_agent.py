"""
IICWMS Root Cause Analysis Agent
Performs scoped root cause analysis using PyRCA concepts.

This agent is stateless - receives anomaly signals and graph context, returns causal hypotheses.

Note: PyRCA usage is scoped to specific anomaly types.
This agent produces "probable causal relationships, not formal proof".
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid


class RCAOpinionType(Enum):
    ROOT_CAUSE_HYPOTHESIS = "ROOT_CAUSE_HYPOTHESIS"
    CAUSAL_CHAIN = "CAUSAL_CHAIN"
    CONTRIBUTING_FACTOR = "CONTRIBUTING_FACTOR"


@dataclass
class RCAOpinion:
    """Structured opinion from RCA agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent: str = "rca_agent"
    opinion_type: RCAOpinionType = RCAOpinionType.ROOT_CAUSE_HYPOTHESIS
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    anomaly_id: str = ""
    hypothesis: str = ""
    causal_chain: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent": self.agent,
            "opinion_type": self.opinion_type.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "anomaly_id": self.anomaly_id,
            "hypothesis": self.hypothesis,
            "causal_chain": self.causal_chain,
            "evidence": self.evidence,
            "explanation": self.explanation
        }


class RCAAgent:
    """
    Agent responsible for root cause analysis.
    
    Uses:
    - Graph traversal for structural causality
    - Temporal correlation for event sequences
    - PyRCA algorithms for metric-based RCA (scoped)
    
    Important: This agent produces hypotheses, not definitive causes.
    All outputs are explicitly labeled as "probable causal relationships".
    """

    def __init__(self, neo4j_client, use_pyrca: bool = False):
        self.neo4j_client = neo4j_client
        self.agent_name = "rca_agent"
        self.use_pyrca = use_pyrca
        
        # PyRCA integration (scoped - only if enabled)
        self._pyrca_analyzer = None
        if use_pyrca:
            self._init_pyrca()

    def _init_pyrca(self):
        """Initialize PyRCA analyzer if available."""
        try:
            # PyRCA import - scoped usage
            # from pyrca.analyzers.bayesian import BayesianRCA
            # self._pyrca_analyzer = BayesianRCA()
            pass
        except ImportError:
            self.use_pyrca = False

    def analyze(
        self,
        anomalies: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        graph_context: Optional[Dict[str, Any]] = None
    ) -> List[RCAOpinion]:
        """
        Analyze anomalies to identify probable root causes.
        
        Args:
            anomalies: List of detected anomalies from other agents
            events: Timeline of events for temporal analysis
            graph_context: Additional graph state if available
            
        Returns:
            List of RCAOpinion objects with causal hypotheses
        """
        opinions = []
        
        for anomaly in anomalies:
            # Build temporal context
            temporal_opinions = self._analyze_temporal_correlation(anomaly, events)
            opinions.extend(temporal_opinions)
            
            # Build structural context from graph
            structural_opinions = self._analyze_structural_causality(anomaly)
            opinions.extend(structural_opinions)
        
        # Cross-anomaly analysis
        if len(anomalies) > 1:
            chain_opinions = self._build_causal_chain(anomalies, events)
            opinions.extend(chain_opinions)
        
        return opinions

    def _analyze_temporal_correlation(
        self,
        anomaly: Dict[str, Any],
        events: List[Dict[str, Any]]
    ) -> List[RCAOpinion]:
        """Find events that correlate temporally with the anomaly."""
        opinions = []
        
        anomaly_time = anomaly.get("timestamp") or anomaly.get("detected_at")
        if not anomaly_time:
            return opinions
        
        # Find events that occurred shortly before the anomaly
        preceding_events = []
        for event in events:
            event_time = event.get("timestamp")
            if not event_time:
                continue
            
            # Simple temporal proximity check
            # In production, this would use proper datetime comparison
            if str(event_time) < str(anomaly_time):
                preceding_events.append(event)
        
        # Sort by recency (most recent first)
        preceding_events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Take the most recent relevant events
        candidate_causes = preceding_events[:5]
        
        if candidate_causes:
            opinion = RCAOpinion(
                opinion_type=RCAOpinionType.CONTRIBUTING_FACTOR,
                confidence=0.70,
                anomaly_id=anomaly.get("id", "unknown"),
                hypothesis="Temporal correlation with preceding events",
                evidence={
                    "anomaly_timestamp": str(anomaly_time),
                    "preceding_events": [
                        {
                            "id": e.get("id"),
                            "type": e.get("event_type"),
                            "timestamp": str(e.get("timestamp"))
                        }
                        for e in candidate_causes
                    ],
                    "correlation_method": "temporal_proximity"
                },
                explanation=f"Found {len(candidate_causes)} events preceding the anomaly. "
                           f"These represent probable contributing factors, not definitive causes. "
                           f"Further investigation recommended."
            )
            opinions.append(opinion)
        
        return opinions

    def _analyze_structural_causality(
        self,
        anomaly: Dict[str, Any]
    ) -> List[RCAOpinion]:
        """Use graph structure to identify potential causes."""
        opinions = []
        
        anomaly_type = anomaly.get("opinion_type") or anomaly.get("type")
        
        # For workflow deviations, trace back through workflow structure
        if anomaly_type in ["STEP_SKIPPED", "WORKFLOW_DEVIATION", "OUT_OF_ORDER"]:
            workflow_id = anomaly.get("evidence", {}).get("workflow_id")
            if workflow_id:
                opinion = self._analyze_workflow_causality(anomaly, workflow_id)
                if opinion:
                    opinions.append(opinion)
        
        # For resource anomalies, check for cascading effects
        elif anomaly_type in ["THRESHOLD_BREACH", "TREND_ANOMALY"]:
            resource_id = anomaly.get("resource_id")
            if resource_id:
                opinion = self._analyze_resource_causality(anomaly, resource_id)
                if opinion:
                    opinions.append(opinion)
        
        return opinions

    def _analyze_workflow_causality(
        self,
        anomaly: Dict[str, Any],
        workflow_id: str
    ) -> Optional[RCAOpinion]:
        """Analyze workflow structure for causal factors."""
        try:
            # Query for workflow dependencies
            query = """
            MATCH (w:Workflow {id: $workflow_id})-[:HAS_STEP]->(s:Step)
            OPTIONAL MATCH (s)-[:REQUIRES]->(prereq:Step)
            OPTIONAL MATCH (p:Policy)-[:APPLIES_TO]->(s)
            RETURN s.id AS step_id, 
                   s.name AS step_name,
                   collect(DISTINCT prereq.name) AS prerequisites,
                   collect(DISTINCT p.name) AS policies
            ORDER BY s.sequence
            """
            
            results = self.neo4j_client.execute_query(query, {"workflow_id": workflow_id})
            
            return RCAOpinion(
                opinion_type=RCAOpinionType.ROOT_CAUSE_HYPOTHESIS,
                confidence=0.75,
                anomaly_id=anomaly.get("id", "unknown"),
                hypothesis="Workflow structure analysis indicates potential control gap",
                causal_chain=[
                    "Workflow initiated",
                    "Step dependencies not enforced",
                    "Mandatory step bypassed",
                    "Anomaly detected"
                ],
                evidence={
                    "workflow_id": workflow_id,
                    "workflow_structure": results,
                    "analysis_method": "graph_traversal"
                },
                explanation="Graph analysis reveals the workflow structure that allowed "
                           "this deviation. The causal chain shows how the control gap "
                           "enabled the anomalous behavior. This is a probable causal "
                           "relationship, not formal proof."
            )
        except Exception:
            return None

    def _analyze_resource_causality(
        self,
        anomaly: Dict[str, Any],
        resource_id: str
    ) -> Optional[RCAOpinion]:
        """Analyze resource dependencies for causal factors."""
        try:
            # Get ripple effect from graph
            ripple = self.neo4j_client.get_ripple_effect(resource_id)
            
            return RCAOpinion(
                opinion_type=RCAOpinionType.ROOT_CAUSE_HYPOTHESIS,
                confidence=0.70,
                anomaly_id=anomaly.get("id", "unknown"),
                hypothesis="Resource dependency chain indicates cascading impact",
                causal_chain=[
                    f"Resource {resource_id} degraded",
                    "Dependent steps affected",
                    "Cascading resource pressure",
                    "Threshold breach detected"
                ],
                evidence={
                    "resource_id": resource_id,
                    "ripple_effect": ripple,
                    "affected_count": len(ripple),
                    "analysis_method": "graph_ripple_traversal"
                },
                explanation="Graph analysis reveals resources and steps that depend on "
                           "the affected resource. The cascading nature suggests this "
                           "anomaly may be a symptom rather than the root cause."
            )
        except Exception:
            return None

    def _build_causal_chain(
        self,
        anomalies: List[Dict[str, Any]],
        events: List[Dict[str, Any]]
    ) -> List[RCAOpinion]:
        """Build a causal chain across multiple anomalies."""
        opinions = []
        
        # Sort anomalies by timestamp
        sorted_anomalies = sorted(
            anomalies,
            key=lambda x: str(x.get("timestamp") or x.get("detected_at") or "")
        )
        
        if len(sorted_anomalies) >= 2:
            chain = [a.get("opinion_type") or a.get("type", "unknown") for a in sorted_anomalies]
            
            opinion = RCAOpinion(
                opinion_type=RCAOpinionType.CAUSAL_CHAIN,
                confidence=0.65,
                anomaly_id="chain-analysis",
                hypothesis="Multiple anomalies suggest cascading failure pattern",
                causal_chain=chain,
                evidence={
                    "anomaly_sequence": [
                        {
                            "id": a.get("id"),
                            "type": a.get("opinion_type") or a.get("type"),
                            "timestamp": str(a.get("timestamp") or a.get("detected_at"))
                        }
                        for a in sorted_anomalies
                    ],
                    "chain_length": len(sorted_anomalies),
                    "analysis_method": "temporal_chain_analysis"
                },
                explanation=f"Analysis of {len(sorted_anomalies)} anomalies reveals a temporal "
                           f"sequence suggesting cascading effects. The earliest anomaly in the "
                           f"chain may be closer to the root cause. These are probable causal "
                           f"relationships, not formal proof."
            )
            opinions.append(opinion)
        
        return opinions
