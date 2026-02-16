"""
IICWMS Simulation Engine
========================
SOURCE OF TRUTH - Generates plausible enterprise behavior.

PURPOSE:
- Advance simulated time
- Mutate workflow states
- Mutate resource conditions
- Emit events + metrics

FORBIDDEN:
- No knowledge of policies
- No knowledge of agents
- No scenario scripting (behavior emerges)

This module creates REALITY, not alerts.
"""

from __future__ import annotations

import uuid
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import json


class EventType(Enum):
    """Raw event types - no interpretation, no severity."""
    # Workflow events
    WORKFLOW_START = "WORKFLOW_START"
    WORKFLOW_STEP_START = "WORKFLOW_STEP_START"
    WORKFLOW_STEP_COMPLETE = "WORKFLOW_STEP_COMPLETE"
    WORKFLOW_STEP_SKIP = "WORKFLOW_STEP_SKIP"
    WORKFLOW_COMPLETE = "WORKFLOW_COMPLETE"
    
    # Access events
    ACCESS_READ = "ACCESS_READ"
    ACCESS_WRITE = "ACCESS_WRITE"
    ACCESS_DELETE = "ACCESS_DELETE"
    
    # Resource events
    RESOURCE_ALLOCATE = "RESOURCE_ALLOCATE"
    RESOURCE_RELEASE = "RESOURCE_RELEASE"
    
    # System events
    CONFIG_CHANGE = "CONFIG_CHANGE"
    CREDENTIAL_ACCESS = "CREDENTIAL_ACCESS"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"


@dataclass
class Event:
    """
    Immutable Fact - The canonical event structure.
    
    Rules:
    - No interpretation
    - No severity
    - No intelligence
    """
    event_id: str
    type: str
    workflow_id: Optional[str]
    actor: str
    resource: Optional[str]
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "type": self.type,
            "workflow_id": self.workflow_id,
            "actor": self.actor,
            "resource": self.resource,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ResourceMetric:
    """Resource metric - raw measurement only."""
    resource_id: str
    metric: str
    value: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "metric": self.metric,
            "value": self.value,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class WorkflowState:
    """Internal workflow state - not exposed directly."""
    workflow_id: str
    name: str
    steps: List[str]
    current_step: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    step_durations: Dict[str, int] = field(default_factory=dict)  # Expected durations in seconds


@dataclass
class ResourceState:
    """Internal resource state."""
    resource_id: str
    name: str
    cpu_usage: float = 30.0
    memory_usage: float = 40.0
    network_latency_ms: float = 50.0
    disk_io_percent: float = 20.0


