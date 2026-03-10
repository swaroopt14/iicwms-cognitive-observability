#!/usr/bin/env python3
"""
Backend smoke-check script (not a pytest test).

Important:
- Keep all executable code behind a `main()` guard so importing this module
  (e.g., by pytest collection) does not execute network/server startup.
"""

import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main() -> int:
    # Test basic imports
    try:
        from api.config import Settings  # noqa: F401
        print("✅ Settings import successful")
    except Exception as e:
        print(f"❌ Settings import failed: {e}")

    try:
        from blackboard import get_shared_state  # noqa: F401
        print("✅ SharedState import successful")
    except Exception as e:
        print(f"❌ SharedState import failed: {e}")

    try:
        from observation import get_observation_layer  # noqa: F401
        print("✅ ObservationLayer import successful")
    except Exception as e:
        print(f"❌ ObservationLayer import failed: {e}")

    try:
        from rag.query_engine import get_rag_engine  # noqa: F401
        print("✅ RAG engine import successful")
    except Exception as e:
        print(f"❌ RAG engine import failed: {e}")
        return 1

    try:
        from agents.query_agent import QueryAgent  # noqa: F401
        print("✅ QueryAgent import successful")
    except Exception as e:
        print(f"❌ QueryAgent import failed: {e}")

    # Test RAG engine object creation
    try:
        from rag.query_engine import get_rag_engine

        rag = get_rag_engine()
        print(f"✅ RAG engine created: {rag is not None}")
    except Exception as e:
        print(f"❌ RAG engine creation failed: {e}")

    print("\n🎯 Smoke checks complete.")
    print("If you want to start the API server, run: `uvicorn api.server:app --reload --port 8000`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
