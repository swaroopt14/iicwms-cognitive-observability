"""
IICWMS Agentic RAG Query Engine
===============================
Dynamic, evidence-backed query engine for Chronos.

Goals:
- Answer broad workflow/system/compliance/risk questions from current state
- Avoid static canned responses
- Keep outputs auditable (all claims trace to evidence IDs)
- Optionally run through LangGraph orchestration when available
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from blackboard import ReasoningCycle, SharedState, get_shared_state
from observation import ObservationLayer, get_observation_layer

try:
    from .vector_store import ChronosVectorStore
except ModuleNotFoundError:
    ChronosVectorStore = None

try:
    from langgraph.graph import END, StateGraph
except ModuleNotFoundError:
    StateGraph = None
    END = None


# Policy definitions are kept here to avoid import cycles.
POLICIES: Dict[str, Dict[str, str]] = {
    "SECURITY_POLICY_001": {
        "name": "Unauthorized Access Prevention",
        "description": "No direct access to production databases from development environments",
        "severity": "HIGH",
    },
    "WORKFLOW_POLICY_002": {
        "name": "Deployment Sequence Validation",
        "description": "All deployment steps must execute in correct order",
        "severity": "MEDIUM",
    },
    "RESOURCE_POLICY_003": {
        "name": "Resource Utilization Limits",
        "description": "CPU usage must not exceed 90% for sustained periods",
        "severity": "MEDIUM",
    },
    "COMPLIANCE_POLICY_004": {
        "name": "Audit Trail Maintenance",
        "description": "All system changes must have audit trail entries",
        "severity": "LOW",
    },
    "DATA_POLICY_005": {
        "name": "Data Retention Compliance",
        "description": "Logs must be retained for minimum 90 days",
        "severity": "LOW",
    },
}


class QueryType(Enum):
    RISK_STATUS = "risk_status"
    CAUSAL_ANALYSIS = "causal_analysis"
    COMPLIANCE_CHECK = "compliance_check"
    WORKFLOW_HEALTH = "workflow_health"
    RESOURCE_STATUS = "resource_status"
    PREDICTION = "prediction"
    GENERAL = "general"


@dataclass
class QueryDecomposition:
    original_query: str
    query_type: QueryType
    sub_queries: List[str]
    target_agents: List[str]
    keywords: List[str]


@dataclass
class Evidence:
    id: str
    type: str
    source_agent: str
    summary: str
    confidence: float
    timestamp: str


@dataclass
class RAGResponse:
    answer: str
    supporting_evidence: List[str]
    evidence_details: List[Evidence]
    confidence: float
    uncertainty: str
    query_decomposition: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "supporting_evidence": self.supporting_evidence,
            "evidence_details": [asdict(e) for e in self.evidence_details],
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "query_decomposition": self.query_decomposition,
        }


class QueryDecomposerAgent:
    PATTERNS: Dict[QueryType, List[str]] = {
        QueryType.RISK_STATUS: [
            r"\brisk\b",
            r"\bunsafe\b",
            r"\bdanger\b",
            r"\bincident\b",
            r"\bhealth\b",
            r"\bstatus\b",
        ],
        QueryType.CAUSAL_ANALYSIS: [
            r"\bwhy\b",
            r"\bcause\b",
            r"\broot\b",
            r"\breason\b",
            r"\bdue to\b",
            r"\bwhat happened\b",
        ],
        QueryType.COMPLIANCE_CHECK: [
            r"\bcompliance\b",
            r"\bpolicy\b",
            r"\baudit\b",
            r"\bviolation\b",
            r"\bsox\b",
            r"\bgdpr\b",
            r"\brule\b",
        ],
        QueryType.WORKFLOW_HEALTH: [
            r"\bworkflow\b",
            r"\bdeploy\b",
            r"\bpipeline\b",
            r"\bstep\b",
            r"\bsla\b",
            r"\bonboarding\b",
            r"\bjob\b",
        ],
        QueryType.RESOURCE_STATUS: [
            r"\bcpu\b",
            r"\bmemory\b",
            r"\bnetwork\b",
            r"\blatency\b",
            r"\bresource\b",
            r"\bcapacity\b",
            r"\butilization\b",
            r"\bpod\b",
            r"\bnode\b",
        ],
        QueryType.PREDICTION: [
            r"\bpredict\b",
            r"\bforecast\b",
            r"\bnext\b",
            r"\bfuture\b",
            r"\bwhat if\b",
            r"\btrajectory\b",
            r"\bwill\b",
        ],
    }

    AGENT_MAPPING: Dict[QueryType, List[str]] = {
        QueryType.RISK_STATUS: ["RiskForecastAgent", "MasterAgent"],
        QueryType.CAUSAL_ANALYSIS: ["CausalAgent", "WorkflowAgent", "ResourceAgent"],
        QueryType.COMPLIANCE_CHECK: ["ComplianceAgent", "RiskForecastAgent"],
        QueryType.WORKFLOW_HEALTH: ["WorkflowAgent", "CausalAgent"],
        QueryType.RESOURCE_STATUS: ["ResourceAgent", "AdaptiveBaselineAgent"],
        QueryType.PREDICTION: ["RiskForecastAgent", "CausalAgent", "ScenarioInjectionAgent"],
        QueryType.GENERAL: ["MasterAgent", "QueryAgent"],
    }

    def decompose(self, query: str) -> QueryDecomposition:
        q = (query or "").strip()
        q_lower = q.lower()
        query_type = self._detect_query_type(q_lower)
        keywords = self._extract_keywords(q_lower)
        sub_queries = self._generate_sub_queries(query_type, keywords)
        target_agents = self.AGENT_MAPPING.get(query_type, ["MasterAgent"])
        return QueryDecomposition(
            original_query=q,
            query_type=query_type,
            sub_queries=sub_queries,
            target_agents=target_agents,
            keywords=keywords,
        )

    def _detect_query_type(self, query: str) -> QueryType:
        best_type = QueryType.GENERAL
        best_score = 0
        for qtype, patterns in self.PATTERNS.items():
            score = 0
            for pat in patterns:
                if re.search(pat, query):
                    score += 1
            if score > best_score:
                best_score = score
                best_type = qtype
        return best_type

    def _extract_keywords(self, query: str) -> List[str]:
        words = re.findall(r"[a-zA-Z0-9_]{3,}", query.lower())
        stop = {
            "what", "why", "when", "where", "which", "show", "tell", "about", "with", "from",
            "that", "this", "then", "than", "there", "their", "your", "have", "will", "should",
            "could", "would", "please", "into", "over", "under", "across", "current", "latest",
            "issue", "issues", "system", "workflow", "resource", "compliance", "risk",
        }
        unique: List[str] = []
        for w in words:
            if w in stop:
                continue
            if w not in unique:
                unique.append(w)
        return unique[:12]

    def _generate_sub_queries(self, query_type: QueryType, keywords: List[str]) -> List[str]:
        focus = ", ".join(keywords[:4]) if keywords else "latest cycle"
        common = [
            f"Top findings related to {focus}",
            "Most relevant evidence IDs and confidence",
        ]
        if query_type == QueryType.CAUSAL_ANALYSIS:
            return common + ["Likely cause-effect chain", "Immediate mitigation sequence"]
        if query_type == QueryType.COMPLIANCE_CHECK:
            return common + ["Active policy hits", "Compliance risk and remediation"]
        if query_type == QueryType.WORKFLOW_HEALTH:
            return common + ["Delayed/failed workflow steps", "Downstream impact"]
        if query_type == QueryType.RESOURCE_STATUS:
            return common + ["Sustained resource anomalies", "Capacity or latency hotspots"]
        if query_type == QueryType.PREDICTION:
            return common + ["Projected state trajectory", "Preventive actions in next 15 minutes"]
        if query_type == QueryType.RISK_STATUS:
            return common + ["Current risk posture", "Top drivers and next actions"]
        return common + ["Overall platform status", "Priority action checklist"]


class ReasoningSynthesizer:
    def __init__(self, state: SharedState, observation: ObservationLayer):
        self._state = state
        self._observation = observation
        enable_vector = os.getenv("ENABLE_VECTOR_STORE", "false").lower().strip() == "true"
        self._vector_store = ChronosVectorStore() if (ChronosVectorStore and enable_vector) else None

    def retrieve_evidence(
        self,
        decomposition: QueryDecomposition,
        cycles: List[ReasoningCycle],
        max_items: int = 18,
    ) -> List[Evidence]:
        query_text = " ".join([decomposition.original_query] + decomposition.sub_queries).lower()
        gathered: List[Tuple[float, Evidence]] = []
        seen_ids: set[str] = set()

        # Optional semantic retrieval first.
        if self._vector_store:
            try:
                vector_hits = self._vector_store.semantic_search(query_text, n_results=12)
                for hit in vector_hits:
                    meta = hit.get("metadata", {})
                    ev = Evidence(
                        id=str(hit.get("id", f"vec_{len(gathered)}")),
                        type=str(meta.get("type", "vector")),
                        source_agent=str(meta.get("agent", "VectorStore")),
                        summary=str(hit.get("content", "")),
                        confidence=float(meta.get("confidence", 0.75)),
                        timestamp=str(meta.get("timestamp", datetime.utcnow().isoformat())),
                    )
                    score = self._relevance_score(ev.summary, query_text, ev.type, decomposition.query_type)
                    gathered.append((score + 0.3, ev))
                    seen_ids.add(ev.id)
            except Exception:
                pass

        # Deterministic retrieval from latest cycles.
        for cycle in cycles[-12:]:
            for a in cycle.anomalies:
                self._add(
                    gathered,
                    seen_ids,
                    Evidence(
                        id=a.anomaly_id,
                        type="anomaly",
                        source_agent=a.agent,
                        summary=a.description,
                        confidence=float(a.confidence),
                        timestamp=a.timestamp.isoformat(),
                    ),
                    query_text,
                    decomposition.query_type,
                )
            for p in cycle.policy_hits:
                self._add(
                    gathered,
                    seen_ids,
                    Evidence(
                        id=p.hit_id,
                        type="policy_hit",
                        source_agent=p.agent,
                        summary=p.description,
                        confidence=0.92,
                        timestamp=p.timestamp.isoformat(),
                    ),
                    query_text,
                    decomposition.query_type,
                )
            for r in cycle.risk_signals:
                self._add(
                    gathered,
                    seen_ids,
                    Evidence(
                        id=r.signal_id,
                        type="risk_signal",
                        source_agent="RiskForecastAgent",
                        summary=r.reasoning,
                        confidence=float(r.confidence),
                        timestamp=r.timestamp.isoformat(),
                    ),
                    query_text,
                    decomposition.query_type,
                )
            for c in cycle.causal_links:
                self._add(
                    gathered,
                    seen_ids,
                    Evidence(
                        id=c.link_id,
                        type="causal_link",
                        source_agent="CausalAgent",
                        summary=f"{c.cause} → {c.effect}: {c.reasoning}",
                        confidence=float(c.confidence),
                        timestamp=c.timestamp.isoformat(),
                    ),
                    query_text,
                    decomposition.query_type,
                )
            for rec2 in cycle.recommendations_v2:
                self._add(
                    gathered,
                    seen_ids,
                    Evidence(
                        id=rec2.rec_id,
                        type="recommendation",
                        source_agent="RecommendationEngineAgent",
                        summary=f"{rec2.action_code}: {rec2.action_description}",
                        confidence=float(rec2.confidence),
                        timestamp=rec2.timestamp.isoformat(),
                    ),
                    query_text,
                    decomposition.query_type,
                )

        # If still sparse, add recent raw observations.
        if len(gathered) < 6:
            events = self._observation.get_recent_events(count=50)
            metrics = self._observation.get_recent_metrics(count=50)
            for e in events:
                ev = Evidence(
                    id=e.event_id,
                    type="event",
                    source_agent="ObservationLayer",
                    summary=f"{e.type} actor={e.actor} workflow={e.workflow_id or 'n/a'} resource={e.resource or 'n/a'}",
                    confidence=0.7,
                    timestamp=e.timestamp.isoformat(),
                )
                self._add(gathered, seen_ids, ev, query_text, decomposition.query_type)
            for m in metrics:
                ev = Evidence(
                    id=f"metric_{m.resource_id}_{m.metric}_{int(m.timestamp.timestamp())}",
                    type="metric",
                    source_agent="ObservationLayer",
                    summary=f"{m.resource_id} {m.metric}={m.value}",
                    confidence=0.7,
                    timestamp=m.timestamp.isoformat(),
                )
                self._add(gathered, seen_ids, ev, query_text, decomposition.query_type)

        if not gathered:
            return []

        gathered.sort(key=lambda x: x[0], reverse=True)
        return [ev for _, ev in gathered[:max_items]]

    def _add(
        self,
        gathered: List[Tuple[float, Evidence]],
        seen_ids: set[str],
        evidence: Evidence,
        query_text: str,
        query_type: QueryType,
    ) -> None:
        if evidence.id in seen_ids:
            return
        score = self._relevance_score(evidence.summary, query_text, evidence.type, query_type)
        # keep weak signals only if we have very little.
        if score < 0.05 and len(gathered) > 10:
            return
        seen_ids.add(evidence.id)
        gathered.append((score, evidence))

    def _relevance_score(self, text: str, query: str, ev_type: str, qtype: QueryType) -> float:
        t_words = set(re.findall(r"[a-zA-Z0-9_]{3,}", (text or "").lower()))
        q_words = set(re.findall(r"[a-zA-Z0-9_]{3,}", (query or "").lower()))
        overlap = len(t_words.intersection(q_words))
        union = max(1, len(q_words))
        base = overlap / union

        type_bonus = 0.0
        if qtype == QueryType.CAUSAL_ANALYSIS and ev_type == "causal_link":
            type_bonus += 0.45
        if qtype == QueryType.COMPLIANCE_CHECK and ev_type == "policy_hit":
            type_bonus += 0.45
        if qtype == QueryType.RISK_STATUS and ev_type == "risk_signal":
            type_bonus += 0.4
        if qtype == QueryType.WORKFLOW_HEALTH and ev_type == "anomaly":
            type_bonus += 0.3
        if qtype == QueryType.RESOURCE_STATUS and ev_type in {"anomaly", "metric"}:
            type_bonus += 0.25
        if ev_type == "recommendation":
            type_bonus += 0.1
        return min(1.0, base + type_bonus)

    def synthesize_answer(
        self,
        decomposition: QueryDecomposition,
        evidence: List[Evidence],
        cycles: List[ReasoningCycle],
    ) -> str:
        if not evidence and not cycles:
            return "No data available yet. Run one analysis cycle or simulation, then ask again."

        qtype = decomposition.query_type
        if qtype == QueryType.RISK_STATUS:
            return self._risk_answer(evidence, cycles)
        if qtype == QueryType.CAUSAL_ANALYSIS:
            return self._causal_answer(evidence)
        if qtype == QueryType.COMPLIANCE_CHECK:
            return self._compliance_answer(evidence)
        if qtype == QueryType.WORKFLOW_HEALTH:
            return self._workflow_answer(evidence)
        if qtype == QueryType.RESOURCE_STATUS:
            return self._resource_answer(evidence)
        if qtype == QueryType.PREDICTION:
            return self._prediction_answer(evidence)
        return self._general_answer(evidence, cycles)

    def _risk_answer(self, evidence: List[Evidence], cycles: List[ReasoningCycle]) -> str:
        risks = [e for e in evidence if e.type == "risk_signal"]
        anoms = [e for e in evidence if e.type == "anomaly"][:3]
        policies = [e for e in evidence if e.type == "policy_hit"][:2]
        if not risks and not anoms:
            return "Current risk appears controlled. No high-priority risk signals in the latest evidence."
        lead = risks[0].summary if risks else "Risk is elevated due to active anomaly signals."
        details: List[str] = []
        if anoms:
            details.append("Top anomalies: " + " | ".join(a.summary for a in anoms))
        if policies:
            details.append("Policy exposure: " + " | ".join(p.summary for p in policies))
        details.append(
            "Next 15 minutes: contain blast radius, stabilize critical path, verify trend is improving."
        )
        return f"{lead} " + " ".join(details)

    def _causal_answer(self, evidence: List[Evidence]) -> str:
        causal = [e for e in evidence if e.type == "causal_link"][:4]
        if not causal:
            return "No strong cause-effect chain found yet in current window. Run another cycle for clearer causality."
        chain = []
        seen = set()
        for c in causal:
            rel = c.summary.split(":")[0].strip()
            if rel not in seen:
                seen.add(rel)
                chain.append(rel)
        return (
            f"Most likely chain: {' | '.join(chain)}. "
            "Recommended flow: contain now, fix upstream cause, verify downstream recovery."
        )

    def _compliance_answer(self, evidence: List[Evidence]) -> str:
        hits = [e for e in evidence if e.type == "policy_hit"]
        if not hits:
            return f"No active policy violations in top evidence. Monitored policy set size: {len(POLICIES)}."
        return (
            f"{len(hits)} compliance finding(s) in current window. Primary: {hits[0].summary}. "
            "Checklist: stop violating path, restore approval/least-privilege controls, re-verify in next cycle."
        )

    def _workflow_answer(self, evidence: List[Evidence]) -> str:
        wf = [e for e in evidence if "workflow" in e.summary.lower() or "deploy" in e.summary.lower()]
        if not wf:
            return "No critical workflow degradations detected in top evidence."
        return (
            f"Workflow risk detected: {wf[0].summary}. "
            "Focus on delayed/failed steps first, then remove the upstream bottleneck before replay."
        )

    def _resource_answer(self, evidence: List[Evidence]) -> str:
        res = [e for e in evidence if any(k in e.summary.lower() for k in ("cpu", "memory", "latency", "network", "resource"))]
        if not res:
            return "Resource usage appears within acceptable operating range in current evidence."
        top = " | ".join(x.summary for x in res[:2])
        return f"Resource pressure detected: {top}. Stabilize utilization and cap retry amplification."

    def _prediction_answer(self, evidence: List[Evidence]) -> str:
        risks = [e for e in evidence if e.type == "risk_signal"]
        if not risks:
            return "No strong deterioration trajectory found. Continue monitoring with scenario checks."
        return (
            f"Projected trajectory signal: {risks[0].summary}. "
            "Preventive action: apply containment and validation checklist before next deploy window."
        )

    def _general_answer(self, evidence: List[Evidence], cycles: List[ReasoningCycle]) -> str:
        if not cycles:
            return "System is initializing. No completed reasoning cycles yet."
        latest = cycles[-1]
        top: List[Evidence] = []
        seen = set()
        for e in evidence:
            key = (e.type, e.summary.strip().lower())
            if key in seen:
                continue
            seen.add(key)
            top.append(e)
            if len(top) >= 3:
                break
        top_txt = " | ".join(e.summary for e in top) if top else "No high-signal evidence ranked yet."
        return (
            f"Latest cycle summary: {len(latest.anomalies)} anomalies, {len(latest.policy_hits)} policy hits, "
            f"{len(latest.risk_signals)} risk signals. Top evidence: {top_txt}"
        )


class AgenticRAGEngine:
    """Dynamic RAG engine with optional LangGraph orchestration."""

    def __init__(
        self,
        state: Optional[SharedState] = None,
        observation: Optional[ObservationLayer] = None,
    ):
        self._state = state or get_shared_state()
        self._observation = observation or get_observation_layer()
        self._decomposer = QueryDecomposerAgent()
        self._synthesizer = ReasoningSynthesizer(self._state, self._observation)
        enable_vector = os.getenv("ENABLE_VECTOR_STORE", "false").lower().strip() == "true"
        self._vector_store = ChronosVectorStore() if (ChronosVectorStore and enable_vector) else None
        self._use_langgraph = (
            os.getenv("ENABLE_LANGGRAPH", "false").lower().strip() == "true"
            and StateGraph is not None
        )
        self._langgraph = self._build_langgraph() if self._use_langgraph else None

    def _build_langgraph(self):
        if StateGraph is None or END is None:
            return None
        graph = StateGraph(dict)

        def node_decompose(state: Dict[str, Any]) -> Dict[str, Any]:
            decomp = self._decomposer.decompose(state["query_text"])
            state["decomposition"] = decomp
            return state

        def node_retrieve(state: Dict[str, Any]) -> Dict[str, Any]:
            cycles = self._state.get_recent_cycles(count=12)
            evidence = self._synthesizer.retrieve_evidence(state["decomposition"], cycles)
            state["cycles"] = cycles
            state["evidence"] = evidence
            return state

        def node_synthesize(state: Dict[str, Any]) -> Dict[str, Any]:
            answer = self._synthesizer.synthesize_answer(
                state["decomposition"], state.get("evidence", []), state.get("cycles", [])
            )
            state["answer"] = answer
            return state

        graph.add_node("decompose", node_decompose)
        graph.add_node("retrieve", node_retrieve)
        graph.add_node("synthesize", node_synthesize)
        graph.set_entry_point("decompose")
        graph.add_edge("decompose", "retrieve")
        graph.add_edge("retrieve", "synthesize")
        graph.add_edge("synthesize", END)
        return graph.compile()

    def query(self, query_text: str) -> RAGResponse:
        q = (query_text or "").strip()
        if not q:
            q = "system status"

        if self._langgraph is not None:
            try:
                state = self._langgraph.invoke({"query_text": q})
                decomposition: QueryDecomposition = state["decomposition"]
                evidence: List[Evidence] = state.get("evidence", [])
                answer: str = state.get("answer", "")
                cycles = state.get("cycles", [])
                return self._build_response(q, decomposition, evidence, answer, cycles, used_langgraph=True)
            except Exception:
                # Fall back to deterministic pipeline if LangGraph path fails.
                pass

        decomposition = self._decomposer.decompose(q)
        cycles = self._state.get_recent_cycles(count=12)
        evidence = self._synthesizer.retrieve_evidence(decomposition, cycles)
        answer = self._synthesizer.synthesize_answer(decomposition, evidence, cycles)
        return self._build_response(q, decomposition, evidence, answer, cycles, used_langgraph=False)

    def _build_response(
        self,
        query_text: str,
        decomposition: QueryDecomposition,
        evidence: List[Evidence],
        answer: str,
        cycles: List[ReasoningCycle],
        used_langgraph: bool,
    ) -> RAGResponse:
        confidence = self._calculate_confidence(evidence)
        uncertainty = self._estimate_uncertainty(evidence, cycles)
        return RAGResponse(
            answer=answer,
            supporting_evidence=[e.id for e in evidence],
            evidence_details=evidence,
            confidence=confidence,
            uncertainty=uncertainty,
            query_decomposition={
                "query_type": decomposition.query_type.value,
                "type": decomposition.query_type.value,
                "sub_queries": decomposition.sub_queries,
                "target_agents": decomposition.target_agents,
                "keywords": decomposition.keywords,
                "orchestrator": "langgraph" if used_langgraph else "deterministic",
                "original_query": query_text,
            },
        )

    def _calculate_confidence(self, evidence: List[Evidence]) -> float:
        if not evidence:
            return 0.0
        scores = [max(0.0, min(1.0, float(e.confidence))) for e in evidence[:10]]
        avg = sum(scores) / len(scores)
        # Evidence volume bonus capped.
        bonus = min(0.08, 0.01 * max(0, len(evidence) - 3))
        return round(min(1.0, avg + bonus), 4)

    def _estimate_uncertainty(self, evidence: List[Evidence], cycles: List[ReasoningCycle]) -> str:
        if not cycles:
            return "High"
        if len(evidence) >= 10:
            return "Low"
        if len(evidence) >= 5:
            return "Medium"
        return "High"


def get_rag_engine() -> AgenticRAGEngine:
    """Compatibility singleton accessor used by existing agents."""
    if not hasattr(get_rag_engine, "_instance"):
        get_rag_engine._instance = AgenticRAGEngine()
    return get_rag_engine._instance
