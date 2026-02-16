#!/usr/bin/env python3
"""Test Vector Store functionality"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag.vector_store import ChronosVectorStore
from datetime import datetime

def test_vector_store():
    print("🧪 Testing Vector Store...")
    
    # Initialize vector store
    store = ChronosVectorStore()
    print("✅ Vector store initialized")
    
    # Add test data
    store.add_anomaly(
        "test_anomaly_1",
        "CPU usage exceeded 90% threshold on server-01",
        "ResourceAgent",
        0.95,
        datetime.now()
    )
    
    store.add_policy_hit(
        "test_policy_1",
        "Unauthorized access attempt detected from IP 192.168.1.100",
        "SECURITY_POLICY_001",
        datetime.now()
    )
    
    store.add_recommendation(
        "test_rec_1",
        "High CPU usage",
        "Scale up server resources or optimize application",
        "HIGH",
        datetime.now()
    )
    
    print("✅ Test data added to vector store")
    
    # Test semantic search
    results = store.semantic_search("high cpu performance issues", n_results=3)
    print(f"✅ Semantic search found {len(results)} results:")
    
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['content'][:50]}... (distance: {result['distance']:.3f})")
    
    print("🎉 Vector Store test PASSED!")

if __name__ == "__main__":
    test_vector_store()