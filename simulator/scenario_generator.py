"""
IICWMS Scenario Generator
Generates realistic IT workflow scenarios for demonstration and testing.

Scenarios:
1. Silent Step-Skipper - Workflow steps are bypassed without authorization
2. Resource Vampire - Gradual resource overconsumption
3. Credential Leaker - Abnormal credential access patterns
"""

import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import json


class ScenarioType(Enum):
    SILENT_STEP_SKIPPER = "silent-step-skipper"
    RESOURCE_VAMPIRE = "resource-vampire"
    CREDENTIAL_LEAKER = "credential-leaker"


@dataclass
class Event:
    """Represents a system event with full traceability."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_type: str = ""
    source: str = ""
    workflow_id: Optional[str] = None
    step_id: Optional[str] = None
    resource_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "source": self.source,
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "resource_id": self.resource_id,
            "metadata": self.metadata
        }


class ScenarioGenerator:
    """Generates structured events for demonstration scenarios."""

    def __init__(self):
        self.events: List[Event] = []
        self.workflow_id = str(uuid.uuid4())

    def generate(self, scenario: ScenarioType) -> List[Event]:
        """Generate events for the specified scenario."""
        self.events = []
        self.workflow_id = str(uuid.uuid4())

        if scenario == ScenarioType.SILENT_STEP_SKIPPER:
            return self._generate_silent_step_skipper()
        elif scenario == ScenarioType.RESOURCE_VAMPIRE:
            return self._generate_resource_vampire()
        elif scenario == ScenarioType.CREDENTIAL_LEAKER:
            return self._generate_credential_leaker()
        else:
            raise ValueError(f"Unknown scenario: {scenario}")

    def _generate_silent_step_skipper(self) -> List[Event]:
        """
        Scenario: A workflow where mandatory approval steps are silently bypassed.
        
        Expected flow: Request -> Validation -> Approval -> Execution -> Completion
        Actual flow:   Request -> Validation -> Execution -> Completion (Approval skipped!)
        """
        base_time = datetime.utcnow()
        steps = [
            ("step-request", "WORKFLOW_STEP_START", "Request submitted"),
            ("step-request", "WORKFLOW_STEP_COMPLETE", "Request validated"),
            ("step-validation", "WORKFLOW_STEP_START", "Validation initiated"),
            ("step-validation", "WORKFLOW_STEP_COMPLETE", "Validation passed"),
            # NOTE: Approval step is SKIPPED here - this is the anomaly
            ("step-execution", "WORKFLOW_STEP_START", "Execution started"),
            ("step-execution", "WORKFLOW_STEP_COMPLETE", "Execution completed"),
            ("step-completion", "WORKFLOW_STEP_START", "Finalization started"),
            ("step-completion", "WORKFLOW_STEP_COMPLETE", "Workflow completed"),
        ]

        for i, (step_id, event_type, description) in enumerate(steps):
            event = Event(
                timestamp=base_time + timedelta(seconds=i * 30),
                event_type=event_type,
                source="workflow-engine",
                workflow_id=self.workflow_id,
                step_id=step_id,
                metadata={
                    "description": description,
                    "sequence_number": i + 1,
                    "expected_sequence": ["request", "validation", "approval", "execution", "completion"]
                }
            )
            self.events.append(event)

        return self.events

    def _generate_resource_vampire(self) -> List[Event]:
        """
        Scenario: A process that gradually consumes excessive resources.
        
        Pattern: Memory and CPU usage increase over time until threshold breach.
        """
        base_time = datetime.utcnow()
        resource_id = str(uuid.uuid4())
        
        # Simulate gradual resource increase
        memory_values = [40, 45, 52, 61, 73, 85, 92, 98]  # Percentage
        cpu_values = [20, 25, 35, 48, 62, 78, 88, 95]      # Percentage

        for i, (mem, cpu) in enumerate(zip(memory_values, cpu_values)):
            # Memory event
            self.events.append(Event(
                timestamp=base_time + timedelta(minutes=i * 5),
                event_type="RESOURCE_METRIC",
                source="monitoring-agent",
                resource_id=resource_id,
                metadata={
                    "metric_type": "memory_usage",
                    "value": mem,
                    "unit": "percent",
                    "threshold": 80,
                    "threshold_breached": mem > 80
                }
            ))
            
            # CPU event
            self.events.append(Event(
                timestamp=base_time + timedelta(minutes=i * 5, seconds=1),
                event_type="RESOURCE_METRIC",
                source="monitoring-agent",
                resource_id=resource_id,
                metadata={
                    "metric_type": "cpu_usage",
                    "value": cpu,
                    "unit": "percent",
                    "threshold": 75,
                    "threshold_breached": cpu > 75
                }
            ))

        return self.events

    def _generate_credential_leaker(self) -> List[Event]:
        """
        Scenario: Credentials accessed outside normal patterns.
        
        Pattern: Service account accesses credentials at unusual times and locations.
        """
        base_time = datetime.utcnow()
        credential_id = str(uuid.uuid4())
        
        access_patterns = [
            # Normal access patterns
            {"time_offset": 0, "location": "datacenter-us-east", "service": "app-server-01", "normal": True},
            {"time_offset": 60, "location": "datacenter-us-east", "service": "app-server-02", "normal": True},
            # Anomalous access patterns
            {"time_offset": 120, "location": "unknown-external", "service": "unknown-client", "normal": False},
            {"time_offset": 125, "location": "datacenter-eu-west", "service": "app-server-01", "normal": False},
            {"time_offset": 130, "location": "unknown-external", "service": "script-automated", "normal": False},
        ]

        for pattern in access_patterns:
            event = Event(
                timestamp=base_time + timedelta(seconds=pattern["time_offset"]),
                event_type="CREDENTIAL_ACCESS",
                source="identity-manager",
                metadata={
                    "credential_id": credential_id,
                    "access_location": pattern["location"],
                    "requesting_service": pattern["service"],
                    "access_type": "read",
                    "matches_normal_pattern": pattern["normal"],
                    "risk_score": 0.2 if pattern["normal"] else 0.85
                }
            )
            self.events.append(event)

        return self.events

    def export_to_jsonl(self, filepath: str):
        """Export generated events to JSONL format."""
        with open(filepath, 'w') as f:
            for event in self.events:
                f.write(json.dumps(event.to_dict()) + '\n')


def main():
    """CLI entry point for scenario generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate IICWMS test scenarios")
    parser.add_argument(
        "--scenario",
        type=str,
        choices=[s.value for s in ScenarioType],
        required=True,
        help="Scenario to generate"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="events.jsonl",
        help="Output file path"
    )
    
    args = parser.parse_args()
    
    generator = ScenarioGenerator()
    scenario = ScenarioType(args.scenario)
    events = generator.generate(scenario)
    
    generator.export_to_jsonl(args.output)
    print(f"Generated {len(events)} events for scenario '{args.scenario}'")
    print(f"Output written to: {args.output}")


if __name__ == "__main__":
    main()
