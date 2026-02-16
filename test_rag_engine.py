#!/usr/bin/env python3
"""Test Enhanced RAG Engine"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag import get_rag_engine

def test_rag_engine():
    print("🧪 Testing Enhanced RAG Engine...")
    
    # Get RAG engine
    engine = get_rag_engine()
    print("✅ RAG engine initialized")
    
    # Test queries
    test_queries = [
        "What resource issues are detected?",
        "Are there any compliance violations?",
        "What is the current risk status?",
        "Show me workflow problems",
        "Predict future system issues"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        
        try:
            response = engine.query(query)
            print(f"✅ Answer: {response.answer[:100]}...")
            print(f"   Confidence: {response.confidence:.2f}")
            print(f"   Evidence count: {len(response.evidence_details)}")
            print(f"   Uncertainty: {response.uncertainty}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n🎉 RAG Engine test COMPLETED!")

if __name__ == "__main__":
    test_rag_engine()