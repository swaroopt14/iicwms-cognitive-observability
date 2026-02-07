"""
IICWMS Query Crew (CrewAI)
==========================
Optional CrewAI-powered query/RAG pipeline.

This crew replaces the pattern-matching RAG engine with richer,
LLM-driven evidence retrieval and synthesis when ENABLE_CREWAI=true.

Two agents collaborate sequentially:
  1. Retriever  — searches Blackboard + Observation Layer for evidence
  2. Synthesizer — composes a structured, evidence-backed answer

Custom tools give the agents read-only access to live system state:
  - BlackboardSearchTool: searches completed reasoning cycles
  - ObservationSearchTool: searches recent events and metrics

IMPORTANT:
- This module is ONLY imported when ENABLE_CREWAI=true
- Tools are READ-ONLY — agents cannot modify system state
- If anything fails, the caller falls back to the pattern-matching RAG
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Type

from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from blackboard import SharedState, get_shared_state
from observation import ObservationLayer, get_observation_layer

logger = logging.getLogger(__name__)

CREWAI_LLM = os.getenv("CREWAI_LLM_MODEL", "gemini/gemini-2.0-flash")


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM TOOLS (read-only access to system state)
# ═══════════════════════════════════════════════════════════════════════════════


class BlackboardSearchInput(BaseModel):
    """Input for searching the Blackboard (shared reasoning state)."""
    query_type: str = Field(
        description=(
            "What to search for. One of: 'anomalies', 'policy_hits', "
            "'risk_signals', 'causal_links', 'recommendations', 'all'"
        )
    )
    count: int = Field(
        default=5,
        description="Number of recent reasoning cycles to search (1-10)"
    )


class BlackboardSearchTool(BaseTool):
    """
    Search the Blackboard (shared reasoning state) for evidence.

    Returns anomalies, policy hits, risk signals, causal links,
    and recommendations from recent reasoning cycles.
    """
    name: str = "blackboard_search"
    description: str = (
        "Search the shared Blackboard state for reasoning evidence. "
        "Returns anomalies, policy violations, risk signals, causal links, "
        "and recommendations from recent reasoning cycles."
    )
    args_schema: Type[BaseModel] = BlackboardSearchInput

    def _run(self, query_type: str = "all", count: int = 5) -> str:
        """Execute the search."""
        try:
            state = get_shared_state()
            cycles = state.get_recent_cycles(min(count, 10))

            if not cycles:
                return json.dumps({"result": "No reasoning cycles available yet."})

            results: Dict[str, list] = {
                "anomalies": [],
                "policy_hits": [],
                "risk_signals": [],
                "causal_links": [],
                "recommendations": [],
            }

            for cycle in cycles:
                if query_type in ("anomalies", "all"):
                    for a in cycle.anomalies:
                        results["anomalies"].append({
                            "id": a.anomaly_id,
                            "type": a.type,
                            "description": a.description,
                            "confidence": a.confidence,
                            "agent": a.agent,
                        })

                if query_type in ("policy_hits", "all"):
                    for h in cycle.policy_hits:
                        results["policy_hits"].append({
                            "id": h.hit_id,
                            "policy": h.policy_id,
                            "description": h.description,
                            "agent": h.agent,
                        })

                if query_type in ("risk_signals", "all"):
                    for s in cycle.risk_signals:
                        results["risk_signals"].append({
                            "id": s.signal_id,
                            "entity": s.entity,
                            "reasoning": s.reasoning,
                            "confidence": s.confidence,
                            "projected_state": s.projected_state.value,
                        })

                if query_type in ("causal_links", "all"):
                    for c in cycle.causal_links:
                        results["causal_links"].append({
                            "cause": c.cause,
                            "effect": c.effect,
                            "reasoning": c.reasoning,
                            "confidence": c.confidence,
                        })

                if query_type in ("recommendations", "all"):
                    for r in cycle.recommendations:
                        results["recommendations"].append({
                            "action": r.action,
                            "rationale": r.rationale,
                            "urgency": r.urgency,
                        })

            # Filter to requested type
            if query_type != "all":
                output = {query_type: results.get(query_type, [])}
            else:
                output = results

            return json.dumps(output, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})


class ObservationSearchInput(BaseModel):
    """Input for searching the Observation Layer."""
    search_type: str = Field(
        description="What to search for. One of: 'events', 'metrics', 'both'"
    )
    count: int = Field(
        default=20,
        description="Number of recent items to retrieve (1-50)"
    )


class ObservationSearchTool(BaseTool):
    """
    Search the Observation Layer for recent events and metrics.

    Returns raw observed events and resource metrics
    from the system's ingestion pipeline.
    """
    name: str = "observation_search"
    description: str = (
        "Search the Observation Layer for recent events and resource metrics. "
        "Returns raw system events (workflow steps, errors) and "
        "resource metrics (CPU, memory, latency)."
    )
    args_schema: Type[BaseModel] = ObservationSearchInput

    def _run(self, search_type: str = "both", count: int = 20) -> str:
        """Execute the search."""
        try:
            obs = get_observation_layer()
            count = min(count, 50)
            output: Dict[str, list] = {}

            if search_type in ("events", "both"):
                events = obs.get_recent_events(count)
                output["events"] = [
                    {
                        "id": e.event_id,
                        "type": e.type,
                        "workflow_id": e.workflow_id,
                        "actor": e.actor,
                        "resource": e.resource,
                        "timestamp": e.timestamp.isoformat(),
                    }
                    for e in events
                ]

            if search_type in ("metrics", "both"):
                metrics = obs.get_recent_metrics(count)
                output["metrics"] = [
                    {
                        "resource_id": m.resource_id,
                        "metric": m.metric,
                        "value": round(m.value, 2),
                        "timestamp": m.timestamp.isoformat(),
                    }
                    for m in metrics
                ]

            return json.dumps(output, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════════
# QUERY CREW
# ═══════════════════════════════════════════════════════════════════════════════


def _build_query_crew() -> Crew:
    """
    Build the 2-agent query crew with custom tools.

    Returns a reusable Crew instance.
    """

    blackboard_tool = BlackboardSearchTool()
    observation_tool = ObservationSearchTool()

    # ── Agent 1: Retriever ──────────────────────────────────────────────
    retriever = Agent(
        role="Evidence Retriever",
        goal=(
            "Given a user's question about the system, search the Blackboard "
            "and Observation Layer to find ALL relevant evidence: anomalies, "
            "policy violations, risk signals, causal links, events, and metrics."
        ),
        backstory=(
            "You are a forensic analyst for IT operations. You have access "
            "to the system's shared reasoning state (Blackboard) and raw "
            "observation data. Your job is to find every piece of evidence "
            "that helps answer the user's question. Be thorough."
        ),
        tools=[blackboard_tool, observation_tool],
        llm=CREWAI_LLM,
        verbose=False,
        allow_delegation=False,
    )

    # ── Agent 2: Synthesizer ────────────────────────────────────────────
    synthesizer = Agent(
        role="Answer Synthesizer",
        goal=(
            "Using the retrieved evidence, compose a clear, structured answer "
            "to the user's question. The answer must cite specific evidence "
            "and include confidence levels."
        ),
        backstory=(
            "You are an expert at synthesizing complex IT operations data "
            "into actionable insights. You always cite evidence, quantify "
            "confidence, and suggest follow-up questions. You are factual "
            "and never speculate beyond what the evidence supports."
        ),
        llm=CREWAI_LLM,
        verbose=False,
        allow_delegation=False,
    )

    # ── Task 1: Retrieve evidence ───────────────────────────────────────
    retrieve_task = Task(
        description=(
            "The user asks: {query}\n\n"
            "Search the Blackboard for anomalies, policy violations, "
            "risk signals, and causal links. Also search the Observation "
            "Layer for recent events and metrics.\n\n"
            "Return ALL evidence relevant to the question."
        ),
        expected_output=(
            "A comprehensive evidence summary listing all relevant "
            "anomalies, policy hits, risk signals, causal links, "
            "events, and metrics found."
        ),
        agent=retriever,
    )

    # ── Task 2: Synthesize answer ───────────────────────────────────────
    synthesize_task = Task(
        description=(
            "Using the retrieved evidence, compose a structured answer "
            "to the user's question: {query}\n\n"
            "You MUST respond with valid JSON and nothing else:\n"
            '{{\n'
            '  "answer": "<comprehensive answer in 2-3 sentences>",\n'
            '  "confidence": <float 0.0-1.0>,\n'
            '  "key_findings": ["finding 1", "finding 2"],\n'
            '  "recommended_actions": ["action 1", "action 2"],\n'
            '  "follow_up_queries": ["question 1", "question 2"]\n'
            '}}\n\n'
            "Be factual. Cite specific evidence. Quantify where possible."
        ),
        expected_output=(
            'A valid JSON object with keys: "answer", "confidence", '
            '"key_findings", "recommended_actions", "follow_up_queries".'
        ),
        agent=synthesizer,
    )

    crew = Crew(
        agents=[retriever, synthesizer],
        tasks=[retrieve_task, synthesize_task],
        process=Process.sequential,
        verbose=False,
    )

    return crew


class QueryCrew:
    """
    Wrapper around the CrewAI query crew.

    Provides a simple `query()` method that returns a dict
    matching the QueryAgent's expected format.
    """

    def __init__(self):
        self._crew = _build_query_crew()
        logger.info("CrewAI QueryCrew initialized (model: %s)", CREWAI_LLM)

    def query(self, user_query: str) -> Optional[Dict[str, Any]]:
        """
        Run the query crew and return structured output.

        Returns:
            Dict with keys: answer, confidence, key_findings,
            recommended_actions, follow_up_queries
            OR None if the crew fails.
        """
        try:
            inputs = {"query": user_query}
            result = self._crew.kickoff(inputs=inputs)

            raw_output = str(result)
            return self._parse_crew_output(raw_output, result)

        except Exception as e:
            logger.warning("CrewAI query crew failed: %s", e)
            return None

    def _parse_crew_output(
        self, raw_output: str, crew_result: Any
    ) -> Optional[Dict[str, Any]]:
        """Parse crew output into the expected dict format."""
        try:
            # Try individual task outputs first
            tasks_output = getattr(crew_result, "tasks_output", [])

            if len(tasks_output) >= 2:
                synth_raw = str(tasks_output[1])
                parsed = self._extract_json(synth_raw)
                if parsed and "answer" in parsed:
                    return parsed

            # Fall back to final crew output
            parsed = self._extract_json(raw_output)
            if parsed and "answer" in parsed:
                return parsed

            # If we got text but no JSON, wrap it
            if raw_output.strip():
                return {
                    "answer": raw_output.strip()[:500],
                    "confidence": 0.6,
                    "key_findings": [],
                    "recommended_actions": [],
                    "follow_up_queries": [],
                }

            return None

        except Exception as e:
            logger.warning("Failed to parse query crew output: %s", e)
            return None

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """Extract the first JSON object from a text string."""
        try:
            return json.loads(text.strip())
        except (json.JSONDecodeError, ValueError):
            pass

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except (json.JSONDecodeError, ValueError):
                pass

        return {}
