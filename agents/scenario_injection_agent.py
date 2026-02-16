"""
IICWMS Scenario Injection Agent
================================
Introduces simulated disruptions and evaluates system response.

PURPOSE:
- Provide predefined stress scenarios for demo / judging
- Inject events and metrics into the simulation
- Track how every agent responds to the injected stress
- Report: detection latency, agent coverage, reasoning quality

COVERS PS-08 ROUND 2: "System Stress or Scenario Injection"
"Introduce simulated disruptions (policy changes, workload spikes,
 abnormal user behavior). Evaluate how the system adapts and responds."

SCENARIOS:
1. LATENCY_SPIKE    — Network latency surge on a critical resource
2. COMPLIANCE_BREACH — After-hours + unusual-location access burst
3. WORKLOAD_SURGE   — Burst of concurrent workflow starts
4. CASCADING_FAILURE — Resource stress → workflow delay → compliance risk
5. RESOURCE_DRIFT   — Gradual resource degradation over time
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

from simulator.engine import Event, ResourceMetric, EventType
from observation import ObservationLayer, get_observation_layer


class ScenarioType(Enum):
    LATENCY_SPIKE = "LATENCY_SPIKE"
    COMPLIANCE_BREACH = "COMPLIANCE_BREACH"
    WORKLOAD_SURGE = "WORKLOAD_SURGE"
    CASCADING_FAILURE = "CASCADING_FAILURE"
    RESOURCE_DRIFT = "RESOURCE_DRIFT"
    PAYTM_HOTFIX_FAIL = "PAYTM_HOTFIX_FAIL"


@dataclass
class ScenarioDefinition:
    """Definition of a stress scenario."""
    scenario_type: ScenarioType
    name: str
    description: str
    severity: str  # low, medium, high, critical
    expected_agent_response: List[str]  # Which agents should detect this
    events_to_inject: int
    metrics_to_inject: int
    estimated_detection_time: str


@dataclass
class ScenarioExecution:
    """Tracks execution and results of a scenario."""
    execution_id: str
    scenario_type: str
    name: str
    status: str  # pending, running, completed
    started_at: str
    completed_at: Optional[str] = None
    events_injected: int = 0
    metrics_injected: int = 0
    expected_agents: List[str] = field(default_factory=list)
    detected_by: List[str] = field(default_factory=list)
    detection_results: List[Dict[str, Any]] = field(default_factory=list)
    system_response_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────
# Scenario Definitions
# ─────────────────────────────────────────────────────────────────────

SCENARIOS: Dict[ScenarioType, ScenarioDefinition] = {
    ScenarioType.LATENCY_SPIKE: ScenarioDefinition(
        scenario_type=ScenarioType.LATENCY_SPIKE,
        name="Network Latency Spike",
        description=(
            "Injects a sustained network latency spike on vm_api_01, "
            "simulating a network degradation event. This should trigger "
            "ResourceAgent detection and cascade into WorkflowAgent delays."
        ),
        severity="high",
        expected_agent_response=[
            "ResourceAgent", "WorkflowAgent", "RiskForecastAgent", "CausalAgent"
        ],
        events_to_inject=0,
        metrics_to_inject=8,
        estimated_detection_time="1–2 cycles",
    ),
    ScenarioType.COMPLIANCE_BREACH: ScenarioDefinition(
        scenario_type=ScenarioType.COMPLIANCE_BREACH,
        name="Compliance Breach Pattern",
        description=(
            "Injects after-hours write access from unusual locations, "
            "simulating a security-concerning access pattern. Should "
            "trigger ComplianceAgent policy violations."
        ),
        severity="high",
        expected_agent_response=[
            "ComplianceAgent", "RiskForecastAgent"
        ],
        events_to_inject=5,
        metrics_to_inject=0,
        estimated_detection_time="1 cycle",
    ),
    ScenarioType.WORKLOAD_SURGE: ScenarioDefinition(
        scenario_type=ScenarioType.WORKLOAD_SURGE,
        name="Workload Surge",
        description=(
            "Injects a burst of concurrent workflow starts, overwhelming "
            "the system. Should trigger WorkflowAgent sequence violations "
            "and ResourceAgent stress detection."
        ),
        severity="medium",
        expected_agent_response=[
            "WorkflowAgent", "ResourceAgent", "RiskForecastAgent"
        ],
        events_to_inject=12,
        metrics_to_inject=4,
        estimated_detection_time="1–2 cycles",
    ),
    ScenarioType.CASCADING_FAILURE: ScenarioDefinition(
        scenario_type=ScenarioType.CASCADING_FAILURE,
        name="Cascading Failure",
        description=(
            "Simulates a cascading failure: resource stress → workflow "
            "delays → SLA pressure → human overrides → compliance risk. "
            "This is the full multi-agent detection test."
        ),
        severity="critical",
        expected_agent_response=[
            "ResourceAgent", "WorkflowAgent", "ComplianceAgent",
            "RiskForecastAgent", "CausalAgent", "AdaptiveBaselineAgent"
        ],
        events_to_inject=8,
        metrics_to_inject=10,
        estimated_detection_time="2–3 cycles",
    ),
    ScenarioType.RESOURCE_DRIFT: ScenarioDefinition(
        scenario_type=ScenarioType.RESOURCE_DRIFT,
        name="Gradual Resource Drift",
        description=(
            "Simulates gradual CPU/memory drift over time, testing whether "
            "the AdaptiveBaselineAgent detects trend-based anomalies rather "
            "than just threshold breaches."
        ),
        severity="medium",
        expected_agent_response=[
            "ResourceAgent", "AdaptiveBaselineAgent", "RiskForecastAgent"
        ],
        events_to_inject=0,
        metrics_to_inject=15,
        estimated_detection_time="3–5 cycles",
    ),
    ScenarioType.PAYTM_HOTFIX_FAIL: ScenarioDefinition(
        scenario_type=ScenarioType.PAYTM_HOTFIX_FAIL,
        name="Paytm Payment Hotfix Fail",
        description=(
            "GitHub PR merge + CI success followed by deploy-time regex regression, "
            "CPU saturation, workflow SLA breach, compliance hit, and incident escalation."
        ),
        severity="critical",
        expected_agent_response=[
            "CodeAgent",
            "WorkflowAgent",
            "ResourceAgent",
            "ComplianceAgent",
            "RiskForecastAgent",
            "CausalAgent",
            "SeverityEngineAgent",
            "RecommendationEngineAgent",
        ],
        events_to_inject=18,
        metrics_to_inject=7,
        estimated_detection_time="1–2 cycles",
    ),
}


class ScenarioInjectionAgent:
    """
    Scenario Injection Agent.

    Provides predefined stress scenarios that can be triggered
    from the UI or API. Injects events/metrics into the observation
    layer, then tracks how the multi-agent system responds.

    This is the DEMO KILLER for judges:
    - Trigger "Cascading Failure"
    - Watch agents detect → reason → explain in real-time
    - Show detection coverage and latency
    """

    AGENT_NAME = "ScenarioInjectionAgent"

    def __init__(self):
        self._observation = get_observation_layer()
        self._executions: List[ScenarioExecution] = []
        self._base_time = datetime.utcnow()

    def list_scenarios(self) -> List[Dict[str, Any]]:
        """List all available scenarios with descriptions."""
        return [
            {
                "id": s.scenario_type.value,
                "name": s.name,
                "description": s.description,
                "severity": s.severity,
                "expected_agents": s.expected_agent_response,
                "events_to_inject": s.events_to_inject,
                "metrics_to_inject": s.metrics_to_inject,
                "estimated_detection_time": s.estimated_detection_time,
            }
            for s in SCENARIOS.values()
        ]

    def inject_scenario(self, scenario_id: str) -> ScenarioExecution:
        """
        Inject a scenario into the system.

        Returns an execution record for tracking.
        """
        try:
            scenario_type = ScenarioType(scenario_id)
        except ValueError:
            raise ValueError(
                f"Unknown scenario: {scenario_id}. "
                f"Available: {[s.value for s in ScenarioType]}"
            )

        definition = SCENARIOS[scenario_type]
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow()

        execution = ScenarioExecution(
            execution_id=execution_id,
            scenario_type=scenario_type.value,
            name=definition.name,
            status="running",
            started_at=now.isoformat(),
            expected_agents=definition.expected_agent_response,
        )

        # Inject based on type
        if scenario_type == ScenarioType.LATENCY_SPIKE:
            execution = self._inject_latency_spike(execution, now)
        elif scenario_type == ScenarioType.COMPLIANCE_BREACH:
            execution = self._inject_compliance_breach(execution, now)
        elif scenario_type == ScenarioType.WORKLOAD_SURGE:
            execution = self._inject_workload_surge(execution, now)
        elif scenario_type == ScenarioType.CASCADING_FAILURE:
            execution = self._inject_cascading_failure(execution, now)
        elif scenario_type == ScenarioType.RESOURCE_DRIFT:
            execution = self._inject_resource_drift(execution, now)
        elif scenario_type == ScenarioType.PAYTM_HOTFIX_FAIL:
            execution = self._inject_paytm_hotfix_fail(execution)

        execution.status = "completed"
        execution.completed_at = datetime.utcnow().isoformat()
        self._executions.append(execution)

        return execution

    def get_executions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent scenario executions."""
        return [e.to_dict() for e in self._executions[-limit:]]

    # ──────────────────────────────────────────────────────────────────
    # Scenario Injectors
    # ──────────────────────────────────────────────────────────────────

    def _inject_latency_spike(
        self, execution: ScenarioExecution, now: datetime
    ) -> ScenarioExecution:
        """Inject sustained network latency spike on vm_api_01."""
        for i in range(8):
            metric = ResourceMetric(
                resource_id="vm_api_01",
                metric="network_latency_ms",
                value=300 + i * 50,  # 300ms → 650ms (rising spike)
                timestamp=now + timedelta(seconds=i * 5),
            )
            self._observation.observe_metric(metric.to_dict())
            execution.metrics_injected += 1

        execution.system_response_summary = (
            "Injected 8 latency metrics (300ms→650ms) on vm_api_01. "
            "Expected: ResourceAgent detects sustained spike, "
            "WorkflowAgent detects deployment delays, "
            "RiskForecastAgent escalates risk state."
        )
        return execution

    def _inject_compliance_breach(
        self, execution: ScenarioExecution, now: datetime
    ) -> ScenarioExecution:
        """Inject after-hours access events from unusual locations."""
        # Simulate 2AM writes from unusual locations
        breach_time = now.replace(hour=2, minute=15)

        events = [
            Event(
                event_id=f"scenario_evt_{uuid.uuid4().hex[:8]}",
                type=EventType.ACCESS_WRITE.value,
                workflow_id=None,
                actor="user_bob",
                resource="sensitive_db",
                timestamp=breach_time + timedelta(minutes=i * 2),
                metadata={
                    "location": "unknown_vpn",
                    "resource_sensitivity": "high",
                },
            )
            for i in range(3)
        ] + [
            Event(
                event_id=f"scenario_evt_{uuid.uuid4().hex[:8]}",
                type=EventType.ACCESS_WRITE.value,
                workflow_id=None,
                actor="svc_account_01",
                resource="repo_main",
                timestamp=breach_time + timedelta(minutes=8),
                metadata={"location": "internal"},
            ),
            Event(
                event_id=f"scenario_evt_{uuid.uuid4().hex[:8]}",
                type=EventType.CREDENTIAL_ACCESS.value,
                workflow_id=None,
                actor="user_carol",
                resource="admin_credentials",
                timestamp=breach_time + timedelta(minutes=12),
                metadata={"location": "unknown_vpn"},
            ),
        ]

        for event in events:
            self._observation.observe_event(event.to_dict())
            execution.events_injected += 1

        execution.system_response_summary = (
            "Injected 5 events: 3 after-hours writes from unknown VPN, "
            "1 service account direct write, 1 credential access. "
            "Expected: ComplianceAgent flags NO_AFTER_HOURS_WRITE, "
            "NO_UNUSUAL_LOCATION, NO_SVC_ACCOUNT_WRITE policies."
        )
        return execution

    def _inject_workload_surge(
        self, execution: ScenarioExecution, now: datetime
    ) -> ScenarioExecution:
        """Inject burst of workflow starts."""
        for i in range(8):
            wf_id = f"wf_surge_{uuid.uuid4().hex[:6]}"
            event = Event(
                event_id=f"scenario_evt_{uuid.uuid4().hex[:8]}",
                type=EventType.WORKFLOW_START.value,
                workflow_id=wf_id,
                actor=f"user_{'alice' if i % 2 == 0 else 'bob'}",
                resource=None,
                timestamp=now + timedelta(seconds=i * 2),
                metadata={"workflow_name": "Deploy Pipeline"},
            )
            self._observation.observe_event(event.to_dict())
            execution.events_injected += 1

        # Also inject CPU spike from the load
        for i in range(4):
            for resource_id in ["vm_web_01", "vm_api_01"]:
                metric = ResourceMetric(
                    resource_id=resource_id,
                    metric="cpu_usage",
                    value=75 + i * 8,  # 75% → 99%
                    timestamp=now + timedelta(seconds=i * 5),
                )
                self._observation.observe_metric(metric.to_dict())
                execution.metrics_injected += 1

        execution.system_response_summary = (
            "Injected 8 concurrent workflow starts + CPU spike (75%→99%). "
            "Expected: WorkflowAgent detects sequence anomalies, "
            "ResourceAgent detects CPU saturation, "
            "RiskForecastAgent escalates."
        )
        return execution

    def _inject_cascading_failure(
        self, execution: ScenarioExecution, now: datetime
    ) -> ScenarioExecution:
        """
        Inject cascading failure:
        1. Network latency → 2. Workflow delay → 3. SLA pressure →
        4. Human override → 5. Compliance risk
        """
        # Phase 1: Network stress
        for i in range(5):
            self._observation.observe_metric(ResourceMetric(
                resource_id="vm_api_01",
                metric="network_latency_ms",
                value=200 + i * 80,
                timestamp=now + timedelta(seconds=i * 5),
            ).to_dict())
            execution.metrics_injected += 1

        # Phase 2: CPU/memory stress
        for i in range(5):
            self._observation.observe_metric(ResourceMetric(
                resource_id="vm_web_01",
                metric="cpu_usage",
                value=60 + i * 10,
                timestamp=now + timedelta(seconds=i * 5),
            ).to_dict())
            execution.metrics_injected += 1

        # Phase 3: Workflow that gets delayed
        wf_id = f"wf_cascade_{uuid.uuid4().hex[:6]}"
        workflow_events = [
            Event(
                event_id=f"scenario_evt_{uuid.uuid4().hex[:8]}",
                type=EventType.WORKFLOW_START.value,
                workflow_id=wf_id,
                actor="user_alice",
                resource=None,
                timestamp=now,
                metadata={"workflow_name": "Deploy Pipeline"},
            ),
            Event(
                event_id=f"scenario_evt_{uuid.uuid4().hex[:8]}",
                type=EventType.WORKFLOW_STEP_START.value,
                workflow_id=wf_id,
                actor="system",
                resource=None,
                timestamp=now + timedelta(seconds=5),
                metadata={"step": "build", "expected_duration": 60},
            ),
            Event(
                event_id=f"scenario_evt_{uuid.uuid4().hex[:8]}",
                type=EventType.WORKFLOW_STEP_COMPLETE.value,
                workflow_id=wf_id,
                actor="system",
                resource=None,
                timestamp=now + timedelta(seconds=180),  # 3x expected
                metadata={"step": "build", "actual_duration": 180},
            ),
        ]

        for event in workflow_events:
            self._observation.observe_event(event.to_dict())
            execution.events_injected += 1

        # Phase 4: Human override (SLA pressure)
        override_events = [
            Event(
                event_id=f"scenario_evt_{uuid.uuid4().hex[:8]}",
                type=EventType.WORKFLOW_STEP_SKIP.value,
                workflow_id=wf_id,
                actor="user_alice",
                resource=None,
                timestamp=now + timedelta(seconds=200),
                metadata={"step": "approval", "reason": "SLA_PRESSURE"},
            ),
            Event(
                event_id=f"scenario_evt_{uuid.uuid4().hex[:8]}",
                type=EventType.ACCESS_WRITE.value,
                workflow_id=None,
                actor="user_alice",
                resource="production_db",
                timestamp=now.replace(hour=2, minute=30),
                metadata={"location": "internal", "resource_sensitivity": "high"},
            ),
        ]

        for event in override_events:
            self._observation.observe_event(event.to_dict())
            execution.events_injected += 1

        execution.system_response_summary = (
            "Injected full cascading failure: "
            "latency spike → CPU stress → workflow delay → "
            "step skip (SLA pressure) → after-hours write. "
            "Expected: ALL agents detect their respective signals, "
            "CausalAgent links the full chain, "
            "RiskForecastAgent reaches AT_RISK or VIOLATION."
        )
        return execution

    def _inject_resource_drift(
        self, execution: ScenarioExecution, now: datetime
    ) -> ScenarioExecution:
        """Inject gradual resource drift (slow degradation)."""
        import math

        for i in range(15):
            # Gradual CPU drift: 40% → 72% over 15 intervals
            cpu_val = 40 + i * 2.2 + math.sin(i / 3) * 3
            self._observation.observe_metric(ResourceMetric(
                resource_id="vm_db_01",
                metric="cpu_usage",
                value=round(cpu_val, 1),
                timestamp=now + timedelta(seconds=i * 10),
            ).to_dict())
            execution.metrics_injected += 1

        execution.system_response_summary = (
            "Injected 15 CPU metrics showing gradual drift (40%→72%). "
            "Expected: AdaptiveBaselineAgent detects drift trend, "
            "ResourceAgent may or may not trigger (depends on threshold), "
            "showing advantage of adaptive detection."
        )
        return execution

    def _inject_paytm_hotfix_fail(self, execution: ScenarioExecution) -> ScenarioExecution:
        """
        Replay predefined Paytm hotfix failure JSONL dataset.
        """
        file_path = Path("scenarios/paytm_hotfix_fail.jsonl")
        if not file_path.exists():
            raise ValueError(f"Scenario file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as fh:
            for idx, line in enumerate(fh):
                raw = line.strip()
                if not raw:
                    continue
                rec = json.loads(raw)
                ts = self._parse_ts(rec.get("timestamp"))
                source = str(rec.get("source", "unknown")).lower()

                if source == "prometheus":
                    metric_name = str(rec.get("metric", "unknown"))
                    mapped_metric = self._map_metric(metric_name)
                    metric_value = float(rec.get("value", 0.0))
                    resource_id = self._extract_resource_id(rec)
                    self._observation.observe_metric({
                        "resource_id": resource_id,
                        "metric": mapped_metric,
                        "value": metric_value if mapped_metric != "network_latency_ms" else metric_value * 1000.0,
                        "timestamp": ts.isoformat(),
                    })
                    execution.metrics_injected += 1
                    continue

                if source == "github":
                    event = self._to_github_observed_event(rec, idx, ts)
                else:
                    event = self._to_generic_observed_event(rec, idx, ts)
                self._observation.observe_event(event)
                execution.events_injected += 1

        execution.system_response_summary = (
            "Replayed paytm_hotfix_fail.jsonl (25 records): PR merge + CI success "
            "followed by regex-induced CPU saturation, workflow timeout, policy hit, "
            "risk escalation, and recommendation path."
        )
        return execution

    def _parse_ts(self, ts: Optional[str]) -> datetime:
        if not ts:
            return datetime.utcnow()
        normalized = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)

    def _map_metric(self, metric_name: str) -> str:
        mapping = {
            "node_cpu_usage_percent": "cpu_percent",
            "node_memory_usage_percent": "memory_percent",
            "http_request_duration_seconds_p95": "network_latency_ms",
            "deploy_concurrency_active": "cpu_percent",
        }
        return mapping.get(metric_name, metric_name)

    def _extract_resource_id(self, rec: Dict[str, Any]) -> str:
        host = rec.get("host")
        labels = rec.get("labels", {}) if isinstance(rec.get("labels"), dict) else {}
        if host:
            return str(host).split(".")[0]
        if "instance" in labels:
            return str(labels["instance"])
        service = rec.get("service")
        return str(service or "svc_unknown")

    def _to_github_observed_event(self, rec: Dict[str, Any], idx: int, ts: datetime) -> Dict[str, Any]:
        event_type = str(rec.get("event_type", "github_event")).lower()
        action = str(rec.get("action", "")).lower() or "unknown"
        event_id = f"scenario_paytm_gh_{idx:03d}"
        deployment_id = "deploy_paytm_hotfix_847"
        workflow_id = "wf_deployment_paytm_847"
        repo = str(rec.get("repository", "paytm/payment-api"))

        if event_type == "pull_request":
            mapped_type = f"PR_{action.upper()}"
            payload = {
                "pull_request": {
                    "number": rec.get("pr_number"),
                    "title": f"PR #{rec.get('pr_number')} payment hotfix",
                    "changed_files": rec.get("files_changed", 0),
                    "additions": rec.get("files_changed", 0),
                    "deletions": 0,
                    "files": ["payment_regex.py"],
                },
                "metadata": {
                    "churn_lines": rec.get("files_changed", 0),
                    "test_coverage": rec.get("test_coverage", 62),
                    "complexity": 8.2,
                    "hotspot_files": ["payment_regex.py"],
                },
            }
        else:
            mapped_type = f"CI_{action.upper()}"
            payload = {
                "workflow_run": {
                    "name": rec.get("workflow_name", "ci-cd-deploy"),
                    "conclusion": rec.get("conclusion", "success"),
                    "status": rec.get("status", "success"),
                },
                "metadata": {"test_coverage": rec.get("test_coverage", 62)},
            }

        return {
            "event_id": event_id,
            "type": mapped_type,
            "workflow_id": workflow_id,
            "actor": str(rec.get("merged_by", "github-actions[bot]")),
            "resource": "payment-api",
            "timestamp": ts.isoformat(),
            "metadata": {
                "source_signature": {"tool_name": "github", "tool_type": "webhook", "source_host": "github.com"},
                "enterprise_context": {
                    "organization_id": "org_paytm",
                    "project_id": "proj_payment_gateway",
                    "environment": "production",
                    "service_name": "payment-api",
                    "deployment_id": deployment_id,
                    "workflow_id": workflow_id,
                },
                "github": {
                    "event": event_type,
                    "action": action,
                    "repo": repo,
                    "deployment_id": deployment_id,
                },
                "event_payload": payload,
            },
        }

    def _to_generic_observed_event(self, rec: Dict[str, Any], idx: int, ts: datetime) -> Dict[str, Any]:
        message = str(rec.get("message", ""))
        service = str(rec.get("service", "unknown_service"))
        event_id = f"scenario_paytm_evt_{idx:03d}"
        workflow_id = rec.get("workflow_id")
        actor = str(rec.get("actor", "svc_deploy_bot"))
        resource = str(rec.get("host", service))
        event_type = "CONFIG_CHANGE"

        # Map to workflow events where possible to trigger WorkflowAgent.
        if "workflow" in service or workflow_id:
            workflow_id = str(workflow_id or "wf_deployment_paytm_847")
            if "timeout" in message.lower():
                event_type = "WORKFLOW_STEP_COMPLETE"
            elif "failed" in message.lower():
                event_type = "WORKFLOW_STEP_SKIP"
            else:
                event_type = "WORKFLOW_STEP_START"

        # Map compliance signal.
        if "compliance violation" in message.lower():
            event_type = EventType.ACCESS_WRITE.value
            actor = "svc_deploy_bot"
            resource = "pg_prod_customers"
            workflow_id = None

        metadata: Dict[str, Any] = {
            "source": rec.get("source"),
            "level": rec.get("level"),
            "raw": rec,
        }

        if event_type == "WORKFLOW_STEP_COMPLETE":
            raw_step = str(rec.get("step", "production"))
            valid_steps = {"build", "test", "staging", "approval", "production", "complete"}
            step_name = raw_step if raw_step in valid_steps else "production"
            duration_seconds = int(float(rec.get("duration_ms", 180000)) / 1000)
            # Ensure SLA breach for wf_deployment when replaying timeout-style records.
            if duration_seconds <= 120:
                duration_seconds = 180
            metadata.update({
                "step": step_name,
                "step_index": 3,
                "duration_seconds": duration_seconds,
            })
        elif event_type == "WORKFLOW_STEP_SKIP":
            metadata.update({
                "skipped_step": "approval",
                "reason": "hotfix_failure",
            })
        elif event_type == EventType.ACCESS_WRITE.value:
            metadata.update({"location": "internal"})

        return {
            "event_id": event_id,
            "type": event_type,
            "workflow_id": workflow_id,
            "actor": actor,
            "resource": resource,
            "timestamp": ts.isoformat(),
            "metadata": metadata,
        }
