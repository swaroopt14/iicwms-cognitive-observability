"""
IICWMS Multi-Agent Reasoning Layer
==================================
Specialized agents for cognitive observability.

Agents do NOT communicate directly.
All coordination happens through SharedState.

AGENT LINEUP (9 total):
1. WorkflowAgent         — Workflow & anomaly monitoring
2. ResourceAgent         — Resource usage analysis
3. ComplianceAgent       — Policy violation detection
4. RiskForecastAgent     — Predictive risk analysis
5. CausalAgent           — Cross-agent causal reasoning
6. QueryAgent            — Agentic RAG reasoning queries
7. AdaptiveBaselineAgent — Dynamic threshold learning
8. ScenarioInjectionAgent— Stress testing & scenario injection
9. MasterAgent           — Coordination (not counted as specialized)
"""

from .workflow_agent import WorkflowAgent
from .resource_agent import ResourceAgent
from .compliance_agent import ComplianceAgent
from .risk_forecast_agent import RiskForecastAgent
from .causal_agent import CausalAgent
from .query_agent import QueryAgent
from .adaptive_baseline_agent import AdaptiveBaselineAgent
from .scenario_injection_agent import ScenarioInjectionAgent
from .code_agent import CodeAgent
from .master_agent import MasterAgent, CycleResult

__all__ = [
    "WorkflowAgent",
    "ResourceAgent",
    "ComplianceAgent",
    "RiskForecastAgent",
    "CausalAgent",
    "QueryAgent",
    "AdaptiveBaselineAgent",
    "ScenarioInjectionAgent",
    "CodeAgent",
    "MasterAgent",
    "CycleResult",
]
