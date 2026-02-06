"""
IICWMS Master Agent
Synthesizes opinions from all agents, resolves conflicts, and generates final insights.

Agents are coordinated through a shared evidence substrate (the Blackboard).
The Master Agent orchestrates this coordination.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid


class InsightSeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class InsightCategory(Enum):
    COMPLIANCE_VIOLATION = "COMPLIANCE_VIOLATION"
    WORKFLOW_ANOMALY = "WORKFLOW_ANOMALY"
    RESOURCE_ISSUE = "RESOURCE_ISSUE"
    SECURITY_CONCERN = "SECURITY_CONCERN"
    OPERATIONAL_WARNING = "OPERATIONAL_WARNING"


@dataclass
class Insight:
    """Final insight synthesized from multiple agent opinions."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    category: InsightCategory = InsightCategory.OPERATIONAL_WARNING
    severity: InsightSeverity = InsightSeverity.MEDIUM
    title: str = ""
    summary: str = ""
    confidence: float = 0.0
    contributing_opinions: List[str] = field(default_factory=list)
    evidence_chain: List[Dict[str, Any]] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    explanation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "summary": self.summary,
            "confidence": self.confidence,
            "contributing_opinions": self.contributing_opinions,
            "evidence_chain": self.evidence_chain,
            "recommended_actions": self.recommended_actions,
            "explanation": self.explanation
        }


