"""
IICWMS Workflow Agent
=====================
Detects workflow anomalies.

INPUT:
- Workflow events
- Expected step durations

DETECTS:
- Delays
- Missing steps
- Sequence violations

OUTPUT:
{
  "type": "WORKFLOW_DELAY",
  "workflow_id": "wf_12",
  "evidence": ["step_DEPLOY exceeded SLA"]
}
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from observation import ObservedEvent
from blackboard import SharedState, Anomaly
from .langgraph_runtime import run_linear_graph, is_langgraph_enabled


# Expected workflow definitions (should match simulator)
WORKFLOW_DEFINITIONS = {
    "wf_onboarding": {
        "name": "User Onboarding",
        "steps": ["init", "validate", "provision", "deploy", "verify", "notify"],
        "step_sla_seconds": {"init": 10, "validate": 30, "provision": 60, "deploy": 240, "verify": 120, "notify": 20}
    },
    "wf_deployment": {
        "name": "Service Deployment",
        "steps": ["build", "test", "staging", "approval", "production", "complete"],
        "step_sla_seconds": {"build": 120, "test": 240, "staging": 60, "approval": 600, "production": 120, "complete": 10}
    },
    "wf_expense": {
        "name": "Expense Reimbursement",
        "steps": ["submit", "manager_review", "finance_approval", "payment", "complete"],
        "step_sla_seconds": {"submit": 10, "manager_review": 60, "finance_approval": 120, "payment": 30, "complete": 10}
    },
    "wf_access": {
        "name": "Access Request",
        "steps": ["request", "security_review", "provisioning", "complete"],
        "step_sla_seconds": {"request": 10, "security_review": 90, "provisioning": 60, "complete": 10}
    },
}


@dataclass
class WorkflowState:
    """Tracks workflow execution state."""
    workflow_id: str
    workflow_type: str
    current_step_index: int = 0
    started_at: Optional[datetime] = None
    step_started_at: Optional[datetime] = None
    completed_steps: List[str] = None
    skipped_steps: List[str] = None
    
    def __post_init__(self):
        if self.completed_steps is None:
            self.completed_steps = []
        if self.skipped_steps is None:
            self.skipped_steps = []


class WorkflowAgent:
    """
    Workflow Agent
    
    Detects:
    - Delays (step exceeds SLA)
    - Missing steps (steps skipped)
    - Sequence violations (out-of-order execution)
    
    Agents do NOT communicate directly.
    All output goes to SharedState.
    """
    
    AGENT_NAME = "WorkflowAgent"
    
    def __init__(self):
        # Track active workflows
        self._workflows: Dict[str, WorkflowState] = {}
        self._use_langgraph = is_langgraph_enabled()
    
    def analyze(
        self,
        events: List[ObservedEvent],
        state: SharedState
    ) -> List[Anomaly]:
        if self._use_langgraph:
            graph_state = run_linear_graph(
                {"events": events, "state": state, "anomalies": []},
                [("detect_workflow_anomalies", self._graph_detect_workflow_anomalies)],
            )
            return graph_state.get("anomalies", [])
        return self._analyze_core(events, state)

    def _graph_detect_workflow_anomalies(self, graph_state: Dict[str, Any]) -> Dict[str, Any]:
        graph_state["anomalies"] = self._analyze_core(graph_state["events"], graph_state["state"])
        return graph_state

    def _analyze_core(
        self,
        events: List[ObservedEvent],
        state: SharedState
    ) -> List[Anomaly]:
        """
        Analyze workflow events and detect anomalies.
        
        Returns anomalies found (also written to state).
        """
        anomalies = []
        
        # Process events in chronological order
        # Normalize to naive UTC to avoid offset-aware vs naive comparison errors
        def _safe_ts(e):
            ts = e.timestamp
            if ts.tzinfo is not None:
                return ts.replace(tzinfo=None)
            return ts
        sorted_events = sorted(events, key=_safe_ts)
        
        for event in sorted_events:
            if not event.workflow_id:
                continue
            
            # Extract workflow type from ID (e.g., "wf_deploy_abc123" -> "wf_deploy")
            workflow_type = self._extract_workflow_type(event.workflow_id)
            if not workflow_type or workflow_type not in WORKFLOW_DEFINITIONS:
                continue
            
            # Get or create workflow state
            if event.workflow_id not in self._workflows:
                self._workflows[event.workflow_id] = WorkflowState(
                    workflow_id=event.workflow_id,
                    workflow_type=workflow_type
                )
            
            wf = self._workflows[event.workflow_id]
            definition = WORKFLOW_DEFINITIONS[workflow_type]
            
            # Handle different event types
            if event.type == "WORKFLOW_START":
                wf.started_at = event.timestamp
            
            elif event.type == "WORKFLOW_STEP_START":
                step = event.metadata.get("step")
                if step:
                    wf.step_started_at = event.timestamp
                    # Check for sequence violation
                    expected_index = event.metadata.get("step_index", 0)
                    if expected_index != wf.current_step_index:
                        anomaly = state.add_anomaly(
                            type="SEQUENCE_VIOLATION",
                            agent=self.AGENT_NAME,
                            evidence=[event.event_id],
                            description=f"Step '{step}' started at index {expected_index}, expected {wf.current_step_index}",
                            confidence=0.9
                        )
                        anomalies.append(anomaly)
            
            elif event.type == "WORKFLOW_STEP_COMPLETE":
                step = event.metadata.get("step")
                duration = event.metadata.get("duration_seconds", 0)
                
                if step:
                    wf.completed_steps.append(step)
                    wf.current_step_index += 1
                    
                    # Check for SLA violation (delay)
                    sla = definition["step_sla_seconds"].get(step, 60)
                    if duration > sla:
                        anomaly = state.add_anomaly(
                            type="WORKFLOW_DELAY",
                            agent=self.AGENT_NAME,
                            evidence=[event.event_id],
                            description=f"Step '{step}' took {duration}s, exceeded SLA of {sla}s",
                            confidence=0.85
                        )
                        anomalies.append(anomaly)
            
            elif event.type == "WORKFLOW_STEP_SKIP":
                skipped_step = event.metadata.get("skipped_step")
                if skipped_step:
                    wf.skipped_steps.append(skipped_step)
                    wf.current_step_index += 1  # Move past skipped step
                    
                    # MISSING STEP detected
                    anomaly = state.add_anomaly(
                        type="MISSING_STEP",
                        agent=self.AGENT_NAME,
                        evidence=[event.event_id],
                        description=f"Step '{skipped_step}' was skipped in workflow {event.workflow_id}",
                        confidence=0.95
                    )
                    anomalies.append(anomaly)
        
        return anomalies
    
    def _extract_workflow_type(self, workflow_id: str) -> Optional[str]:
        """Extract workflow type from instance ID."""
        # Pattern: wf_type_instanceid
        for wf_type in WORKFLOW_DEFINITIONS.keys():
            if workflow_id.startswith(wf_type):
                return wf_type
        return None
    
    def get_tracked_workflows(self) -> Dict[str, WorkflowState]:
        """Get currently tracked workflows."""
        return self._workflows.copy()
