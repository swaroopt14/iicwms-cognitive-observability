"""
IICWMS Vector Store for RAG
===========================
Semantic search capabilities for reasoning outputs.
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class VectorDocument:
    """Document for vector storage."""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None

class ChronosVectorStore:
    """Vector database for semantic search across reasoning outputs."""
    
    def __init__(self, persist_directory: str = "data/vectordb"):
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(allow_reset=True)
        )
        self.collection = self.client.get_or_create_collection(
            name="chronos_reasoning",
            metadata={"description": "IICWMS reasoning outputs"}
        )
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
    
    def add_anomaly(self, anomaly_id: str, description: str, 
                   agent: str, confidence: float, timestamp: datetime):
        """Add anomaly to vector store."""
        doc = VectorDocument(
            id=f"anomaly_{anomaly_id}",
            content=description,
            metadata={
                "type": "anomaly",
                "agent": agent,
                "confidence": confidence,
                "timestamp": timestamp.isoformat()
            }
        )
        self._add_document(doc)
    
    def add_policy_hit(self, hit_id: str, description: str,
                      policy_id: str, timestamp: datetime):
        """Add policy violation to vector store."""
        doc = VectorDocument(
            id=f"policy_{hit_id}",
            content=description,
            metadata={
                "type": "policy_hit",
                "policy_id": policy_id,
                "timestamp": timestamp.isoformat()
            }
        )
        self._add_document(doc)
    
    def add_recommendation(self, rec_id: str, cause: str, action: str,
                         urgency: str, timestamp: datetime):
        """Add recommendation to vector store."""
        content = f"Cause: {cause}. Action: {action}. Urgency: {urgency}"
        doc = VectorDocument(
            id=f"rec_{rec_id}",
            content=content,
            metadata={
                "type": "recommendation",
                "urgency": urgency,
                "timestamp": timestamp.isoformat()
            }
        )
        self._add_document(doc)
    
    def semantic_search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Perform semantic search."""
        query_embedding = self.encoder.encode(query).tolist()
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        return [
            {
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            }
            for i in range(len(results["ids"][0]))
        ]
    
    def _add_document(self, doc: VectorDocument):
        """Add document to collection."""
        embedding = self.encoder.encode(doc.content).tolist()
        
        self.collection.add(
            ids=[doc.id],
            embeddings=[embedding],
            documents=[doc.content],
            metadatas=[doc.metadata]
        )