class MasterAgent:
    """
    Master Agent responsible for:
    1. Orchestrating specialized agents
    2. Synthesizing opinions into insights
    3. Resolving conflicting opinions
    4. Generating human-readable explanations
    
    Note: LLMs are used for explanation, not detection.
    The Master Agent coordinates but does not override agent opinions.
    """

    def __init__(
        self,
        neo4j_client,
        evidence_store,
        llm_client: Optional[Any] = None
    ):
        self.neo4j_client = neo4j_client
        self.evidence_store = evidence_store
        self.llm_client = llm_client
        self.agent_name = "master_agent"
        
        # Import specialized agents
        from .workflow_agent import WorkflowAgent
        from .policy_agent import PolicyAgent
        from .resource_agent import ResourceAgent
        from .rca_agent import RCAAgent
        
        # Initialize agent mesh
        self.workflow_agent = WorkflowAgent(neo4j_client)
        self.policy_agent = PolicyAgent(neo4j_client)
        self.resource_agent = ResourceAgent(neo4j_client)
        self.rca_agent = RCAAgent(neo4j_client)

    def analyze(
        self,
        events: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Insight]:
        """
        Orchestrate all agents and synthesize insights.
        
        Args:
            events: List of events to analyze
            context: Additional context (workflow_id, resource_id, etc.)
            
        Returns:
            List of synthesized Insight objects
        """
        all_opinions = []
        context = context or {}
        
        # Phase 1: Collect opinions from specialized agents
        
        # Workflow analysis
        if "workflow_id" in context:
            workflow_opinions = self.workflow_agent.analyze(
                context["workflow_id"],
                events
            )
            all_opinions.extend([o.to_dict() for o in workflow_opinions])
        
        # Policy analysis
        policy_opinions = self.policy_agent.analyze(events, context)
        all_opinions.extend([o.to_dict() for o in policy_opinions])
        
        # Resource analysis
        resource_opinions = self.resource_agent.analyze(
            events,
            context.get("resource_id")
        )
        all_opinions.extend([o.to_dict() for o in resource_opinions])
        
        # Phase 2: Log all opinions to evidence store
        for opinion in all_opinions:
            self.evidence_store.append(opinion)
        
        # Phase 3: RCA analysis on detected anomalies
        if all_opinions:
            rca_opinions = self.rca_agent.analyze(all_opinions, events, context)
            for opinion in rca_opinions:
                opinion_dict = opinion.to_dict()
                all_opinions.append(opinion_dict)
                self.evidence_store.append(opinion_dict)
        
        # Phase 4: Synthesize insights from opinions
        insights = self._synthesize_insights(all_opinions)
        
        return insights

    def _synthesize_insights(
        self,
        opinions: List[Dict[str, Any]]
    ) -> List[Insight]:
        """Synthesize opinions into actionable insights."""
        insights = []
        
        # Group opinions by type/category
        groups = self._group_opinions(opinions)
        
        for category, category_opinions in groups.items():
            if not category_opinions:
                continue
            
            insight = self._create_insight_from_group(category, category_opinions)
            if insight:
                insights.append(insight)
        
        # Sort by severity
        severity_order = {
            InsightSeverity.CRITICAL: 0,
            InsightSeverity.HIGH: 1,
            InsightSeverity.MEDIUM: 2,
            InsightSeverity.LOW: 3,
            InsightSeverity.INFO: 4
        }
        insights.sort(key=lambda x: severity_order.get(x.severity, 99))
        
        return insights

    def _group_opinions(
        self,
        opinions: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group opinions by their category."""
        groups = {
            "workflow": [],
            "policy": [],
            "resource": [],
            "rca": []
        }
        
        for opinion in opinions:
            agent = opinion.get("agent", "")
            opinion_type = opinion.get("opinion_type", "")
            
            if agent == "workflow_agent" or "WORKFLOW" in opinion_type:
                groups["workflow"].append(opinion)
            elif agent == "policy_agent" or "POLICY" in opinion_type:
                groups["policy"].append(opinion)
            elif agent == "resource_agent" or "RESOURCE" in opinion_type or "THRESHOLD" in opinion_type:
                groups["resource"].append(opinion)
            elif agent == "rca_agent" or "CAUSAL" in opinion_type or "ROOT_CAUSE" in opinion_type:
                groups["rca"].append(opinion)
        
        return groups

    def _create_insight_from_group(
        self,
        category: str,
        opinions: List[Dict[str, Any]]
    ) -> Optional[Insight]:
        """Create an insight from a group of related opinions."""
        if not opinions:
            return None
        
        # Calculate aggregate confidence
        confidences = [o.get("confidence", 0.5) for o in opinions]
        avg_confidence = sum(confidences) / len(confidences)
        max_confidence = max(confidences)
        
        # Use weighted confidence (favor higher individual confidences)
        aggregate_confidence = (avg_confidence + max_confidence) / 2
        
        # Determine severity based on category and confidence
        severity = self._determine_severity(category, opinions, aggregate_confidence)
        
        # Build evidence chain
        evidence_chain = [
            {
                "opinion_id": o.get("id"),
                "agent": o.get("agent"),
                "type": o.get("opinion_type"),
                "confidence": o.get("confidence")
            }
            for o in opinions
        ]
        
        # Map category to InsightCategory
        category_map = {
            "workflow": InsightCategory.WORKFLOW_ANOMALY,
            "policy": InsightCategory.COMPLIANCE_VIOLATION,
            "resource": InsightCategory.RESOURCE_ISSUE,
            "rca": InsightCategory.OPERATIONAL_WARNING
        }
        
        insight_category = category_map.get(category, InsightCategory.OPERATIONAL_WARNING)
        
        # Generate title and summary
        title, summary = self._generate_insight_text(category, opinions)
        
        # Generate recommended actions
        actions = self._generate_recommended_actions(category, opinions)
        
        # Generate explanation
        explanation = self._generate_explanation(opinions)
        
        return Insight(
            category=insight_category,
            severity=severity,
            title=title,
            summary=summary,
            confidence=round(aggregate_confidence, 3),
            contributing_opinions=[o.get("id") for o in opinions],
            evidence_chain=evidence_chain,
            recommended_actions=actions,
            explanation=explanation
        )

    def _determine_severity(
        self,
        category: str,
        opinions: List[Dict[str, Any]],
        confidence: float
    ) -> InsightSeverity:
        """Determine insight severity based on category and evidence."""
        # Check for explicit severity in opinions
        for opinion in opinions:
            if opinion.get("severity") == "CRITICAL":
                return InsightSeverity.CRITICAL
        
        # Policy violations are generally high severity
        if category == "policy":
            return InsightSeverity.HIGH if confidence > 0.7 else InsightSeverity.MEDIUM
        
        # Workflow anomalies depend on the specific type
        if category == "workflow":
            for opinion in opinions:
                if "SKIPPED" in opinion.get("opinion_type", ""):
                    return InsightSeverity.HIGH
            return InsightSeverity.MEDIUM
        
        # Resource issues based on threshold breach
        if category == "resource":
            for opinion in opinions:
                evidence = opinion.get("evidence", {})
                if evidence.get("overage_percent", 0) > 20:
                    return InsightSeverity.HIGH
            return InsightSeverity.MEDIUM
        
        return InsightSeverity.MEDIUM if confidence > 0.6 else InsightSeverity.LOW

    def _generate_insight_text(
        self,
        category: str,
        opinions: List[Dict[str, Any]]
    ) -> tuple:
        """Generate title and summary for an insight."""
        titles = {
            "workflow": "Workflow Integrity Issue Detected",
            "policy": "Policy Compliance Violation",
            "resource": "Resource Anomaly Detected",
            "rca": "Root Cause Analysis Available"
        }
        
        title = titles.get(category, "System Anomaly Detected")
        
        # Build summary from opinion explanations
        explanations = [o.get("explanation", "") for o in opinions if o.get("explanation")]
        if explanations:
            summary = " ".join(explanations[:2])  # Take first 2
        else:
            summary = f"Multiple {category} anomalies detected requiring attention."
        
        return title, summary

    def _generate_recommended_actions(
        self,
        category: str,
        opinions: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommended actions based on insight category."""
        actions = {
            "workflow": [
                "Review workflow execution logs",
                "Verify mandatory step enforcement configuration",
                "Check for unauthorized workflow modifications"
            ],
            "policy": [
                "Investigate policy violation details",
                "Review access logs for the affected period",
                "Verify identity and authorization of involved actors"
            ],
            "resource": [
                "Monitor resource trends over next 30 minutes",
                "Identify processes consuming excessive resources",
                "Consider scaling or load balancing if pattern persists"
            ],
            "rca": [
                "Review the causal chain analysis",
                "Investigate the earliest event in the chain",
                "Correlate with recent system changes"
            ]
        }
        
        return actions.get(category, ["Investigate further", "Review system logs"])

    def _generate_explanation(
        self,
        opinions: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a human-readable explanation.
        
        Note: If LLM is available, it's used for natural language generation.
        LLMs are used for explanation, not detection.
        """
        # Build structured explanation from evidence
        parts = [
            "This insight was generated by synthesizing opinions from multiple agents.",
            f"Total contributing opinions: {len(opinions)}.",
        ]
        
        agents = set(o.get("agent", "unknown") for o in opinions)
        parts.append(f"Agents involved: {', '.join(agents)}.")
        
        parts.append(
            "Each opinion is traceable to specific evidence in the evidence store. "
            "These represent probable causal relationships, not formal proof."
        )
        
        # If LLM available, enhance explanation (placeholder)
        if self.llm_client:
            # In production, this would call the LLM for natural language generation
            pass
        
        return " ".join(parts)

    def get_insight_evidence(self, insight_id: str) -> Dict[str, Any]:
        """Retrieve full evidence chain for an insight."""
        # Query evidence store for related records
        return self.evidence_store.get_by_insight(insight_id)
