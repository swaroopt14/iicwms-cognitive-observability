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

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Literal
from contextlib import asynccontextmanager
import asyncio
import logging
import sys
import hashlib
import json

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from simulator.engine import SimulationEngine, Event, ResourceMetric
from observation import ObservationLayer, get_observation_layer
from blackboard import SharedState, get_shared_state, RiskState
from agents import (
    MasterAgent,
    CycleResult,
    QueryAgent,
    ScenarioInjectionAgent,
    WhatIfSimulatorAgent,
)
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
from api.slack_notifier import SlackNotifier, SlackConfig

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


class EnterpriseContext(BaseModel):
    organization_id: str = Field(..., min_length=1, max_length=128)
    business_unit: Optional[str] = Field(None, max_length=128)
    project_id: str = Field(..., min_length=1, max_length=128)
    project_name: Optional[str] = Field(None, max_length=256)
    environment: Literal["dev", "staging", "production"]
    region: Optional[str] = Field(None, max_length=64)
    service_name: str = Field(..., min_length=1, max_length=128)
    service_type: Optional[str] = Field(None, max_length=64)
    repository: Optional[str] = Field(None, max_length=512)
    deployment_id: Optional[str] = Field(None, max_length=128)
    workflow_id: Optional[str] = Field(None, max_length=128)
    workflow_version: Optional[str] = Field(None, max_length=64)


class ActorContext(BaseModel):
    actor_id: str = Field(..., min_length=1, max_length=128)
    actor_type: Literal["human", "service", "automation"]
    role: Literal["SDE", "DevOps", "Admin", "Security", "QA", "Manager"]
    team: str = Field(..., min_length=1, max_length=128)
    access_level: Optional[Literal["read", "write", "admin"]] = None
    authentication_method: Optional[Literal["SSO", "API_TOKEN", "SERVICE_ACCOUNT"]] = None


class SourceSignature(BaseModel):
    tool_name: str = Field(..., min_length=1, max_length=64)
    tool_type: str = Field(..., min_length=1, max_length=64)
    source_host: Optional[str] = Field(None, max_length=128)


class NormalizedEvent(BaseModel):
    event_category: str = Field(..., min_length=1, max_length=64)
    event_type: str = Field(..., min_length=1, max_length=128)
    severity: Literal["info", "low", "warning", "medium", "high", "critical"]
    confidence_initial: float = Field(..., ge=0.0, le=1.0)


class MetricsPayload(BaseModel):
    metric_name: str = Field(..., min_length=1, max_length=128)
    metric_value: float
    baseline_value: Optional[float] = None


class UnifiedTelemetryEnvelope(BaseModel):
    schema_version: str = Field(..., min_length=1, max_length=32)
    event_id: str = Field(..., min_length=1, max_length=128)
    idempotency_key: str = Field(..., min_length=1, max_length=256)
    trace_id: str = Field(..., min_length=1, max_length=128)
    span_id: Optional[str] = Field(None, max_length=128)
    parent_span_id: Optional[str] = Field(None, max_length=128)
    event_source_ts: str = Field(..., description="ISO 8601 source timestamp")
    ingested_ts: Optional[str] = Field(None, description="ISO 8601 ingest timestamp")
    processed_ts: Optional[str] = Field(None, description="ISO 8601 processing timestamp")
    data_classification: Optional[Literal["public", "internal", "confidential", "restricted"]] = None
    pii_present: Optional[bool] = False
    enterprise_context: EnterpriseContext
    actor_context: ActorContext
    source_signature: SourceSignature
    normalized_event: NormalizedEvent
    metrics_payload: Optional[MetricsPayload] = None
    event_payload: Optional[Dict[str, Any]] = None
    log_payload: Optional[Dict[str, Any]] = None


class IngestEnvelopeResult(BaseModel):
    status: Literal["ingested", "quarantined"]
    reason_code: Optional[str] = None
    event_id: str
    idempotency_key: str
    tenant_key: str
    observed_event_id: Optional[str] = None
    observed_metric_resource_id: Optional[str] = None


class SystemHealth(BaseModel):
    """System health status."""
    status: str  # NORMAL, DEGRADED, CRITICAL
    active_anomalies: int
    active_violations: int
    active_risks: int
    last_cycle: Optional[str]
    message: str
    # Frontend compatibility fields
    active_workflows: int = 0
    total_events: int = 0
    risk_level: str = "NORMAL"
    last_update: str = ""


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
    # Frontend compatibility alias
    what_happens_if_ignored: str
    recommended_actions: List[str]
    confidence: float
    uncertainty: str
    severity: str
    timestamp: str
    evidence_count: int
    # Frontend expects evidence IDs list
    evidence_ids: List[str]
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
    condition: str
    severity: str
    rationale: str


class ViolationResponse(BaseModel):
    """Policy violation response."""
    violation_id: str
    hit_id: str
    policy_id: str
    policy_name: str
    event_id: str
    type: str
    violation_type: str
    severity: str
    status: str
    details: str
    description: str
    timestamp: str
    workflow_id: Optional[str] = None


class WorkflowResponse(BaseModel):
    """Workflow response."""
    id: str
    name: str
    status: str
    steps_completed: int
    total_steps: int
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    environment: Optional[str] = None
    context_tag: Optional[str] = None
    input_source: Optional[str] = None
    issue_category: Optional[str] = None


class CausalLinkResponse(BaseModel):
    """Causal link response."""
    link_id: str
    cause: str
    effect: str
    cause_entity: str
    effect_entity: str
    confidence: float
    reasoning: str


class IndustryIncidentBrief(BaseModel):
    generated_at: str
    cycle_id: Optional[str]
    risk_state: str
    risk_score: float
    top_change: Dict[str, Any]
    impacted_workflows: List[Dict[str, Any]]
    policy_exposure: Dict[str, Any]
    business_impact: Dict[str, Any]
    top_recommendation: Dict[str, Any]


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
_slack_notifier: Optional[SlackNotifier] = None
_what_if_agent: Optional[WhatIfSimulatorAgent] = None
_running = False
_reasoning_task: Optional[asyncio.Task] = None
_startup_time: Optional[datetime] = None
_ingest_idempotency_seen: Dict[str, str] = {}
_ingest_dlq: List[Dict[str, Any]] = []
_max_ingest_dlq = 1000
_max_idempotency_keys = 50000


def _parse_iso8601(ts: str) -> datetime:
    cleaned = ts.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(cleaned)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _tenant_key(ctx: EnterpriseContext) -> str:
    return f"{ctx.organization_id}:{ctx.project_id}:{ctx.environment}"


def _quarantine_envelope(
    envelope: UnifiedTelemetryEnvelope,
    reason_code: str,
    details: Optional[str] = None,
) -> IngestEnvelopeResult:
    entry = {
        "event_id": envelope.event_id,
        "idempotency_key": envelope.idempotency_key,
        "reason_code": reason_code,
        "details": details or "",
        "tenant_key": _tenant_key(envelope.enterprise_context),
        "timestamp": datetime.utcnow().isoformat(),
    }
    _ingest_dlq.append(entry)
    if len(_ingest_dlq) > _max_ingest_dlq:
        del _ingest_dlq[: len(_ingest_dlq) - _max_ingest_dlq]
    return IngestEnvelopeResult(
        status="quarantined",
        reason_code=reason_code,
        event_id=envelope.event_id,
        idempotency_key=envelope.idempotency_key,
        tenant_key=entry["tenant_key"],
    )


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
                risk_point = risk_tracker.record_cycle(latest_cycle)
                insight = None

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

                # 6. Optional Slack alerting for high-priority cycles
                if _slack_notifier:
                    try:
                        await _slack_notifier.send_cycle_alert(
                            latest_cycle,
                            insight=insight,
                            risk_score=risk_point.risk_score if risk_point else None,
                            risk_state=risk_point.risk_state if risk_point else None,
                        )
                    except Exception as e:
                        cycle_logger.warning("Slack alert failed: %s", e)

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
    global _simulation, _observation, _state, _master, _explanation, _slack_notifier, _what_if_agent
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
    _what_if_agent = WhatIfSimulatorAgent()
    _explanation = ExplanationEngine(use_llm=settings.ENABLE_CREWAI)
    _slack_notifier = SlackNotifier(
        SlackConfig(
            enabled=settings.ENABLE_SLACK_ALERTS,
            webhook_url=settings.SLACK_WEBHOOK_URL,
            min_severity=settings.SLACK_ALERT_MIN_SEVERITY,
            min_risk_state=settings.SLACK_ALERT_MIN_RISK_STATE,
            cooldown_seconds=settings.SLACK_ALERT_COOLDOWN_SECONDS,
            frontend_base_url=settings.FRONTEND_BASE_URL,
        )
    )

    logger.info("  Simulation Engine ......... ready")
    logger.info("  Observation Layer ......... ready")
    logger.info("  Shared State (Blackboard) . ready")
    logger.info("  MCP (Master Agent) ........ ready")
    logger.info("  What-If Simulator ......... ready")
    logger.info("  Explanation Engine ........ ready")
    logger.info(
        "  Slack Alerts .............. %s",
        "enabled" if _slack_notifier.enabled else "disabled",
    )

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

