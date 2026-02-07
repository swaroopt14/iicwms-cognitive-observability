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

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

from simulator.engine import Event, ResourceMetric, EventType
from observation import ObservationLayer, get_observation_layer


class ScenarioType(Enum):
    LATENCY_SPIKE = "LATENCY_SPIKE"
    COMPLIANCE_BREACH = "COMPLIANCE_BREACH"
    WORKLOAD_SURGE = "WORKLOAD_SURGE"
    CASCADING_FAILURE = "CASCADING_FAILURE"
    RESOURCE_DRIFT = "RESOURCE_DRIFT"


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
