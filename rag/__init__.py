"""
IICWMS Agentic RAG Query Engine
Reasoning Query Interface - NOT a chatbot.
"""

from .vector_store import (
    ChronosVectorStore,
    VectorDocument
)

# Lazy import to avoid circular dependency
def get_rag_engine():
    from .query_engine import AgenticRAGEngine
    from blackboard import get_shared_state
    from observation import get_observation_layer
    
    # Singleton pattern
    if not hasattr(get_rag_engine, '_instance'):
        get_rag_engine._instance = AgenticRAGEngine()
    return get_rag_engine._instance

__all__ = [
    "ChronosVectorStore",
    "VectorDocument",
    "get_rag_engine"
]