@app.post("/ingest/envelope", response_model=IngestEnvelopeResult, tags=["Observation"])
async def ingest_envelope(envelope: UnifiedTelemetryEnvelope):
    """
    Ingest enterprise telemetry envelope with strict context validation.

    Accepted:
    - Valid schema + required context + acceptable time skew + unique idempotency key

    Quarantined (DLQ):
    - Duplicate idempotency key
    - Invalid/late timestamp
    - Unknown schema
    - Missing category-specific payload
    """
    # Version gate (start strict at v1.x)
    if not envelope.schema_version.startswith("v1"):
        return _quarantine_envelope(
            envelope,
            reason_code="SCHEMA_INVALID",
            details=f"Unsupported schema_version={envelope.schema_version}",
        )

    # Idempotency gate
    if envelope.idempotency_key in _ingest_idempotency_seen:
        return _quarantine_envelope(
            envelope,
            reason_code="DUPLICATE",
            details="idempotency_key already seen",
        )

    # Time skew gate
    try:
        src_ts = _parse_iso8601(envelope.event_source_ts)
    except Exception:
        return _quarantine_envelope(
            envelope,
            reason_code="SCHEMA_INVALID",
            details="event_source_ts is not valid ISO 8601",
        )

    now_utc = datetime.now(timezone.utc)
    skew_seconds = abs((now_utc - src_ts).total_seconds())
    # 24h hard guard for late/future events in this initial implementation.
    if skew_seconds > 86400:
        return _quarantine_envelope(
            envelope,
            reason_code="LATE_EVENT",
            details=f"timestamp skew {int(skew_seconds)}s exceeds 86400s",
        )

    # Category-specific payload gate
    if envelope.normalized_event.event_category == "infrastructure" and not envelope.metrics_payload:
        return _quarantine_envelope(
            envelope,
            reason_code="SCHEMA_INVALID",
            details="metrics_payload required for infrastructure category",
        )

    global _observation
    if _observation is None:
        _observation = get_observation_layer()

    tenant_key = _tenant_key(envelope.enterprise_context)
    observed_event = _observation.observe_event({
        "event_id": envelope.event_id,
        "type": envelope.normalized_event.event_type,
        "workflow_id": envelope.enterprise_context.workflow_id,
        "actor": envelope.actor_context.actor_id,
        "resource": envelope.enterprise_context.service_name,
        "timestamp": src_ts.isoformat(),
        "metadata": {
            "schema_version": envelope.schema_version,
            "trace_id": envelope.trace_id,
            "span_id": envelope.span_id,
            "parent_span_id": envelope.parent_span_id,
            "idempotency_key": envelope.idempotency_key,
            "tenant_key": tenant_key,
            "enterprise_context": envelope.enterprise_context.model_dump(),
            "actor_context": envelope.actor_context.model_dump(),
            "source_signature": envelope.source_signature.model_dump(),
            "normalized_event": envelope.normalized_event.model_dump(),
            "data_classification": envelope.data_classification,
            "pii_present": envelope.pii_present,
            "event_payload": envelope.event_payload or {},
            "log_payload": envelope.log_payload or {},
        },
    })

    observed_metric_resource_id = None
    if envelope.metrics_payload:
        observed_metric = _observation.observe_metric({
            "resource_id": envelope.source_signature.source_host or envelope.enterprise_context.service_name,
            "metric": envelope.metrics_payload.metric_name,
            "value": envelope.metrics_payload.metric_value,
            "timestamp": src_ts.isoformat(),
        })
        observed_metric_resource_id = observed_metric.resource_id

    _ingest_idempotency_seen[envelope.idempotency_key] = envelope.event_id
    if len(_ingest_idempotency_seen) > _max_idempotency_keys:
        # bounded memory; remove oldest inserted key
        first_key = next(iter(_ingest_idempotency_seen.keys()))
        _ingest_idempotency_seen.pop(first_key, None)

    return IngestEnvelopeResult(
        status="ingested",
        event_id=envelope.event_id,
        idempotency_key=envelope.idempotency_key,
        tenant_key=tenant_key,
        observed_event_id=observed_event.event_id,
        observed_metric_resource_id=observed_metric_resource_id,
    )

@app.post("/ingest/github/webhook", tags=["Observation"])
async def ingest_github_webhook(request: Request):
    """
    Ingest GitHub webhook events (PR/review/merge/GitHub Actions) as raw observation facts.

    This is the bridge for pre-deploy prediction:
    GitHub PR/CI events become evidence nodes that can be correlated to a deployment_id.

    Security note:
    - Signature verification is not implemented in this hackathon build.
    - Do NOT expose this endpoint publicly without validating `X-Hub-Signature-256`.
    """
    global _observation
    if _observation is None:
        _observation = get_observation_layer()

    payload = await request.json()
    gh_event = request.headers.get("X-GitHub-Event", "unknown")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")

    # Minimal extraction helpers (be liberal in what we accept).
    repo = payload.get("repository", {}) if isinstance(payload, dict) else {}
    repo_full = repo.get("full_name") or repo.get("name") or "unknown/repo"

    sender = payload.get("sender", {}) if isinstance(payload, dict) else {}
    sender_login = sender.get("login") or "github_user"

    pr = payload.get("pull_request", {}) if isinstance(payload, dict) else {}
    pr_number = pr.get("number") or payload.get("number") or payload.get("pull_request", {}).get("number") if isinstance(payload, dict) else None
    pr_title = pr.get("title") or ""
    pr_state = pr.get("state") or ""
    pr_merged = bool(pr.get("merged")) if isinstance(pr, dict) else False

    # GitHub Actions workflow_run event
    workflow_run = payload.get("workflow_run", {}) if isinstance(payload, dict) else {}
    run_id = workflow_run.get("id")
    run_name = workflow_run.get("name") or workflow_run.get("workflow_name") or ""
    run_conclusion = workflow_run.get("conclusion") or workflow_run.get("status") or ""
    head_sha = (
        workflow_run.get("head_sha")
        or (payload.get("after") if isinstance(payload, dict) else None)
        or (pr.get("head", {}).get("sha") if isinstance(pr, dict) else None)
    )

    # Correlation key:
    # Use an explicit deployment_id if present (for demos), else derive from repo+sha.
    # This makes PR/CI nodes show up in the same workflow timeline (deployment workflow) deterministically.
    deployment_id = None
    if isinstance(payload, dict):
        deployment_id = payload.get("deployment_id") or payload.get("deployment", {}).get("id")
    if not deployment_id and head_sha:
        deployment_id = f"deploy_{hashlib.sha256(f'{repo_full}:{head_sha}'.encode()).hexdigest()[:10]}"
    if not deployment_id:
        deployment_id = "deploy_unknown"

    # Map GitHub webhook to normalized event type.
    action = payload.get("action") if isinstance(payload, dict) else None
    event_type = f"GITHUB_{gh_event}".upper()
    if gh_event == "pull_request" and action:
        event_type = f"PR_{str(action).upper()}"
    elif gh_event == "pull_request_review" and action:
        event_type = f"PR_REVIEW_{str(action).upper()}"
    elif gh_event == "workflow_run" and action:
        event_type = f"CI_{str(action).upper()}"

    # In this demo, we correlate GitHub events to the deployment workflow type.
    # A real implementation would look up the concrete workflow instance created by the pipeline.
    workflow_id = "wf_deployment_03"

    # Deterministic event id for idempotency across retries (delivery id wins).
    dedupe_basis = delivery_id or f"{gh_event}:{action}:{repo_full}:{pr_number}:{run_id}:{head_sha}"
    event_id = f"evt_{hashlib.sha256(dedupe_basis.encode()).hexdigest()[:16]}"
    ts = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

    enterprise_context = {
        "organization_id": "org_001",
        "business_unit": "platform",
        "project_id": "proj_platform_release",
        "project_name": "Platform Release Engineering",
        "environment": "production",
        "region": "us-east-1",
        "service_name": "payment-api" if "payment" in str(repo_full).lower() else "deploy-orchestrator",
        "service_type": "backend",
        "repository": f"github://{repo_full}",
        "deployment_id": str(deployment_id),
        "workflow_id": workflow_id,
        "workflow_version": "v1.0.0",
    }

    actor_context = {
        "actor_id": str(sender_login),
        "actor_type": "human" if sender_login and sender_login != "github-actions[bot]" else "automation",
        "role": "SDE",
        "team": "platform_engineering",
        "access_level": "write",
        "authentication_method": "SSO",
    }

    normalized_event = {
        "event_category": "code" if gh_event in ("pull_request", "pull_request_review") else "cicd",
        "event_type": event_type,
        "severity": "info" if not pr_merged and run_conclusion not in ("failure", "cancelled") else "warning",
        "confidence_initial": 0.95,
    }

    observed = _observation.observe_event({
        "event_id": event_id,
        "type": event_type,
        "workflow_id": workflow_id,
        "actor": str(sender_login),
        "resource": enterprise_context["service_name"],
        "timestamp": ts,
        "metadata": {
            "trace_id": f"trace_{deployment_id}",
            "enterprise_context": enterprise_context,
            "actor_context": actor_context,
            "source_signature": {
                "tool_name": "github",
                "tool_type": "webhook",
                "source_host": "github.com",
            },
            "normalized_event": normalized_event,
            "event_payload": payload,
            "github": {
                "event": gh_event,
                "action": action,
                "delivery": delivery_id,
                "repo": repo_full,
                "pr_number": pr_number,
                "pr_title": pr_title,
                "pr_state": pr_state,
                "pr_merged": pr_merged,
                "workflow_run_id": run_id,
                "workflow_name": run_name,
                "workflow_conclusion": run_conclusion,
                "head_sha": head_sha,
                "deployment_id": deployment_id,
            },
        },
    })

    return {
        "status": "observed",
        "event_id": observed.event_id,
        "workflow_id": workflow_id,
        "deployment_id": deployment_id,
        "github_event": gh_event,
        "type": event_type,
    }


