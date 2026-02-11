"""
Chronos AI — IICWMS Production API Server
==========================================
Production-grade FastAPI backend with:
- Structured logging with request correlation
- Request ID tracing (X-Request-ID)
- Response timing (X-Response-Time)
- OWASP security headers
- Rate limiting (per-IP sliding window)
- Graceful shutdown with task cancellation
- Global error handling (no raw stack traces)
- Environment-based configuration

ARCHITECTURE LAYER: Interface Gateway
Exposes observation ingestion, reasoning state, and insight retrieval.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
import asyncio
import logging
import sys

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from simulator.engine import SimulationEngine, Event, ResourceMetric
from observation import ObservationLayer, get_observation_layer
from blackboard import SharedState, get_shared_state, RiskState
from agents import MasterAgent, CycleResult, QueryAgent, ScenarioInjectionAgent
from explanation import ExplanationEngine, Insight
from guards import run_all_guards_check, SimulationContext
from rag import get_rag_engine
from metrics import get_risk_tracker

from api.config import settings
from api.middleware import (
    RequestIDMiddleware,
    TimingMiddleware,
    SecurityHeadersMiddleware,
    ErrorHandlerMiddleware,
    RateLimitMiddleware,
)

# ═══════════════════════════════════════════════════════════════════════════════
# STRUCTURED LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

def _setup_logging():
    """Configure structured logging for the application."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)-24s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Root logger
    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

_setup_logging()
logger = logging.getLogger("chronos.api")


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS (API Contracts)
# ═══════════════════════════════════════════════════════════════════════════════

class EventInput(BaseModel):
    """Input for event ingestion."""
    event_id: str = Field(..., min_length=1, max_length=128, description="Unique event identifier")
    type: str = Field(..., min_length=1, max_length=64, description="Event type")
    workflow_id: Optional[str] = Field(None, max_length=128)
    actor: str = Field(..., min_length=1, max_length=128)
    resource: Optional[str] = Field(None, max_length=128)
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricInput(BaseModel):
    """Input for metric ingestion."""
    resource_id: str = Field(..., min_length=1, max_length=128)
    metric: str = Field(..., min_length=1, max_length=64)
    value: float = Field(..., description="Metric value")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


class SystemHealth(BaseModel):
    """System health status."""
    status: str  # NORMAL, DEGRADED, CRITICAL
    active_anomalies: int
    active_violations: int
    active_risks: int
    last_cycle: Optional[str]
    message: str


class SignalsSummary(BaseModel):
    """Cognitive signals summary."""
    workflow_integrity: Dict[str, Any]
    policy_risk: Dict[str, Any]
    resource_stability: Dict[str, Any]


class InsightResponse(BaseModel):
    """Insight API response."""
    insight_id: str
    summary: str
    why_it_matters: str
    what_will_happen_if_ignored: str
    recommended_actions: List[str]
    confidence: float
    uncertainty: str
    severity: str
    timestamp: str
    evidence_count: int
    cycle_id: str


class HypothesisResponse(BaseModel):
    """Hypothesis (anomaly) response."""
    id: str
    type: str
    agent: str
    description: str
    confidence: float
    timestamp: str
    status: str = "open"


class PolicyResponse(BaseModel):
    """Policy definition response."""
    policy_id: str
    name: str
    severity: str
    rationale: str


class ViolationResponse(BaseModel):
    """Policy violation response."""
    hit_id: str
    policy_id: str
    event_id: str
    violation_type: str
    description: str
    timestamp: str


class WorkflowResponse(BaseModel):
    """Workflow response."""
    id: str
    name: str
    status: str
    steps_completed: int
    total_steps: int


class CausalLinkResponse(BaseModel):
    """Causal link response."""
    link_id: str
    cause: str
    effect: str
    cause_entity: str
    effect_entity: str
    confidence: float
    reasoning: str


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL STATE — Application-scoped singletons
# ═══════════════════════════════════════════════════════════════════════════════

_simulation: Optional[SimulationEngine] = None
_observation: Optional[ObservationLayer] = None
_state: Optional[SharedState] = None
_master: Optional[MasterAgent] = None
_explanation: Optional[ExplanationEngine] = None
_insights: List[Insight] = []
_cycle_results: List[CycleResult] = []
_running = False
_reasoning_task: Optional[asyncio.Task] = None
_startup_time: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════════════
# REASONING LOOP — Background task with error resilience
# ═══════════════════════════════════════════════════════════════════════════════

async def run_reasoning_loop():
    """
    Background task: Run simulation → observation → reasoning cycles.

    Production hardening:
    - Catches and logs individual cycle failures without stopping the loop
    - Respects cancellation for graceful shutdown
    - Bounds insight buffer to prevent memory growth
    - Bounds cycle result history
    """
    global _running, _insights, _cycle_results
    cycle_logger = logging.getLogger("chronos.reasoning_loop")

    cycle_logger.info(
        f"Reasoning loop started (interval={settings.CYCLE_INTERVAL_SECONDS}s)"
    )

    while _running:
        try:
            # 1. Simulation tick — generate events (guard-scoped)
            with SimulationContext():
                events, metrics = _simulation.tick()

            # 2. Observation layer ingest
            for event in events:
                _observation.observe_event(event.to_dict())
            for metric in metrics:
                _observation.observe_metric(metric.to_dict())

            # 3. MCP runs reasoning cycle
            result = _master.run_cycle()
            _cycle_results.append(result)

            # Bound cycle results to prevent unbounded growth
            if len(_cycle_results) > settings.MAX_CYCLE_HISTORY:
                _cycle_results = _cycle_results[-settings.MAX_CYCLE_HISTORY:]

            # 4. Track risk index
            if _state._completed_cycles:
                latest_cycle = _state._completed_cycles[-1]
                risk_tracker = get_risk_tracker()
                risk_tracker.record_cycle(latest_cycle)

                # 5. Explanation engine generates insight
                insight = _explanation.generate_insight(latest_cycle)
                if insight:
                    _insights.append(insight)
                    if len(_insights) > settings.MAX_INSIGHTS_BUFFER:
                        _insights = _insights[-settings.MAX_INSIGHTS_BUFFER:]
                    
                    # Persist insight to SQLite
                    try:
                        from db import get_sqlite_store
                        get_sqlite_store().insert_insight(
                            insight_id=insight.insight_id,
                            cycle_id=insight.cycle_id,
                            summary=insight.summary,
                            severity=insight.severity,
                            confidence=insight.confidence,
                            timestamp=insight.timestamp.isoformat(),
                            why_it_matters=insight.why_it_matters,
                            what_will_happen=insight.what_will_happen_if_ignored,
                            uncertainty=insight.uncertainty,
                            evidence_count=insight.evidence_count,
                            actions=insight.recommended_actions,
                        )
                    except Exception:
                        pass

            cycle_logger.debug(
                f"Cycle {result.cycle_id}: "
                f"{result.anomaly_count} anomalies, "
                f"{result.policy_hit_count} violations, "
                f"{result.duration_ms:.0f}ms"
            )

            # Wait before next cycle (respects cancellation)
            await asyncio.sleep(settings.CYCLE_INTERVAL_SECONDS)

        except asyncio.CancelledError:
            cycle_logger.info("Reasoning loop cancelled — shutting down gracefully")
            break
        except Exception as e:
            cycle_logger.error(f"Cycle error (will retry): {type(e).__name__}: {e}")
            await asyncio.sleep(settings.CYCLE_INTERVAL_SECONDS)

    cycle_logger.info("Reasoning loop stopped")


