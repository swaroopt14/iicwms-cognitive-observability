#!/usr/bin/env python3
"""Direct RAG engine test without problematic imports"""

import warnings
warnings.filterwarnings('ignore')

# Test RAG engine directly
try:
    # Direct import without going through rag module
    import sys
    sys.path.insert(0, '/d:/PCCOE_REPO1/iicwms-cognitive-observability')
    
    # Import the modules directly
    from rag.query_engine import AgenticRAGEngine
    from blackboard import get_shared_state
    from observation import get_observation_layer
    from rag.query_engine import ReasoningSynthesizer
    
    print("✅ Direct imports successful")
    
    # Create RAG engine with minimal dependencies
    rag = AgenticRAGEngine()
    print(f"✅ RAG engine created: {rag is not None}")
    
    # Initialize synthesizer directly
    synthesizer = ReasoningSynthesizer(get_shared_state(), get_observation_layer())
    print(f"✅ Synthesizer created: {synthesizer is not None}")
    
    # Initialize LLM directly
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            llm = genai.GenerativeModel("gemini-2.5-flash")
            print("✅ LLM initialized successfully")
            
            # Test generation
            response = llm.generate_content("What caused the cost spike?")
            print(f"✅ LLM generation successful: {response.text[:100]}...")
            
            # Set LLM in synthesizer
            synthesizer._llm = llm
            print("✅ LLM set in synthesizer")
            
        except Exception as e:
            print(f"❌ LLM initialization failed: {e}")
    else:
        print("❌ No API key")
    
    print("\n🎯 Direct RAG test complete!")
    
except Exception as e:
    print(f"❌ Direct RAG test failed: {e}")