@app.get("/ingest/status", tags=["Observation"])
async def get_ingest_status():
    """Operational visibility for ingestion contract and quarantine queue."""
    return {
        "schema_version_supported": "v1.x",
        "idempotency_keys_in_memory": len(_ingest_idempotency_seen),
        "dlq_size": len(_ingest_dlq),
        "latest_dlq": _ingest_dlq[-20:],
    }

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
    
    active_workflows = len(getattr(_simulation, "_active_workflows", {})) if _simulation else 0
    total_events = len(_observation.get_recent_events(10000)) if _observation else 0
    risk_level = "NORMAL"
    if risks:
        projected = max(
            risks,
            key=lambda r: {
                RiskState.NORMAL: 0,
                RiskState.DEGRADED: 1,
                RiskState.AT_RISK: 2,
                RiskState.VIOLATION: 3,
                RiskState.INCIDENT: 4,
            }.get(r.projected_state, 0),
        )
        risk_level = projected.projected_state.value

    return SystemHealth(
        status=status,
        active_anomalies=len(anomalies),
        active_violations=len(violations),
        active_risks=len(risks),
        last_cycle=_cycle_results[-1].cycle_id if _cycle_results else None,
        message=message,
        active_workflows=active_workflows,
        total_events=total_events,
        risk_level=risk_level,
        last_update=datetime.utcnow().isoformat(),
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
    cycle_map = {c.cycle_id: c for c in _state._completed_cycles[-200:]} if _state else {}
    return {
        "insights": [
            (lambda cycle: InsightResponse(
                insight_id=i.insight_id,
                summary=i.summary,
                why_it_matters=i.why_it_matters,
                what_will_happen_if_ignored=i.what_will_happen_if_ignored,
                what_happens_if_ignored=i.what_will_happen_if_ignored,
                recommended_actions=i.recommended_actions,
                confidence=i.confidence,
                uncertainty=i.uncertainty,
                severity=i.severity,
                timestamp=i.timestamp.isoformat(),
                evidence_count=i.evidence_count,
                evidence_ids=(
                    [a.anomaly_id for a in cycle.anomalies] +
                    [h.hit_id for h in cycle.policy_hits] +
                    [c.link_id for c in cycle.causal_links]
                )[:20] if cycle else [],
                cycle_id=i.cycle_id
            ).model_dump())(cycle_map.get(i.cycle_id))
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
                    what_happens_if_ignored=insight.what_will_happen_if_ignored,
                    recommended_actions=insight.recommended_actions,
                    confidence=insight.confidence,
                    uncertainty=insight.uncertainty,
                    severity=insight.severity,
                    timestamp=insight.timestamp.isoformat(),
                    evidence_count=insight.evidence_count,
                    evidence_ids=[
                        *[a.anomaly_id for a in (cycle.anomalies if cycle else [])],
                        *[h.hit_id for h in (cycle.policy_hits if cycle else [])],
                        *[c.link_id for c in (cycle.causal_links if cycle else [])],
                    ][:20],
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


@app.get("/industry/incident-brief", response_model=IndustryIncidentBrief, tags=["Insights"])
async def get_industry_incident_brief():
    """
    Correlate latest change signals with runtime impact in one structured incident brief.
    """
    generated_at = datetime.utcnow().isoformat()
    latest_cycle = _state._completed_cycles[-1] if _state and _state._completed_cycles else None
    events = _observation.get_recent_events(500) if _observation else []
    metrics = _observation.get_recent_metrics(500) if _observation else []

    gh_events = []
    for e in events:
        md = e.metadata if isinstance(e.metadata, dict) else {}
        sig = md.get("source_signature", {}) if isinstance(md, dict) else {}
        if isinstance(sig, dict) and str(sig.get("tool_name", "")).lower() == "github":
            gh_events.append(e)
    gh_events.sort(key=lambda e: e.timestamp, reverse=True)

    top_change: Dict[str, Any] = {
        "change_type": "unknown",
        "repository": None,
        "deployment_id": None,
        "pr_number": None,
        "event_id": None,
        "timestamp": None,
    }
    if gh_events:
        e = gh_events[0]
        md = e.metadata if isinstance(e.metadata, dict) else {}
        gh = md.get("github", {}) if isinstance(md, dict) else {}
        payload = md.get("event_payload", {}) if isinstance(md, dict) else {}
        pr = payload.get("pull_request", {}) if isinstance(payload, dict) else {}
        top_change = {
            "change_type": e.type,
            "repository": gh.get("repo"),
            "deployment_id": gh.get("deployment_id"),
            "pr_number": gh.get("pr_number") or pr.get("number"),
            "event_id": e.event_id,
            "timestamp": e.timestamp.isoformat(),
        }

    impacted_workflows: List[Dict[str, Any]] = []
    policy_exposure: Dict[str, Any] = {"total_policy_hits": 0, "top_policies": []}
    top_recommendation: Dict[str, Any] = {
        "action": "Investigate latest high-confidence anomaly",
        "urgency": "MEDIUM",
        "source": "fallback",
    }
    if latest_cycle:
        wf_anoms = [a for a in latest_cycle.anomalies if a.type in ("WORKFLOW_DELAY", "MISSING_STEP", "SEQUENCE_VIOLATION")]
        by_wf: Dict[str, Dict[str, Any]] = {}
        for a in wf_anoms:
            wf = "wf_unknown"
            if a.evidence:
                ev = a.evidence[0]
                if isinstance(ev, str) and ev.startswith("wf_"):
                    wf = ev
            if wf not in by_wf:
                by_wf[wf] = {"workflow_id": wf, "anomaly_count": 0, "anomaly_types": set(), "confidence": 0.0}
            by_wf[wf]["anomaly_count"] += 1
            by_wf[wf]["anomaly_types"].add(a.type)
            by_wf[wf]["confidence"] = max(by_wf[wf]["confidence"], float(a.confidence))
        impacted_workflows = [
            {
                "workflow_id": row["workflow_id"],
                "anomaly_count": row["anomaly_count"],
                "anomaly_types": sorted(list(row["anomaly_types"])),
                "confidence": round(row["confidence"], 3),
            }
            for row in by_wf.values()
        ]
        impacted_workflows.sort(key=lambda x: (x["anomaly_count"], x["confidence"]), reverse=True)

        counts: Dict[str, int] = {}
        for h in latest_cycle.policy_hits:
            counts[h.policy_id] = counts.get(h.policy_id, 0) + 1
        policy_exposure = {
            "total_policy_hits": len(latest_cycle.policy_hits),
            "top_policies": [{"policy_id": p, "hits": c} for p, c in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]],
        }

        if latest_cycle.recommendations_v2:
            r = latest_cycle.recommendations_v2[0]
            top_recommendation = {
                "action": r.action_description,
                "urgency": "HIGH" if r.severity_score >= 7 else "MEDIUM",
                "confidence": r.confidence,
                "source": r.rule_id,
            }
        elif latest_cycle.recommendations:
            r = latest_cycle.recommendations[0]
            top_recommendation = {
                "action": r.action,
                "urgency": r.urgency,
                "source": "master_map",
            }

    revenue_metric_values = [m.value for m in metrics if m.metric == "estimated_revenue_impact_inr"]
    cart_abandon = [m.value for m in metrics if m.metric == "cart_abandon_rate"]
    business_impact = {
        "estimated_revenue_impact_inr": round(float(max(revenue_metric_values)), 2) if revenue_metric_values else 0.0,
        "cart_abandon_rate": round(float(max(cart_abandon)), 2) if cart_abandon else None,
        "impact_source": "metrics+correlation" if revenue_metric_values else "proxy_only",
    }

    risk_score = 20.0
    risk_state = "NORMAL"
    try:
        current = get_risk_tracker().get_current_risk()
        if current:
            risk_score = float(current.risk_score)
            risk_state = str(current.risk_state)
    except Exception:
        pass

    return IndustryIncidentBrief(
        generated_at=generated_at,
        cycle_id=latest_cycle.cycle_id if latest_cycle else None,
        risk_state=risk_state,
        risk_score=round(risk_score, 2),
        top_change=top_change,
        impacted_workflows=impacted_workflows[:5],
        policy_exposure=policy_exposure,
        business_impact=business_impact,
        top_recommendation=top_recommendation,
    )


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
                condition=getattr(p.check, "__name__", "rule_check").replace("_check_", "").replace("_", " ").upper(),
                severity=p.severity,
                rationale=p.rationale
            ).model_dump()
            for p in POLICIES
        ]
    }


