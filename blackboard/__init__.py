"""
IICWMS Blackboard Module
Append-only evidence store implementing the ATRE pillar.
"""

from .evidence_store import EvidenceStore, get_evidence_store

__all__ = ["EvidenceStore", "get_evidence_store"]
