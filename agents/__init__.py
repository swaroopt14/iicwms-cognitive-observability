"""
IICWMS Agent Module
Multi-agent system for cognitive observability.

Agents are coordinated through a shared evidence substrate (the Blackboard).
Each agent is stateless and produces structured opinions.
"""

from .workflow_agent import WorkflowAgent, Opinion
from .policy_agent import PolicyAgent, PolicyOpinion
from .resource_agent import ResourceAgent, ResourceOpinion
from .rca_agent import RCAAgent, RCAOpinion
from .master_agent import MasterAgent, Insight

__all__ = [
    "WorkflowAgent",
    "PolicyAgent", 
    "ResourceAgent",
    "RCAAgent",
    "MasterAgent",
    "Opinion",
    "PolicyOpinion",
    "ResourceOpinion",
    "RCAOpinion",
    "Insight"
]