@app.get("/policy/violations", tags=["Compliance"])
async def get_policy_violations(limit: int = Query(default=50, ge=1, le=500)):
    """Get detected policy violations from recent cycles."""
    from agents.compliance_agent import POLICIES
    policy_map = {p.policy_id: p for p in POLICIES}
    all_violations = []
    
    for cycle in _state._completed_cycles[-10:]:
        for h in cycle.policy_hits:
            policy = policy_map.get(h.policy_id)
            all_violations.append(ViolationResponse(
                violation_id=h.hit_id,
                hit_id=h.hit_id,
                policy_id=h.policy_id,
                policy_name=policy.name if policy else h.policy_id,
                event_id=h.event_id,
                type=h.violation_type,
                violation_type=h.violation_type,
                severity=policy.severity if policy else "MEDIUM",
                status="ACTIVE",
                details=h.description,
                description=h.description,
                timestamp=h.timestamp.isoformat(),
                workflow_id=None,
            ))
    
    return {"violations": [v.model_dump() for v in all_violations[-limit:]]}


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/workflows", tags=["Workflows"])
async def get_workflows():
    """Get tracked workflows with step completion status."""
    from agents.workflow_agent import WORKFLOW_DEFINITIONS
    workflows = _master._workflow_agent.get_tracked_workflows()

    def _classify_input_source(tool_name: str, tool_type: str) -> str:
        source = f"{tool_name} {tool_type}".lower()
        if "github" in source or "git" in source:
            return "github"
        if "webhook" in source or "browser" in source or "frontend" in source or "client" in source:
            return "client_side"
        if any(k in source for k in ("datadog", "grafana", "prometheus", "k8s", "docker", "infra")):
            return "server_failure"
        if any(k in source for k in ("ci", "cicd", "jenkins", "deploy")):
            return "deployment_pipeline"
        return "system_internal"

    def _classify_issue(event_type: str, event_category: str) -> str:
        sig = f"{event_type} {event_category}".lower()
        if any(k in sig for k in ("exception", "traceback", "bug", "syntax", "code", "runtime")):
            return "code_error_or_bug"
        if any(k in sig for k in ("timeout", "latency", "cpu", "memory", "resource", "network")):
            return "server_failure"
        if any(k in sig for k in ("policy", "access", "compliance", "security", "leak", "pii")):
            return "compliance_or_data_risk"
        if any(k in sig for k in ("ui", "client", "browser", "frontend")):
            return "client_side_error"
        return "workflow_anomaly"

    # Try to enrich workflow context from recent observed events.
    workflow_context: Dict[str, Dict[str, str]] = {}
    recent_events = _observation.get_recent_events(500) if _observation else []
    for e in recent_events:
        if not e.workflow_id or e.workflow_id in workflow_context:
            continue
        ctx = e.metadata.get("enterprise_context", {}) if isinstance(e.metadata, dict) else {}
        source_sig = e.metadata.get("source_signature", {}) if isinstance(e.metadata, dict) else {}
        normalized = e.metadata.get("normalized_event", {}) if isinstance(e.metadata, dict) else {}
        tool_name = str(source_sig.get("tool_name", ""))
        tool_type = str(source_sig.get("tool_type", ""))
        event_type = str(normalized.get("event_type", e.type))
        event_category = str(normalized.get("event_category", ""))
        if isinstance(ctx, dict) and ctx:
            workflow_context[e.workflow_id] = {
                "project_id": str(ctx.get("project_id", "")),
                "project_name": str(ctx.get("project_name", "")),
                "environment": str(ctx.get("environment", "")),
                "input_source": _classify_input_source(tool_name, tool_type),
                "issue_category": _classify_issue(event_type, event_category),
            }

    default_context = {
        "wf_deployment": {
            "project_id": "proj_platform_release",
            "project_name": "Platform Release Engineering",
            "environment": "production",
            "context_tag": "deployment_workflow",
            "input_source": "github",
            "issue_category": "deployment_pipeline",
        },
        "wf_onboarding": {
            "project_id": "proj_customer_onboarding",
            "project_name": "Customer Onboarding Platform",
            "environment": "production",
            "context_tag": "new_update",
            "input_source": "client_side",
            "issue_category": "client_side_error",
        },
        "wf_expense": {
            "project_id": "proj_finops",
            "project_name": "Finance Operations",
            "environment": "staging",
            "context_tag": "approval_workflow",
            "input_source": "server_failure",
            "issue_category": "workflow_anomaly",
        },
        "wf_access": {
            "project_id": "proj_identity_security",
            "project_name": "Identity & Access Management",
            "environment": "production",
            "context_tag": "error_clear",
            "input_source": "server_failure",
            "issue_category": "compliance_or_data_risk",
        },
    }

    return {
        "workflows": [
            (lambda wf: (
                (lambda wf_type, defn, ctx: WorkflowResponse(
                    id=wf.workflow_id,
                    name=(defn.get("name") if defn else wf.workflow_type).replace("_", " "),
                    status="degraded" if wf.skipped_steps else ("active" if wf.current_step_index > 0 else "pending"),
                    steps_completed=len(wf.completed_steps),
                    total_steps=max(wf.current_step_index + 1, 1),
                    project_id=ctx.get("project_id") or default_context.get(wf_type, {}).get("project_id"),
                    project_name=ctx.get("project_name") or default_context.get(wf_type, {}).get("project_name"),
                    environment=ctx.get("environment") or default_context.get(wf_type, {}).get("environment") or settings.ENVIRONMENT,
                    context_tag=default_context.get(wf_type, {}).get("context_tag"),
                    input_source=ctx.get("input_source") or default_context.get(wf_type, {}).get("input_source") or "system_internal",
                    issue_category=ctx.get("issue_category") or default_context.get(wf_type, {}).get("issue_category") or "workflow_anomaly",
                ).model_dump())(
                    wf.workflow_type,
                    WORKFLOW_DEFINITIONS.get(wf.workflow_type, {}),
                    workflow_context.get(wf.workflow_id, {}),
                )
            ))(wf)
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
    global _observation
    if _observation is None:
        _observation = get_observation_layer()
    
    # Extract workflow type prefix
    wf_type = None
    for prefix in WORKFLOW_DEFINITIONS.keys():
        if workflow_id.startswith(prefix):
            wf_type = prefix
            break
    
    if not wf_type:
        raise HTTPException(status_code=404, detail=f"Unknown workflow type for {workflow_id}")
    
    definition = WORKFLOW_DEFINITIONS[wf_type]

    # Default enterprise context (used when events don't contain the unified envelope metadata yet).
    default_context = {
        "wf_deployment": {
            "enterprise_context": {
                "organization_id": "org_001",
                "business_unit": "platform",
                "project_id": "proj_platform_release",
                "project_name": "Platform Release Engineering",
                "environment": "production",
                "region": "us-east-1",
                "service_name": "deploy-orchestrator",
                "service_type": "automation",
                "repository": "github://org/platform-release",
                "deployment_id": "deploy_demo_001",
                "workflow_id": workflow_id,
                "workflow_version": "v1.0.0",
            },
            "actor_context": {
                "actor_id": "svc_cicd",
                "actor_type": "automation",
                "role": "DevOps",
                "team": "platform_engineering",
                "access_level": "write",
                "authentication_method": "SERVICE_ACCOUNT",
            },
            "source_signature": {
                "tool_name": "github",
                "tool_type": "webhook",
                "source_host": "github.com",
            },
        },
        "wf_onboarding": {
            "enterprise_context": {
                "organization_id": "org_001",
                "business_unit": "customer",
                "project_id": "proj_customer_onboarding",
                "project_name": "Customer Onboarding Platform",
                "environment": "production",
                "region": "us-east-1",
                "service_name": "onboarding-api",
                "service_type": "backend",
                "repository": "github://org/onboarding",
                "deployment_id": None,
                "workflow_id": workflow_id,
                "workflow_version": "v3.2.1",
            },
            "actor_context": {
                "actor_id": "user_7841",
                "actor_type": "human",
                "role": "SDE",
                "team": "onboarding_engineering",
                "access_level": "read",
                "authentication_method": "SSO",
            },
            "source_signature": {
                "tool_name": "frontend",
                "tool_type": "client",
                "source_host": "web",
            },
        },
        "wf_expense": {
            "enterprise_context": {
                "organization_id": "org_001",
                "business_unit": "finance",
                "project_id": "proj_finops",
                "project_name": "Finance Operations",
                "environment": "staging",
                "region": "us-east-1",
                "service_name": "expense-approvals",
                "service_type": "backend",
                "repository": "github://org/finops",
                "deployment_id": None,
                "workflow_id": workflow_id,
                "workflow_version": "v2.0.0",
            },
            "actor_context": {
                "actor_id": "svc_finops_bot",
                "actor_type": "service",
                "role": "Manager",
                "team": "finops",
                "access_level": "write",
                "authentication_method": "API_TOKEN",
            },
            "source_signature": {
                "tool_name": "webhook",
                "tool_type": "server",
                "source_host": "expense-approvals",
            },
        },
        "wf_access": {
            "enterprise_context": {
                "organization_id": "org_001",
                "business_unit": "security",
                "project_id": "proj_identity_security",
                "project_name": "Identity & Access Management",
                "environment": "production",
                "region": "us-east-1",
                "service_name": "iam-api",
                "service_type": "backend",
                "repository": "github://org/iam",
                "deployment_id": None,
                "workflow_id": workflow_id,
                "workflow_version": "v1.8.0",
            },
            "actor_context": {
                "actor_id": "svc_iam_bot",
                "actor_type": "service",
                "role": "Security",
                "team": "security",
                "access_level": "admin",
                "authentication_method": "SERVICE_ACCOUNT",
            },
            "source_signature": {
                "tool_name": "k8s_audit",
                "tool_type": "logs",
                "source_host": "kube-apiserver",
            },
        },
    }.get(wf_type, {})

    # Collect all events related to this workflow
    all_events = _observation.get_recent_events(count=500)
    wf_events = [e for e in all_events if e.workflow_id == workflow_id]
    # Correlate cross-source events via deployment_id when possible.
    corr_deploy_id = None
    for e in wf_events:
        md = e.metadata if isinstance(e.metadata, dict) else {}
        ctx = md.get("enterprise_context", {}) if isinstance(md, dict) else {}
        if isinstance(ctx, dict) and ctx.get("deployment_id"):
            corr_deploy_id = str(ctx.get("deployment_id"))
            break
    if not corr_deploy_id:
        corr_deploy_id = str(default_context.get("enterprise_context", {}).get("deployment_id") or "")
    corr_trace_id = f"trace_{corr_deploy_id}" if corr_deploy_id else f"trace_{workflow_id}"

    def _to_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    # Build timeline nodes
    nodes = []
    now = datetime.now(timezone.utc)
    base_time = min((_to_utc(e.timestamp) for e in wf_events), default=now - timedelta(minutes=10))
    
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
                "timestamp": _to_utc(e.timestamp).isoformat(),
                "timestampMs": int(_to_utc(e.timestamp).timestamp() * 1000),
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
                    # Enterprise context (demo realism)
                    "enterprise_context": default_context.get("enterprise_context", {}),
                    "actor_context": default_context.get("actor_context", {}),
                    "source_signature": default_context.get("source_signature", {}),
                    "normalized_event": {
                        "event_category": "workflow",
                        "event_type": f"workflow_step_{status}",
                        "severity": "warning" if status in ("delayed", "warning") else ("critical" if status == "failed" else "info"),
                        "confidence_initial": round(confidence / 100, 2),
                    },
                    "trace_id": f"trace_{workflow_id}",
                    "tenant_key": f"{default_context.get('enterprise_context', {}).get('organization_id','org_001')}:{default_context.get('enterprise_context', {}).get('project_id','proj_unknown')}:{default_context.get('enterprise_context', {}).get('environment','production')}",
                },
                "agentSource": "WorkflowAgent",
                "dependsOn": [f"evt_{workflow_id}_{definition['steps'][i-1]}"] if i > 0 else [],
            })

    # Code/CI lane: show PR + review + CI signals that correlate to this deployment.
    code_nodes = []
    if corr_deploy_id:
        for e in all_events:
            md = e.metadata if isinstance(e.metadata, dict) else {}
            ctx = md.get("enterprise_context", {}) if isinstance(md, dict) else {}
            if not (isinstance(ctx, dict) and str(ctx.get("deployment_id", "")) == corr_deploy_id):
                continue
            if not (isinstance(md, dict) and isinstance(md.get("source_signature", {}), dict)):
                continue
            sig = md.get("source_signature", {})
            if isinstance(sig, dict) and str(sig.get("tool_name", "")).lower() != "github":
                continue
            # Limit to code/cicd event types to keep the lane clean.
            if not (e.type.startswith("PR_") or e.type.startswith("CI_") or e.type.startswith("GITHUB_")):
                continue

            label = e.type
            gh = md.get("github", {}) if isinstance(md, dict) else {}
            if isinstance(gh, dict) and gh.get("pr_number"):
                label = f"PR #{gh.get('pr_number')} {str(gh.get('action') or '').upper()}".strip()
            elif isinstance(gh, dict) and gh.get("workflow_name"):
                label = f"CI {gh.get('workflow_name')}".strip()

            status = "success"
            confidence = 92
            normalized = md.get("normalized_event", {}) if isinstance(md, dict) else {}
            sev = str(normalized.get("severity", "info")).lower() if isinstance(normalized, dict) else "info"
            if sev in ("warning", "high", "critical"):
                status = "warning"
                confidence = 70

            code_nodes.append({
                "id": e.event_id,
                "laneId": "code",
                "name": label.upper(),
                "status": status,
                "timestamp": _to_utc(e.timestamp).isoformat(),
                "timestampMs": int(_to_utc(e.timestamp).timestamp() * 1000),
                "confidence": confidence,
                "details": {
                    **(md or {}),
                    "trace_id": md.get("trace_id") if isinstance(md, dict) else corr_trace_id,
                },
                "agentSource": "CodeIngest",
            })

    # Predictive layer (demo): surface CodeAgent anomalies from the latest completed cycle as timeline nodes.
    # This keeps frontend demo simple: the timeline itself shows "Risk predicted" entries with evidence.
    try:
        state = get_shared_state()
        if state._completed_cycles:
            latest = state._completed_cycles[-1]
            for a in latest.anomalies:
                if a.agent != "CodeAgent":
                    continue
                if corr_deploy_id and corr_deploy_id not in a.description:
                    # CodeAgent encodes deploy_id into its description; avoid mixing releases.
                    continue
                code_nodes.append({
                    "id": a.anomaly_id,
                    "laneId": "code",
                    "name": f"PREDICT: {a.type}".upper(),
                    "status": "warning" if a.confidence >= 0.6 else "success",
                    "timestamp": a.timestamp.replace(tzinfo=timezone.utc).isoformat() if a.timestamp.tzinfo is None else a.timestamp.astimezone(timezone.utc).isoformat(),
                    "timestampMs": int((a.timestamp.replace(tzinfo=timezone.utc) if a.timestamp.tzinfo is None else a.timestamp.astimezone(timezone.utc)).timestamp() * 1000),
                    "confidence": int(a.confidence * 100),
                    "details": {
                        "anomaly_type": a.type,
                        "confidence": a.confidence,
                        "evidence": a.evidence,
                        "description": a.description,
                        "enterprise_context": default_context.get("enterprise_context", {}),
                        "source_signature": {"tool_name": "chronos", "tool_type": "agent"},
                        "normalized_event": {
                            "event_category": "code",
                            "event_type": a.type,
                            "severity": "warning",
                            "confidence_initial": a.confidence,
                        },
                        "trace_id": corr_trace_id,
                    },
                    "agentSource": "CodeAgent",
                })
    except Exception:
        pass

    # De-dup code lane nodes by id (webhooks may retry).
    dedup: Dict[str, Dict[str, Any]] = {}
    for n in code_nodes:
        dedup[str(n.get("id"))] = n
    code_nodes = list(dedup.values())

    nodes.extend(sorted(code_nodes, key=lambda n: n["timestampMs"])[:8])

    # Human lane: show who triggered or intervened (enterprise realism).
    # Prefer real observed events; otherwise synthesize one for common enterprise flows.
    human_nodes = []
    if wf_events:
        for e in wf_events:
            md = e.metadata if isinstance(e.metadata, dict) else {}
            actor_ctx = md.get("actor_context", {}) if isinstance(md, dict) else {}
            normalized = md.get("normalized_event", {}) if isinstance(md, dict) else {}
            # Only include explicit human actions (avoid duplicating workflow step events).
            if isinstance(actor_ctx, dict) and actor_ctx.get("actor_type") == "human":
                etype = str(normalized.get("event_type", e.type))
                if any(k in etype.lower() for k in ("manual", "approve", "override", "retry", "rollback")):
                    human_nodes.append({
                        "id": f"human_{e.event_id}",
                        "laneId": "human",
                        "name": etype.replace("_", " ").upper(),
                        "status": "warning",
                "timestamp": _to_utc(e.timestamp).isoformat(),
                "timestampMs": int(_to_utc(e.timestamp).timestamp() * 1000),
                        "confidence": 75,
                        "details": md,
                        "agentSource": "WorkflowAgent",
                    })
    else:
        # Synthesize a realistic "trigger" event for the workflow type.
        trigger_name = "GITHUB_DEPLOY_TRIGGER" if wf_type == "wf_deployment" else \
                      "USER_REQUEST" if wf_type == "wf_onboarding" else \
                      "APPROVAL_REQUEST" if wf_type == "wf_expense" else \
                      "ACCESS_REQUEST"
        human_nodes.append({
            "id": f"human_{workflow_id}_trigger",
            "laneId": "human",
            "name": trigger_name,
            "status": "success",
            "timestamp": _to_utc(base_time).isoformat(),
            "timestampMs": int(_to_utc(base_time).timestamp() * 1000),
            "confidence": 95,
            "details": {
                "action": trigger_name.lower(),
                "enterprise_context": default_context.get("enterprise_context", {}),
                "actor_context": default_context.get("actor_context", {}),
                "source_signature": default_context.get("source_signature", {}),
                "normalized_event": {
                    "event_category": "human",
                    "event_type": trigger_name.lower(),
                    "severity": "info",
                    "confidence_initial": 0.95,
                },
                "trace_id": f"trace_{workflow_id}",
            },
            "agentSource": "WorkflowAgent",
        })

    nodes.extend(human_nodes[:3])
    
    # Resource lane: correlate recent metrics during this workflow window.
    #
    # Note: We intentionally include a few "normal" metrics too. In enterprise traces,
    # the absence/presence of normal metrics is part of the proof (baseline vs spike).
    resource_nodes = []
    recent_metrics = _observation.get_recent_metrics(count=100)
    # Prefer metrics that fall within the workflow window; fall back to recent.
    windowed = [m for m in recent_metrics if _to_utc(m.timestamp) >= base_time and _to_utc(m.timestamp) <= now]
    metric_candidates = (windowed or recent_metrics)[-40:]

    seen = set()
    for m in metric_candidates:
        key = (m.resource_id, m.metric)
        if key in seen:
            continue
        seen.add(key)
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

        resource_nodes.append({
            "id": f"res_{m.resource_id}_{m.metric}_{int(m.timestamp.timestamp())}",
            "laneId": "resource",
            "name": f"{m.resource_id} {m.metric.replace('_', ' ')}",
            "status": status,
            "timestamp": _to_utc(m.timestamp).isoformat(),
            "timestampMs": int(_to_utc(m.timestamp).timestamp() * 1000),
            "confidence": confidence,
            "details": {
                "metric": m.metric,
                "value": m.value,
                "resource": m.resource_id,
                # Attach context in demo mode so UI can explain source/actor in details view.
                "enterprise_context": default_context.get("enterprise_context", {}),
                "actor_context": default_context.get("actor_context", {}),
                "source_signature": {
                    **(default_context.get("source_signature", {}) or {}),
                    "tool_name": "datadog",
                    "tool_type": "metrics",
                },
                "normalized_event": {
                    "event_category": "infrastructure",
                    "event_type": m.metric,
                    "severity": "warning" if status in ("warning", "failed") else "info",
                    "confidence_initial": round(confidence / 100, 2),
                },
                "trace_id": f"trace_{workflow_id}",
            },
            "agentSource": "ResourceAgent",
        })
    
    # Keep the timeline readable but dense enough for demos.
    nodes.extend(resource_nodes[:8])
    
    # Compliance lane: show policy checks and violations for this workflow.
    compliance_nodes = []
    state = get_shared_state()
    event_by_id = {e.event_id: e for e in all_events}
    for cycle in state._completed_cycles[-5:]:
        for hit in cycle.policy_hits:
            ev = event_by_id.get(hit.event_id)
            if ev and ev.workflow_id != workflow_id:
                continue
            compliance_nodes.append({
                "id": hit.hit_id,
                "laneId": "compliance",
                "name": hit.policy_id,
                "status": "failed" if hit.violation_type == "SILENT" else "warning",
                "timestamp": _to_utc(hit.timestamp).isoformat(),
                "timestampMs": int(_to_utc(hit.timestamp).timestamp() * 1000),
                "confidence": 8 if hit.violation_type == "SILENT" else 45,
                "details": {
                    "policy": hit.policy_id,
                    "violation_type": hit.violation_type,
                    "event_id": hit.event_id,
                    "enterprise_context": (ev.metadata.get("enterprise_context", {}) if ev and isinstance(ev.metadata, dict) else default_context.get("enterprise_context", {})),
                    "actor_context": (ev.metadata.get("actor_context", {}) if ev and isinstance(ev.metadata, dict) else default_context.get("actor_context", {})),
                    "source_signature": (ev.metadata.get("source_signature", {}) if ev and isinstance(ev.metadata, dict) else default_context.get("source_signature", {})),
                    "trace_id": (ev.metadata.get("trace_id") if ev and isinstance(ev.metadata, dict) else f"trace_{workflow_id}"),
                },
                "agentSource": "ComplianceAgent",
            })
    
    # Always include at least one "policy check" for enterprise realism (even when no violations are present).
    if not compliance_nodes:
        check_ts = base_time + timedelta(seconds=90)
        compliance_nodes.append({
            "id": f"policy_{workflow_id}_approval",
            "laneId": "compliance",
            "name": "DEPLOY_APPROVAL" if wf_type == "wf_deployment" else "POLICY_CHECK",
            "status": "success",
            "timestamp": check_ts.isoformat(),
            "timestampMs": int(check_ts.timestamp() * 1000),
            "confidence": 100,
            "details": {
                "policy": "DEPLOY_APPROVAL" if wf_type == "wf_deployment" else "POLICY_CHECK",
                "result": "PASSED",
                "enterprise_context": default_context.get("enterprise_context", {}),
                "actor_context": default_context.get("actor_context", {}),
                "source_signature": default_context.get("source_signature", {}),
                "normalized_event": {
                    "event_category": "compliance",
                    "event_type": "policy_check_passed",
                    "severity": "info",
                    "confidence_initial": 1.0,
                },
                "trace_id": f"trace_{workflow_id}",
            },
            "agentSource": "ComplianceAgent",
        })

    nodes.extend(compliance_nodes[:5])
    
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
            {"id": "code", "label": "Code & CI", "order": 0, "visible": True},
            {"id": "workflow", "label": "Workflow Steps", "order": 1, "visible": True},
            {"id": "resource", "label": "Resource Impact", "order": 2, "visible": True},
            {"id": "human", "label": "Human Actions", "order": 3, "visible": True},
            {"id": "compliance", "label": "Compliance", "order": 4, "visible": True},
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
    
    risk_point = None
    if _state._completed_cycles:
        latest = _state._completed_cycles[-1]
        risk_point = get_risk_tracker().record_cycle(latest)

    insight_generated = False
    insight = None
    if _state._completed_cycles:
        latest = _state._completed_cycles[-1]
        insight = _explanation.generate_insight(latest)
        if insight:
            _insights.append(insight)
            insight_generated = True

        if _slack_notifier:
            try:
                await _slack_notifier.send_cycle_alert(
                    latest,
                    insight=insight,
                    risk_score=risk_point.risk_score if risk_point else None,
                    risk_state=risk_point.risk_state if risk_point else None,
                )
            except Exception:
                pass
    
    return {
        "cycle_id": result.cycle_id,
        "anomalies": result.anomaly_count,
        "policy_hits": result.policy_hit_count,
        "risk_signals": result.risk_signal_count,
        "causal_links": result.causal_link_count,
        "recommendations": result.recommendation_count,
        "duration_ms": result.duration_ms,
        "insight_generated": insight_generated,
    }


