"""
IICWMS Graph Module
Neo4j graph database client and queries.

Neo4j is the authoritative system state.
"""

from .neo4j_client import Neo4jClient

__all__ = ["Neo4jClient"]
