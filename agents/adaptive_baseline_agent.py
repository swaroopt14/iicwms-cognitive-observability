"""
IICWMS Adaptive Baseline Agent
===============================
Learns "normal" behavior and dynamically adjusts detection thresholds.

PURPOSE:
- Observe metrics/events over multiple cycles
- Compute rolling baselines (mean, stddev) per resource/workflow
- Adjust detection thresholds dynamically
- Distinguish "new normal" from "actual anomaly"

COVERS PS-08 ROUND 2: "Adaptive Intelligence"
"Agents evolve their decision rules over time."

NO ML REQUIRED — statistical rolling windows are sufficient.

OUTPUT:
{
  "entity": "vm_api_01",
  "metric": "cpu_usage",
  "baseline_mean": 42.3,
  "baseline_stddev": 8.1,
  "current_value": 91.0,
  "deviation_sigma": 6.0,
  "threshold_adjusted": true,
  "old_threshold": 80,
  "new_threshold": 58.5,
  "reasoning": "Rolling baseline shows normal CPU at 42±8. Current 91 is 6σ deviation."
}
"""

import uuid
import math
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict

from blackboard import SharedState, Anomaly
from observation import ObservedMetric


AGENT_NAME = "AdaptiveBaselineAgent"

# Configuration
WINDOW_SIZE = 50          # Rolling window for baseline calculation
MIN_SAMPLES = 10          # Minimum samples before baseline is active
DEVIATION_THRESHOLD = 2.5 # Standard deviations for anomaly detection
DRIFT_THRESHOLD = 1.5     # Sigma for baseline drift notification
ADAPTATION_RATE = 0.1     # How fast baselines adapt (0=never, 1=instant)


@dataclass
class BaselineProfile:
    """Rolling baseline for a single metric on a single entity."""
    entity: str
    metric: str
    values: List[float] = field(default_factory=list)
    mean: float = 0.0
    stddev: float = 0.0
    last_threshold: float = 80.0  # Default starting threshold
    adapted_threshold: float = 80.0
    samples_seen: int = 0
    last_updated: Optional[datetime] = None
    is_active: bool = False  # True once MIN_SAMPLES reached

    def add_value(self, value: float, timestamp: datetime):
        """Add a new observation and recompute baseline."""
        self.values.append(value)
        self.samples_seen += 1
        self.last_updated = timestamp

        # Keep rolling window
        if len(self.values) > WINDOW_SIZE:
            self.values = self.values[-WINDOW_SIZE:]

        # Recompute stats
        if len(self.values) >= MIN_SAMPLES:
            self.is_active = True
            self.mean = sum(self.values) / len(self.values)
            variance = sum((v - self.mean) ** 2 for v in self.values) / len(self.values)
            self.stddev = math.sqrt(variance) if variance > 0 else 1.0

            # Adapt threshold: mean + DEVIATION_THRESHOLD * stddev
            new_threshold = self.mean + DEVIATION_THRESHOLD * self.stddev
            # Smooth adaptation
            self.last_threshold = self.adapted_threshold
            self.adapted_threshold = (
                (1 - ADAPTATION_RATE) * self.adapted_threshold
                + ADAPTATION_RATE * new_threshold
            )

    def get_deviation(self, value: float) -> float:
        """Get deviation in standard deviations from baseline."""
        if not self.is_active or self.stddev == 0:
            return 0.0
        return (value - self.mean) / self.stddev

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity": self.entity,
            "metric": self.metric,
            "mean": round(self.mean, 2),
            "stddev": round(self.stddev, 2),
            "adapted_threshold": round(self.adapted_threshold, 2),
            "samples_seen": self.samples_seen,
            "is_active": self.is_active,
            "window_size": len(self.values),
        }


@dataclass
class BaselineDeviation:
    """A detected deviation from learned baseline."""
    entity: str
    metric: str
    current_value: float
    baseline_mean: float
    baseline_stddev: float
    deviation_sigma: float
    old_threshold: float
    new_threshold: float
    is_anomaly: bool
    reasoning: str


