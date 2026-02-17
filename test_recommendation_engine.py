#!/usr/bin/env python3
"""Test Dynamic Recommendation Engine"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.recommendation_engine_agent import RecommendationEngineAgent
from blackboard import get_shared_state


def test_recommendation_engine():
    print("Testing Dynamic Recommendation Engine...")
    state = get_shared_state()

    print("Adding mock data to system state...")

    # Ensure a clean active cycle before seeding.
    if state.current_cycle:
        state.complete_cycle()

    # Seed one completed cycle with findings so the engine has context.
    seed_cycle_id = state.start_cycle()
    print(f"Started seed cycle: {seed_cycle_id}")

    state.add_anomaly(
        type="HIGH_CPU_USAGE",
        agent="TestAgent",
        evidence=["test-evidence-1"],
        description="High CPU usage detected on server-01",
        confidence=0.85,
    )

    state.add_policy_hit(
        policy_id="SECURITY_POLICY_001",
        event_id="evt_test_001",
        violation_type="SILENT",
        agent="TestAgent",
        description="Security policy violation: unauthorized access attempt",
    )

    state.complete_cycle()

    # Start an active cycle where RecommendationV2 outputs will be appended.
    active_cycle_id = state.start_cycle()
    print(f"Started active recommendation cycle: {active_cycle_id}")

    print("Mock data added to system state")

    try:
        agent = RecommendationEngineAgent()
        print("Recommendation engine initialized")

        if agent.llm:
            print("LangChain (Gemini) available")
        else:
            print("LangChain not available, using fallback")

        print("\nTesting recommendation generation...")

        recommendations = agent.perceive(state)

        if recommendations:
            print(f"Generated {len(recommendations)} recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec.action_description}")
                print(f"     Severity Score: {rec.severity_score:.2f}")
                print(f"     Confidence: {rec.confidence:.2f}")
                print(f"     Expected: {rec.expected_effect}")
        else:
            print("No recommendations generated")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()

    print("\nRecommendation Engine Test COMPLETED!")


if __name__ == "__main__":
    test_recommendation_engine()
