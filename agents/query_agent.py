"""
IICWMS Query Agent (Agentic RAG)
================================
Reasoning Query Interface — NOT a chatbot.

PURPOSE:
- Decomposes natural language questions into agent-specific sub-queries
- Retrieves evidence from Blackboard state + agent outputs
- Synthesizes structured, evidence-backed answers

This agent wraps the RAG engine as a first-class citizen
in the multi-agent system, making its outputs trackable
on the Blackboard like every other agent.

WHAT IT INDEXES:
- Agent outputs (NOT raw logs)
- Blackboard state (anomalies, policy hits, risk signals, causal links)
- Policy definitions
- Risk forecasts
- Recommendations

This is why the system is smarter than Datadog.
"""

from datetime import datetime
from rag.query_engine import get_rag_engine, RAGResponse
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import uuid
import os
import logging
import re

from blackboard import SharedState, Hypothesis
# Local types and interfaces
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from observation import ObservationLayer, get_observation_layer

logger = logging.getLogger(__name__)


AGENT_NAME = "QueryAgent"


@dataclass
class QueryResult:
    """Structured result from QueryAgent."""
    query_id: str
    original_query: str
    answer: str
    why_it_matters: List[str]
    supporting_evidence: List[Dict[str, Any]]
    causal_chain: List[Dict[str, str]]
    recommended_actions: List[Dict[str, str]]
    confidence: float
    time_horizon: str
    uncertainty: str
    query_type: str
    target_agents: List[str]
    follow_up_queries: List[str]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class QueryAgent:
    """
    Query Agent — wraps the RAG engine as a proper agent.

    Participates in the multi-agent system:
    - Outputs are recorded on the Blackboard as Hypotheses
    - Agent attribution is tracked
    - Confidence scores are auditable

    Architecture:
        User Query
           ↓
        QueryAgent.query()
           ↓
        Query Decomposer (pattern matching → sub-queries)
           ↓
        Evidence Retrieval (Blackboard + Observation Layer)
           ↓
        Reasoning Synthesizer (structured answer)
           ↓
        QueryResult + Hypothesis on Blackboard
    """

    AGENT_NAME = "QueryAgent"

    def __init__(self):
        from rag import get_rag_engine
        self._rag_engine = get_rag_engine()
        self._crewai_crew = None
        self._init_crewai()

    def _init_crewai(self):
        """Initialize CrewAI query crew if ENABLE_CREWAI=true."""
        enable_crewai = os.getenv("ENABLE_CREWAI", "false").lower().strip()
        if enable_crewai != "true":
            return

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("ENABLE_CREWAI=true but GEMINI_API_KEY not set; skipping CrewAI query init")
            return

        try:
            from agents.query_crew import QueryCrew
            self._crewai_crew = QueryCrew()
            logger.info("CrewAI QueryCrew loaded successfully")
        except ImportError as e:
            logger.warning("CrewAI not installed, falling back to RAG engine: %s", e)
        except Exception as e:
            logger.warning("CrewAI query init failed, falling back to RAG engine: %s", e)

    def query(
        self,
        user_query: str,
        state: Optional[SharedState] = None,
    ) -> QueryResult:
        """
        Process a reasoning query and return structured result.

        If CrewAI is enabled, tries the AI crew first with RAG fallback.
        If a SharedState is provided and a cycle is active,
        the answer is also recorded as a Hypothesis.
        """
        # Try CrewAI first if available
        checklist_result = self._maybe_ops_checklist_query(user_query, state)
        if checklist_result:
            return checklist_result

        if self._crewai_crew:
            crewai_result = self._query_via_crewai(user_query, state)
            if crewai_result:
                return crewai_result
            logger.info("CrewAI query returned None, falling back to RAG engine")

        # Fallback: use the existing RAG engine
        return self._query_via_rag(user_query, state)

    def _maybe_ops_checklist_query(
        self,
        user_query: str,
        state: Optional[SharedState],
    ) -> Optional[QueryResult]:
        """
        Deterministic response mode for operational prompts.
        Example:
            "Given projected_state=VIOLATION and impact_score=64, what should DevOps do in next 15 minutes?"
        """
        q = (user_query or "").lower()
        if "devops" not in q and "next 15 minutes" not in q and "checklist" not in q:
            return None

        # Parse explicit query context if provided.
        state_match = re.search(r"projected_state\s*=\s*([a-z_]+)", q, flags=re.IGNORECASE)
        score_match = re.search(r"impact_score\s*=\s*([0-9]+(?:\.[0-9]+)?)", q, flags=re.IGNORECASE)
        projected_state = state_match.group(1).upper() if state_match else "AT_RISK"
        impact_score = float(score_match.group(1)) if score_match else 50.0

        latest_cycle = state._completed_cycles[-1] if state and state._completed_cycles else None
        top_action = "Throttle concurrent deploy jobs and cap retries"
        if latest_cycle:
            if getattr(latest_cycle, "recommendations_v2", None):
                top_action = latest_cycle.recommendations_v2[0].action_description
            elif latest_cycle.recommendations:
                top_action = latest_cycle.recommendations[0].action

        severity_label = "high" if projected_state in ("VIOLATION", "INCIDENT") or impact_score >= 60 else "medium"
        answer = (
            f"DevOps 15-minute checklist for {projected_state} (impact {impact_score:.0f}, {severity_label} severity):\n"
            f"1. Minute 0-5: Contain blast radius — {top_action}. Freeze non-critical deploys.\n"
            f"2. Minute 5-10: Stabilize service — reduce queue pressure, cap retries, and scale critical pods/workers.\n"
            f"3. Minute 10-15: Verify recovery — confirm risk trend down, SLA errors reducing, and no new policy hits.\n"
            f"4. Escalate if not improving — open incident bridge and assign owners for app, infra, and compliance."
        )

        recs = [
            {"action": "Contain blast radius now", "expected_impact": "Prevent additional failures while root cause is isolated", "priority": "high"},
            {"action": "Throttle/cap deployment concurrency", "expected_impact": "Reduces CPU/memory saturation and timeout cascade", "priority": "high"},
            {"action": "Apply retry + timeout guardrails", "expected_impact": "Stops retry storms and stabilizes upstream dependencies", "priority": "high"},
            {"action": "Prioritize critical service/workflow lanes", "expected_impact": "Protects customer-facing paths during mitigation", "priority": "high"},
            {"action": "Scale critical serving path", "expected_impact": "Restores error budget and reduces p95 latency", "priority": "medium"},
            {"action": "Validate root cause from first failing evidence", "expected_impact": "Prevents treating symptoms only", "priority": "medium"},
            {"action": "Define rollback trigger (error rate/SLA threshold)", "expected_impact": "Faster safe decision if mitigation fails", "priority": "medium"},
            {"action": "Run compliance verification pass", "expected_impact": "Ensures no silent policy violations during mitigation", "priority": "medium"},
            {"action": "Confirm recovery across two cycles", "expected_impact": "Avoids premature close and recurrence", "priority": "low"},
        ]

        evidence: List[Dict[str, Any]] = []
        if latest_cycle:
            for a in latest_cycle.anomalies[:3]:
                evidence.append({
                    "id": a.anomaly_id,
                    "type": "anomaly",
                    "summary": a.description,
                    "confidence": a.confidence,
                    "agent": a.agent,
                })
            for h in latest_cycle.policy_hits[:2]:
                evidence.append({
                    "id": h.hit_id,
                    "type": "policy_hit",
                    "summary": h.description,
                    "confidence": 0.9,
                    "agent": h.agent,
                })
            for r in latest_cycle.risk_signals[:1]:
                evidence.append({
                    "id": r.signal_id,
                    "type": "risk_signal",
                    "summary": r.reasoning,
                    "confidence": r.confidence,
                    "agent": "RiskForecastAgent",
                })

        query_id = f"qry_{uuid.uuid4().hex[:8]}"
        result = QueryResult(
            query_id=query_id,
            original_query=user_query,
            answer=answer,
            why_it_matters=[
                "Fast containment reduces incident escalation probability.",
                "Retry/cap controls prevent cost and latency amplification.",
                "Compliance checks avoid introducing silent governance risk during hotfixes.",
            ],
            supporting_evidence=evidence,
            causal_chain=[
                {"label": "Load/latency pressure", "type": "cause"},
                {"label": "Workflow delay + errors", "type": "effect"},
                {"label": f"{projected_state} state", "type": "risk"},
                {"label": "Potential incident/customer impact", "type": "outcome"},
            ],
            recommended_actions=recs,
            confidence=0.86 if projected_state in ("VIOLATION", "INCIDENT") else 0.78,
            time_horizon="Next 15 minutes",
            uncertainty="Checklist is deterministic; validate against live telemetry each cycle.",
            query_type="ops_checklist",
            target_agents=["ResourceAgent", "WorkflowAgent", "ComplianceAgent", "RiskForecastAgent", "CausalAgent"],
            follow_up_queries=[
                "What should SDE team do in parallel?",
                "What is rollback decision criteria in next 15 minutes?",
                "Show me evidence for each checklist step.",
            ],
            timestamp=datetime.utcnow().isoformat(),
        )

        if state and state.current_cycle:
            try:
                state.add_hypothesis(
                    agent=self.AGENT_NAME,
                    claim=f"Ops checklist generated for {projected_state} impact {impact_score:.0f}",
                    evidence_ids=[e["id"] for e in evidence[:5]],
                    confidence=result.confidence,
                )
            except RuntimeError:
                pass

        return result

    def _query_via_crewai(
        self,
        user_query: str,
        state: Optional[SharedState] = None,
    ) -> Optional[QueryResult]:
        """
        Process query using CrewAI crew.
        Returns None on failure (caller falls back to RAG).
        """
        try:
            crew_output = self._crewai_crew.query(user_query)
            if not crew_output or not crew_output.get("answer"):
                return None

            query_id = f"qry_{uuid.uuid4().hex[:8]}"
            answer = crew_output["answer"]
            confidence = crew_output.get("confidence", 0.7)

            result = QueryResult(
                query_id=query_id,
                original_query=user_query,
                answer=answer,
                why_it_matters=crew_output.get("key_findings", []),
                supporting_evidence=[],  # CrewAI doesn't return structured evidence IDs
                causal_chain=[],
                recommended_actions=[
                    {"action": a, "expected_impact": "", "priority": "medium"}
                    for a in crew_output.get("recommended_actions", [])
                ],
                confidence=confidence,
                time_horizon="Current state",
                uncertainty="Analysis powered by CrewAI multi-agent reasoning",
                query_type="crewai",
                target_agents=["CrewAI-Retriever", "CrewAI-Synthesizer"],
                follow_up_queries=crew_output.get("follow_up_queries", []),
                timestamp=datetime.utcnow().isoformat(),
            )

            # Record on Blackboard
            if state and state.current_cycle:
                try:
                    state.add_hypothesis(
                        agent=self.AGENT_NAME,
                        claim=f"CrewAI answer: {answer[:200]}",
                        evidence_ids=[],
                        confidence=confidence,
                    )
                except RuntimeError:
                    pass

            logger.info("CrewAI query completed successfully (confidence: %.2f)", confidence)
            return result

        except Exception as e:
            logger.warning("CrewAI query failed: %s", e)
            return None

    def _query_via_rag(
        self,
        user_query: str,
        state: Optional[SharedState] = None,
    ) -> QueryResult:
        """Process query using the pattern-matching RAG engine (original logic)."""
        # 1. Use the existing RAG engine for core reasoning
        #rag_response: RAGResponse = self._rag_engine.query(user_query)
        rag_response= None
        # 2. Enrich with "why it matters" and causal chain
        why_it_matters = self._derive_why_it_matters(rag_response)
        causal_chain = self._derive_causal_chain(rag_response)
        recommended_actions = self._derive_recommendations(rag_response)
        follow_ups = self._generate_follow_ups(rag_response)
        time_horizon = self._estimate_time_horizon(rag_response)

        # 3. Build result
        query_id = f"qry_{uuid.uuid4().hex[:8]}"
        result = QueryResult(
            query_id=query_id,
            original_query=user_query,
            answer=rag_response.answer,
            why_it_matters=why_it_matters,
            supporting_evidence=[
                asdict(e) for e in rag_response.evidence_details
            ],
            causal_chain=causal_chain,
            recommended_actions=recommended_actions,
            confidence=rag_response.confidence,
            time_horizon=time_horizon,
            uncertainty=rag_response.uncertainty,
            query_type=rag_response.query_decomposition.get("query_type", "general"),
            target_agents=rag_response.query_decomposition.get("target_agents", []),
            follow_up_queries=follow_ups,
            timestamp=datetime.utcnow().isoformat(),
        )

        # 4. Record on Blackboard if cycle is active
        if state and state.current_cycle:
            try:
                state.add_hypothesis(
                    agent=self.AGENT_NAME,
                    claim=f"Query answer: {rag_response.answer[:200]}",
                    evidence_ids=rag_response.supporting_evidence,
                    confidence=rag_response.confidence,
                )
            except RuntimeError:
                pass  # No active cycle — skip

        return result

    # ──────────────────────────────────────────────────────────────
    # Enrichment helpers
    # ──────────────────────────────────────────────────────────────

    def _derive_why_it_matters(self, resp: RAGResponse) -> List[str]:
        """Derive business-impact bullets from evidence."""
        matters: List[str] = []
        for e in resp.evidence_details:
            if e.type == "risk_signal":
                matters.append(f"Risk trajectory indicates: {e.summary}")
            elif e.type == "policy_hit":
                matters.append(f"Compliance exposure: {e.summary}")
            elif e.type == "anomaly" and e.confidence > 0.8:
                matters.append(f"High-confidence anomaly: {e.summary}")
            elif e.type == "causal_link":
                matters.append(f"Causal relationship: {e.summary}")

        if not matters:
            matters.append("System is operating within normal parameters.")

        return matters[:5]

    def _derive_causal_chain(self, resp: RAGResponse) -> List[Dict[str, str]]:
        """Extract causal chain from evidence."""
        chain: List[Dict[str, str]] = []
        for e in resp.evidence_details:
            if e.type == "causal_link" and "→" in e.summary:
                parts = e.summary.split("→")
                if len(parts) >= 2:
                    chain.append({
                        "label": parts[0].strip(),
                        "type": "cause",
                    })
                    chain.append({
                        "label": parts[1].split(":")[0].strip(),
                        "type": "effect",
                    })

        # Deduplicate
        seen = set()
        unique_chain = []
        for item in chain:
            key = item["label"]
            if key not in seen:
                seen.add(key)
                unique_chain.append(item)

        return unique_chain

    def _derive_recommendations(self, resp: RAGResponse) -> List[Dict[str, str]]:
        """Derive actionable recommendations from state."""
        recs: List[Dict[str, str]] = []
        state = self._rag_engine._state

        for cycle in state._completed_cycles[-3:]:
            for rec2 in cycle.recommendations_v2:
                priority = "high" if rec2.severity_score >= 8.5 else "medium" if rec2.severity_score >= 7 else "low"
                recs.append({
                    "action": rec2.action_description,
                    "expected_impact": rec2.expected_effect,
                    "priority": priority,
                })
            for rec in cycle.recommendations:
                recs.append({
                    "action": rec.action,
                    "expected_impact": rec.rationale,
                    "priority": rec.urgency.lower(),
                })

        # Deduplicate by action + impact so stepwise actions are preserved.
        seen = set()
        unique = []
        for r in recs:
            key = (r["action"], r["expected_impact"])
            if key not in seen:
                seen.add(key)
                unique.append(r)

        return unique[:12]

    def _generate_follow_ups(self, resp: RAGResponse) -> List[str]:
        """Generate contextual follow-up question suggestions."""
        qt = resp.query_decomposition.get("query_type", "general")

        follow_ups_map = {
            "risk_status": [
                "What is causing the risk to increase?",
                "Which workflows are most affected?",
                "What happens if we do nothing?",
            ],
            "causal_analysis": [
                "What is the root cause?",
                "Which resources are involved?",
                "Show the full evidence chain",
            ],
            "compliance_check": [
                "Show all active violations",
                "Which policies are most at risk?",
                "What corrective actions are recommended?",
            ],
            "workflow_health": [
                "Which step is causing the delay?",
                "Is this affecting compliance?",
                "Show the workflow timeline",
            ],
            "resource_status": [
                "Is this a spike or a trend?",
                "Which workflows depend on this resource?",
                "What is the cost impact?",
            ],
            "prediction": [
                "What is the confidence level?",
                "What preventive actions exist?",
                "Show historical patterns",
            ],
        }
        return follow_ups_map.get(qt, [
            "What requires immediate attention?",
            "Show me the full system status",
            "What are the active risks?",
        ])

    def _estimate_time_horizon(self, resp: RAGResponse) -> str:
        """Estimate time horizon from risk signals."""
        for e in resp.evidence_details:
            if e.type == "risk_signal":
                return "10–15 minutes"
        return "Current state"