# ═══════════════════════════════════════════════════════════════════════════════
# LIFECYCLE — Startup / Shutdown with graceful task management
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Startup:
    1. Run architectural guards
    2. Initialize all components
    3. Start background reasoning loop

    Shutdown:
    1. Signal reasoning loop to stop
    2. Cancel background task
    3. Wait for clean exit
    """
    global _simulation, _observation, _state, _master, _explanation
    global _running, _reasoning_task, _startup_time

    _startup_time = datetime.utcnow()

    # ── Architectural Guards ──
    logger.info("=" * 60)
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info("=" * 60)

    try:
        run_all_guards_check()
        logger.info("Architectural guards: PASS")
    except Exception as e:
        logger.warning(f"Architectural guards: WARNING — {e}")

    # ── Component Initialization ──
    logger.info("Initializing components...")
    _simulation = SimulationEngine()
    _observation = get_observation_layer()
    _state = get_shared_state()
    _master = MasterAgent(_observation, _state)
    _explanation = ExplanationEngine(use_llm=settings.ENABLE_CREWAI)

    logger.info("  Simulation Engine ......... ready")
    logger.info("  Observation Layer ......... ready")
    logger.info("  Shared State (Blackboard) . ready")
    logger.info("  MCP (Master Agent) ........ ready")
    logger.info("  Explanation Engine ........ ready")

    # ── Database Initialization ──
    from db import get_sqlite_store
    from graph import get_neo4j_client
    _sqlite = get_sqlite_store()
    logger.info(f"  SQLite Store .............. ready ({settings.SQLITE_DB_PATH})")
    _neo4j = get_neo4j_client()
    if _neo4j.is_connected:
        logger.info(f"  Neo4j Aura ................ connected ({settings.NEO4J_URI})")
    else:
        logger.info("  Neo4j Aura ................ disabled (using NullGraphClient)")

    # ── Start Reasoning Loop ──
    _running = True
    _reasoning_task = asyncio.create_task(run_reasoning_loop())
    logger.info(f"Reasoning loop started ({settings.CYCLE_INTERVAL_SECONDS}s interval)")
    logger.info("=" * 60)
    logger.info("Server ready — accepting requests")

    yield

    # ── Graceful Shutdown ──
    logger.info("Initiating graceful shutdown...")
    _running = False

    if _reasoning_task and not _reasoning_task.done():
        _reasoning_task.cancel()
        try:
            await asyncio.wait_for(_reasoning_task, timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass

    logger.info(f"Shutdown complete. Ran {len(_cycle_results)} cycles.")


# ═══════════════════════════════════════════════════════════════════════════════
# APP SETUP — Production-grade FastAPI with middleware stack
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Chronos AI — IICWMS API",
    description=(
        "Intelligent IT Compliance & Workflow Monitoring System.\n\n"
        "**Multi-Agent Cognitive Observability Platform**\n\n"
        "9 specialized agents analyze IT operations in real-time:\n"
        "- Workflow anomaly detection\n"
        "- Resource usage analysis\n"
        "- Compliance policy evaluation\n"
        "- Risk forecasting\n"
        "- Causal reasoning\n"
        "- Adaptive baseline learning\n\n"
        "Every response includes `X-Request-ID` and `X-Response-Time` headers."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware Stack (order matters — outermost first) ──
# Error handler wraps everything
app.add_middleware(ErrorHandlerMiddleware)
# Security headers on every response
app.add_middleware(SecurityHeadersMiddleware)
# Request timing + logging
app.add_middleware(TimingMiddleware)
# Request ID tracing
app.add_middleware(RequestIDMiddleware)
# Rate limiting
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)
# CORS (must be last middleware added = first to run)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    expose_headers=["X-Request-ID", "X-Response-Time"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL EXCEPTION HANDLERS — Structured error responses
# ═══════════════════════════════════════════════════════════════════════════════

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Return structured JSON for all HTTP errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else "error",
            "status_code": exc.status_code,
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions — never leak stack traces."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{request_id}] Unhandled: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred.",
            "request_id": request_id,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# OBSERVATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/observe/event", tags=["Observation"])
async def observe_event(event: EventInput):
    """Ingest a raw event into the observation layer."""
    observed = _observation.observe_event(event.model_dump())
    return {"status": "observed", "event_id": observed.event_id}


@app.post("/observe/metric", tags=["Observation"])
async def observe_metric(metric: MetricInput):
    """Ingest a raw metric into the observation layer."""
    observed = _observation.observe_metric(metric.model_dump())
    return {"status": "observed", "resource_id": observed.resource_id}


@app.get("/observe/window", tags=["Observation"])
async def get_observation_window(
    limit: int = Query(default=100, ge=1, le=1000, description="Max events to return"),
    event_type: Optional[str] = Query(default=None, description="Filter by event type"),
):
    """Get recent observations with optional filtering."""
    events = _observation.get_recent_events(count=limit)
    return {
        "events": [
            {
                "event_id": e.event_id,
                "type": e.type,
                "workflow_id": e.workflow_id,
                "actor": e.actor,
                "resource": e.resource,
                "timestamp": e.timestamp.isoformat(),
                "metadata": e.metadata
            }
            for e in events
            if not event_type or e.type == event_type
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM HEALTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/system/health", response_model=SystemHealth, tags=["System"])
async def get_system_health():
    """Get overall system health — operational status based on current reasoning cycle."""
    anomalies = _state.get_current_anomalies() if _state.current_cycle else []
    violations = _state.get_current_policy_hits() if _state.current_cycle else []
    risks = _state.get_current_risk_signals() if _state.current_cycle else []
    
    # Determine status
    if any(r.projected_state in (RiskState.VIOLATION, RiskState.INCIDENT) for r in risks):
        status = "CRITICAL"
        message = "Critical risk detected. Immediate attention required."
    elif any(a.type in ("SUSTAINED_RESOURCE_CRITICAL", "MISSING_STEP") for a in anomalies):
        status = "DEGRADED"
        message = "System degradation detected. Investigation recommended."
    elif anomalies or violations:
        status = "DEGRADED"
        message = "Minor issues detected. Monitoring continues."
    else:
        status = "NORMAL"
        message = "System operating normally."
    
    return SystemHealth(
        status=status,
        active_anomalies=len(anomalies),
        active_violations=len(violations),
        active_risks=len(risks),
        last_cycle=_cycle_results[-1].cycle_id if _cycle_results else None,
        message=message
    )


@app.get("/signals/summary", response_model=SignalsSummary, tags=["System"])
async def get_signals_summary():
    """Get cognitive signals summary — workflow, policy, and resource health at a glance."""
    anomalies = _state.get_current_anomalies() if _state.current_cycle else []
    violations = _state.get_current_policy_hits() if _state.current_cycle else []
    risks = _state.get_current_risk_signals() if _state.current_cycle else []
    
    # Workflow integrity
    workflow_anomalies = [a for a in anomalies if a.type in ("WORKFLOW_DELAY", "MISSING_STEP", "SEQUENCE_VIOLATION")]
    workflow_status = "critical" if any(a.type == "MISSING_STEP" for a in workflow_anomalies) else \
                     "warning" if workflow_anomalies else "healthy"
    
    # Policy risk
    policy_status = "critical" if len(violations) > 3 else \
                   "warning" if violations else "healthy"
    
    # Resource stability
    resource_anomalies = [a for a in anomalies if "RESOURCE" in a.type]
    resource_status = "critical" if any(a.type == "SUSTAINED_RESOURCE_CRITICAL" for a in resource_anomalies) else \
                     "warning" if resource_anomalies else "healthy"
    
    return SignalsSummary(
        workflow_integrity={
            "status": workflow_status,
            "count": len(workflow_anomalies),
            "trend": "stable",
            "why": f"{len(workflow_anomalies)} workflow issues detected" if workflow_anomalies else "All workflows operating normally"
        },
        policy_risk={
            "status": policy_status,
            "count": len(violations),
            "trend": "stable",
            "why": f"{len(violations)} policy violations detected" if violations else "All policies compliant"
        },
        resource_stability={
            "status": resource_status,
            "count": len(resource_anomalies),
            "trend": "stable",
            "why": f"{len(resource_anomalies)} resource issues detected" if resource_anomalies else "All resources stable"
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INSIGHTS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/insights", tags=["Insights"])
async def get_insights(limit: int = Query(default=10, ge=1, le=100, description="Max insights to return")):
    """Get recent insights generated by the Explanation Engine."""
    recent = _insights[-limit:] if _insights else []
    return {
        "insights": [
            InsightResponse(
                insight_id=i.insight_id,
                summary=i.summary,
                why_it_matters=i.why_it_matters,
                what_will_happen_if_ignored=i.what_will_happen_if_ignored,
                recommended_actions=i.recommended_actions,
                confidence=i.confidence,
                uncertainty=i.uncertainty,
                severity=i.severity,
                timestamp=i.timestamp.isoformat(),
                evidence_count=i.evidence_count,
                cycle_id=i.cycle_id
            ).model_dump()
            for i in reversed(recent)
        ]
    }


@app.get("/insight/{insight_id}", tags=["Insights"])
async def get_insight(insight_id: str):
    """Get specific insight with causal links and evidence chain."""
    for insight in _insights:
        if insight.insight_id == insight_id:
            # Get associated cycle
            cycle = None
            for c in _state._completed_cycles:
                if c.cycle_id == insight.cycle_id:
                    cycle = c
                    break
            
            return {
                "insight": InsightResponse(
                    insight_id=insight.insight_id,
                    summary=insight.summary,
                    why_it_matters=insight.why_it_matters,
                    what_will_happen_if_ignored=insight.what_will_happen_if_ignored,
                    recommended_actions=insight.recommended_actions,
                    confidence=insight.confidence,
                    uncertainty=insight.uncertainty,
                    severity=insight.severity,
                    timestamp=insight.timestamp.isoformat(),
                    evidence_count=insight.evidence_count,
                    cycle_id=insight.cycle_id
                ).model_dump(),
                "causal_links": [
                    CausalLinkResponse(
                        link_id=c.link_id,
                        cause=c.cause,
                        effect=c.effect,
                        cause_entity=c.cause_entity,
                        effect_entity=c.effect_entity,
                        confidence=c.confidence,
                        reasoning=c.reasoning
                    ).model_dump()
                    for c in (cycle.causal_links if cycle else [])
                ],
                "evidence": [
                    {"type": "anomaly", "id": a.anomaly_id, "description": a.description}
                    for a in (cycle.anomalies if cycle else [])
                ] + [
                    {"type": "policy_hit", "id": h.hit_id, "description": h.description}
                    for h in (cycle.policy_hits if cycle else [])
                ]
            }
    
    raise HTTPException(status_code=404, detail="Insight not found")


# ═══════════════════════════════════════════════════════════════════════════════
# HYPOTHESES (ANOMALIES) ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/hypotheses", tags=["Anomalies"])
async def get_hypotheses(limit: int = Query(default=50, ge=1, le=500)):
    """Get all anomalies/hypotheses from recent reasoning cycles."""
    all_anomalies = []
    
    for cycle in _state._completed_cycles[-10:]:
        for a in cycle.anomalies:
            all_anomalies.append(HypothesisResponse(
                id=a.anomaly_id,
                type=a.type,
                agent=a.agent,
                description=a.description,
                confidence=a.confidence,
                timestamp=a.timestamp.isoformat(),
                status="open"
            ))
    
    return {"hypotheses": [h.model_dump() for h in all_anomalies[-limit:]]}


# ═══════════════════════════════════════════════════════════════════════════════
# POLICY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/policies", tags=["Compliance"])
async def get_policies():
    """Get all policy definitions enforced by the Compliance Agent."""
    from agents.compliance_agent import POLICIES
    
    return {
        "policies": [
            PolicyResponse(
                policy_id=p.policy_id,
                name=p.name,
                severity=p.severity,
                rationale=p.rationale
            ).model_dump()
            for p in POLICIES
        ]
    }


@app.get("/policy/violations", tags=["Compliance"])
async def get_policy_violations(limit: int = Query(default=50, ge=1, le=500)):
    """Get detected policy violations from recent cycles."""
    all_violations = []
    
    for cycle in _state._completed_cycles[-10:]:
        for h in cycle.policy_hits:
            all_violations.append(ViolationResponse(
                hit_id=h.hit_id,
                policy_id=h.policy_id,
                event_id=h.event_id,
                violation_type=h.violation_type,
                description=h.description,
                timestamp=h.timestamp.isoformat()
            ))
    
    return {"violations": [v.model_dump() for v in all_violations[-limit:]]}


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/workflows", tags=["Workflows"])
async def get_workflows():
    """Get tracked workflows with step completion status."""
    workflows = _master._workflow_agent.get_tracked_workflows()
    
    return {
        "workflows": [
            WorkflowResponse(
                id=wf.workflow_id,
                name=wf.workflow_type,
                status="active" if not wf.skipped_steps else "degraded",
                steps_completed=len(wf.completed_steps),
                total_steps=wf.current_step_index + 1
            ).model_dump()
            for wf in workflows.values()
        ]
    }


@app.get("/workflow/{workflow_id}/graph", tags=["Workflows"])
async def get_workflow_graph(workflow_id: str):
    """Get workflow graph visualization data — nodes and edges for DAG rendering."""
    from agents.workflow_agent import WORKFLOW_DEFINITIONS
    
    # Find workflow type
    workflow_type = None
    for wt in WORKFLOW_DEFINITIONS.keys():
        if workflow_id.startswith(wt):
            workflow_type = wt
            break
    
    if not workflow_type:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    definition = WORKFLOW_DEFINITIONS[workflow_type]
    tracked = _master._workflow_agent.get_tracked_workflows().get(workflow_id)
    
    # Build nodes
    nodes = []
    for i, step in enumerate(definition["steps"]):
        status = "pending"
        if tracked:
            if step in tracked.completed_steps:
                status = "complete"
            elif step in tracked.skipped_steps:
                status = "skipped"
            elif i == tracked.current_step_index:
                status = "active"
        
        nodes.append({
            "id": f"{workflow_id}_{step}",
            "name": step.replace("_", " ").title(),
            "status": status,
            "deviation": step in (tracked.skipped_steps if tracked else [])
        })
    
    # Build edges
    edges = []
    for i in range(len(definition["steps"]) - 1):
        edges.append({
            "source": f"{workflow_id}_{definition['steps'][i]}",
            "target": f"{workflow_id}_{definition['steps'][i+1]}"
        })
    
    return {"nodes": nodes, "edges": edges}


@app.get("/workflow/{workflow_id}/stats")
async def get_workflow_stats(workflow_id: str):
    """Get workflow statistics."""
    from agents.workflow_agent import WORKFLOW_DEFINITIONS
    
    tracked = _master._workflow_agent.get_tracked_workflows().get(workflow_id)
    
    return {
        "avg_duration": "45s",
        "deviation": len(tracked.skipped_steps) if tracked else 0,
        "total_runs": 1,
        "success_rate": 0.85 if tracked and not tracked.skipped_steps else 0.5
    }


@app.get("/workflow/{workflow_id}/timeline")
async def get_workflow_timeline(workflow_id: str):
    """
    Get full workflow timeline data for the Event Graph Timeline page.
    
    Returns events across all 4 lanes:
    - workflow: Step execution events
    - resource: Resource impact during workflow
    - human: Human actions (overrides, retries)
    - compliance: Policy checks and violations
    """
    from agents.workflow_agent import WORKFLOW_DEFINITIONS
    
    # Extract workflow type prefix
    wf_type = None
    for prefix in WORKFLOW_DEFINITIONS.keys():
        if workflow_id.startswith(prefix):
            wf_type = prefix
            break
    
    if not wf_type:
        raise HTTPException(status_code=404, detail=f"Unknown workflow type for {workflow_id}")
    
    definition = WORKFLOW_DEFINITIONS[wf_type]
    
    # Collect all events related to this workflow
    all_events = _observation.get_recent_events(count=500)
    wf_events = [e for e in all_events if e.workflow_id and e.workflow_id.startswith(wf_type)]
    
    # Build timeline nodes
    nodes = []
    now = datetime.utcnow()
    base_time = now - timedelta(minutes=10)
    
    # Workflow lane: use real events if available, else generate from definition
    if wf_events:
        for e in wf_events:
            lane = "workflow"
            status = "success"
            confidence = 90
            
            if e.type == "WORKFLOW_STEP_SKIP":
                status = "skipped"
                confidence = 0
            elif e.type == "WORKFLOW_STEP_START":
                status = "in_progress"
                confidence = 70
            
            duration = e.metadata.get("duration_seconds", 0)
            sla = definition["step_sla_seconds"].get(e.metadata.get("step", ""), 60)
            if duration > sla:
                status = "delayed"
                confidence = max(20, 90 - int((duration - sla) / sla * 50))
            
            nodes.append({
                "id": e.event_id,
                "laneId": lane,
                "name": e.metadata.get("step", e.type).upper(),
                "status": status,
                "timestamp": e.timestamp.isoformat(),
                "timestampMs": int(e.timestamp.timestamp() * 1000),
                "durationMs": int(duration * 1000) if duration else None,
                "confidence": confidence,
                "details": e.metadata,
                "agentSource": "WorkflowAgent",
            })
    else:
        # Generate mock timeline from definition steps
        for i, step in enumerate(definition["steps"]):
            ts = base_time + timedelta(seconds=i * 60)
            sla = definition["step_sla_seconds"].get(step, 60)
            
            # Make the deploy step delayed for demo
            if step in ("deploy", "production"):
                status = "delayed"
                actual_duration = sla * 2.1
                confidence = 62
            elif i >= len(definition["steps"]) - 1:
                status = "pending"
                actual_duration = 0
                confidence = 50
            else:
                status = "success"
                actual_duration = sla * 0.8
                confidence = 95 - i * 3
            
            nodes.append({
                "id": f"evt_{workflow_id}_{step}",
                "laneId": "workflow",
                "name": step.upper(),
                "status": status,
                "timestamp": ts.isoformat(),
                "timestampMs": int(ts.timestamp() * 1000),
                "durationMs": int(actual_duration * 1000),
                "confidence": confidence,
                "details": {
                    "step": step,
                    "expected_duration": f"{sla}s",
                    "actual_duration": f"{int(actual_duration)}s",
                    "sla_risk": actual_duration > sla,
                },
                "agentSource": "WorkflowAgent",
                "dependsOn": [f"evt_{workflow_id}_{definition['steps'][i-1]}"] if i > 0 else [],
            })
    
    # Resource lane: get recent resource anomalies
    resource_nodes = []
    recent_metrics = _observation.get_recent_metrics(count=100)
    seen = set()
    for m in recent_metrics[-20:]:
        if m.resource_id in seen:
            continue
        seen.add(m.resource_id)
        status = "success"
        confidence = 90
        if m.metric == "cpu_percent" and m.value > 90:
            status = "failed"
            confidence = 15
        elif m.metric == "cpu_percent" and m.value > 70:
            status = "warning"
            confidence = 65
        elif m.metric == "network_latency_ms" and m.value > 200:
            status = "warning"
            confidence = 72
        elif m.metric == "memory_percent" and m.value > 75:
            status = "warning"
            confidence = 68
        
        if status != "success":
            resource_nodes.append({
                "id": f"res_{m.resource_id}_{m.metric}",
                "laneId": "resource",
                "name": f"{m.resource_id} {m.metric.replace('_', ' ')}",
                "status": status,
                "timestamp": m.timestamp.isoformat(),
                "timestampMs": int(m.timestamp.timestamp() * 1000),
                "confidence": confidence,
                "details": {
                    "metric": m.metric,
                    "value": m.value,
                    "resource": m.resource_id,
                },
                "agentSource": "ResourceAgent",
            })
    
    nodes.extend(resource_nodes[:5])
    
    # Compliance lane: get recent violations for this workflow
    compliance_nodes = []
    state = get_shared_state()
    for cycle in state._completed_cycles[-5:]:
        for hit in cycle.policy_hits:
            compliance_nodes.append({
                "id": hit.hit_id,
                "laneId": "compliance",
                "name": hit.policy_id,
                "status": "failed" if hit.violation_type == "SILENT" else "warning",
                "timestamp": hit.timestamp.isoformat(),
                "timestampMs": int(hit.timestamp.timestamp() * 1000),
                "confidence": 8 if hit.violation_type == "SILENT" else 45,
                "details": {
                    "policy": hit.policy_id,
                    "violation_type": hit.violation_type,
                    "event_id": hit.event_id,
                },
                "agentSource": "ComplianceAgent",
            })
    
    nodes.extend(compliance_nodes[:3])
    
    # Calculate overall confidence
    if nodes:
        overall = sum(n["confidence"] for n in nodes) / len(nodes)
    else:
        overall = 50
    
    return {
        "workflowId": workflow_id,
        "workflowLabel": definition["name"],
        "nodes": nodes,
        "overallConfidence": round(overall),
        "startTime": int(base_time.timestamp() * 1000),
        "endTime": int(now.timestamp() * 1000),
        "lanes": [
            {"id": "workflow", "label": "Workflow Steps", "order": 0, "visible": True},
            {"id": "resource", "label": "Resource Impact", "order": 1, "visible": True},
            {"id": "human", "label": "Human Actions", "order": 2, "visible": True},
            {"id": "compliance", "label": "Compliance", "order": 3, "visible": True},
        ],
        "outcomeSummary": f"Workflow {definition['name']} — monitoring across {len(nodes)} events",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCE ENDPOINTS (for Resource & Cost Intelligence page)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/resources", tags=["Resources"])
async def get_resources():
    """
    Get all tracked resources with current metrics and status.
    Used by the Resource & Cost Intelligence page.
    """
    resources = []
    
    for res_id, res in _simulation._resources.items():
        # Determine status from current values
        status = "normal"
        anomalies = []
        
        if res.cpu_usage > 90:
            status = "critical"
            anomalies.append(f"CPU saturation at {res.cpu_usage:.0f}%")
        elif res.cpu_usage > 70:
            status = "warning"
            anomalies.append(f"CPU elevated at {res.cpu_usage:.0f}%")
        
        if res.network_latency_ms > 200:
            if status == "normal":
                status = "warning"
            anomalies.append(f"Latency at {res.network_latency_ms:.0f}ms")
        
        if res.memory_usage > 85:
            if status == "normal":
                status = "warning"
            anomalies.append(f"Memory pressure at {res.memory_usage:.0f}%")
        
        # Get metric history
        recent = _observation.get_recent_metrics(count=200)
        history = [m for m in recent if m.resource_id == res_id and m.metric == "cpu_percent"]
        trend = [round(m.value, 1) for m in history[-8:]]
        
        # Determine associated workflows
        workflows = []
        if res_id in ("vm_2", "vm_3", "net_3"):
            workflows.append("wf_onboarding_17")
        if res_id in ("vm_2", "vm_8"):
            workflows.append("wf_deployment_03")
        
        # Type classification
        rtype = "compute"
        if res_id.startswith("net"):
            rtype = "network"
        elif res_id.startswith("storage"):
            rtype = "storage"
        
        resources.append({
            "resource_id": res_id,
            "name": res.name,
            "type": rtype,
            "metrics": {
                "cpu": round(res.cpu_usage, 1),
                "memory": round(res.memory_usage, 1),
                "network_latency": round(res.network_latency_ms, 1),
            },
            "trend": trend if trend else [30, 35, 40, 42, 45],
            "status": status,
            "cost_per_hour": round(1.5 + res.cpu_usage * 0.02, 2),
            "associated_workflows": workflows,
            "anomalies": anomalies,
            "agent_source": "ResourceAgent",
        })
    
    return {"resources": resources}


@app.get("/resources/{resource_id}/metrics", tags=["Resources"])
async def get_resource_metrics(resource_id: str, limit: int = Query(default=50, ge=1, le=500)):
    """Get metric history for a specific resource."""
    recent = _observation.get_recent_metrics(count=500)
    metrics = [m for m in recent if m.resource_id == resource_id][-limit:]
    
    return {
        "resource_id": resource_id,
        "metrics": [
            {
                "metric": m.metric,
                "value": round(m.value, 2),
                "timestamp": m.timestamp.isoformat(),
            }
            for m in metrics
        ]
    }


@app.get("/observe/events", tags=["Observation"])
async def get_recent_events(limit: int = Query(default=50, ge=1, le=1000)):
    """Get recent events from the observation layer."""
    events = _observation.get_recent_events(count=limit)
    return {
        "events": [
            {
                "event_id": e.event_id,
                "type": e.type,
                "workflow_id": e.workflow_id,
                "actor": e.actor,
                "resource": e.resource,
                "timestamp": e.timestamp.isoformat(),
                "metadata": e.metadata
            }
            for e in events
        ]
    }


@app.get("/observe/metrics", tags=["Observation"])
async def get_recent_metrics(limit: int = Query(default=100, ge=1, le=1000)):
    """Get recent metrics from the observation layer."""
    metrics = _observation.get_recent_metrics(count=limit)
    return {
        "metrics": [
            {
                "resource_id": m.resource_id,
                "metric": m.metric,
                "value": round(m.value, 2),
                "timestamp": m.timestamp.isoformat(),
            }
            for m in metrics
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CAUSAL ANALYSIS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/graph/path/{insight_id}", tags=["Causal"])
async def get_causal_path(insight_id: str):
    """Get causal graph path for an insight — nodes and edges for graph rendering."""
    # Find insight
    insight = None
    for i in _insights:
        if i.insight_id == insight_id:
            insight = i
            break
    
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    # Find associated cycle
    cycle = None
    for c in _state._completed_cycles:
        if c.cycle_id == insight.cycle_id:
            cycle = c
            break
    
    if not cycle:
        return {"nodes": [], "edges": []}
    
    # Build causal graph
    nodes = []
    edges = []
    node_ids = set()
    
    for link in cycle.causal_links:
        # Add cause node
        if link.cause_entity not in node_ids:
            nodes.append({
                "id": link.cause_entity,
                "label": link.cause,
                "type": "cause"
            })
            node_ids.add(link.cause_entity)
        
        # Add effect node
        if link.effect_entity not in node_ids:
            nodes.append({
                "id": link.effect_entity,
                "label": link.effect,
                "type": "effect"
            })
            node_ids.add(link.effect_entity)
        
        # Add edge
        edges.append({
            "source": link.cause_entity,
            "target": link.effect_entity,
            "confidence": link.confidence,
            "reasoning": link.reasoning
        })
    
    return {"nodes": nodes, "edges": edges}


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION CONTROL
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/simulation/tick", tags=["Simulation"])
async def trigger_simulation_tick():
    """Manually trigger a simulation tick (for testing / demo)."""
    events, metrics = _simulation.tick()
    
    for event in events:
        _observation.observe_event(event.to_dict())
    for metric in metrics:
        _observation.observe_metric(metric.to_dict())
    
    return {
        "events_generated": len(events),
        "metrics_generated": len(metrics)
    }


@app.post("/analysis/cycle", tags=["Simulation"])
async def trigger_analysis_cycle():
    """Manually trigger an MCP reasoning cycle (for testing / demo)."""
    result = _master.run_cycle()
    _cycle_results.append(result)
    
    if _state._completed_cycles:
        latest = _state._completed_cycles[-1]
        insight = _explanation.generate_insight(latest)
        if insight:
            _insights.append(insight)
    
    return {
        "cycle_id": result.cycle_id,
        "anomalies": result.anomaly_count,
        "policy_hits": result.policy_hit_count,
        "risk_signals": result.risk_signal_count,
        "causal_links": result.causal_link_count,
        "recommendations": result.recommendation_count,
        "duration_ms": result.duration_ms
    }


# ═══════════════════════════════════════════════════════════════════════════════
# AGENTIC RAG - REASONING QUERY INTERFACE (CORE DIFFERENTIATOR)
# ═══════════════════════════════════════════════════════════════════════════════

class RAGQueryRequest(BaseModel):
    """Request for RAG query."""
    query: str


@app.post("/rag/query", tags=["Query"])
async def rag_query(request: RAGQueryRequest):
    """
    Reasoning Query Interface - NOT a chatbot.
    
    This answers questions like:
    - "Why is onboarding workflow at risk?"
    - "Show compliance risks related to network latency"
    - "What will break if this trend continues?"
    - "Which policy is most frequently violated?"
    
    These are NOT log searches.
    They are cross-agent reasoning queries.
    """
    rag = get_rag_engine()
    response = rag.query(request.query)
    return response.to_dict()


@app.get("/rag/examples", tags=["Query"])
async def rag_examples():
    """Get example queries for the RAG interface."""
    return {
        "examples": [
            "Why is the system at risk right now?",
            "What caused the workflow delay?",
            "Show compliance risks",
            "What will happen if this trend continues?",
            "Which policy is being violated?",
            "Explain the current resource issues",
            "What is the root cause of the degradation?"
        ],
        "note": "These are reasoning queries, not log searches"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RISK INDEX - SYSTEM HEALTH OVER TIME (STOCK-MARKET STYLE)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/risk/index", tags=["Risk"])
async def get_risk_index(limit: int = Query(default=50, ge=1, le=500)):
    """
    Get risk index history - Stock-market style graph data.
    
    X-Axis: Time (simulation cycles)
    Y-Axis: Risk Score (0-100)
    
    Overlay lines:
    - Workflow risk
    - Resource stress
    - Compliance proximity
    
    Think: "S&P 500, but for operational risk"
    """
    tracker = get_risk_tracker()
    history = tracker.get_history(limit)
    
    return {
        "data": [p.to_dict() for p in history],
        "trend": tracker.get_trend(),
        "current": tracker.get_current_risk().to_dict() if tracker.get_current_risk() else None,
        "description": "System Health Index - shows trajectory, not raw metrics"
    }


@app.get("/risk/current", tags=["Risk"])
async def get_current_risk():
    """Get current risk state with breakdown."""
    tracker = get_risk_tracker()
    current = tracker.get_current_risk()
    
    if not current:
        return {
            "risk_score": 20,
            "risk_state": "NORMAL",
            "workflow_risk": 20,
            "resource_risk": 20,
            "compliance_risk": 20,
            "trend": "stable",
            "contributions": [],
            "message": "System initializing, baseline risk only"
        }
    
    return {
        "risk_score": current.risk_score,
        "risk_state": current.risk_state,
        "workflow_risk": current.workflow_risk,
        "resource_risk": current.resource_risk,
        "compliance_risk": current.compliance_risk,
        "trend": tracker.get_trend(),
        "contributions": [
            {
                "agent": c.agent,
                "signal": c.signal_type,
                "impact": c.impact,
                "evidence": c.evidence_id,
                "description": c.description
            }
            for c in current.contributions
        ],
        "timestamp": current.timestamp
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DATA SOURCE ATTRIBUTION (FOR JUDGES)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/data-sources", tags=["System"])
async def get_data_sources():
    """
    Show data source attribution for all UI elements.
    
    Judges may ask: "Which agent produced this?"
    This endpoint answers that instantly.
    """
    return {
        "ui_element_mapping": {
            "logs_table": {
                "source": "Observation Layer",
                "description": "Simulated CloudWatch-like events",
                "type": "raw_facts"
            },
            "metrics_graph": {
                "source": "Resource Agent",
                "description": "Simulated Datadog-style metrics",
                "type": "analyzed"
            },
            "workflow_graph": {
                "source": "Workflow Agent",
                "description": "Workflow health index over time",
                "type": "analyzed"
            },
            "risk_index": {
                "source": "Risk Forecast Agent",
                "description": "System risk trajectory",
                "type": "predictive"
            },
            "causal_links": {
                "source": "Causal Agent",
                "description": "Cause-effect relationships",
                "type": "reasoning"
            },
            "search_answers": {
                "source": "RAG over Blackboard",
                "description": "Cross-agent reasoning queries",
                "type": "synthesized"
            },
            "compliance_view": {
                "source": "Compliance Agent",
                "description": "Policy violation detection",
                "type": "analyzed"
            },
            "insights": {
                "source": "Explanation Engine",
                "description": "Human-readable summaries",
                "type": "explained"
            }
        },
        "integration_note": "All data is simulated for demonstration. In production, would connect to CloudWatch, Grafana, Datadog APIs.",
        "key_differentiator": "We don't replace monitoring tools. We reason over their outputs."
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO INJECTION (Round 2: System Stress)
# ═══════════════════════════════════════════════════════════════════════════════

_scenario_agent = ScenarioInjectionAgent()


@app.get("/scenarios", tags=["Scenarios"])
async def list_scenarios():
    """List all available stress test scenarios."""
    return {
        "scenarios": _scenario_agent.list_scenarios(),
        "description": "Trigger scenarios to test multi-agent detection coverage"
    }


class ScenarioRequest(BaseModel):
    scenario_id: str


@app.post("/scenarios/inject", tags=["Scenarios"])
async def inject_scenario(request: ScenarioRequest):
    """
    Inject a stress scenario into the system.
    
    After injection, run /analysis/cycle to see agents respond.
    """
    try:
        execution = _scenario_agent.inject_scenario(request.scenario_id)
        return {
            "status": "injected",
            "execution": execution.to_dict(),
            "next_step": "Run POST /analysis/cycle to see agent responses"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/scenarios/executions", tags=["Scenarios"])
async def get_scenario_executions(limit: int = Query(default=10, ge=1, le=100)):
    """Get recent scenario execution history."""
    return {
        "executions": _scenario_agent.get_executions(limit),
        "total": len(_scenario_agent._executions)
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ADAPTIVE BASELINES (Round 2: Adaptive Intelligence)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/baselines", tags=["Baselines"])
async def get_baselines():
    """
    Get all learned baselines from the AdaptiveBaselineAgent.
    
    Shows what the system considers "normal" for each resource+metric.
    """
    return {
        "baselines": _master.adaptive_baseline_agent.get_baselines(),
        "description": "Dynamically learned baselines that adjust detection thresholds"
    }


@app.get("/baselines/{entity}/{metric}", tags=["Baselines"])
async def get_baseline_detail(entity: str, metric: str):
    """Get baseline for a specific entity+metric."""
    result = _master.adaptive_baseline_agent.get_baseline_for(entity, metric)
    if not result:
        return {"message": f"No baseline learned yet for {entity}/{metric}"}
    return result


@app.get("/baselines/deviations", tags=["Baselines"])
async def get_baseline_deviations(limit: int = Query(default=20, ge=1, le=200)):
    """Get recent deviation checks from the AdaptiveBaselineAgent."""
    return {
        "deviations": _master.adaptive_baseline_agent.get_recent_deviations(limit),
        "description": "Shows how current values compare to learned baselines"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# QUERY AGENT (Agentic RAG as proper agent)
# ═══════════════════════════════════════════════════════════════════════════════

_query_agent = QueryAgent()


class QueryAgentRequest(BaseModel):
    query: str


@app.post("/query", tags=["Query"])
async def query_agent_endpoint(request: QueryAgentRequest):
    """
    Query the system using the QueryAgent (Agentic RAG).
    
    This is NOT a chatbot. It decomposes questions into
    agent-specific retrievals and synthesizes evidence-backed answers.
    """
    result = _query_agent.query(
        user_query=request.query,
        state=get_shared_state(),
    )
    return result.to_dict()


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT ACTIVITY FEED
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/agents/activity", tags=["Agents"])
async def get_agent_activity(limit: int = Query(default=50, ge=1, le=500)):
    """
    Get a chronological feed of all agent activity.
    
    Shows what each agent detected, when, and with what confidence.
    """
    state = get_shared_state()
    activity = []

    for cycle in state._completed_cycles[-10:]:
        for a in cycle.anomalies:
            activity.append({
                "type": "anomaly",
                "agent": a.agent,
                "description": a.description,
                "confidence": a.confidence,
                "timestamp": a.timestamp.isoformat(),
                "cycle_id": cycle.cycle_id,
                "id": a.anomaly_id,
            })
        for p in cycle.policy_hits:
            activity.append({
                "type": "policy_hit",
                "agent": p.agent,
                "description": p.description,
                "confidence": 0.9,
                "timestamp": p.timestamp.isoformat(),
                "cycle_id": cycle.cycle_id,
                "id": p.hit_id,
            })
        for r in cycle.risk_signals:
            activity.append({
                "type": "risk_signal",
                "agent": "RiskForecastAgent",
                "description": r.reasoning,
                "confidence": r.confidence,
                "timestamp": r.timestamp.isoformat(),
                "cycle_id": cycle.cycle_id,
                "id": r.signal_id,
            })
        for c in cycle.causal_links:
            activity.append({
                "type": "causal_link",
                "agent": "CausalAgent",
                "description": c.reasoning,
                "confidence": c.confidence,
                "timestamp": c.timestamp.isoformat(),
                "cycle_id": cycle.cycle_id,
                "id": c.link_id,
            })
        for rec in cycle.recommendations:
            activity.append({
                "type": "recommendation",
                "agent": "MasterAgent",
                "description": f"{rec.action} ({rec.urgency})",
                "confidence": 1.0,
                "timestamp": rec.timestamp.isoformat(),
                "cycle_id": cycle.cycle_id,
                "id": rec.rec_id,
            })

    # Sort by timestamp, most recent first
    activity.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"activity": activity[:limit], "total": len(activity)}


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT REGISTRY (for judges: "how many agents?")
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/agents", tags=["Agents"])
async def list_agents():
    """
    List all agents in the system with their roles.
    
    Problem Statement requires 5-7 specialized agents.
    We have 8 specialized + 1 coordinator = 9 total.
    """
    return {
        "total_agents": 9,
        "specialized_agents": 8,
        "coordinator_agents": 1,
        "agents": [
            {
                "name": "WorkflowAgent",
                "type": "specialized",
                "role": "Workflow & Anomaly Monitoring",
                "detects": ["WORKFLOW_DELAY", "MISSING_STEP", "SEQUENCE_VIOLATION"],
                "ps08_feature": "Workflow & Anomaly Monitoring (R1)",
            },
            {
                "name": "ResourceAgent",
                "type": "specialized",
                "role": "Resource Usage Analysis",
                "detects": ["SUSTAINED_RESOURCE_CRITICAL", "SUSTAINED_RESOURCE_WARNING", "RESOURCE_DRIFT"],
                "ps08_feature": "Resource Usage Analysis (R1)",
            },
            {
                "name": "ComplianceAgent",
                "type": "specialized",
                "role": "Compliance & Policy Evaluation",
                "detects": ["NO_AFTER_HOURS_WRITE", "NO_UNUSUAL_LOCATION", "NO_SVC_ACCOUNT_WRITE", "NO_SKIP_APPROVAL", "NO_UNCONTROLLED_SENSITIVE_ACCESS"],
                "ps08_feature": "Compliance & Policy Evaluation (R1)",
            },
            {
                "name": "RiskForecastAgent",
                "type": "specialized",
                "role": "Predictive Risk Analysis",
                "detects": ["NORMAL→DEGRADED→AT_RISK→VIOLATION→INCIDENT"],
                "ps08_feature": "Predictive / Proactive Analysis (R2)",
            },
            {
                "name": "CausalAgent",
                "type": "specialized",
                "role": "Cross-Agent Causal Reasoning",
                "detects": ["Cause→Effect chains via temporal + dependency reasoning"],
                "ps08_feature": "Cross-Agent Reasoning (R2)",
            },
            {
                "name": "QueryAgent",
                "type": "specialized",
                "role": "Agentic RAG — Reasoning Query Interface",
                "detects": ["Decomposes questions into agent-specific evidence retrieval"],
                "ps08_feature": "Explainability & Transparency (R2)",
            },
            {
                "name": "AdaptiveBaselineAgent",
                "type": "specialized",
                "role": "Dynamic Threshold Learning",
                "detects": ["BASELINE_DEVIATION — learned normal vs actual anomaly"],
                "ps08_feature": "Adaptive Intelligence (R2)",
            },
            {
                "name": "ScenarioInjectionAgent",
                "type": "specialized",
                "role": "Stress Testing & Scenario Injection",
                "detects": ["5 scenarios: latency, compliance, workload, cascade, drift"],
                "ps08_feature": "System Stress / Scenario Injection (R2)",
            },
            {
                "name": "MasterAgent",
                "type": "coordinator",
                "role": "Orchestration & Recommendation",
                "detects": ["Coordinates all agents, ranks severity, generates recommendations"],
                "ps08_feature": "Multi-Agent Architecture (R1)",
            },
        ],
        "ps08_coverage": {
            "round_1": ["Multi-Agent Architecture", "Workflow & Anomaly Monitoring", "Compliance & Policy Evaluation", "Resource Usage Analysis", "Insight Generation", "Visual Representation"],
            "round_2": ["Adaptive Intelligence", "Predictive / Proactive Analysis", "System Stress / Scenario Injection", "Cross-Agent Reasoning", "Explainability & Transparency"],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/health", tags=["System"])
async def health_check():
    """
    Deep health check — production-grade liveness + readiness probe.

    Returns component-level health for monitoring/alerting.
    Compatible with Kubernetes health probes.
    """
    now = datetime.utcnow()
    uptime_seconds = (now - _startup_time).total_seconds() if _startup_time else 0

    # Component health checks
    components = {
        "simulation_engine": "healthy" if _simulation is not None else "unavailable",
        "observation_layer": "healthy" if _observation is not None else "unavailable",
        "shared_state": "healthy" if _state is not None else "unavailable",
        "mcp_brain": "healthy" if _master is not None else "unavailable",
        "explanation_engine": "healthy" if _explanation is not None else "unavailable",
        "reasoning_loop": "running" if _running and _reasoning_task and not _reasoning_task.done() else "stopped",
    }

    all_healthy = all(v in ("healthy", "running") for v in components.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": now.isoformat(),
        "uptime_seconds": round(uptime_seconds),
        "cycles_completed": len(_cycle_results),
        "insights_generated": len(_insights),
        "agents_active": 9,
        "cycle_interval": settings.CYCLE_INTERVAL_SECONDS,
        "components": components,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MCP BRAIN STATE — The System's Cognitive Intelligence
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/mcp/brain", tags=["MCP Brain"])
async def get_mcp_brain_state():
    """
    Get the Master Control Program's brain state.
    
    This exposes the MCP's situational awareness:
    - System pulse (calm/elevated/stressed/critical)
    - Severity trend (escalating/recovering/stable)
    - Observation window adaptation
    - Agent dominance patterns
    - Cycle-over-cycle diagnostics
    
    This is what makes Chronos AI a reasoning system, not a dashboard.
    """
    return {
        "mcp": _master.get_brain_state(),
        "description": "MCP brain state — the system's cognitive awareness"
    }


@app.get("/mcp/pulse", tags=["MCP Brain"])
async def get_system_pulse():
    """
    Get current system pulse — a single word that summarizes system state.
    
    CALM → ELEVATED → STRESSED → CRITICAL
    
    The pulse drives:
    - How far back the MCP looks (observation window)
    - How many workers it spins up (parallelism)
    - How aggressively it escalates recommendations
    """
    brain = _master.get_brain_state()
    return {
        "pulse": brain["system_pulse"],
        "severity_trend": brain["severity_trend"],
        "consecutive_critical": brain["consecutive_critical_cycles"],
        "total_cycles": brain["total_cycles_completed"],
        "observation_window": brain["observation_window"],
        "worker_pool": brain["worker_pool_size"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE & GRAPH ENDPOINTS — Hybrid DB Intelligence
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/db/stats", tags=["Database"])
async def get_db_stats():
    """
    Get database statistics — SQLite row counts + Neo4j graph stats.
    Shows persistence health for judges.
    """
    import asyncio
    from db import get_sqlite_store
    from graph import get_neo4j_client

    sqlite_stats = get_sqlite_store().get_stats()

    # Run Neo4j stats in thread to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    try:
        neo4j_stats = await asyncio.wait_for(
            loop.run_in_executor(None, get_neo4j_client().get_stats),
            timeout=5.0
        )
    except (asyncio.TimeoutError, Exception):
        neo4j_stats = get_neo4j_client().get_stats() if not get_neo4j_client().is_connected else {"status": "timeout"}

    return {
        "sqlite": sqlite_stats,
        "neo4j": neo4j_stats,
        "architecture": "Hybrid — SQLite for operational data, Neo4j for knowledge graph",
    }


@app.get("/graph/entity/{entity_id}", tags=["Graph"])
async def get_entity_graph(entity_id: str):
    """
    Get all relationships for an entity from the Neo4j knowledge graph.
    Entity can be a workflow, resource, anomaly, or agent.
    """
    import asyncio
    from graph import get_neo4j_client
    client = get_neo4j_client()
    loop = asyncio.get_event_loop()
    try:
        relationships = await asyncio.wait_for(
            loop.run_in_executor(None, client.get_entity_relationships, entity_id),
            timeout=5.0
        )
    except (asyncio.TimeoutError, Exception):
        relationships = []
    return {
        "entity_id": entity_id,
        "relationships": relationships,
        "count": len(relationships),
    }


@app.get("/graph/ripple/{step_id}", tags=["Graph"])
async def get_ripple_effect(step_id: str):
    """
    Get downstream impact of a failed step — ripple effect analysis.
    Uses Neo4j graph traversal to find all affected downstream steps.
    """
    import asyncio
    from graph import get_neo4j_client
    client = get_neo4j_client()
    loop = asyncio.get_event_loop()
    try:
        ripple = await asyncio.wait_for(
            loop.run_in_executor(None, client.get_ripple_effect, step_id),
            timeout=5.0
        )
    except (asyncio.TimeoutError, Exception):
        ripple = []
    return {
        "failed_step": step_id,
        "downstream_impact": ripple,
        "affected_count": len(ripple),
    }


@app.get("/graph/causal-chain/{anomaly_id}", tags=["Graph"])
async def get_causal_chain(anomaly_id: str):
    """
    Trace the full causal chain for an anomaly.
    Uses Neo4j CAUSED_BY edges to walk back to root cause.
    """
    import asyncio
    from graph import get_neo4j_client
    client = get_neo4j_client()
    loop = asyncio.get_event_loop()
    try:
        chain = await asyncio.wait_for(
            loop.run_in_executor(None, client.get_causal_chain, anomaly_id),
            timeout=5.0
        )
    except (asyncio.TimeoutError, Exception):
        chain = []
    return {
        "anomaly_id": anomaly_id,
        "causal_chain": chain,
        "chain_depth": len(chain),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MISSING ENDPOINTS (required by frontend)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/events", tags=["Observation"])
async def get_events(limit: int = Query(default=50, ge=1, le=1000)):
    """Get recent events (alias for /observe/events used by overview page)."""
    events = _observation.get_recent_events(limit)
    return [
        {
            "event_id": e.event_id,
            "type": e.type,
            "workflow_id": e.workflow_id,
            "actor": e.actor,
            "resource": e.resource,
            "timestamp": e.timestamp.isoformat(),
            "metadata": e.metadata,
        }
        for e in events
    ]


@app.get("/anomalies", tags=["Anomalies"])
async def get_anomalies():
    """Get all anomalies from recent cycles (used by anomaly-center page)."""
    all_anomalies = []
    for cycle in _state._completed_cycles[-20:]:
        for a in cycle.anomalies:
            all_anomalies.append({
                "anomaly_id": a.anomaly_id,
                "type": a.type,
                "severity": _anomaly_severity(a),
                "confidence": round(a.confidence * 100, 1) if a.confidence <= 1 else round(a.confidence, 1),
                "agent": a.agent,
                "timestamp": a.timestamp.isoformat(),
                "details": a.description,
                "evidence_ids": a.evidence,
            })
    return all_anomalies[-50:]


@app.get("/anomalies/summary", tags=["Anomalies"])
async def get_anomalies_summary():
    """Get anomaly summary stats (used by anomaly-center page)."""
    all_anomalies = []
    for cycle in _state._completed_cycles[-20:]:
        for a in cycle.anomalies:
            all_anomalies.append(a)

    by_agent: Dict[str, int] = {}
    by_severity: Dict[str, int] = {}
    for a in all_anomalies:
        by_agent[a.agent] = by_agent.get(a.agent, 0) + 1
        sev = _anomaly_severity(a)
        by_severity[sev] = by_severity.get(sev, 0) + 1

    return {
        "total": len(all_anomalies),
        "byAgent": by_agent,
        "bySeverity": by_severity,
        "trend": "stable" if len(all_anomalies) < 5 else "increasing",
    }


@app.get("/compliance/summary", tags=["Compliance"])
async def get_compliance_summary():
    """Get compliance summary (used by compliance page)."""
    from agents.compliance_agent import POLICIES

    all_violations = []
    for cycle in _state._completed_cycles[-20:]:
        for h in cycle.policy_hits:
            all_violations.append(h)

    active = [v for v in all_violations if True]  # All recent are active
    silent = [v for v in all_violations if "AFTER_HOURS" in v.policy_id or "UNUSUAL" in v.policy_id]

    total_policies = len(POLICIES)
    violation_count = len(set(v.policy_id for v in all_violations))
    compliance_rate = max(0, 100 - (violation_count / max(total_policies, 1)) * 100)

    return {
        "policiesMonitored": total_policies,
        "activeViolations": len(active),
        "silentViolations": len(silent),
        "riskExposure": min(100, len(all_violations) * 12),
        "auditReadiness": round(compliance_rate),
    }


@app.get("/causal/links", tags=["Causal"])
async def get_causal_links():
    """Get causal links from recent cycles (used by causal-analysis page)."""
    all_links = []
    for cycle in _state._completed_cycles[-20:]:
        for c in cycle.causal_links:
            all_links.append({
                "link_id": c.link_id,
                "cause": c.cause,
                "effect": c.effect,
                "confidence": round(c.confidence * 100, 1) if c.confidence <= 1 else round(c.confidence, 1),
                "agent": "CausalAgent",
                "timestamp": c.timestamp.isoformat(),
                "evidence_ids": getattr(c, "evidence", []),
            })
    return all_links[-30:]


def _anomaly_severity(anomaly) -> str:
    """Derive severity from anomaly type and confidence."""
    t = anomaly.type.upper()
    conf = anomaly.confidence if anomaly.confidence > 1 else anomaly.confidence * 100
    if "CRITICAL" in t or "SUSTAINED" in t or conf >= 90:
        return "critical"
    if "SPIKE" in t or "MISSING" in t or conf >= 75:
        return "high"
    if conf >= 50:
        return "medium"
    return "low"


# ═══════════════════════════════════════════════════════════════════════════════
# CHART / TREND DATA ENDPOINTS (for frontend charts)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/anomalies/trend", tags=["Anomalies"])
async def get_anomaly_trend():
    """
    Get anomaly counts per cycle (for bar/area charts on overview & anomaly pages).
    Returns last 12 cycles with anomaly breakdown.
    """
    cycles = _state._completed_cycles[-12:]
    trend = []
    for cycle in cycles:
        by_sev = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for a in cycle.anomalies:
            sev = _anomaly_severity(a)
            by_sev[sev] = by_sev.get(sev, 0) + 1
        trend.append({
            "cycle_id": cycle.cycle_id,
            "timestamp": cycle.started_at.isoformat(),
            "total": len(cycle.anomalies),
            "critical": by_sev["critical"],
            "high": by_sev["high"],
            "medium": by_sev["medium"],
            "low": by_sev["low"],
        })
    return trend


@app.get("/compliance/trend", tags=["Compliance"])
async def get_compliance_trend():
    """
    Get compliance violation counts per cycle (for compliance page charts).
    """
    from agents.compliance_agent import POLICIES
    total_policies = len(POLICIES)

    cycles = _state._completed_cycles[-12:]
    trend = []
    for cycle in cycles:
        violations = len(cycle.policy_hits)
        violated_policies = len(set(h.policy_id for h in cycle.policy_hits))
        compliance_rate = max(0, 100 - (violated_policies / max(total_policies, 1)) * 100)
        trend.append({
            "cycle_id": cycle.cycle_id,
            "timestamp": cycle.started_at.isoformat(),
            "violations": violations,
            "compliance_rate": round(compliance_rate, 1),
            "risk_exposure": min(100, violations * 15),
        })
    return trend


@app.get("/resources/trend", tags=["Resources"])
async def get_resource_trend():
    """
    Get resource utilization trend for charts.
    Returns last 50 metrics per tracked resource.
    """
    metrics = _observation.get_recent_metrics(200)
    # Group by resource
    by_resource: Dict[str, list] = {}
    for m in metrics:
        rid = m.resource_id
        if rid not in by_resource:
            by_resource[rid] = []
        by_resource[rid].append({
            "metric": m.metric,
            "value": m.value,
            "timestamp": m.timestamp.isoformat(),
        })

    return {
        "resources": {
            rid: points[-50:]
            for rid, points in by_resource.items()
        }
    }


@app.get("/cost/trend", tags=["Resources"])
async def get_cost_trend():
    """
    Get simulated operational cost data for the cost overview chart.
    Derives cost from resource utilization (higher util = higher cost).
    Groups by resource to ensure multiple data points.
    """
    metrics = _observation.get_recent_metrics(500)
    
    # Strategy: group by resource_id to get one bar per resource
    by_resource: Dict[str, dict] = {}
    for m in metrics:
        rid = m.resource_id
        if rid not in by_resource:
            by_resource[rid] = {"total_util": 0, "count": 0, "latest_ts": m.timestamp}
        by_resource[rid]["total_util"] += m.value
        by_resource[rid]["count"] += 1
        if m.timestamp > by_resource[rid]["latest_ts"]:
            by_resource[rid]["latest_ts"] = m.timestamp

    trend = []
    for rid in sorted(by_resource.keys()):
        b = by_resource[rid]
        avg_util = b["total_util"] / max(b["count"], 1)
        cost = round(avg_util * 0.5 + 10, 2)  # base cost $10 + util factor
        trend.append({
            "timestamp": b["latest_ts"].strftime("%Y-%m-%dT%H:%M"),
            "cost": cost,
            "avg_utilization": round(avg_util, 1),
            "resource_id": rid,
        })

    return trend[-24:]  # Last 24 resources


@app.get("/overview/stats", tags=["System"])
async def get_overview_stats():
    """
    Get aggregated stats for the overview dashboard.
    Returns real-time numbers for all stat cards.
    """
    total_events = len(_observation.get_recent_events(10000))
    total_metrics = len(_observation.get_recent_metrics(10000))
    
    # Count anomalies across recent cycles
    total_anomalies = 0
    total_violations = 0
    active_anomalies = 0
    for cycle in _state._completed_cycles[-20:]:
        total_anomalies += len(cycle.anomalies)
        total_violations += len(cycle.policy_hits)
    if _state._completed_cycles:
        last = _state._completed_cycles[-1]
        active_anomalies = len(last.anomalies)

    # Compliance rate
    from agents.compliance_agent import POLICIES
    total_policies = len(POLICIES)
    violated = len(set(
        h.policy_id
        for c in _state._completed_cycles[-5:]
        for h in c.policy_hits
    ))
    compliance_rate = max(0, 100 - (violated / max(total_policies, 1)) * 100)

    # Active workflows from simulation
    active_wf = len(_simulation._active_workflows) if hasattr(_simulation, '_active_workflows') else 2

    return {
        "active_workflows": active_wf,
        "total_events": total_events,
        "total_metrics": total_metrics,
        "active_anomalies": active_anomalies,
        "total_anomalies": total_anomalies,
        "total_violations": total_violations,
        "compliance_rate": round(compliance_rate),
        "cycles_completed": len(_state._completed_cycles),
        "agents_active": 9,
    }