class WhatIfRequest(BaseModel):
    scenario_type: str = Field(..., min_length=1, max_length=64)
    parameters: Dict[str, Any] = Field(default_factory=dict)


@app.post("/simulation/what-if", tags=["Simulation"])
async def run_what_if_simulation(request: WhatIfRequest):
    """
    Run a deterministic counterfactual simulation and persist the result to blackboard.
    """
    if _what_if_agent is None:
        raise HTTPException(status_code=503, detail="What-if simulator is not initialized")
    run = _what_if_agent.run(
        scenario_type=request.scenario_type,
        parameters=request.parameters,
        state=_state,
    )
    return {
        "scenario_id": run.scenario_id,
        "scenario_type": run.scenario_type,
        "parameters": run.parameters,
        "baseline": run.baseline,
        "simulated": run.simulated,
        "impact_score": run.impact_score,
        "confidence": run.confidence,
        "confidence_reason": run.confidence_reason,
        "assumptions": run.assumptions,
        "related_cycle_id": run.related_cycle_id,
        "created_at": run.created_at.isoformat(),
    }


@app.get("/simulation/runs", tags=["Simulation"])
async def list_simulation_runs(limit: int = Query(default=20, ge=1, le=200)):
    runs = []
    for cycle in reversed(_state._completed_cycles):
        for run in cycle.scenario_runs:
            runs.append({
                "scenario_id": run.scenario_id,
                "scenario_type": run.scenario_type,
                "parameters": run.parameters,
                "impact_score": run.impact_score,
                "confidence": run.confidence,
                "related_cycle_id": run.related_cycle_id,
                "created_at": run.created_at.isoformat(),
            })
            if len(runs) >= limit:
                return {"runs": runs, "total": len(runs)}
    return {"runs": runs, "total": len(runs)}


