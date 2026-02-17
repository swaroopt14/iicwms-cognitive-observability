#!/usr/bin/env python3
"""Simple backend test without problematic imports"""

import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test basic imports
try:
    from api.config import Settings
    print("✅ Settings import successful")
except Exception as e:
    print(f"❌ Settings import failed: {e}")

try:
    from blackboard import get_shared_state
    print("✅ SharedState import successful")
except Exception as e:
    print(f"❌ SharedState import failed: {e}")

try:
    from observation import get_observation_layer
    print("✅ ObservationLayer import successful")
except Exception as e:
    print(f"❌ ObservationLayer import failed: {e}")

try:
    from rag.query_engine import get_rag_engine, force_refresh_rag_engine
    print("✅ RAG engine import successful")
except Exception as e:
    print(f"❌ RAG engine import failed: {e}")

try:
    from agents.query_agent import QueryAgent
    print("✅ QueryAgent import successful")
except Exception as e:
    print(f"❌ QueryAgent import failed: {e}")

# Test RAG engine
try:
    rag = get_rag_engine()
    print(f"✅ RAG engine created: {rag is not None}")
    
    # Test LLM initialization
    synthesizer = rag._synthesizer
    llm = synthesizer._llm if hasattr(synthesizer, '_llm') else None
    print(f"✅ LLM available: {llm is not None}")
    
    if llm:
        # Test simple generation
        try:
            response = llm.generate_content("Hello, test message")
            print(f"✅ LLM generation successful: {response.text[:50]}...")
        except Exception as e:
            print(f"❌ LLM generation failed: {e}")
    else:
        print("❌ LLM not available")

print("\n🎯 All imports successful! Ready to start backend.")
print("Starting backend with minimal dependencies...")

# Try to start the server
try:
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000, reload=True)
    print("✅ Backend started successfully!")
except Exception as e:
    print(f"❌ Backend start failed: {e}")