class SimulationEngine:
    """
    The Simulation Engine - Source of Truth.
    
    Generates plausible enterprise behavior, not alerts.
    Reality is generated, not inferred.
    """
    
    def __init__(self):
        # Simulated clock
        self._clock = datetime.utcnow()
        self._tick_interval = timedelta(seconds=5)
        
        # Internal state (not exposed)
        self._workflows: Dict[str, WorkflowState] = {}
        self._resources: Dict[str, ResourceState] = {}
        self._actors = ["user_alice", "user_bob", "user_carol", "svc_account_01", "svc_account_02"]
        
        # Event buffer
        self._pending_events: List[Event] = []
        self._pending_metrics: List[ResourceMetric] = []
        
        # Initialize default state
        self._initialize_state()
    
    def _initialize_state(self):
        """Set up initial simulation state."""
        # Define workflows with expected step durations
        self._workflows["wf_onboarding"] = WorkflowState(
            workflow_id="wf_onboarding",
            name="User Onboarding",
            steps=["init", "validate", "provision", "deploy", "verify", "notify"],
            step_durations={"init": 5, "validate": 15, "provision": 30, "deploy": 120, "verify": 60, "notify": 10}
        )
        self._workflows["wf_deployment"] = WorkflowState(
            workflow_id="wf_deployment",
            name="Service Deployment",
            steps=["build", "test", "staging", "approval", "production", "complete"],
            step_durations={"build": 60, "test": 120, "staging": 30, "approval": 300, "production": 120, "complete": 5}
        )
        self._workflows["wf_expense"] = WorkflowState(
            workflow_id="wf_expense",
            name="Expense Reimbursement",
            steps=["submit", "manager_review", "finance_approval", "payment", "complete"],
            step_durations={"submit": 5, "manager_review": 30, "finance_approval": 60, "payment": 10, "complete": 5}
        )
        self._workflows["wf_access"] = WorkflowState(
            workflow_id="wf_access",
            name="Access Request",
            steps=["request", "security_review", "provisioning", "complete"],
            step_durations={"request": 5, "security_review": 45, "provisioning": 20, "complete": 5}
        )
        
        # Define resources (match frontend resource IDs)
        self._resources["vm_2"] = ResourceState("vm_2", "Deploy Server")
        self._resources["vm_3"] = ResourceState("vm_3", "API Gateway")
        self._resources["vm_8"] = ResourceState("vm_8", "Build Runner")
        self._resources["net_3"] = ResourceState("net_3", "CDN Edge", network_latency_ms=60.0)
        self._resources["storage_7"] = ResourceState("storage_7", "Log Archive", cpu_usage=15.0, memory_usage=20.0)
    
    @property
    def current_time(self) -> datetime:
        return self._clock
    
    def tick(self) -> tuple[List[Event], List[ResourceMetric]]:
        """
        Advance simulation by one tick.
        
        Returns:
            Tuple of (events, metrics) generated this tick
        """
        self._pending_events = []
        self._pending_metrics = []
        
        # Advance clock
        self._clock += self._tick_interval
        
        # Run simulation logic
        self._maybe_start_workflow()
        self._maybe_advance_workflows()
        self._maybe_mutate_resources()
        self._maybe_trigger_access_event()
        
        return self._pending_events, self._pending_metrics
    
    def _maybe_start_workflow(self):
        """Possibly start a new workflow instance."""
        if random.random() < 0.1:  # 10% chance per tick
            workflow_template = random.choice(list(self._workflows.values()))
            
            # Create new instance
            instance_id = f"{workflow_template.workflow_id}_{uuid.uuid4().hex[:8]}"
            actor = random.choice(self._actors)
            
            self._emit_event(
                event_type=EventType.WORKFLOW_START,
                workflow_id=instance_id,
                actor=actor,
                metadata={
                    "workflow_name": workflow_template.name,
                    "steps": workflow_template.steps
                }
            )
            
            # Start first step
            self._emit_event(
                event_type=EventType.WORKFLOW_STEP_START,
                workflow_id=instance_id,
                actor=actor,
                metadata={
                    "step": workflow_template.steps[0],
                    "step_index": 0
                }
            )
    
    def _maybe_advance_workflows(self):
        """Possibly advance active workflows."""
        # Simulate workflow progression with possible anomalies
        if random.random() < 0.3:  # 30% chance
            workflow_template = random.choice(list(self._workflows.values()))
            instance_id = f"{workflow_template.workflow_id}_{uuid.uuid4().hex[:8]}"
            actor = random.choice(self._actors)
            
            # Simulate step completion
            step_index = random.randint(0, len(workflow_template.steps) - 2)
            current_step = workflow_template.steps[step_index]
            next_step = workflow_template.steps[step_index + 1]
            
            # Complete current step
            self._emit_event(
                event_type=EventType.WORKFLOW_STEP_COMPLETE,
                workflow_id=instance_id,
                actor=actor,
                metadata={
                    "step": current_step,
                    "step_index": step_index,
                    "duration_seconds": workflow_template.step_durations.get(current_step, 30) + random.randint(-10, 50)
                }
            )
            
            # ANOMALY: Sometimes skip a step (this creates detectable behavior)
            if random.random() < 0.15:  # 15% chance of skipping
                self._emit_event(
                    event_type=EventType.WORKFLOW_STEP_SKIP,
                    workflow_id=instance_id,
                    actor=actor,
                    metadata={
                        "skipped_step": next_step,
                        "step_index": step_index + 1,
                        "reason": "user_override"  # Raw fact, no judgment
                    }
                )
            else:
                # Normal progression
                self._emit_event(
                    event_type=EventType.WORKFLOW_STEP_START,
                    workflow_id=instance_id,
                    actor=actor,
                    metadata={
                        "step": next_step,
                        "step_index": step_index + 1
                    }
                )
    
    def _maybe_mutate_resources(self):
        """Mutate resource conditions."""
        for resource in self._resources.values():
            # CPU - random walk with drift
            resource.cpu_usage += random.gauss(0.5, 3)  # Slight upward drift
            resource.cpu_usage = max(5, min(99, resource.cpu_usage))
            
            # Memory - tends to grow (simulating leak)
            resource.memory_usage += random.gauss(0.3, 2)
            resource.memory_usage = max(10, min(99, resource.memory_usage))
            
            # Network latency - occasional spikes
            if random.random() < 0.1:
                resource.network_latency_ms += random.uniform(50, 200)
            else:
                resource.network_latency_ms = max(10, resource.network_latency_ms - random.uniform(0, 20))
            
            # Emit metrics
            self._emit_metric(resource.resource_id, "cpu_percent", resource.cpu_usage)
            self._emit_metric(resource.resource_id, "memory_percent", resource.memory_usage)
            self._emit_metric(resource.resource_id, "network_latency_ms", resource.network_latency_ms)
    
    def _maybe_trigger_access_event(self):
        """Generate access events."""
        if random.random() < 0.4:  # 40% chance
            actor = random.choice(self._actors)
            resource = random.choice(["repo_main", "db_production", "config_secrets", "storage_backup"])
            event_type = random.choice([EventType.ACCESS_READ, EventType.ACCESS_WRITE])
            
            # Sometimes access from unusual location (creates detectable pattern)
            location = "datacenter_us_east"
            if random.random() < 0.1:  # 10% unusual access
                location = random.choice(["external_unknown", "vpn_foreign", "tor_exit_node"])
            
            self._emit_event(
                event_type=event_type,
                workflow_id=None,
                actor=actor,
                resource=resource,
                metadata={
                    "location": location,
                    "hour": self._clock.hour
                }
            )
    
    def _emit_event(
        self,
        event_type: EventType,
        workflow_id: Optional[str],
        actor: str,
        resource: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Create and buffer an event."""
        event = Event(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            type=event_type.value,
            workflow_id=workflow_id,
            actor=actor,
            resource=resource,
            timestamp=self._clock,
            metadata=metadata or {}
        )
        self._pending_events.append(event)
    
    def _emit_metric(self, resource_id: str, metric: str, value: float):
        """Create and buffer a metric."""
        metric_obj = ResourceMetric(
            resource_id=resource_id,
            metric=metric,
            value=round(value, 2),
            timestamp=self._clock
        )
        self._pending_metrics.append(metric_obj)
    
    def run_scenario(self, ticks: int = 20) -> tuple[List[Event], List[ResourceMetric]]:
        """
        Run simulation for N ticks.
        
        Returns:
            All events and metrics generated
        """
        all_events = []
        all_metrics = []
        
        for _ in range(ticks):
            events, metrics = self.tick()
            all_events.extend(events)
            all_metrics.extend(metrics)
        
        return all_events, all_metrics


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Interface
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Run simulation and output events."""
    import argparse
    
    parser = argparse.ArgumentParser(description="IICWMS Simulation Engine")
    parser.add_argument("--ticks", type=int, default=20, help="Number of simulation ticks")
    parser.add_argument("--output", type=str, default="simulation_output.jsonl", help="Output file")
    
    args = parser.parse_args()
    
    engine = SimulationEngine()
    events, metrics = engine.run_scenario(args.ticks)
    
    # Write to file
    with open(args.output, 'w') as f:
        for event in events:
            f.write(json.dumps({"type": "event", "data": event.to_dict()}) + '\n')
        for metric in metrics:
            f.write(json.dumps({"type": "metric", "data": metric.to_dict()}) + '\n')
    
    print(f"Generated {len(events)} events and {len(metrics)} metrics")
    print(f"Output written to: {args.output}")


if __name__ == "__main__":
    main()