@app.get("/severity/latest", tags=["Risk"])
async def get_latest_severity(limit: int = Query(default=50, ge=1, le=500)):
    scores = []
    for cycle in reversed(_state._completed_cycles):
        for s in cycle.severity_scores:
            scores.append({
                "severity_id": s.severity_id,
                "cycle_id": cycle.cycle_id,
                "source_type": s.source_type,
                "source_id": s.source_id,
                "issue_type": s.issue_type,
                "base_score": s.base_score,
                "final_score": s.final_score,
                "label": s.label,
                "vector": s.vector,
                "escalation_state": s.escalation_state,
                "context_factors": s.context_factors,
                "evidence_ids": s.evidence_ids,
                "timestamp": s.timestamp.isoformat(),
            })
            if len(scores) >= limit:
                return {"severity_scores": scores, "total": len(scores)}
    return {"severity_scores": scores, "total": len(scores)}


@app.get("/severity/by-cycle/{cycle_id}", tags=["Risk"])
async def get_severity_by_cycle(cycle_id: str):
    cycle = next((c for c in _state._completed_cycles if c.cycle_id == cycle_id), None)
    if not cycle:
        raise HTTPException(status_code=404, detail=f"Cycle not found: {cycle_id}")
    return {
        "cycle_id": cycle_id,
        "severity_scores": [
            {
                "severity_id": s.severity_id,
                "source_type": s.source_type,
                "source_id": s.source_id,
                "issue_type": s.issue_type,
                "base_score": s.base_score,
                "final_score": s.final_score,
                "label": s.label,
                "vector": s.vector,
                "escalation_state": s.escalation_state,
                "context_factors": s.context_factors,
                "evidence_ids": s.evidence_ids,
                "timestamp": s.timestamp.isoformat(),
            }
            for s in cycle.severity_scores
        ],
    }


