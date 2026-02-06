"""
IICWMS Workflow Agent
Detects workflow anomalies: skipped steps, out-of-order execution, incomplete workflows.

This agent is stateless - receives events and graph snapshots, returns structured opinions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid


class OpinionType(Enum):
    WORKFLOW_DEVIATION = "WORKFLOW_DEVIATION"
    STEP_SKIPPED = "STEP_SKIPPED"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    INCOMPLETE_WORKFLOW = "INCOMPLETE_WORKFLOW"


@dataclass
class Opinion:
    """Structured opinion from an agent - the unit of evidence."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent: str = "workflow_agent"
    opinion_type: OpinionType = OpinionType.WORKFLOW_DEVIATION
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    evidence: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent": self.agent,
            "opinion_type": self.opinion_type.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "evidence": self.evidence,
            "explanation": self.explanation
        }


class WorkflowAgent:
    """
    Agent responsible for workflow integrity monitoring.
    
    Detects:
    - Skipped mandatory steps
    - Out-of-order step execution
    - Incomplete or abandoned workflows
    
    Note: This agent uses graph queries for detection, not LLM inference.
    LLMs are used for explanation, not detection.
    """

    def __init__(self, neo4j_client):
        self.neo4j_client = neo4j_client
        self.agent_name = "workflow_agent"

    def analyze(
        self,
        workflow_id: str,
        events: List[Dict[str, Any]]
    ) -> List[Opinion]:
        """
        Analyze a workflow for anomalies.
        
        Args:
            workflow_id: ID of the workflow to analyze
            events: List of events that occurred in this workflow
            
        Returns:
            List of Opinion objects representing detected anomalies
        """
        opinions = []
        
        # Check for skipped steps
        skipped_opinions = self._detect_skipped_steps(workflow_id, events)
        opinions.extend(skipped_opinions)
        
        # Check for out-of-order execution
        order_opinions = self._detect_out_of_order(workflow_id, events)
        opinions.extend(order_opinions)
        
        # Check for incomplete workflows
        incomplete_opinions = self._detect_incomplete_workflow(workflow_id, events)
        opinions.extend(incomplete_opinions)
        
        return opinions

    def _detect_skipped_steps(
        self,
        workflow_id: str,
        events: List[Dict[str, Any]]
    ) -> List[Opinion]:
        """Detect mandatory steps that were skipped."""
        opinions = []
        
        # Query graph for workflow structure
        workflow_state = self.neo4j_client.get_workflow_state(workflow_id)
        if not workflow_state:
            return opinions
        
        steps = workflow_state.get("steps", [])
        mandatory_steps = [s for s in steps if s.get("mandatory", False)]
        
        # Find which steps have completion events
        completed_step_ids = set()
        for event in events:
            if event.get("event_type") == "WORKFLOW_STEP_COMPLETE":
                completed_step_ids.add(event.get("step_id"))
        
        # Check for skipped mandatory steps
        for step in mandatory_steps:
            if step["id"] not in completed_step_ids:
                # Check if workflow progressed past this step
                step_sequence = step.get("sequence", 0)
                later_completed = any(
                    s.get("sequence", 0) > step_sequence 
                    for s in steps 
                    if s["id"] in completed_step_ids
                )
                
                if later_completed:
                    opinion = Opinion(
                        opinion_type=OpinionType.STEP_SKIPPED,
                        confidence=0.95,
                        evidence={
                            "workflow_id": workflow_id,
                            "skipped_step_id": step["id"],
                            "skipped_step_name": step.get("name", "Unknown"),
                            "expected_sequence": step_sequence,
                            "completed_steps": list(completed_step_ids),
                            "detection_method": "graph_query"
                        },
                        explanation=f"Mandatory step '{step.get('name', step['id'])}' was skipped. "
                                   f"Later steps in the workflow were completed, indicating this step "
                                   f"was bypassed rather than pending."
                    )
                    opinions.append(opinion)
        
        return opinions

    def _detect_out_of_order(
        self,
        workflow_id: str,
        events: List[Dict[str, Any]]
    ) -> List[Opinion]:
        """Detect steps executed out of their defined order."""
        opinions = []
        
        # Get workflow structure from graph
        workflow_state = self.neo4j_client.get_workflow_state(workflow_id)
        if not workflow_state:
            return opinions
        
        steps = {s["id"]: s for s in workflow_state.get("steps", [])}
        
        # Build completion timeline
        completions = []
        for event in events:
            if event.get("event_type") == "WORKFLOW_STEP_COMPLETE":
                step_id = event.get("step_id")
                if step_id in steps:
                    completions.append({
                        "step_id": step_id,
                        "sequence": steps[step_id].get("sequence", 0),
                        "timestamp": event.get("timestamp")
                    })
        
        # Sort by timestamp and check sequence
        completions.sort(key=lambda x: x["timestamp"])
        
        for i in range(len(completions) - 1):
            current = completions[i]
            next_step = completions[i + 1]
            
            if current["sequence"] > next_step["sequence"]:
                opinion = Opinion(
                    opinion_type=OpinionType.OUT_OF_ORDER,
                    confidence=0.90,
                    evidence={
                        "workflow_id": workflow_id,
                        "expected_order": [current["step_id"], next_step["step_id"]],
                        "actual_order": [next_step["step_id"], current["step_id"]],
                        "timestamps": {
                            current["step_id"]: current["timestamp"],
                            next_step["step_id"]: next_step["timestamp"]
                        }
                    },
                    explanation=f"Steps were executed out of order. Step with sequence "
                               f"{next_step['sequence']} completed before step with sequence "
                               f"{current['sequence']}."
                )
                opinions.append(opinion)
        
        return opinions

    def _detect_incomplete_workflow(
        self,
        workflow_id: str,
        events: List[Dict[str, Any]]
    ) -> List[Opinion]:
        """Detect workflows that appear to be abandoned or incomplete."""
        opinions = []
        
        workflow_state = self.neo4j_client.get_workflow_state(workflow_id)
        if not workflow_state:
            return opinions
        
        steps = workflow_state.get("steps", [])
        total_steps = len(steps)
        
        # Count completed steps
        completed_step_ids = set()
        for event in events:
            if event.get("event_type") == "WORKFLOW_STEP_COMPLETE":
                completed_step_ids.add(event.get("step_id"))
        
        completed_count = len(completed_step_ids)
        
        # Check if workflow started but didn't finish
        if 0 < completed_count < total_steps:
            # Check for workflow completion event
            has_completion = any(
                e.get("event_type") == "WORKFLOW_COMPLETE" 
                for e in events
            )
            
            if not has_completion:
                completion_ratio = completed_count / total_steps
                opinion = Opinion(
                    opinion_type=OpinionType.INCOMPLETE_WORKFLOW,
                    confidence=0.75 if completion_ratio < 0.5 else 0.60,
                    evidence={
                        "workflow_id": workflow_id,
                        "total_steps": total_steps,
                        "completed_steps": completed_count,
                        "completion_ratio": completion_ratio,
                        "missing_steps": [
                            s["id"] for s in steps 
                            if s["id"] not in completed_step_ids
                        ]
                    },
                    explanation=f"Workflow appears incomplete. Only {completed_count} of "
                               f"{total_steps} steps were completed ({completion_ratio:.0%}), "
                               f"and no workflow completion event was recorded."
                )
                opinions.append(opinion)
        
        return opinions
