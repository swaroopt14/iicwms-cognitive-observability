"""
IICWMS Master Control Program (MCP) — The System Brain
========================================================
The MCP is the cognitive core of Chronos AI.

Unlike a simple orchestrator that just "runs agents in order", the MCP:

1. PERCEIVES   — Reads the environment (observations) and the reasoning state
2. DECIDES     — Chooses execution strategy based on system pulse
3. ORCHESTRATES — Runs agents in optimal order with adaptive parallelism
4. SYNTHESIZES — Merges findings, detects cross-agent patterns, ranks severity
5. RECOMMENDS  — Maps causes to actions with priority intelligence
6. LEARNS      — Tracks cycle-over-cycle trends to detect escalation/recovery

FORBIDDEN:
- No deep domain reasoning (delegates to specialized agents)
- No LLM usage (only Explanation Engine uses LLM)
- No auto-remediation (recommends only, humans decide)
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import concurrent.futures
import threading
import time

from observation import ObservationLayer, ObservedEvent, ObservedMetric
from blackboard import (
    SharedState, ReasoningCycle,
    Anomaly, PolicyHit, RiskSignal, CausalLink, Recommendation, RiskState
)
from .workflow_agent import WorkflowAgent
from .resource_agent import ResourceAgent
from .compliance_agent import ComplianceAgent
from .risk_forecast_agent import RiskForecastAgent
from .causal_agent import CausalAgent
from .adaptive_baseline_agent import AdaptiveBaselineAgent


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PULSE — The MCP's Situational Awareness
# ═══════════════════════════════════════════════════════════════════════════════

class SystemPulse(Enum):
    """System-wide operational state as perceived by the MCP."""
    CALM = "calm"                # No significant issues — standard scan
    ELEVATED = "elevated"        # Minor anomalies — increased vigilance
    STRESSED = "stressed"        # Multiple issues — full agent deployment
    CRITICAL = "critical"        # Cascading failures — emergency mode


@dataclass
class CycleDiagnostics:
    """Diagnostics from a completed reasoning cycle — MCP's memory."""
    cycle_id: str
    timestamp: datetime
    pulse: SystemPulse
    anomaly_count: int
    policy_hit_count: int
    risk_signal_count: int
    causal_link_count: int
    recommendation_count: int
    duration_ms: float
    severity_score: float           # 0-100 composite severity
    dominant_agent: Optional[str]    # Which agent found the most
    escalation_detected: bool        # Did risk escalate vs previous cycle?
    new_root_causes: int             # Causal links not seen before


@dataclass
class CycleResult:
    """Result of a reasoning cycle — returned to the API layer."""
    cycle_id: str
    anomaly_count: int
    policy_hit_count: int
    risk_signal_count: int
    causal_link_count: int
    recommendation_count: int
    duration_ms: float


# ═══════════════════════════════════════════════════════════════════════════════
# SOLUTION MAP — Actions are MAPPED, never invented
# ═══════════════════════════════════════════════════════════════════════════════

SOLUTION_MAP = {
    "SUSTAINED_RESOURCE_CRITICAL": {
        "action": "Throttle jobs or scale resources immediately",
        "urgency": "CRITICAL",
        "rationale": "Resource saturation causes cascading failures across dependent workflows"
    },
    "SUSTAINED_RESOURCE_WARNING": {
        "action": "Monitor closely, prepare scaling plan",
        "urgency": "MEDIUM",
        "rationale": "Early intervention prevents escalation to critical"
    },
    "RESOURCE_DRIFT": {
        "action": "Investigate root cause of resource growth",
        "urgency": "MEDIUM",
        "rationale": "Drift indicates potential memory leak or capacity shortfall"
    },
    "BASELINE_DEVIATION": {
        "action": "Investigate abnormal behavior pattern",
        "urgency": "MEDIUM",
        "rationale": "Deviation from learned baseline signals unexpected system change"
    },
    "WORKFLOW_DELAY": {
        "action": "Pre-notify stakeholders of SLA pressure",
        "urgency": "HIGH",
        "rationale": "Delays compound across dependent steps and affect SLA commitments"
    },
    "MISSING_STEP": {
        "action": "Apply temporary access guard and trigger audit",
        "urgency": "CRITICAL",
        "rationale": "Skipped steps bypass critical controls — governance risk"
    },
    "SEQUENCE_VIOLATION": {
        "action": "Review workflow execution and enforce step ordering",
        "urgency": "HIGH",
        "rationale": "Out-of-order execution indicates process breakdown"
    },
    "SILENT": {
        "action": "Flag for compliance review and escalate to governance",
        "urgency": "CRITICAL",
        "rationale": "Silent violations accumulate undetected audit risk"
    },
}

