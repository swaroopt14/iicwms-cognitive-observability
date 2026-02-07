"""
IICWMS Explanation Crew (CrewAI)
================================
Optional CrewAI-powered explanation generation.

This crew replaces template-based explanations with richer,
LLM-generated narratives when ENABLE_CREWAI=true.

Three agents collaborate sequentially:
  1. Analyst   — structures raw evidence into a summary
  2. Explainer — writes human-readable narrative
  3. Recommender — derives prioritized action items

IMPORTANT:
- This module is ONLY imported when ENABLE_CREWAI=true
- All detection/reasoning is still done by the deterministic agents
- CrewAI is used ONLY for explanation wording (post-reasoning)
- If anything fails, the caller falls back to templates
"""

import os
import json
import logging
from typing import Dict, Any, Optional

from crewai import Agent, Task, Crew, Process

logger = logging.getLogger(__name__)

# ─── LLM config ────────────────────────────────────────────────────────────
# CrewAI uses litellm under the hood. For Gemini, the model string is
# "gemini/gemini-1.5-flash" and it reads GEMINI_API_KEY from env.
CREWAI_LLM = os.getenv("CREWAI_LLM_MODEL", "gemini/gemini-2.0-flash")


def _build_explanation_crew() -> Crew:
    """
    Build the 3-agent explanation crew.

    Returns a reusable Crew instance.
    """

    # ── Agent 1: Analyst ────────────────────────────────────────────────
    analyst = Agent(
        role="Evidence Analyst",
        goal=(
            "Analyze raw reasoning artifacts (anomalies, policy violations, "
            "risk signals, causal links) and produce a concise structured "
            "evidence summary."
        ),
        backstory=(
            "You are a senior IT operations analyst specializing in "
            "cognitive observability systems. You receive raw machine "
            "reasoning outputs and distill them into clear evidence summaries."
        ),
        llm=CREWAI_LLM,
        verbose=False,
        allow_delegation=False,
    )

    # ── Agent 2: Explainer ──────────────────────────────────────────────
    explainer = Agent(
        role="Insight Narrator",
        goal=(
            "Transform the evidence summary into a professional, "
            "human-readable insight with three sections: summary, "
            "why_it_matters, and what_will_happen_if_ignored."
        ),
        backstory=(
            "You are an executive communication specialist for IT operations. "
            "You translate technical evidence into clear, actionable language "
            "that non-technical stakeholders understand. You are factual, "
            "never alarmist, and always professional."
        ),
        llm=CREWAI_LLM,
        verbose=False,
        allow_delegation=False,
    )

    # ── Agent 3: Recommender ────────────────────────────────────────────
    recommender = Agent(
        role="Action Recommender",
        goal=(
            "Based on the evidence and narrative, produce 2-4 prioritized, "
            "specific recommended actions with urgency levels."
        ),
        backstory=(
            "You are an operations advisor who specializes in incident "
            "prevention and SLA management. You always recommend concrete, "
            "actionable steps — never vague advice."
        ),
        llm=CREWAI_LLM,
        verbose=False,
        allow_delegation=False,
    )

    # ── Task 1: Analyze evidence ────────────────────────────────────────
    analyze_task = Task(
        description=(
            "Analyze the following reasoning cycle evidence and produce "
            "a structured summary.\n\n"
            "SEVERITY: {severity}\n"
            "ANOMALIES: {anomalies}\n"
            "POLICY VIOLATIONS: {policy_violations}\n"
            "RISK SIGNALS: {risk_signals}\n"
            "CAUSAL LINKS: {causal_links}\n"
            "RECOMMENDATIONS: {recommendations}\n\n"
            "Output a structured evidence summary covering: "
            "what happened, which systems are affected, "
            "and how severe the situation is."
        ),
        expected_output=(
            "A structured evidence summary in plain text, covering "
            "the key findings, affected systems, and severity assessment."
        ),
        agent=analyst,
    )

    # ── Task 2: Write narrative ─────────────────────────────────────────
    narrate_task = Task(
        description=(
            "Using the evidence summary from the analyst, write a "
            "professional insight with exactly these three sections.\n\n"
            "You MUST respond with valid JSON and nothing else:\n"
            '{{\n'
            '  "summary": "<one sentence, max 30 words>",\n'
            '  "why_it_matters": "<business impact, max 50 words>",\n'
            '  "what_will_happen_if_ignored": "<consequences, max 40 words>"\n'
            '}}\n\n'
            "Be factual, professional, and concise. "
            "Use IT operations language."
        ),
        expected_output=(
            'A valid JSON object with keys: "summary", "why_it_matters", '
            '"what_will_happen_if_ignored".'
        ),
        agent=explainer,
    )

    # ── Task 3: Recommend actions ───────────────────────────────────────
    recommend_task = Task(
        description=(
            "Based on the evidence and narrative, produce 2-4 specific "
            "recommended actions.\n\n"
            "You MUST respond with valid JSON and nothing else:\n"
            '{{\n'
            '  "recommended_actions": [\n'
            '    "action description 1",\n'
            '    "action description 2"\n'
            '  ]\n'
            '}}\n\n'
            "Each action must be concrete and actionable."
        ),
        expected_output=(
            'A valid JSON object with key "recommended_actions" '
            "containing an array of 2-4 action strings."
        ),
        agent=recommender,
    )

    # ── Build crew ──────────────────────────────────────────────────────
    crew = Crew(
        agents=[analyst, explainer, recommender],
        tasks=[analyze_task, narrate_task, recommend_task],
        process=Process.sequential,
        verbose=False,
    )

    return crew


