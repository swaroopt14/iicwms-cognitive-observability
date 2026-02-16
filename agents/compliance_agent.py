"""
IICWMS Compliance Agent
=======================
Detects policy violations.

INPUT:
- Events
- Policy definitions

DETECTS:
- Silent violations

OUTPUT:
{
  "policy_id": "NO_AFTER_HOURS_WRITE",
  "event_id": "evt_001",
  "violation_type": "SILENT"
}
"""

from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass

from observation import ObservedEvent
from blackboard import SharedState, PolicyHit
from .langgraph_runtime import run_linear_graph, is_langgraph_enabled


@dataclass
class Policy:
    """
    Static Policy Definition.
    
    Policies are rules, not detectors.
    """
    policy_id: str
    name: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    rationale: str
    check: Callable[[ObservedEvent], bool]  # Returns True if violated


# ═══════════════════════════════════════════════════════════════════════════════
# POLICY DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _check_after_hours_write(event: ObservedEvent) -> bool:
    """WRITE operations outside business hours (9-18)."""
    if event.type != "ACCESS_WRITE":
        return False
    hour = event.timestamp.hour
    return hour < 9 or hour > 18


def _check_unusual_location_access(event: ObservedEvent) -> bool:
    """Access from unusual/untrusted locations."""
    if event.type not in ("ACCESS_READ", "ACCESS_WRITE", "CREDENTIAL_ACCESS"):
        return False
    location = event.metadata.get("location", "")
    return location in ("external_unknown", "vpn_foreign", "tor_exit_node")


def _check_sensitive_resource_access(event: ObservedEvent) -> bool:
    """Access to sensitive resources without proper workflow."""
    if event.type not in ("ACCESS_READ", "ACCESS_WRITE"):
        return False
    resource = event.resource or ""
    sensitive = ("secrets", "production", "credentials", "config_secrets")
    return any(s in resource.lower() for s in sensitive) and not event.workflow_id


def _check_service_account_write(event: ObservedEvent) -> bool:
    """Service accounts should not perform direct writes."""
    if event.type != "ACCESS_WRITE":
        return False
    return event.actor.startswith("svc_")


def _check_skipped_approval(event: ObservedEvent) -> bool:
    """Deployment without approval step."""
    if event.type != "WORKFLOW_STEP_SKIP":
        return False
    skipped = event.metadata.get("skipped_step", "")
    return "approval" in skipped.lower()


# Policy registry
POLICIES: List[Policy] = [
    Policy(
        policy_id="NO_AFTER_HOURS_WRITE",
        name="No After-Hours Write Operations",
        severity="MEDIUM",
        rationale="Reduces audit and breach risk",
        check=_check_after_hours_write
    ),
    Policy(
        policy_id="NO_UNUSUAL_LOCATION",
        name="No Access from Unusual Locations",
        severity="HIGH",
        rationale="Prevents unauthorized access from untrusted networks",
        check=_check_unusual_location_access
    ),
    Policy(
        policy_id="NO_UNCONTROLLED_SENSITIVE_ACCESS",
        name="Sensitive Resources Require Workflow",
        severity="HIGH",
        rationale="Ensures audit trail for sensitive data access",
        check=_check_sensitive_resource_access
    ),
    Policy(
        policy_id="NO_SVC_ACCOUNT_WRITE",
        name="Service Accounts Cannot Write Directly",
        severity="MEDIUM",
        rationale="Service accounts should use workflows for writes",
        check=_check_service_account_write
    ),
    Policy(
        policy_id="NO_SKIP_APPROVAL",
        name="Approval Steps Cannot Be Skipped",
        severity="CRITICAL",
        rationale="Approvals are mandatory compliance checkpoints",
        check=_check_skipped_approval
    )
]


class ComplianceAgent:
    """
    Compliance Agent
    
    Detects policy violations. Silent violations are detected
    when events violate policy without raising alerts.
    
    Agents do NOT communicate directly.
    All output goes to SharedState.
    """
    
    AGENT_NAME = "ComplianceAgent"
    
    def __init__(self):
        self._policies = {p.policy_id: p for p in POLICIES}
        self._violation_history: List[str] = []  # Track for dedup
        self._use_langgraph = is_langgraph_enabled()
    
    def analyze(
        self,
        events: List[ObservedEvent],
        state: SharedState
    ) -> List[PolicyHit]:
        if self._use_langgraph:
            graph_state = run_linear_graph(
                {"events": events, "state": state, "hits": []},
                [("evaluate_policies", self._graph_evaluate_policies)],
            )
            return graph_state.get("hits", [])
        return self._analyze_core(events, state)

    def _graph_evaluate_policies(self, graph_state: Dict[str, Any]) -> Dict[str, Any]:
        graph_state["hits"] = self._analyze_core(graph_state["events"], graph_state["state"])
        return graph_state

    def _analyze_core(
        self,
        events: List[ObservedEvent],
        state: SharedState
    ) -> List[PolicyHit]:
        """
        Check events against all policies.
        
        Returns policy hits found (also written to state).
        """
        hits = []
        
        for event in events:
            for policy in POLICIES:
                if policy.check(event):
                    # Check for duplicate
                    hit_key = f"{policy.policy_id}:{event.event_id}"
                    if hit_key in self._violation_history:
                        continue
                    
                    self._violation_history.append(hit_key)
                    
                    # Add to state
                    hit = state.add_policy_hit(
                        policy_id=policy.policy_id,
                        event_id=event.event_id,
                        violation_type="SILENT",
                        agent=self.AGENT_NAME,
                        description=f"Event {event.event_id} violated policy '{policy.name}': {policy.rationale}"
                    )
                    hits.append(hit)
        
        return hits
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get policy definition by ID."""
        return self._policies.get(policy_id)
    
    def get_all_policies(self) -> List[Policy]:
        """Get all policy definitions."""
        return list(POLICIES)
    
    def get_violation_count(self) -> int:
        """Get total violations detected."""
        return len(self._violation_history)