# Priority escalation: if causal chain links a root cause, boost urgency
ESCALATION_RULES = {
    ("SUSTAINED_RESOURCE_CRITICAL", "WORKFLOW_DELAY"): "CRITICAL",
    ("MISSING_STEP", "SILENT"): "CRITICAL",
    ("RESOURCE_DRIFT", "WORKFLOW_DELAY"): "HIGH",
    ("SEQUENCE_VIOLATION", "SILENT"): "CRITICAL",
}


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER CONTROL PROGRAM
# ═══════════════════════════════════════════════════════════════════════════════

class MasterAgent:
    """
    Master Control Program (MCP) — The Cognitive Brain of Chronos AI.

    The MCP doesn't just run agents sequentially. It:

    1. Reads the system pulse (calm/elevated/stressed/critical)
    2. Adapts its observation window based on pulse
    3. Runs detection agents in parallel with adaptive worker count
    4. Runs dependent agents (risk, causal) sequentially
    5. Cross-correlates findings to detect multi-agent patterns
    6. Ranks severity with composite scoring (not just count)
    7. Generates prioritized recommendations with escalation logic
    8. Tracks cycle-over-cycle trends for escalation detection
    9. Maintains diagnostics history for trend analysis

    If this loop breaks → system fails.
    """

    AGENT_NAME = "MasterAgent"

    # Observation window sizes based on system pulse
    _OBSERVATION_WINDOWS = {
        SystemPulse.CALM: {"events": 50, "metrics": 50},
        SystemPulse.ELEVATED: {"events": 100, "metrics": 100},
        SystemPulse.STRESSED: {"events": 200, "metrics": 200},
        SystemPulse.CRITICAL: {"events": 500, "metrics": 500},
    }

    # Worker pool sizes based on pulse
    _WORKER_POOLS = {
        SystemPulse.CALM: 2,
        SystemPulse.ELEVATED: 4,
        SystemPulse.STRESSED: 6,
        SystemPulse.CRITICAL: 8,
    }

    def __init__(
        self,
        observation: ObservationLayer,
        state: SharedState
    ):
        self._observation = observation
        self._state = state

        # Initialize specialized agents
        self._workflow_agent = WorkflowAgent()
        self._resource_agent = ResourceAgent()
        self._compliance_agent = ComplianceAgent()
        self._risk_forecast_agent = RiskForecastAgent()
        self._causal_agent = CausalAgent()
        self._adaptive_baseline_agent = AdaptiveBaselineAgent()

        # Neo4j graph client (lazy init)
        self._graph = None

        # MCP Brain State — cycle-over-cycle memory
        self._cycle_history: List[CycleDiagnostics] = []
        self._current_pulse = SystemPulse.CALM
        self._consecutive_critical = 0
        self._consecutive_calm = 0
        self._known_root_causes: set = set()
        self._total_cycles = 0
        self._last_cycle_time: Optional[datetime] = None

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 1: PERCEPTION — Read the system pulse
    # ─────────────────────────────────────────────────────────────────────────

    def _perceive_pulse(self) -> SystemPulse:
        """
        Determine the system's current operational pulse.

        Uses the MCP's memory of recent cycles to decide how aggressively
        to scan the environment. This is NOT a detection — it's the brain
        deciding how much attention to pay.
        """
        if not self._cycle_history:
            return SystemPulse.CALM

        recent = self._cycle_history[-5:]  # Last 5 cycles

        # Compute aggregate severity
        avg_severity = sum(d.severity_score for d in recent) / len(recent)
        max_severity = max(d.severity_score for d in recent)
        escalation_count = sum(1 for d in recent if d.escalation_detected)

        # Check for consecutive critical
        if self._consecutive_critical >= 3:
            return SystemPulse.CRITICAL

        # Severity-based pulse
        if max_severity >= 80 or escalation_count >= 3:
            return SystemPulse.CRITICAL
        elif avg_severity >= 50 or max_severity >= 60:
            return SystemPulse.STRESSED
        elif avg_severity >= 25 or escalation_count >= 1:
            return SystemPulse.ELEVATED
        else:
            return SystemPulse.CALM

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 2: DECISION — Choose execution strategy
    # ─────────────────────────────────────────────────────────────────────────

    def _decide_observation_window(self) -> Tuple[int, int]:
        """Decide how far back to look based on system pulse."""
        window = self._OBSERVATION_WINDOWS[self._current_pulse]
        return window["events"], window["metrics"]

    def _decide_worker_count(self) -> int:
        """Decide parallel worker count based on pulse."""
        return self._WORKER_POOLS[self._current_pulse]

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 3: ORCHESTRATION — Run the reasoning cycle
    # ─────────────────────────────────────────────────────────────────────────

    def run_cycle(self) -> CycleResult:
        """
        Execute one complete MCP reasoning cycle.

        MANDATORY FLOW:
        ┌─────────────────────────────────────────────────────────┐
        │ 1. PERCEIVE  — Read system pulse from cycle history     │
        │ 2. DECIDE    — Set observation window + worker count    │
        │ 3. OBSERVE   — Fetch events and metrics                 │
        │ 4. DETECT    — Run detection agents (parallel)          │
        │ 5. FORECAST  — Run risk forecast (sequential)           │
        │ 6. REASON    — Run causal analysis (sequential)         │
        │ 7. SYNTHESIZE — Cross-correlate + rank severity         │
        │ 8. RECOMMEND — Generate prioritized actions             │
        │ 9. LEARN     — Update MCP memory + diagnostics          │
        └─────────────────────────────────────────────────────────┘
        """
        cycle_start = time.perf_counter()
        now = datetime.utcnow()

        # ── PHASE 1: PERCEIVE ──
        self._current_pulse = self._perceive_pulse()

        # ── PHASE 2: DECIDE ──
        event_window, metric_window = self._decide_observation_window()
        workers = self._decide_worker_count()

        # ── PHASE 3: START CYCLE ──
        cycle_id = self._state.start_cycle()

        # ── PHASE 4: OBSERVE ──
        events = self._observation.get_recent_events(count=event_window)
        metrics = self._observation.get_recent_metrics(count=metric_window)

        # ── PHASE 5: DETECT (Parallel) ──
        anomalies = []
        policy_hits = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            # Submit all detection agents
            futures = {
                pool.submit(self._workflow_agent.analyze, events, self._state): "workflow",
                pool.submit(self._resource_agent.analyze, metrics, self._state): "resource",
                pool.submit(self._compliance_agent.analyze, events, self._state): "compliance",
                pool.submit(self._adaptive_baseline_agent.analyze, metrics, self._state): "baseline",
            }

            # Collect results as they complete (fastest first)
            for future in concurrent.futures.as_completed(futures):
                agent_name = futures[future]
                try:
                    result = future.result()
                    if agent_name == "compliance":
                        policy_hits.extend(result)
                    else:
                        anomalies.extend(result)
                except Exception as e:
                    print(f"  [MCP] Agent '{agent_name}' failed: {e}")

        # ── PHASE 6: FORECAST (Sequential — depends on Phase 5) ──
        risk_signals = self._risk_forecast_agent.analyze(
            anomalies, policy_hits, self._state
        )

        # ── PHASE 7: REASON (Sequential — depends on Phase 5+6) ──
        causal_links = self._causal_agent.analyze(
            anomalies, policy_hits, risk_signals, self._state
        )

        # ── PHASE 8: SYNTHESIZE ──
        severity_score = self._compute_severity_score(
            anomalies, policy_hits, risk_signals, causal_links
        )
        dominant_agent = self._find_dominant_agent(anomalies, policy_hits)
        escalation = self._detect_escalation(risk_signals)
        new_roots = self._count_new_root_causes(causal_links)

        # ── PHASE 9: RECOMMEND ──
        recommendations = self._generate_recommendations(
            anomalies, policy_hits, causal_links, severity_score
        )

        # ── PHASE 10: COMPLETE CYCLE ──
        cycle = self._state.complete_cycle()

        cycle_end = time.perf_counter()
        duration_ms = (cycle_end - cycle_start) * 1000

        # ── PHASE 11: LEARN ──
        diagnostics = CycleDiagnostics(
            cycle_id=cycle_id,
            timestamp=now,
            pulse=self._current_pulse,
            anomaly_count=len(anomalies),
            policy_hit_count=len(policy_hits),
            risk_signal_count=len(risk_signals),
            causal_link_count=len(causal_links),
            recommendation_count=len(recommendations),
            duration_ms=duration_ms,
            severity_score=severity_score,
            dominant_agent=dominant_agent,
            escalation_detected=escalation,
            new_root_causes=new_roots,
        )
        self._update_brain_state(diagnostics)

        # ── PHASE 12: SYNC TO NEO4J (non-blocking) ──
        self._sync_to_graph(anomalies, recommendations)

        self._total_cycles += 1
        self._last_cycle_time = now

        return CycleResult(
            cycle_id=cycle_id,
            anomaly_count=len(anomalies),
            policy_hit_count=len(policy_hits),
            risk_signal_count=len(risk_signals),
            causal_link_count=len(causal_links),
            recommendation_count=len(recommendations),
            duration_ms=round(duration_ms, 3),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 4: SYNTHESIS — Cross-agent intelligence
    # ─────────────────────────────────────────────────────────────────────────

    def _compute_severity_score(
        self,
        anomalies: List[Anomaly],
        policy_hits: List[PolicyHit],
        risk_signals: List[RiskSignal],
        causal_links: List[CausalLink],
    ) -> float:
        """
        Compute a composite severity score (0-100) for this cycle.

        This is NOT a simple count. It weighs:
        - Anomaly confidence and type (critical types score higher)
        - Policy violation severity
        - Risk escalation signals
        - Causal chain depth (cascading = worse)
        """
        score = 0.0

        # Anomaly contribution (max 40 points)
        anomaly_weight = {
            "MISSING_STEP": 8, "SUSTAINED_RESOURCE_CRITICAL": 7,
            "SEQUENCE_VIOLATION": 5, "WORKFLOW_DELAY": 4,
            "SUSTAINED_RESOURCE_WARNING": 3, "RESOURCE_DRIFT": 2,
            "BASELINE_DEVIATION": 2,
        }
        anomaly_score = sum(
            anomaly_weight.get(a.type, 1) * a.confidence
            for a in anomalies
        )
        score += min(40.0, anomaly_score)

        # Policy contribution (max 30 points)
        policy_score = len(policy_hits) * 6
        score += min(30.0, policy_score)

        # Risk signal contribution (max 20 points)
        for rs in risk_signals:
            if rs.projected_state in (RiskState.VIOLATION, RiskState.INCIDENT):
                score += 10
            elif rs.projected_state == RiskState.AT_RISK:
                score += 5
            elif rs.projected_state == RiskState.DEGRADED:
                score += 2
        score = min(score, 90.0)  # Cap before causal bonus

        # Causal chain bonus (max 10 points) — cascading is worse
        score += min(10.0, len(causal_links) * 2.5)

        return min(100.0, round(score, 2))

    def _find_dominant_agent(
        self, anomalies: List[Anomaly], policy_hits: List[PolicyHit]
    ) -> Optional[str]:
        """Find which agent produced the most findings this cycle."""
        counts: Dict[str, int] = {}
        for a in anomalies:
            counts[a.agent] = counts.get(a.agent, 0) + 1
        for p in policy_hits:
            counts[p.agent] = counts.get(p.agent, 0) + 1

        if not counts:
            return None
        return max(counts, key=counts.get)

    # Risk state severity ordering (higher = worse)
    _RISK_SEVERITY_ORDER = {
        RiskState.NORMAL: 0,
        RiskState.DEGRADED: 1,
        RiskState.AT_RISK: 2,
        RiskState.VIOLATION: 3,
        RiskState.INCIDENT: 4,
    }

    def _detect_escalation(self, risk_signals: List[RiskSignal]) -> bool:
        """Check if any risk signal shows escalation vs previous cycle."""
        order = self._RISK_SEVERITY_ORDER

        for rs in risk_signals:
            current_sev = order.get(rs.current_state, 0)
            projected_sev = order.get(rs.projected_state, 0)
            if projected_sev > current_sev:
                return True

        # Also check if anomaly count is trending upward
        if len(self._cycle_history) >= 2:
            prev = self._cycle_history[-1]
            if risk_signals and len(risk_signals) > prev.risk_signal_count:
                return True

        return False

    def _count_new_root_causes(self, causal_links: List[CausalLink]) -> int:
        """Count causal links with root causes not seen in prior cycles."""
        new_count = 0
        for link in causal_links:
            cause_key = f"{link.cause}:{link.cause_entity}"
            if cause_key not in self._known_root_causes:
                new_count += 1
        return new_count

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 5: RECOMMENDATION — Prioritized action mapping
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_recommendations(
        self,
        anomalies: List[Anomaly],
        policy_hits: List[PolicyHit],
        causal_links: List[CausalLink],
        severity_score: float,
    ) -> List[Recommendation]:
        """
        Generate prioritized recommendations.

        Solutions are MAPPED, never invented. But the MCP adds intelligence:
        1. De-duplicates by cause type
        2. Escalates urgency when causal chains link root causes
        3. Orders by urgency (CRITICAL → HIGH → MEDIUM → LOW)
        4. Boosts urgency when system pulse is CRITICAL
        """
        recommendations = []
        seen_causes = set()

        # ── Root-cause-first: prioritize causal chain origins ──
        causal_causes = set()
        for link in causal_links:
            causal_causes.add(link.cause)
            if link.cause in SOLUTION_MAP and link.cause not in seen_causes:
                solution = SOLUTION_MAP[link.cause]
                # Check for escalation pair
                urgency = solution["urgency"]
                cause_effect_pair = (link.cause, link.effect)
                if cause_effect_pair in ESCALATION_RULES:
                    urgency = ESCALATION_RULES[cause_effect_pair]

                # Boost urgency in critical pulse
                if self._current_pulse == SystemPulse.CRITICAL and urgency == "MEDIUM":
                    urgency = "HIGH"

                rec = self._state.add_recommendation(
                    cause=f"RootCause:{link.cause} → {link.effect}",
                    action=solution["action"],
                    urgency=urgency,
                    rationale=f"Causal chain: {link.cause} → {link.effect}. {solution['rationale']}"
                )
                recommendations.append(rec)
                seen_causes.add(link.cause)

        # ── Anomaly-based recommendations (skip if already covered by causal) ──
        for anomaly in anomalies:
            if anomaly.type in SOLUTION_MAP and anomaly.type not in seen_causes:
                solution = SOLUTION_MAP[anomaly.type]
                urgency = solution["urgency"]

                # Boost high-confidence anomalies
                if anomaly.confidence >= 0.9 and urgency == "MEDIUM":
                    urgency = "HIGH"

                # Boost in critical pulse
                if self._current_pulse == SystemPulse.CRITICAL and urgency == "MEDIUM":
                    urgency = "HIGH"

                rec = self._state.add_recommendation(
                    cause=anomaly.type,
                    action=solution["action"],
                    urgency=urgency,
                    rationale=solution["rationale"]
                )
                recommendations.append(rec)
                seen_causes.add(anomaly.type)

        # ── Policy violation recommendations ──
        for hit in policy_hits:
            if hit.violation_type in SOLUTION_MAP and hit.violation_type not in seen_causes:
                solution = SOLUTION_MAP[hit.violation_type]
                rec = self._state.add_recommendation(
                    cause=f"Policy:{hit.policy_id}",
                    action=solution["action"],
                    urgency=solution["urgency"],
                    rationale=solution["rationale"]
                )
                recommendations.append(rec)
                seen_causes.add(hit.violation_type)

        # ── Emergency recommendation if severity is extreme ──
        if severity_score >= 85 and "EMERGENCY" not in seen_causes:
            rec = self._state.add_recommendation(
                cause="EMERGENCY_SEVERITY",
                action="Initiate incident response — multiple cascading failures detected",
                urgency="CRITICAL",
                rationale=f"System severity score {severity_score}/100 exceeds emergency threshold. Multiple agents reporting concurrent issues."
            )
            recommendations.append(rec)
            seen_causes.add("EMERGENCY")

        return recommendations

    # ─────────────────────────────────────────────────────────────────────────
    # NEO4J SYNC — Write anomalies + recommendations to knowledge graph
    # ─────────────────────────────────────────────────────────────────────────

    def _get_graph(self):
        """Lazy-init Neo4j client."""
        if self._graph is None:
            from graph import get_neo4j_client
            self._graph = get_neo4j_client()
        return self._graph

    def _sync_to_graph(self, anomalies: List[Anomaly], recommendations: List[Recommendation]):
        """Sync cycle findings to Neo4j knowledge graph (fire-and-forget in background thread)."""
        def _do_sync():
            try:
                graph = self._get_graph()
                # Write top anomalies (limit to avoid flooding)
                for a in anomalies[:10]:
                    graph.write_anomaly(
                        anomaly_id=a.anomaly_id, type=a.type,
                        agent=a.agent, confidence=a.confidence,
                        description=a.description,
                    )
                # Write recommendations
                for r in recommendations[:5]:
                    graph.write_recommendation(
                        rec_id=r.rec_id, cause=r.cause,
                        action=r.action, urgency=r.urgency,
                    )
            except Exception:
                pass  # Neo4j failure must never break the reasoning loop

        # Fire and forget in a background thread so we don't block the event loop
        threading.Thread(target=_do_sync, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 6: LEARNING — Update MCP brain state
    # ─────────────────────────────────────────────────────────────────────────

    def _update_brain_state(self, diagnostics: CycleDiagnostics):
        """
        Update the MCP's internal memory after each cycle.

        This is what makes it a brain, not just a scheduler.
        """
        self._cycle_history.append(diagnostics)

        # Keep memory bounded (last 100 cycles)
        if len(self._cycle_history) > 100:
            self._cycle_history = self._cycle_history[-100:]

        # Track consecutive critical/calm streaks
        if diagnostics.severity_score >= 70:
            self._consecutive_critical += 1
            self._consecutive_calm = 0
        elif diagnostics.severity_score <= 20:
            self._consecutive_calm += 1
            self._consecutive_critical = 0
        else:
            self._consecutive_critical = 0
            self._consecutive_calm = 0

        # Remember root causes seen
        # (stored from causal links during the cycle)
        for cycle in self._state._completed_cycles[-1:]:
            for link in cycle.causal_links:
                self._known_root_causes.add(f"{link.cause}:{link.cause_entity}")

    # ─────────────────────────────────────────────────────────────────────────
    # QUERY APIs — External access to MCP intelligence
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def adaptive_baseline_agent(self) -> AdaptiveBaselineAgent:
        """Expose adaptive baseline agent for API queries."""
        return self._adaptive_baseline_agent

    def get_current_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state including MCP intelligence."""
        return {
            "cycle": self._state.current_cycle.cycle_id if self._state.current_cycle else None,
            "anomalies": len(self._state.get_current_anomalies()),
            "policy_hits": len(self._state.get_current_policy_hits()),
            "risk_signals": len(self._state.get_current_risk_signals()),
        }

    def get_brain_state(self) -> Dict[str, Any]:
        """
        Get the MCP's current brain state — its situational awareness.

        This is what differentiates MCP from a simple task scheduler.
        It shows the system's cognitive state, not just data.
        """
        recent = self._cycle_history[-10:] if self._cycle_history else []

        # Compute trend
        if len(recent) >= 3:
            first_half = recent[:len(recent)//2]
            second_half = recent[len(recent)//2:]
            avg_first = sum(d.severity_score for d in first_half) / len(first_half)
            avg_second = sum(d.severity_score for d in second_half) / len(second_half)
            if avg_second > avg_first + 5:
                severity_trend = "escalating"
            elif avg_second < avg_first - 5:
                severity_trend = "recovering"
            else:
                severity_trend = "stable"
        else:
            severity_trend = "insufficient_data"

        # Agent performance
        agent_stats: Dict[str, int] = {}
        for d in recent:
            if d.dominant_agent:
                agent_stats[d.dominant_agent] = agent_stats.get(d.dominant_agent, 0) + 1

        return {
            "system_pulse": self._current_pulse.value,
            "total_cycles_completed": self._total_cycles,
            "severity_trend": severity_trend,
            "consecutive_critical_cycles": self._consecutive_critical,
            "consecutive_calm_cycles": self._consecutive_calm,
            "known_root_causes": len(self._known_root_causes),
            "last_cycle_time": self._last_cycle_time.isoformat() if self._last_cycle_time else None,
            "observation_window": self._OBSERVATION_WINDOWS[self._current_pulse],
            "worker_pool_size": self._WORKER_POOLS[self._current_pulse],
            "agent_dominance_last_10": agent_stats,
            "recent_diagnostics": [
                {
                    "cycle_id": d.cycle_id,
                    "pulse": d.pulse.value,
                    "severity": d.severity_score,
                    "anomalies": d.anomaly_count,
                    "policy_hits": d.policy_hit_count,
                    "causal_links": d.causal_link_count,
                    "escalation": d.escalation_detected,
                    "new_roots": d.new_root_causes,
                    "duration_ms": round(d.duration_ms, 2),
                    "dominant_agent": d.dominant_agent,
                }
                for d in recent[-5:]
            ],
        }
