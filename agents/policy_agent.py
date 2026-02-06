"""
IICWMS Policy Agent
Checks compliance against encoded policies stored in the graph.

This agent is stateless - receives events and graph snapshots, returns structured opinions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid


class PolicyOpinionType(Enum):
    POLICY_VIOLATION = "POLICY_VIOLATION"
    POLICY_WARNING = "POLICY_WARNING"
    COMPLIANCE_VERIFIED = "COMPLIANCE_VERIFIED"


class PolicySeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class PolicyOpinion:
    """Structured opinion from policy agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent: str = "policy_agent"
    opinion_type: PolicyOpinionType = PolicyOpinionType.POLICY_VIOLATION
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    policy_id: str = ""
    policy_name: str = ""
    severity: PolicySeverity = PolicySeverity.MEDIUM
    evidence: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent": self.agent,
            "opinion_type": self.opinion_type.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "policy_id": self.policy_id,
            "policy_name": self.policy_name,
            "severity": self.severity.value,
            "evidence": self.evidence,
            "explanation": self.explanation
        }


class PolicyAgent:
    """
    Agent responsible for policy compliance checking.
    
    Checks:
    - Mandatory approval policies
    - Access control policies
    - Time-window policies
    - Resource usage policies
    
    Policies are first-class entities in the graph, not hardcoded rules.
    """

    def __init__(self, neo4j_client):
        self.neo4j_client = neo4j_client
        self.agent_name = "policy_agent"

    def analyze(
        self,
        events: List[Dict[str, Any]],
        scope: Optional[Dict[str, Any]] = None
    ) -> List[PolicyOpinion]:
        """
        Analyze events for policy violations.
        
        Args:
            events: List of events to check
            scope: Optional scope (workflow_id, resource_id, etc.)
            
        Returns:
            List of PolicyOpinion objects
        """
        opinions = []
        
        # Check approval policies
        approval_opinions = self._check_approval_policies(events, scope)
        opinions.extend(approval_opinions)
        
        # Check access policies
        access_opinions = self._check_access_policies(events)
        opinions.extend(access_opinions)
        
        # Check time-window policies
        time_opinions = self._check_time_policies(events)
        opinions.extend(time_opinions)
        
        return opinions

    def _check_approval_policies(
        self,
        events: List[Dict[str, Any]],
        scope: Optional[Dict[str, Any]]
    ) -> List[PolicyOpinion]:
        """Check for violations of approval policies."""
        opinions = []
        
        if not scope or "workflow_id" not in scope:
            return opinions
        
        workflow_id = scope["workflow_id"]
        
        # Query policies applicable to this workflow
        query = """
        MATCH (w:Workflow {id: $workflow_id})-[:HAS_STEP]->(s:Step)
        MATCH (p:Policy {type: 'APPROVAL_REQUIRED'})-[:APPLIES_TO]->(s)
        RETURN p.id AS policy_id, 
               p.name AS policy_name, 
               p.severity AS severity,
               s.id AS step_id, 
               s.name AS step_name
        """
        
        try:
            results = self.neo4j_client.execute_query(query, {"workflow_id": workflow_id})
        except Exception:
            # Graph may not have policies yet
            results = []
        
        for policy in results:
            step_id = policy["step_id"]
            
            # Check if approval event exists for this step
            approval_events = [
                e for e in events 
                if e.get("event_type") == "APPROVAL_GRANTED" 
                and e.get("step_id") == step_id
            ]
            
            # Check if step was completed without approval
            completion_events = [
                e for e in events 
                if e.get("event_type") == "WORKFLOW_STEP_COMPLETE" 
                and e.get("step_id") == step_id
            ]
            
            if completion_events and not approval_events:
                opinion = PolicyOpinion(
                    opinion_type=PolicyOpinionType.POLICY_VIOLATION,
                    confidence=0.95,
                    policy_id=policy["policy_id"],
                    policy_name=policy["policy_name"],
                    severity=PolicySeverity(policy.get("severity", "HIGH")),
                    evidence={
                        "workflow_id": workflow_id,
                        "step_id": step_id,
                        "step_name": policy["step_name"],
                        "required_event": "APPROVAL_GRANTED",
                        "found_events": [e.get("event_type") for e in events if e.get("step_id") == step_id]
                    },
                    explanation=f"Policy '{policy['policy_name']}' requires approval for step "
                               f"'{policy['step_name']}', but the step was completed without "
                               f"an approval event."
                )
                opinions.append(opinion)
        
        return opinions

    def _check_access_policies(
        self,
        events: List[Dict[str, Any]]
    ) -> List[PolicyOpinion]:
        """Check for violations of access control policies."""
        opinions = []
        
        # Look for credential access events
        access_events = [
            e for e in events 
            if e.get("event_type") == "CREDENTIAL_ACCESS"
        ]
        
        for event in access_events:
            metadata = event.get("metadata", {})
            
            # Check if access matches normal pattern
            if not metadata.get("matches_normal_pattern", True):
                risk_score = metadata.get("risk_score", 0.5)
                
                severity = PolicySeverity.CRITICAL if risk_score > 0.8 else (
                    PolicySeverity.HIGH if risk_score > 0.6 else PolicySeverity.MEDIUM
                )
                
                opinion = PolicyOpinion(
                    opinion_type=PolicyOpinionType.POLICY_VIOLATION,
                    confidence=risk_score,
                    policy_id="access-control-baseline",
                    policy_name="Access Control Baseline Policy",
                    severity=severity,
                    evidence={
                        "event_id": event.get("id"),
                        "timestamp": event.get("timestamp"),
                        "access_location": metadata.get("access_location"),
                        "requesting_service": metadata.get("requesting_service"),
                        "risk_score": risk_score,
                        "normal_pattern_match": False
                    },
                    explanation=f"Credential access from '{metadata.get('access_location')}' by "
                               f"'{metadata.get('requesting_service')}' does not match normal "
                               f"access patterns. Risk score: {risk_score:.2f}"
                )
                opinions.append(opinion)
        
        return opinions

    def _check_time_policies(
        self,
        events: List[Dict[str, Any]]
    ) -> List[PolicyOpinion]:
        """Check for violations of time-window policies."""
        opinions = []
        
        # This is a placeholder for time-based policy checks
        # In production, this would query time-window policies from the graph
        # and check if events occurred within allowed windows
        
        for event in events:
            timestamp = event.get("timestamp")
            if not timestamp:
                continue
            
            # Parse timestamp if it's a string
            if isinstance(timestamp, str):
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    hour = dt.hour
                except Exception:
                    continue
            else:
                hour = timestamp.hour
            
            # Check for after-hours critical operations
            is_after_hours = hour < 6 or hour > 22
            is_critical_op = event.get("event_type") in [
                "CREDENTIAL_ACCESS", 
                "RESOURCE_MODIFY", 
                "CONFIG_CHANGE"
            ]
            
            if is_after_hours and is_critical_op:
                opinion = PolicyOpinion(
                    opinion_type=PolicyOpinionType.POLICY_WARNING,
                    confidence=0.70,
                    policy_id="time-window-critical-ops",
                    policy_name="Critical Operations Time Window",
                    severity=PolicySeverity.MEDIUM,
                    evidence={
                        "event_id": event.get("id"),
                        "event_type": event.get("event_type"),
                        "timestamp": str(timestamp),
                        "hour": hour,
                        "allowed_hours": "06:00-22:00"
                    },
                    explanation=f"Critical operation '{event.get('event_type')}' occurred at "
                               f"{hour:02d}:00, outside the recommended operational window "
                               f"(06:00-22:00)."
                )
                opinions.append(opinion)
        
        return opinions

    def get_applicable_policies(self, entity_id: str, entity_type: str) -> List[Dict]:
        """Retrieve all policies applicable to a given entity."""
        query = f"""
        MATCH (p:Policy)-[:APPLIES_TO]->(e:{entity_type} {{id: $entity_id}})
        RETURN p.id AS id, 
               p.name AS name, 
               p.description AS description,
               p.severity AS severity,
               p.type AS type
        """
        
        try:
            return self.neo4j_client.execute_query(query, {"entity_id": entity_id})
        except Exception:
            return []