class AdaptiveBaselineAgent:
    """
    Adaptive Baseline Agent.

    Learns normal behavior patterns and dynamically adjusts
    detection thresholds. This means:

    - If CPU normally runs at 70%, don't alert at 75%
    - If latency baseline drifts up, detect the *drift* not just the value
    - If a metric stabilizes at a new level, adapt to the "new normal"

    This agent does NOT detect anomalies itself — it provides
    adaptive thresholds that the ResourceAgent can consume.
    """

    AGENT_NAME = "AdaptiveBaselineAgent"

    def __init__(self):
        # Nested dict: entity -> metric -> BaselineProfile
        self._baselines: Dict[str, Dict[str, BaselineProfile]] = defaultdict(dict)
        self._deviation_history: List[BaselineDeviation] = []

    def analyze(
        self,
        metrics: List[ObservedMetric],
        state: SharedState,
    ) -> List[Anomaly]:
        """
        Process metrics, update baselines, detect deviations.

        Returns list of anomalies where current values deviate
        significantly from learned baselines.
        """
        anomalies: List[Anomaly] = []

        for metric in metrics:
            entity = metric.resource_id
            metric_name = metric.metric
            value = metric.value
            timestamp = metric.timestamp

            # Get or create baseline profile
            if metric_name not in self._baselines[entity]:
                self._baselines[entity][metric_name] = BaselineProfile(
                    entity=entity,
                    metric=metric_name,
                )

            profile = self._baselines[entity][metric_name]

            # Check deviation BEFORE updating baseline
            if profile.is_active:
                deviation = profile.get_deviation(value)
                is_anomaly = abs(deviation) > DEVIATION_THRESHOLD

                dev = BaselineDeviation(
                    entity=entity,
                    metric=metric_name,
                    current_value=value,
                    baseline_mean=profile.mean,
                    baseline_stddev=profile.stddev,
                    deviation_sigma=round(deviation, 2),
                    old_threshold=round(profile.adapted_threshold, 2),
                    new_threshold=round(
                        profile.mean + DEVIATION_THRESHOLD * profile.stddev, 2
                    ),
                    is_anomaly=is_anomaly,
                    reasoning=self._build_reasoning(
                        entity, metric_name, value, profile, deviation
                    ),
                )
                self._deviation_history.append(dev)

                if is_anomaly:
                    anomaly = state.add_anomaly(
                        type="BASELINE_DEVIATION",
                        agent=self.AGENT_NAME,
                        evidence=[f"metric_{entity}_{metric_name}"],
                        description=(
                            f"{metric_name} on {entity} at {value:.1f} "
                            f"is {abs(deviation):.1f}σ from baseline "
                            f"(mean={profile.mean:.1f}, σ={profile.stddev:.1f}). "
                            f"Adaptive threshold: {profile.adapted_threshold:.1f}"
                        ),
                        confidence=min(0.95, 0.5 + abs(deviation) * 0.1),
                    )
                    anomalies.append(anomaly)

            # Update baseline with new value
            profile.add_value(value, timestamp)

        return anomalies

    def get_baselines(self) -> Dict[str, Any]:
        """Get all current baselines for API/UI consumption."""
        result = {}
        for entity, metrics in self._baselines.items():
            result[entity] = {
                name: profile.to_dict()
                for name, profile in metrics.items()
            }
        return result

    def get_baseline_for(self, entity: str, metric: str) -> Optional[Dict[str, Any]]:
        """Get baseline for a specific entity+metric."""
        if entity in self._baselines and metric in self._baselines[entity]:
            return self._baselines[entity][metric].to_dict()
        return None

    def get_recent_deviations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent deviation checks."""
        return [
            {
                "entity": d.entity,
                "metric": d.metric,
                "current_value": d.current_value,
                "baseline_mean": round(d.baseline_mean, 2),
                "baseline_stddev": round(d.baseline_stddev, 2),
                "deviation_sigma": d.deviation_sigma,
                "is_anomaly": d.is_anomaly,
                "reasoning": d.reasoning,
            }
            for d in self._deviation_history[-limit:]
        ]

    def _build_reasoning(
        self,
        entity: str,
        metric: str,
        value: float,
        profile: BaselineProfile,
        deviation: float,
    ) -> str:
        """Build human-readable reasoning for a deviation check."""
        if abs(deviation) > DEVIATION_THRESHOLD:
            return (
                f"ANOMALY: {metric} on {entity} is {value:.1f}, "
                f"which is {abs(deviation):.1f}σ from learned baseline "
                f"(mean={profile.mean:.1f} ± {profile.stddev:.1f}). "
                f"Threshold dynamically adjusted to {profile.adapted_threshold:.1f}."
            )
        elif abs(deviation) > DRIFT_THRESHOLD:
            return (
                f"DRIFT: {metric} on {entity} at {value:.1f} shows drift "
                f"({deviation:.1f}σ from baseline). Not yet anomalous but trending."
            )
        else:
            return (
                f"NORMAL: {metric} on {entity} at {value:.1f} "
                f"is within baseline ({profile.mean:.1f} ± {profile.stddev:.1f})."
            )
