"""
IICWMS Agentic RAG Query Engine
Reasoning Query Interface - NOT a chatbot.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .vector_store import ChronosVectorStore, VectorDocument

__all__ = ["get_rag_engine"]

try:
    from .vector_store import ChronosVectorStore, VectorDocument
    __all__.extend(["ChronosVectorStore", "VectorDocument"])
except ModuleNotFoundError:
    # Optional dependency path (sentence-transformers/chromadb) is not required
    # for core API startup.
    ChronosVectorStore = None
    VectorDocument = None

# Lazy import to avoid circular dependency
def get_rag_engine():
    from .query_engine import AgenticRAGEngine
    from blackboard import get_shared_state
    from observation import get_observation_layer
    
    # Singleton pattern
    if not hasattr(get_rag_engine, '_instance'):
        get_rag_engine._instance = AgenticRAGEngine()
    return get_rag_engine._instance