class ExplanationCrew:
    """
    Wrapper around the CrewAI explanation crew.

    Provides a simple `generate()` method that returns a dict
    matching the ExplanationEngine's expected format.
    """

    def __init__(self):
        self._crew = _build_explanation_crew()
        logger.info("CrewAI ExplanationCrew initialized (model: %s)", CREWAI_LLM)

    def generate(
        self,
        severity: str,
        anomalies: list,
        policy_violations: list,
        risk_signals: list,
        causal_links: list,
        recommendations: list,
    ) -> Optional[Dict[str, Any]]:
        """
        Run the explanation crew and return structured output.

        Returns:
            Dict with keys: summary, why_it_matters,
            what_will_happen_if_ignored, recommended_actions
            OR None if the crew fails.
        """
        try:
            inputs = {
                "severity": severity,
                "anomalies": json.dumps(anomalies, default=str),
                "policy_violations": json.dumps(policy_violations, default=str),
                "risk_signals": json.dumps(risk_signals, default=str),
                "causal_links": json.dumps(causal_links, default=str),
                "recommendations": json.dumps(recommendations, default=str),
            }

            result = self._crew.kickoff(inputs=inputs)

            # CrewAI returns a CrewOutput — get the raw string
            raw_output = str(result)

            # Parse the last task's JSON output (recommend_task)
            # We need both the narrate output and recommend output
            return self._parse_crew_output(raw_output, result)

        except Exception as e:
            logger.warning("CrewAI explanation crew failed: %s", e)
            return None

    def _parse_crew_output(
        self, raw_output: str, crew_result: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Parse crew output into the expected dict format.

        The crew runs 3 sequential tasks. We extract:
        - narrative from task 2 (narrate_task)
        - actions from task 3 (recommend_task)
        """
        try:
            # Try to get individual task outputs
            tasks_output = getattr(crew_result, "tasks_output", [])

            narrative = {}
            actions = []

            # Parse narrate task output (index 1)
            if len(tasks_output) >= 2:
                narrate_raw = str(tasks_output[1])
                narrative = self._extract_json(narrate_raw)

            # Parse recommend task output (index 2)
            if len(tasks_output) >= 3:
                recommend_raw = str(tasks_output[2])
                recommend_data = self._extract_json(recommend_raw)
                actions = recommend_data.get("recommended_actions", [])

            # If we couldn't parse task outputs, try the final output
            if not narrative:
                narrative = self._extract_json(raw_output)

            if not narrative:
                return None

            return {
                "summary": narrative.get("summary", ""),
                "why_it_matters": narrative.get("why_it_matters", ""),
                "what_will_happen_if_ignored": narrative.get(
                    "what_will_happen_if_ignored", ""
                ),
                "recommended_actions": actions,
            }

        except Exception as e:
            logger.warning("Failed to parse crew output: %s", e)
            return None

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """Extract the first JSON object from a text string."""
        # Try direct parse first
        try:
            return json.loads(text.strip())
        except (json.JSONDecodeError, ValueError):
            pass

        # Try to find JSON block in text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except (json.JSONDecodeError, ValueError):
                pass

        return {}