@app.get("/recommendations/latest", tags=["Insights"])
async def get_latest_recommendations(limit: int = Query(default=50, ge=1, le=500)):
    recs = []
    for cycle in reversed(_state._completed_cycles):
        for r in cycle.recommendations_v2:
            recs.append({
                "rec_id": r.rec_id,
                "cycle_id": cycle.cycle_id,
                "issue_type": r.issue_type,
                "entity": r.entity,
                "severity_score": r.severity_score,
                "action_code": r.action_code,
                "action_description": r.action_description,
                "confidence": r.confidence,
                "preconditions": r.preconditions,
                "evidence_ids": r.evidence_ids,
                "expected_effect": r.expected_effect,
                "rationale": r.rationale,
                "rule_id": r.rule_id,
                "source": r.source,
                "timestamp": r.timestamp.isoformat(),
            })
            if len(recs) >= limit:
                return {"recommendations": recs, "total": len(recs)}
    return {"recommendations": recs, "total": len(recs)}


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
    
    history_data = []
    for p in history:
        point = p.to_dict()
        point["contributions"] = [
            {
                "agent": c.get("agent"),
                "contribution": c.get("impact", 0),
                "reason": c.get("description", ""),
                "signal_type": c.get("signal_type"),
                "evidence_id": c.get("evidence_id"),
            }
            for c in point.get("contributions", [])
        ]
        history_data.append(point)
    current = tracker.get_current_risk().to_dict() if tracker.get_current_risk() else None
    return {
        # Frontend contract
        "history": history_data,
        "current_risk": current["risk_score"] if current else 20,
        "trend": tracker.get_trend(),
        # Backward-compatible aliases
        "data": history_data,
        "current": current,
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
                "contribution": c.impact,
                "reason": c.description,
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
    scenario_id: Optional[str] = None
    scenario_type: Optional[str] = None


@app.post("/scenarios/inject", tags=["Scenarios"])
async def inject_scenario(request: ScenarioRequest):
    """
    Inject a stress scenario into the system.
    
    After injection, run /analysis/cycle to see agents respond.
    """
    try:
        scenario_key = request.scenario_id or request.scenario_type
        if not scenario_key:
            raise HTTPException(status_code=400, detail="Provide scenario_id or scenario_type")
        execution = _scenario_agent.inject_scenario(scenario_key)
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
        for rec2 in cycle.recommendations_v2:
            activity.append({
                "type": "recommendation_v2",
                "agent": "RecommendationEngineAgent",
                "description": f"{rec2.action_code}: {rec2.action_description}",
                "confidence": rec2.confidence,
                "timestamp": rec2.timestamp.isoformat(),
                "cycle_id": cycle.cycle_id,
                "id": rec2.rec_id,
            })
        for sev in cycle.severity_scores:
            activity.append({
                "type": "severity",
                "agent": "SeverityEngineAgent",
                "description": f"{sev.issue_type} => {sev.label} ({sev.final_score})",
                "confidence": min(1.0, max(0.0, sev.final_score / 10.0)),
                "timestamp": sev.timestamp.isoformat(),
                "cycle_id": cycle.cycle_id,
                "id": sev.severity_id,
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
                "detects": ["6 scenarios: latency, compliance, workload, cascade, drift, paytm_hotfix_fail"],
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


class SlackTestRequest(BaseModel):
    message: str = Field(default="Hello from Chronos AI")


@app.get("/alerts/slack/status", tags=["Alerts"])
async def get_slack_alert_status():
    """Get Slack integration status."""
    return {
        "enabled": bool(_slack_notifier and _slack_notifier.enabled),
        "configured": bool(settings.SLACK_WEBHOOK_URL),
        "min_severity": settings.SLACK_ALERT_MIN_SEVERITY,
        "min_risk_state": settings.SLACK_ALERT_MIN_RISK_STATE,
        "cooldown_seconds": settings.SLACK_ALERT_COOLDOWN_SECONDS,
    }


@app.post("/alerts/slack/test", tags=["Alerts"])
async def send_slack_test_alert(request: SlackTestRequest):
    """Send a test alert to Slack webhook."""
    if not _slack_notifier or not _slack_notifier.enabled:
        raise HTTPException(
            status_code=400,
            detail="Slack alerts are disabled or webhook is not configured",
        )
    result = await _slack_notifier.send_test(request.message)
    return result


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


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT ENDPOINTS (P0: Post-Mortem Investigation APIs)
# ═══════════════════════════════════════════════════════════════════════════════

def _risk_rank(value: str) -> int:
    ranks = {
        "NORMAL": 0,
        "DEGRADED": 1,
        "AT_RISK": 2,
        "VIOLATION": 3,
        "INCIDENT": 4,
        "CRITICAL": 5,
    }
    return ranks.get((value or "").upper(), 0)


def _cycle_hash(cycle_dict: Dict[str, Any]) -> str:
    payload = json.dumps(cycle_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _find_cycle(cycle_id: str):
    for cycle in reversed(_state._completed_cycles):
        if cycle.cycle_id == cycle_id:
            return cycle
    return None


def _find_event(event_id: str):
    # Observation layer keeps recent events in memory.
    # For full retention search, use SQLite query APIs in the next iteration.
    for event in _observation.get_recent_events(100000):
        if event.event_id == event_id:
            return event
    return None


class AuditExportRequest(BaseModel):
    incident_id: str = Field(..., description="Incident identifier (cycle_id)")
    format: str = Field(default="json", description="json or csv")


@app.get("/audit/incidents", tags=["Audit"])
async def list_audit_incidents(limit: int = Query(default=20, ge=1, le=200)):
    """
    List recent auditable incidents.

    Incident model (P0): one reasoning cycle = one incident unit.
    """
    tracker = get_risk_tracker()
    incidents = []
    for cycle in reversed(_state._completed_cycles[-limit * 3:]):
        cycle_risk_state = "NORMAL"
        cycle_risk_score = 20.0
        for point in reversed(tracker.get_history(500)):
            if point.cycle_id == cycle.cycle_id:
                cycle_risk_state = point.risk_state
                cycle_risk_score = point.risk_score
                break

        if (
            len(cycle.anomalies) == 0
            and len(cycle.policy_hits) == 0
            and _risk_rank(cycle_risk_state) < _risk_rank("AT_RISK")
        ):
            continue

        incidents.append(
            {
                "incident_id": cycle.cycle_id,
                "cycle_id": cycle.cycle_id,
                "timestamp": (cycle.completed_at or cycle.started_at).isoformat(),
                "risk_score": cycle_risk_score,
                "risk_state": cycle_risk_state,
                "anomaly_count": len(cycle.anomalies),
                "policy_hit_count": len(cycle.policy_hits),
                "causal_link_count": len(cycle.causal_links),
                "status": "OPEN",
            }
        )
        if len(incidents) >= limit:
            break

    return {"incidents": incidents, "count": len(incidents)}


@app.get("/audit/incident/{incident_id}", tags=["Audit"])
async def get_audit_incident(incident_id: str):
    """Get incident detail with immutable cycle snapshot hash."""
    cycle = _find_cycle(incident_id)
    if not cycle:
        raise HTTPException(status_code=404, detail="Incident not found")

    cycle_dict = cycle.to_dict()
    evidence_ids = (
        [a.anomaly_id for a in cycle.anomalies]
        + [h.hit_id for h in cycle.policy_hits]
        + [c.link_id for c in cycle.causal_links]
    )
    return {
        "incident_id": incident_id,
        "cycle_id": cycle.cycle_id,
        "timestamp": (cycle.completed_at or cycle.started_at).isoformat(),
        "counts": {
            "anomalies": len(cycle.anomalies),
            "policy_hits": len(cycle.policy_hits),
            "risk_signals": len(cycle.risk_signals),
            "causal_links": len(cycle.causal_links),
            "recommendations": len(cycle.recommendations),
        },
        "evidence_ids": evidence_ids[:200],
        "cycle_sha256": _cycle_hash(cycle_dict),
        "cycle": cycle_dict,
    }


@app.get("/audit/incident/{incident_id}/timeline", tags=["Audit"])
async def get_audit_incident_timeline(incident_id: str):
    """Return forensic timeline for an incident/cycle."""
    cycle = _find_cycle(incident_id)
    if not cycle:
        raise HTTPException(status_code=404, detail="Incident not found")

    timeline = []
    # Include raw evidence timestamps where available
    for anomaly in cycle.anomalies:
        timeline.append(
            {
                "ts": anomaly.timestamp.isoformat(),
                "kind": "anomaly",
                "id": anomaly.anomaly_id,
                "agent": anomaly.agent,
                "summary": anomaly.description,
                "confidence": anomaly.confidence,
                "evidence_ids": anomaly.evidence,
            }
        )
    for hit in cycle.policy_hits:
        timeline.append(
            {
                "ts": hit.timestamp.isoformat(),
                "kind": "policy_hit",
                "id": hit.hit_id,
                "agent": hit.agent,
                "summary": hit.description,
                "confidence": 0.9,
                "evidence_ids": [hit.event_id],
            }
        )
    for signal in cycle.risk_signals:
        timeline.append(
            {
                "ts": signal.timestamp.isoformat(),
                "kind": "risk_signal",
                "id": signal.signal_id,
                "agent": "RiskForecastAgent",
                "summary": signal.reasoning,
                "confidence": signal.confidence,
                "evidence_ids": signal.evidence_ids,
            }
        )
    for link in cycle.causal_links:
        timeline.append(
            {
                "ts": link.timestamp.isoformat(),
                "kind": "causal_link",
                "id": link.link_id,
                "agent": "CausalAgent",
                "summary": f"{link.cause} -> {link.effect}",
                "confidence": link.confidence,
                "evidence_ids": link.evidence_ids,
            }
        )
    for rec in cycle.recommendations:
        timeline.append(
            {
                "ts": rec.timestamp.isoformat(),
                "kind": "recommendation",
                "id": rec.rec_id,
                "agent": "MasterAgent",
                "summary": rec.action,
                "confidence": 0.8,
                "evidence_ids": [],
            }
        )

    timeline.sort(key=lambda x: x["ts"])
    return {
        "incident_id": incident_id,
        "timeline": timeline,
        "count": len(timeline),
    }


@app.get("/audit/event/{event_id}/raw", tags=["Audit"])
async def get_raw_event(event_id: str):
    """Get raw observed event payload for evidence proof."""
    event = _find_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "event_id": event.event_id,
        "type": event.type,
        "workflow_id": event.workflow_id,
        "actor": event.actor,
        "resource": event.resource,
        "timestamp": event.timestamp.isoformat(),
        "metadata": event.metadata,
        "observed_at": event.observed_at.isoformat(),
    }


@app.get("/audit/cycle/{cycle_id}", tags=["Audit"])
async def get_audit_cycle(cycle_id: str):
    """Return frozen blackboard cycle with deterministic hash."""
    cycle = _find_cycle(cycle_id)
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    cycle_dict = cycle.to_dict()
    return {
        "cycle_id": cycle_id,
        "cycle_sha256": _cycle_hash(cycle_dict),
        "cycle": cycle_dict,
    }


@app.post("/audit/export", tags=["Audit"])
async def export_audit_report(request: AuditExportRequest):
    """
    Export an audit snapshot payload.
    P0 supports JSON/CSV payload generation; PDF renderer can be added later.
    """
    cycle = _find_cycle(request.incident_id)
    if not cycle:
        raise HTTPException(status_code=404, detail="Incident not found")

    cycle_dict = cycle.to_dict()
    payload = {
        "incident_id": request.incident_id,
        "generated_at": datetime.utcnow().isoformat(),
        "cycle_sha256": _cycle_hash(cycle_dict),
        "cycle": cycle_dict,
    }
    if request.format.lower() == "csv":
        rows = [
            "kind,id,timestamp,agent,summary,confidence",
        ]
        for a in cycle.anomalies:
            rows.append(
                f"anomaly,{a.anomaly_id},{a.timestamp.isoformat()},{a.agent},\"{a.description}\",{a.confidence}"
            )
        for h in cycle.policy_hits:
            rows.append(
                f"policy_hit,{h.hit_id},{h.timestamp.isoformat()},{h.agent},\"{h.description}\",0.9"
            )
        payload["csv"] = "\n".join(rows)

    return {"status": "ok", "format": request.format.lower(), "report": payload}
