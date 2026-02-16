"""
IICWMS Shared State (Blackboard)
Makes reasoning inspectable and debuggable.
"""

from .state import (
    SharedState,
    ReasoningCycle,
    Fact,
    Anomaly,
    PolicyHit,
    RiskSignal,
    RiskState,
    Hypothesis,
    CausalLink,
    Recommendation,
    SeverityScore,
    ScenarioRun,
    RecommendationV2,
    get_shared_state
)

__all__ = [
    "SharedState",
    "ReasoningCycle",
    "Fact",
    "Anomaly",
    "PolicyHit",
    "RiskSignal",
    "RiskState",
    "Hypothesis",
    "CausalLink",
    "Recommendation",
    "SeverityScore",
    "ScenarioRun",
    "RecommendationV2",
    "get_shared_state"
]
