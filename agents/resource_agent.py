"""
IICWMS Resource Agent
Monitors resource consumption patterns and detects anomalies.

This agent is stateless - receives events and graph snapshots, returns structured opinions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid


class ResourceOpinionType(Enum):
    THRESHOLD_BREACH = "THRESHOLD_BREACH"
    TREND_ANOMALY = "TREND_ANOMALY"
    CORRELATION_ALERT = "CORRELATION_ALERT"
    CAPACITY_WARNING = "CAPACITY_WARNING"


@dataclass
class ResourceOpinion:
    """Structured opinion from resource agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent: str = "resource_agent"
    opinion_type: ResourceOpinionType = ResourceOpinionType.THRESHOLD_BREACH
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resource_id: str = ""
    resource_name: str = ""
    metric_type: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent": self.agent,
            "opinion_type": self.opinion_type.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "metric_type": self.metric_type,
            "evidence": self.evidence,
            "explanation": self.explanation
        }


class ResourceAgent:
    """
    Agent responsible for resource monitoring and anomaly detection.
    
    Detects:
    - Threshold breaches (immediate alerts)
    - Trend anomalies (gradual degradation)
    - Resource correlation (multiple resources affected together)
    - Capacity warnings (approaching limits)
    
    Note: Detection is rule-based using thresholds.
    LLMs are used for explanation, not detection.
    """

    def __init__(self, neo4j_client):
        self.neo4j_client = neo4j_client
        self.agent_name = "resource_agent"
        
        # Configurable thresholds
        self.thresholds = {
            "memory_usage": {"warning": 75, "critical": 90},
            "cpu_usage": {"warning": 70, "critical": 85},
            "disk_usage": {"warning": 80, "critical": 95},
            "network_latency": {"warning": 100, "critical": 500}  # ms
        }

    def analyze(
        self,
        events: List[Dict[str, Any]],
        resource_id: Optional[str] = None
    ) -> List[ResourceOpinion]:
        """
        Analyze resource metrics for anomalies.
        
        Args:
            events: List of resource metric events
            resource_id: Optional filter for specific resource
            
        Returns:
            List of ResourceOpinion objects
        """
        opinions = []
        
        # Filter to resource events
        resource_events = [
            e for e in events 
            if e.get("event_type") == "RESOURCE_METRIC"
            and (resource_id is None or e.get("resource_id") == resource_id)
        ]
        
        if not resource_events:
            return opinions
        
        # Group events by resource
        by_resource = {}
        for event in resource_events:
            rid = event.get("resource_id", "unknown")
            if rid not in by_resource:
                by_resource[rid] = []
            by_resource[rid].append(event)
        
        # Analyze each resource
        for rid, events_list in by_resource.items():
            # Check for threshold breaches
            breach_opinions = self._detect_threshold_breaches(rid, events_list)
            opinions.extend(breach_opinions)
            
            # Check for trend anomalies
            trend_opinions = self._detect_trend_anomalies(rid, events_list)
            opinions.extend(trend_opinions)
        
        # Check for correlated resource issues
        correlation_opinions = self._detect_correlations(by_resource)
        opinions.extend(correlation_opinions)
        
        return opinions

    def _detect_threshold_breaches(
        self,
        resource_id: str,
        events: List[Dict[str, Any]]
    ) -> List[ResourceOpinion]:
        """Detect immediate threshold breaches."""
        opinions = []
        
        for event in events:
            metadata = event.get("metadata", {})
            metric_type = metadata.get("metric_type", "unknown")
            value = metadata.get("value", 0)
            threshold = metadata.get("threshold")
            
            # Use event's threshold or fall back to our defaults
            if threshold is None and metric_type in self.thresholds:
                threshold = self.thresholds[metric_type]["critical"]
            
            if threshold and value > threshold:
                # Determine severity based on how much over threshold
                overage = (value - threshold) / threshold
                confidence = min(0.95, 0.7 + overage * 0.25)
                
                opinion = ResourceOpinion(
                    opinion_type=ResourceOpinionType.THRESHOLD_BREACH,
                    confidence=confidence,
                    resource_id=resource_id,
                    metric_type=metric_type,
                    evidence={
                        "event_id": event.get("id"),
                        "timestamp": event.get("timestamp"),
                        "metric_value": value,
                        "threshold": threshold,
                        "overage_percent": round(overage * 100, 2),
                        "unit": metadata.get("unit", "unknown")
                    },
                    explanation=f"Resource {metric_type} at {value}% exceeds threshold of "
                               f"{threshold}% by {overage*100:.1f}%. Immediate attention may be required."
                )
                opinions.append(opinion)
        
        return opinions

    def _detect_trend_anomalies(
        self,
        resource_id: str,
        events: List[Dict[str, Any]]
    ) -> List[ResourceOpinion]:
        """Detect gradual degradation trends (Resource Vampire pattern)."""
        opinions = []
        
        # Group by metric type
        by_metric = {}
        for event in events:
            metadata = event.get("metadata", {})
            metric_type = metadata.get("metric_type", "unknown")
            if metric_type not in by_metric:
                by_metric[metric_type] = []
            by_metric[metric_type].append({
                "timestamp": event.get("timestamp"),
                "value": metadata.get("value", 0)
            })
        
        for metric_type, data_points in by_metric.items():
            if len(data_points) < 3:
                continue
            
            # Sort by timestamp
            data_points.sort(key=lambda x: x["timestamp"])
            
            # Calculate trend
            values = [d["value"] for d in data_points]
            first_third = sum(values[:len(values)//3]) / (len(values)//3 or 1)
            last_third = sum(values[-len(values)//3:]) / (len(values)//3 or 1)
            
            # Detect increasing trend
            if last_third > first_third * 1.3:  # 30% increase
                trend_increase = (last_third - first_third) / first_third * 100
                
                opinion = ResourceOpinion(
                    opinion_type=ResourceOpinionType.TREND_ANOMALY,
                    confidence=min(0.90, 0.6 + trend_increase / 200),
                    resource_id=resource_id,
                    metric_type=metric_type,
                    evidence={
                        "metric_type": metric_type,
                        "initial_average": round(first_third, 2),
                        "current_average": round(last_third, 2),
                        "trend_increase_percent": round(trend_increase, 2),
                        "data_points": len(data_points),
                        "time_range": {
                            "start": data_points[0]["timestamp"],
                            "end": data_points[-1]["timestamp"]
                        }
                    },
                    explanation=f"Gradual increase detected in {metric_type}. "
                               f"Average increased from {first_third:.1f}% to {last_third:.1f}% "
                               f"({trend_increase:.1f}% increase). This pattern may indicate "
                               f"a 'Resource Vampire' condition."
                )
                opinions.append(opinion)
        
        return opinions

    def _detect_correlations(
        self,
        events_by_resource: Dict[str, List[Dict[str, Any]]]
    ) -> List[ResourceOpinion]:
        """Detect correlated issues across multiple resources."""
        opinions = []
        
        # Find resources with threshold breaches
        breaching_resources = []
        for resource_id, events in events_by_resource.items():
            for event in events:
                metadata = event.get("metadata", {})
                if metadata.get("threshold_breached", False):
                    breaching_resources.append({
                        "resource_id": resource_id,
                        "metric_type": metadata.get("metric_type"),
                        "timestamp": event.get("timestamp"),
                        "value": metadata.get("value")
                    })
                    break  # One breach per resource is enough
        
        # If multiple resources are breaching, it might be correlated
        if len(breaching_resources) >= 2:
            opinion = ResourceOpinion(
                opinion_type=ResourceOpinionType.CORRELATION_ALERT,
                confidence=0.85,
                resource_id="multiple",
                metric_type="multiple",
                evidence={
                    "affected_resources": breaching_resources,
                    "resource_count": len(breaching_resources),
                    "pattern": "simultaneous_breach"
                },
                explanation=f"Multiple resources ({len(breaching_resources)}) are experiencing "
                           f"threshold breaches simultaneously. This correlation suggests a "
                           f"common cause or cascading failure. Probable causal relationships, "
                           f"not formal proof."
            )
            opinions.append(opinion)
        
        return opinions

    def get_ripple_effect(self, resource_id: str) -> List[Dict]:
        """Query graph for downstream impact of resource issues."""
        return self.neo4j_client.get_ripple_effect(resource_id)
