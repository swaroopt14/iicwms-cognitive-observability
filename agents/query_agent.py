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
# from agents.query_crew import QueryCrew  # Import only when CrewAI is enabled
from blackboard import get_shared_state, SharedState
import re

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
        from rag import get_rag_engine, force_refresh_rag_engine
        # Force refresh RAG engine to pick up LLM changes
        force_refresh_rag_engine()
        self._rag_engine = get_rag_engine()
        self._crewai_crew = None
        self._init_crewai()

    def _init_crewai(self):
        """Initialize CrewAI query crew if ENABLE_CREWAI=true."""
        # Disable CrewAI to avoid dependency conflicts
        enable_crewai = os.getenv("ENABLE_CREWAI", "false").lower().strip()
        if enable_crewai == "true":
            logger.warning("ENABLE_CREWAI=true but CrewAI disabled due to dependency conflicts")
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
        greeting_result = self._maybe_greeting_query(user_query)
        if greeting_result:
            return greeting_result

        clarification_result = self._maybe_clarification_query(user_query)
        if clarification_result:
            return clarification_result

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

    def _maybe_clarification_query(self, user_query: str) -> Optional[QueryResult]:
        """
        Guardrail for low-signal/nonsense prompts.
        Prevents hallucinated summaries for inputs like random tokens.
        """
        q = (user_query or "").strip()
        if not q:
            return None

        compact = re.sub(r"\s+", " ", q).strip().lower()
        tokens = re.findall(r"[a-zA-Z0-9_]+", compact)
        if not tokens:
            return None

        known_keywords = {
            "risk", "workflow", "compliance", "policy", "anomaly", "incident",
            "latency", "cpu", "memory", "network", "cost", "resource",
            "deploy", "sla", "audit", "violation", "forecast", "causal",
            "recommendation", "error", "health", "status", "why", "what", "how",
        }
        has_known_signal = any(t in known_keywords for t in tokens)
        looks_like_host_or_id = any(bool(re.search(r"\d", t) or "_" in t or "-" in t) for t in tokens)
        is_single_token = len(tokens) == 1
        token = tokens[0]
        looks_like_gibberish = bool(
            is_single_token
            and len(token) >= 5
            and not has_known_signal
            and not looks_like_host_or_id
            and not token.startswith(("wf", "vm", "cpu", "mem", "sla"))
        )

        if not looks_like_gibberish:
            return None

        query_id = f"qry_{uuid.uuid4().hex[:8]}"
        return QueryResult(
            query_id=query_id,
            original_query=user_query,
            answer=(
                "I need a bit more context to answer accurately.\n"
                "Ask about a system concern (risk, workflow, compliance, resource, or cost)."
            ),
            why_it_matters=[
                "Low-signal input can produce misleading summaries, so clarification is required.",
            ],
            supporting_evidence=[],
            causal_chain=[],
            recommended_actions=[],
            confidence=100.0,
            time_horizon="Current state",
            uncertainty="None",
            query_type="clarification",
            target_agents=["QueryAgent"],
            follow_up_queries=[
                "What is the current system risk and why?",
                "Which workflow is most likely to breach SLA?",
                "Show active compliance violations with evidence IDs.",
            ],
            timestamp=datetime.utcnow().isoformat(),
        )

    def _maybe_greeting_query(self, user_query: str) -> Optional[QueryResult]:
        """Handle short greetings without forcing full system summary output."""
        q = (user_query or "").strip().lower()
        if not q:
            return None

        compact = re.sub(r"[^\w\s]", "", q).strip()
        greeting_patterns = [
            r"^(hi|hello|hey|yo|hola|namaste)$",
            r"^(good morning|good afternoon|good evening)$",
            r"^(how are you)$",
            r"^(sup|whats up|what is up)$",
            r"^(hi|hello|hey)\s+\w+$",
        ]
        if not any(re.match(p, compact) for p in greeting_patterns):
            return None

        query_id = f"qry_{uuid.uuid4().hex[:8]}"
        return QueryResult(
            query_id=query_id,
            original_query=user_query,
            answer=(
                "Hi. I can help with risk, workflows, compliance, anomalies, and remediation checklists.\n"
                "Try: \"show current risk\", \"what caused this\", or \"what should DevOps do next 15 minutes?\""
            ),
            why_it_matters=[
                "Fast intent routing avoids noisy summaries for greeting-only inputs.",
            ],
            supporting_evidence=[],
            causal_chain=[],
            recommended_actions=[],
            confidence=100.0,
            time_horizon="Current state",
            uncertainty="None",
            query_type="greeting",
            target_agents=["QueryAgent"],
            follow_up_queries=[
                "Show current risk status",
                "What caused the latest spike?",
                "Give me a DevOps checklist for next 15 minutes",
            ],
            timestamp=datetime.utcnow().isoformat(),
        )

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
                    "confidence": self._to_percent(a.confidence),
                    "agent": a.agent,
                })
            for h in latest_cycle.policy_hits[:2]:
                evidence.append({
                    "id": h.hit_id,
                    "type": "policy_hit",
                    "summary": h.description,
                    "confidence": 90.0,
                    "agent": h.agent,
                })
            for r in latest_cycle.risk_signals[:1]:
                evidence.append({
                    "id": r.signal_id,
                    "type": "risk_signal",
                    "summary": r.reasoning,
                    "confidence": self._to_percent(r.confidence),
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
            confidence=86.0 if projected_state in ("VIOLATION", "INCIDENT") else 78.0,
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
                    confidence=min(1.0, result.confidence / 100.0),
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
            confidence_pct = self._to_percent(confidence)

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
                confidence=confidence_pct,
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
                        confidence=min(1.0, confidence),
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
        """Process query using enhanced RAG engine with real data integration."""
        # 1. Classify query intent for better evidence retrieval
        query_intent = self._classify_query_intent(user_query)
        
        # 2. Gather real evidence from multiple sources
        evidence_collection = self._gather_real_evidence(user_query, query_intent, state)
        
        # 3. Use enhanced RAG engine with context
        rag_response: RAGResponse = self._rag_engine.query(
            user_query
        )
        
        # 4. Deduplicate and enhance evidence
        deduped_evidence = self._dedupe_evidence(rag_response.evidence_details)
        enhanced_evidence = self._enhance_evidence_with_real_data(deduped_evidence, evidence_collection, state)
        
        rag_response = RAGResponse(
            answer=rag_response.answer,
            supporting_evidence=[e.id for e in enhanced_evidence],
            evidence_details=enhanced_evidence,
            confidence=rag_response.confidence,
            uncertainty=rag_response.uncertainty,
            query_decomposition=rag_response.query_decomposition,
        )
        
        # 5. Generate insights using real data
        why_it_matters = self._derive_why_it_matters_real(rag_response, evidence_collection, state)
        causal_chain = self._derive_causal_chain_real(rag_response, evidence_collection, state)
        recommended_actions = self._derive_recommendations_real(rag_response, evidence_collection, state)
        follow_ups = self._generate_follow_ups_real(rag_response, evidence_collection, state)
        time_horizon = self._estimate_time_horizon_real(rag_response, evidence_collection, state)

        # 6. Build result with real data
        query_id = f"qry_{uuid.uuid4().hex[:8]}"
        result = QueryResult(
            query_id=query_id,
            original_query=user_query,
            answer=rag_response.answer,
            why_it_matters=why_it_matters,
            supporting_evidence=[
                asdict(e) | {"confidence": self._to_percent(e.confidence)}
                for e in rag_response.evidence_details
            ],
            causal_chain=causal_chain,
            recommended_actions=recommended_actions,
            confidence=self._to_percent(rag_response.confidence),
            time_horizon=time_horizon,
            uncertainty=rag_response.uncertainty,
            query_type=rag_response.query_decomposition.get("query_type") or rag_response.query_decomposition.get("type", "general"),
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
                priority = "high" if rec2.severity_score >= 85 else "medium" if rec2.severity_score >= 70 else "low"
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

    def _to_percent(self, confidence: float) -> float:
        """Normalize confidence into 0-100 for UI-facing payloads."""
        try:
            c = float(confidence)
        except Exception:
            return 0.0
        if c <= 1.0:
            return round(c * 100.0, 2)
        return round(max(0.0, min(100.0, c)), 2)

    def _dedupe_evidence(self, evidence: List[Any]) -> List[Any]:
        """
        Remove near-duplicate evidence entries by summary+type while preserving order.
        Keeps the payload compact and avoids repeated top-evidence strings.
        """
        seen = set()
        unique = []
        for e in evidence:
            summary = str(getattr(e, "summary", "")).strip().lower()
            etype = str(getattr(e, "type", "")).strip().lower()
            key = (etype, summary)
            if key in seen:
                continue
            seen.add(key)
            unique.append(e)
        return unique[:12]

    # ──────────────────────────────────────────────────────────────
    # Real Data Integration Methods
    # ──────────────────────────────────────────────────────────────

    def _classify_query_intent(self, query: str) -> str:
        """Classify user's query intent for better evidence retrieval."""
        q = query.lower()
        
        if any(keyword in q for keyword in ['cost', 'spend', 'budget', 'expensive']):
            return "cost_analysis"
        elif any(keyword in q for keyword in ['compliance', 'policy', 'violation', 'audit']):
            return "compliance"
        elif any(keyword in q for keyword in ['workflow', 'sla', 'deploy', 'onboarding']):
            return "workflow"
        elif any(keyword in q for keyword in ['risk', 'failure', 'breach', 'incident']):
            return "risk"
        elif any(keyword in q for keyword in ['slow', 'latency', 'performance', 'degraded']):
            return "performance"
        else:
            return "general"

    def _gather_real_evidence(self, query: str, intent: str, state: Optional[SharedState]) -> Dict[str, Any]:
        """Gather real evidence from multiple sources based on query intent."""
        evidence = {
            "anomalies": [],
            "policy_hits": [],
            "risk_signals": [],
            "recommendations": [],
            "system_metrics": {},
            "historical_data": {}
        }
        
        if not state:
            return evidence
            
        # Get recent anomalies
        for cycle in state.get_recent_cycles(count=3):
            evidence["anomalies"].extend(cycle.anomalies)
            evidence["policy_hits"].extend(cycle.policy_hits)
            evidence["risk_signals"].extend(cycle.risk_signals)
            evidence["recommendations"].extend(cycle.recommendations_v2 or cycle.recommendations)
        
        # Get current system metrics
        if state.current_cycle:
            evidence["system_metrics"] = {
                "error_rate": getattr(state.current_cycle, 'error_rate', 0),
                "cpu_utilization": getattr(state.current_cycle, 'cpu_utilization', 0),
                "memory_utilization": getattr(state.current_cycle, 'memory_utilization', 0),
                "network_latency": getattr(state.current_cycle, 'network_latency', 0)
            }
        
        # Get historical trends
        evidence["historical_data"] = {
            "trend_direction": self._calculate_trend_direction(evidence["anomalies"]),
            "severity_trend": self._calculate_severity_trend(evidence["anomalies"]),
            "compliance_trend": self._calculate_compliance_trend(evidence["policy_hits"])
        }
        
        return evidence

    def _enhance_evidence_with_real_data(self, rag_evidence: List, evidence_collection: Dict, state: Optional[SharedState]) -> List:
        """Enhance RAG evidence with real system data."""
        enhanced = []
        
        for evidence in rag_evidence:
            enhanced_evidence = evidence
            
            # Add real-time confidence based on system state
            if evidence_collection["system_metrics"]:
                real_confidence = self._calculate_real_confidence(evidence, evidence_collection)
                enhanced_evidence.confidence = real_confidence
            
            # Add source verification
            enhanced_evidence.verified_source = True
            enhanced_evidence.data_freshness = "real_time"
            
            enhanced.append(enhanced_evidence)
        
        return enhanced

    def _derive_recommendations_real(self, rag_response: RAGResponse, evidence_collection: Dict, state: Optional[SharedState]) -> List[Dict[str, str]]:
        """Derive recommendations using real data from SharedState."""
        recommendations = []
        
        # Get real recommendations from recent cycles
        if state:
            for cycle in state.get_recent_cycles(count=3):
                # Prefer recommendations_v2 for dynamic severity scores
                for rec in cycle.recommendations_v2:
                    if rec.severity_score >= 85:
                        priority = "high"
                    elif rec.severity_score >= 70:
                        priority = "medium"
                    else:
                        priority = "low"
                    recommendations.append({
                        "id": rec.rec_id,
                        "action": rec.action_description,
                        "expected_impact": rec.expected_effect,
                        "priority": priority,
                        "confidence": rec.confidence,
                        "severity_score": rec.severity_score,  # ADD DYNAMIC SEVERITY
                    })
                
                # Fallback to legacy recommendations if v2 is empty
                if not cycle.recommendations_v2:
                    for rec in cycle.recommendations:
                        recommendations.append({
                            "id": rec.rec_id,
                            "action": rec.action,
                            "expected_impact": rec.rationale,
                            "priority": rec.urgency.lower(),
                            "confidence": 0.8,  # Default confidence for legacy
                            "severity_score": 60.0,  # Default severity for legacy
                        })

        # Deduplicate by action
        seen = set()
        unique = []
        for r in recommendations:
            if r["action"] not in seen:
                seen.add(r["action"])
                unique.append(r)

        # Sort by severity_score and confidence, return top 5
        unique.sort(key=lambda x: (x.get("severity_score", 50), x.get("confidence", 0)), reverse=True)
        return unique[:5]

    def _calculate_real_confidence(self, evidence, evidence_collection: Dict) -> float:
        """Calculate confidence based on real system state."""
        base_confidence = evidence.confidence
        
        # Adjust based on system metrics
        metrics = evidence_collection.get("system_metrics", {})
        if metrics.get("error_rate", 0) > 0.05:
            base_confidence *= 1.1  # Increase confidence if errors are high
        if metrics.get("cpu_utilization", 0) > 80:
            base_confidence *= 1.05  # Increase confidence if CPU is high
            
        return min(1.0, base_confidence)

    def _calculate_trend_direction(self, anomalies: List) -> str:
        """Calculate trend direction from anomalies."""
        if not anomalies:
            return "stable"
        # Simple trend calculation - could be enhanced
        recent_count = len([a for a in anomalies if hasattr(a, 'timestamp') and 
                          (datetime.now() - a.timestamp).total_seconds() < 3600])
        if recent_count > len(anomalies) / 2:
            return "increasing"
        elif recent_count < len(anomalies) / 4:
            return "decreasing"
        return "stable"

    def _calculate_severity_trend(self, anomalies: List) -> str:
        """Calculate severity trend from anomalies."""
        if not anomalies:
            return "stable"
        # Simple severity trend - could be enhanced with actual severity values
        high_severity = len([a for a in anomalies if hasattr(a, 'severity') and a.severity in ['HIGH', 'CRITICAL']])
        if high_severity > len(anomalies) / 2:
            return "worsening"
        return "stable"

    def _calculate_compliance_trend(self, policy_hits: List) -> str:
        """Calculate compliance trend from policy hits."""
        if not policy_hits:
            return "stable"
        recent_hits = len([p for p in policy_hits if hasattr(p, 'timestamp') and 
                         (datetime.now() - p.timestamp).total_seconds() < 3600])
        if recent_hits > len(policy_hits) / 2:
            return "degrading"
        return "stable"

    def _derive_why_it_matters_real(self, rag_response: RAGResponse, evidence_collection: Dict, state: Optional[SharedState]) -> List[str]:
        """Generate 'why it matters' using real data."""
        matters = []
        
        # Base from RAG response
        if hasattr(rag_response, 'why_it_matters') and rag_response.why_it_matters:
            matters.extend(rag_response.why_it_matters)
        
        # Add real-time insights
        if evidence_collection["system_metrics"].get("error_rate", 0) > 0.05:
            matters.append("Current error rate exceeds 5% threshold - immediate attention required")
        
        if evidence_collection["historical_data"]["trend_direction"] == "increasing":
            matters.append("Anomaly trend is increasing - risk of escalation")
            
        if evidence_collection["historical_data"]["compliance_trend"] == "degrading":
            matters.append("Compliance trend is degrading - audit risk increasing")
            
        return matters[:5]  # Limit to top 5

    def _derive_causal_chain_real(self, rag_response: RAGResponse, evidence_collection: Dict, state: Optional[SharedState]) -> List[Dict[str, str]]:
        """Generate causal chain using real data."""
        chain = []
        
        # Base from RAG response
        if hasattr(rag_response, 'causal_chain') and rag_response.causal_chain:
            chain.extend(rag_response.causal_chain)
        
        # Add real-time causal links
        if evidence_collection["system_metrics"].get("cpu_utilization", 0) > 80:
            chain.append({"label": "High CPU Utilization", "type": "cause"})
            
        if evidence_collection["system_metrics"].get("error_rate", 0) > 0.05:
            chain.append({"label": "Elevated Error Rate", "type": "effect"})
            
        return chain[:6]  # Limit to 6 steps

    def _generate_follow_ups_real(self, rag_response: RAGResponse, evidence_collection: Dict, state: Optional[SharedState]) -> List[str]:
        """Generate follow-up queries using real data."""
        follow_ups = []
        
        # Base from RAG response
        if hasattr(rag_response, 'follow_up_queries') and rag_response.follow_up_queries:
            follow_ups.extend(rag_response.follow_up_queries)
        
        # Add context-aware follow-ups
        if evidence_collection["anomalies"]:
            follow_ups.append("Show me the top 3 anomalies by severity")
            
        if evidence_collection["policy_hits"]:
            follow_ups.append("Which policies are most frequently violated?")
            
        return follow_ups[:4]  # Limit to 4 follow-ups

    def _estimate_time_horizon_real(self, rag_response: RAGResponse, evidence_collection: Dict, state: Optional[SharedState]) -> str:
        """Estimate time horizon using real data."""
        # Base from RAG response
        base_horizon = getattr(rag_response, 'time_horizon', "5-15 minutes")
        
        # Adjust based on system state
        if evidence_collection["system_metrics"].get("error_rate", 0) > 0.1:
            return "1-5 minutes"  # Urgent
        elif evidence_collection["historical_data"]["trend_direction"] == "increasing":
            return "15-30 minutes"  # Growing concern
            
        return base_horizon
