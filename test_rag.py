#!/usr/bin/env python3
"""Test RAG engine with Gemini 2.5 Flash"""

import warnings
warnings.filterwarnings('ignore')

# Test the RAG engine
try:
    from rag import get_rag_engine, force_refresh_rag_engine
    print("✅ RAG engine import successful")
    
    rag = get_rag_engine()
    print(f"✅ RAG engine created: {rag is not None}")
    
    # Test LLM
    synthesizer = rag._synthesizer
    llm = synthesizer._llm if hasattr(synthesizer, '_llm') else None
    print(f"✅ LLM available: {llm is not None}")
    
    if llm:
        # Test query
        evidence_context = {
            'query_intent': 'cost_analysis',
            'system_metrics': {
                'error_rate': 0.08,
                'cpu_utilization': 85
            }
        }
        
        result = rag.query_with_context('What caused the cost spike?', evidence_context)
        print(f"✅ Query result: {result.answer[:100]}...")
        print(f"✅ Dynamic LLM working: {'Yes' if 'Unable to generate dynamic response' not in result.answer else 'No'}")
    else:
        print("❌ LLM not available")
    
    print("\n🎯 RAG engine test complete!")
    
except Exception as e:
    print(f"❌ RAG test failed: {e}")
