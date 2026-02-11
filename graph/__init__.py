"""
IICWMS Graph Module — Neo4j Knowledge Graph
With graceful fallback to NullGraphClient when Neo4j is unavailable.
"""

from .neo4j_client import Neo4jClient, NullGraphClient, get_neo4j_client

__all__ = ["Neo4jClient", "NullGraphClient", "get_neo4j_client"]
