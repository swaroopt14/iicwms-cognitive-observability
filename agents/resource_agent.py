"""
IICWMS Resource Agent
=====================
Monitors resource conditions.

INPUT:
- Resource metrics (time-windowed)

DETECTS:
- Sustained spikes (NOT single spikes)
- Drift trends

IMPORTANT:
- Single spikes ≠ anomaly
- Trend slope matters
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

from observation import ObservedMetric
from blackboard import SharedState, Anomaly


# Thresholds
THRESHOLDS = {
    "cpu_percent": {"warning": 70, "critical": 90, "sustained_window": 3},
    "memory_percent": {"warning": 75, "critical": 95, "sustained_window": 3},
    "network_latency_ms": {"warning": 200, "critical": 500, "sustained_window": 3}
}


@dataclass
class ResourceHistory:
    """Tracks resource metric history."""
    resource_id: str
    metric: str
    values: List[Tuple[datetime, float]] = field(default_factory=list)
    
    def add(self, timestamp: datetime, value: float):
        self.values.append((timestamp, value))
        # Keep only recent history
        if len(self.values) > 100:
            self.values = self.values[-100:]
    
    def get_recent(self, count: int = 10) -> List[float]:
        return [v for _, v in self.values[-count:]]
    
    def compute_trend_slope(self, window: int = 5) -> float:
        """Compute trend slope (positive = increasing)."""
        recent = self.get_recent(window)
        if len(recent) < 2:
            return 0.0
        
        # Simple linear regression slope
        n = len(recent)
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(recent)
        
        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(recent))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        return numerator / denominator


class ResourceAgent:
    """
    Resource Agent
    
    Detects:
    - Sustained spikes (multiple readings above threshold)
    - Drift trends (consistent upward movement)
    
    IMPORTANT: Single spikes ≠ anomaly. Trend slope matters.
    
    Agents do NOT communicate directly.
    All output goes to SharedState.
    """
    
    AGENT_NAME = "ResourceAgent"
    
    def __init__(self):
        # Track resource history: resource_id -> metric -> history
        self._history: Dict[str, Dict[str, ResourceHistory]] = defaultdict(dict)
    
    def analyze(
        self,
        metrics: List[ObservedMetric],
        state: SharedState
    ) -> List[Anomaly]:
        """
        Analyze resource metrics and detect anomalies.
        
        Returns anomalies found (also written to state).
        """
        anomalies = []
        
        # Group metrics by resource
        for metric in metrics:
            if metric.metric not in THRESHOLDS:
                continue
            
            # Get or create history
            if metric.metric not in self._history[metric.resource_id]:
                self._history[metric.resource_id][metric.metric] = ResourceHistory(
                    resource_id=metric.resource_id,
                    metric=metric.metric
                )
            
            history = self._history[metric.resource_id][metric.metric]
            history.add(metric.timestamp, metric.value)
        
        # Analyze each resource's metrics
        for resource_id, metrics_dict in self._history.items():
            for metric_name, history in metrics_dict.items():
                threshold_config = THRESHOLDS[metric_name]
                
                # Check for SUSTAINED spike
                anomaly = self._check_sustained_spike(
                    resource_id, metric_name, history, threshold_config, state
                )
                if anomaly:
                    anomalies.append(anomaly)
                
                # Check for DRIFT trend
                anomaly = self._check_drift_trend(
                    resource_id, metric_name, history, threshold_config, state
                )
                if anomaly:
                    anomalies.append(anomaly)
        
        return anomalies
    
    def _check_sustained_spike(
        self,
        resource_id: str,
        metric_name: str,
        history: ResourceHistory,
        config: Dict,
        state: SharedState
    ) -> Anomaly | None:
        """
        Check for sustained spike (NOT single spike).
        
        Requires multiple consecutive readings above threshold.
        """
        sustained_window = config["sustained_window"]
        warning_threshold = config["warning"]
        critical_threshold = config["critical"]
        
        recent = history.get_recent(sustained_window)
        if len(recent) < sustained_window:
            return None
        
        # Check if ALL readings in window exceed critical
        if all(v >= critical_threshold for v in recent):
            return state.add_anomaly(
                type="SUSTAINED_RESOURCE_CRITICAL",
                agent=self.AGENT_NAME,
                evidence=[f"{resource_id}/{metric_name}/last_{sustained_window}"],
                description=f"Resource {resource_id} has {metric_name} at critical level ({statistics.mean(recent):.1f}) for {sustained_window} consecutive readings",
                confidence=0.9
            )
        
        # Check if ALL readings in window exceed warning
        if all(v >= warning_threshold for v in recent):
            return state.add_anomaly(
                type="SUSTAINED_RESOURCE_WARNING",
                agent=self.AGENT_NAME,
                evidence=[f"{resource_id}/{metric_name}/last_{sustained_window}"],
                description=f"Resource {resource_id} has {metric_name} at elevated level ({statistics.mean(recent):.1f}) for {sustained_window} consecutive readings",
                confidence=0.75
            )
        
        return None
    
    def _check_drift_trend(
        self,
        resource_id: str,
        metric_name: str,
        history: ResourceHistory,
        config: Dict,
        state: SharedState
    ) -> Anomaly | None:
        """
        Check for drift trend (consistent upward movement).
        
        Detects slow but steady resource degradation.
        """
        slope = history.compute_trend_slope(window=5)
        
        # Significant upward drift (slope > 2 means ~2 units increase per reading)
        if slope > 2.0:
            return state.add_anomaly(
                type="RESOURCE_DRIFT",
                agent=self.AGENT_NAME,
                evidence=[f"{resource_id}/{metric_name}/trend"],
                description=f"Resource {resource_id} shows upward drift in {metric_name} (slope: {slope:.2f})",
                confidence=0.7
            )
        
        return None
    
    def get_resource_summary(self, resource_id: str) -> Dict[str, Any]:
        """Get summary of resource state."""
        summary = {"resource_id": resource_id, "metrics": {}}
        
        if resource_id in self._history:
            for metric_name, history in self._history[resource_id].items():
                recent = history.get_recent(5)
                if recent:
                    summary["metrics"][metric_name] = {
                        "current": recent[-1],
                        "avg": statistics.mean(recent),
                        "trend": history.compute_trend_slope()
                    }
        
        return summary
