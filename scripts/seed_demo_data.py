#!/usr/bin/env python3
"""
IICWMS Demo Data Seeder — Per-Page Data Generator
===================================================
Ensures EVERY frontend page has rich, diverse, real-time data.

Run AFTER the backend is started:
    python3 scripts/seed_demo_data.py

What it does per page:
  1. Overview     - Diverse events, cost metrics, multi-agent insights
  2. Anomaly Ctr  - Multi-type anomalies across severity levels
  3. Compliance   - Violation-triggering events (after-hours, unusual access)
  4. Causal       - Cascading failure events that create causal chains
  5. Insight Feed - Enough cycles to generate diverse insights
  6. System Graph - Risk-driving metrics to fill risk trend chart
  7. Workflow Map - Events for both tracked workflows
  8. Resource/Cost- Metrics for all 5 resource types (CPU, mem, network)
  9. Search       - (no seeding needed, works on existing data)
  10. Scenarios   - Inject 3 scenarios + run cycles for execution history
"""

import urllib.request
import json
import time
import sys
from datetime import datetime, timezone, timedelta

API = "http://localhost:8000"


def post(path, body=None):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        f"{API}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        return None


def get(path):
    try:
        with urllib.request.urlopen(f"{API}{path}", timeout=10) as r:
            return json.loads(r.read())
    except:
        return None


def seed_workflow_events():
    """Seed events for both tracked workflows (Timeline & Overview pages)."""
    print("\n[1/7] Seeding workflow events...", flush=True)
    now = datetime.now(timezone.utc)
    count = 0

    # wf_onboarding_17 lifecycle
    wf1_steps = [
        ("WORKFLOW_START", 0, "system", None, {"step": "INIT"}),
        ("WORKFLOW_STEP_START", 1, "svc_account_01", "repo_A", {"step": "PROVISION", "expected_duration": 60}),
        ("WORKFLOW_STEP_COMPLETE", 3, "svc_account_01", "repo_A", {"step": "PROVISION", "actual_duration": 120}),
        ("WORKFLOW_STEP_START", 4, "svc_account_01", "vm_2", {"step": "DEPLOY", "expected_duration": 120}),
        ("WORKFLOW_STEP_COMPLETE", 8, "svc_account_01", "vm_2", {"step": "DEPLOY", "actual_duration": 480}),
        ("WORKFLOW_STEP_START", 9, "svc_account_01", None, {"step": "VERIFY", "expected_duration": 60}),
        ("WORKFLOW_STEP_COMPLETE", 12, "svc_account_01", None, {"step": "VERIFY", "actual_duration": 180}),
        ("ACCESS_WRITE", 5, "user_alice", "repo_A", {"ip": "10.0.1.55", "hour": 14}),
        ("ACCESS_READ", 7, "user_alice", "config_store", {"ip": "10.0.1.55", "hour": 15}),
    ]

    for t, offset, actor, resource, meta in wf1_steps:
        result = post("/observe/event", {
            "event_id": f"seed_wf1_{count:03d}",
            "type": t,
            "workflow_id": "wf_onboarding_17",
            "actor": actor,
            "resource": resource,
            "timestamp": (now - timedelta(minutes=30 - offset)).isoformat(),
            "metadata": meta,
        })
        if result:
            count += 1

    # wf_deployment_03 lifecycle
    wf2_steps = [
        ("WORKFLOW_START", 0, "system", None, {"step": "INIT"}),
        ("WORKFLOW_STEP_START", 1, "svc_account_02", "vm_3", {"step": "BUILD", "expected_duration": 180}),
        ("WORKFLOW_STEP_COMPLETE", 5, "svc_account_02", "vm_3", {"step": "BUILD", "actual_duration": 300}),
        ("WORKFLOW_STEP_START", 6, "svc_account_02", "vm_3", {"step": "TEST", "expected_duration": 120}),
        ("WORKFLOW_STEP_COMPLETE", 10, "svc_account_02", "vm_3", {"step": "TEST", "actual_duration": 240}),
        ("WORKFLOW_STEP_START", 11, "svc_account_02", "vm_8", {"step": "DEPLOY", "expected_duration": 60}),
        ("WORKFLOW_STEP_COMPLETE", 15, "svc_account_02", "vm_8", {"step": "DEPLOY", "actual_duration": 240}),
        ("WORKFLOW_STEP_SKIP", 16, "admin_dave", None, {"step": "APPROVAL", "reason": "HOTFIX_URGENCY"}),
    ]

    for t, offset, actor, resource, meta in wf2_steps:
        result = post("/observe/event", {
            "event_id": f"seed_wf2_{count:03d}",
            "type": t,
            "workflow_id": "wf_deployment_03",
            "actor": actor,
            "resource": resource,
            "timestamp": (now - timedelta(minutes=25 - offset)).isoformat(),
            "metadata": meta,
        })
        if result:
            count += 1

    print(f"  {count} workflow events injected", flush=True)
    return count


def seed_compliance_events():
    """Seed compliance-triggering events (Compliance page)."""
    print("\n[2/7] Seeding compliance-triggering events...", flush=True)
    now = datetime.now(timezone.utc)
    count = 0

    compliance_events = [
        # After-hours writes
        ("ACCESS_WRITE", "user_bob", "repo_B", {"ip": "192.168.99.1", "hour": 2, "location": "unknown_vpn"}),
        ("ACCESS_WRITE", "user_charlie", "db_prod", {"ip": "10.0.1.77", "hour": 3, "location": "internal"}),
        ("ACCESS_WRITE", "user_bob", "sensitive_db", {"ip": "192.168.99.1", "hour": 1, "resource_sensitivity": "high"}),
        # Unusual location access
        ("ACCESS_WRITE", "user_dave", "admin_panel", {"ip": "203.0.113.45", "hour": 14, "location": "unknown_vpn"}),
        # Credential access
        ("CREDENTIAL_ACCESS", "user_carol", "admin_credentials", {"ip": "192.168.99.1", "hour": 2, "location": "unknown_vpn"}),
        # Manual override (skip approval)
        ("WORKFLOW_STEP_SKIP", "admin_dave", None, {"step": "APPROVAL", "reason": "SLA_PRESSURE"}),
        # Service account direct write
        ("ACCESS_WRITE", "svc_account_01", "production_db", {"ip": "10.0.1.100", "hour": 22, "location": "internal"}),
    ]

    for t, actor, resource, meta in compliance_events:
        result = post("/observe/event", {
            "event_id": f"seed_comp_{count:03d}",
            "type": t,
            "workflow_id": None,
            "actor": actor,
            "resource": resource,
            "timestamp": (now - timedelta(minutes=20 - count)).isoformat(),
            "metadata": meta,
        })
        if result:
            count += 1

    print(f"  {count} compliance events injected", flush=True)
    return count


def seed_resource_metrics():
    """Seed diverse resource metrics (Resource/Cost & System Graph pages)."""
    print("\n[3/7] Seeding resource metrics...", flush=True)
    now = datetime.now(timezone.utc)
    count = 0

    resources = {
        "vm_2": {
            "cpu_percent": [55, 62, 68, 75, 82, 88, 93, 96, 98, 99, 97, 95],
            "memory_percent": [45, 48, 52, 58, 64, 70, 75, 78, 80, 82, 79, 77],
            "network_latency_ms": [15, 18, 22, 28, 35, 45, 55, 65, 70, 68, 62, 58],
        },
        "vm_3": {
            "cpu_percent": [35, 38, 42, 48, 55, 62, 68, 72, 75, 78, 74, 70],
            "memory_percent": [40, 42, 45, 48, 52, 55, 58, 62, 65, 68, 66, 63],
            "network_latency_ms": [120, 150, 180, 220, 280, 350, 420, 480, 520, 550, 500, 460],
        },
        "vm_8": {
            "cpu_percent": [60, 65, 72, 78, 85, 90, 94, 97, 99, 98, 96, 93],
            "memory_percent": [50, 55, 62, 68, 75, 82, 88, 91, 93, 92, 89, 86],
            "network_latency_ms": [20, 25, 35, 50, 80, 120, 180, 250, 300, 280, 240, 200],
        },
        "net_3": {
            "cpu_percent": [25, 28, 32, 35, 38, 42, 45, 48, 52, 55, 52, 48],
            "memory_percent": [35, 38, 42, 45, 48, 52, 55, 58, 62, 65, 63, 60],
            "network_latency_ms": [100, 130, 160, 200, 260, 340, 420, 500, 560, 600, 550, 480],
        },
        "storage_7": {
            "cpu_percent": [15, 18, 20, 22, 25, 28, 30, 33, 35, 38, 36, 34],
            "memory_percent": [30, 32, 35, 38, 42, 45, 48, 52, 55, 58, 56, 53],
            "network_latency_ms": [40, 55, 75, 100, 140, 190, 250, 320, 380, 420, 380, 340],
        },
        # Additional resources for the cascading failure scenario
        "vm_api_01": {
            "cpu_percent": [40, 45, 52, 60, 68, 75, 82, 88, 92, 95, 93, 90],
            "memory_percent": [35, 38, 42, 48, 55, 62, 68, 72, 75, 78, 76, 73],
            "network_latency_ms": [200, 250, 320, 400, 480, 550, 620, 680, 720, 750, 700, 650],
        },
        "vm_web_01": {
            "cpu_percent": [50, 55, 62, 70, 78, 85, 90, 94, 97, 99, 96, 92],
            "memory_percent": [45, 48, 52, 58, 65, 72, 78, 82, 85, 88, 85, 82],
            "network_latency_ms": [30, 35, 45, 60, 80, 110, 150, 200, 260, 320, 290, 250],
        },
    }

    for res_id, metrics_map in resources.items():
        for metric_name, values in metrics_map.items():
            for i, val in enumerate(values):
                result = post("/observe/metric", {
                    "resource_id": res_id,
                    "metric": metric_name,
                    "value": float(val),
                    "timestamp": (now - timedelta(minutes=60 - i * 5)).isoformat(),
                })
                if result:
                    count += 1

    print(f"  {count} metrics injected across {len(resources)} resources", flush=True)
    return count


def run_scenarios():
    """Inject scenarios for the Scenarios page execution history."""
    print("\n[4/7] Injecting stress scenarios...", flush=True)
    injected = 0
    for sid in ["LATENCY_SPIKE", "COMPLIANCE_BREACH", "CASCADING_FAILURE"]:
        result = post("/scenarios/inject", {"scenario_id": sid})
        if result and result.get("status") == "injected":
            injected += 1
            exec_data = result.get("execution", {})
            print(f"  {sid}: {exec_data.get('events_injected', 0)} events, {exec_data.get('metrics_injected', 0)} metrics", flush=True)
        else:
            print(f"  {sid}: skipped", flush=True)
        time.sleep(0.3)
    print(f"  {injected}/3 scenarios injected", flush=True)
    return injected


def run_analysis_cycles(n=6):
    """Run analysis cycles to generate insights, anomalies, causal links."""
    print(f"\n[5/7] Running {n} analysis cycles...", flush=True)
    for i in range(n):
        post("/simulation/tick")
        time.sleep(0.3)
        result = post("/analysis/cycle")
        if result:
            a = result.get("anomalies", 0)
            v = result.get("policy_hits", 0)
            r = result.get("risk_signals", 0)
            ins = "yes" if result.get("insight_generated") else "no"
            print(f"  Cycle {i+1}: {a} anomalies, {v} violations, {r} risks, insight={ins}", flush=True)
        time.sleep(1)


def run_additional_scenarios():
    """Run remaining scenarios for full coverage."""
    print("\n[6/7] Injecting remaining scenarios...", flush=True)
    for sid in ["WORKLOAD_SURGE", "RESOURCE_DRIFT"]:
        result = post("/scenarios/inject", {"scenario_id": sid})
        if result and result.get("status") == "injected":
            print(f"  {sid}: injected", flush=True)
        time.sleep(0.3)
    # Run 2 more cycles to process these
    for i in range(2):
        post("/simulation/tick")
        time.sleep(0.3)
        post("/analysis/cycle")
        time.sleep(1)
    print("  2 additional cycles completed", flush=True)


def verify():
    """Verify all pages have sufficient data."""
    print("\n[7/7] Verifying page data coverage...", flush=True)

    checks = [
        # Page, Endpoint, Check function, Description
        ("Overview Stats", "/overview/stats", lambda d: d.get("total_events", 0) >= 10, "events & stats"),
        ("Overview Insights", "/insights?limit=5", lambda d: len(d.get("insights", [])) >= 2, "insights"),
        ("Overview Events", "/events?limit=10", lambda d: len(d) >= 5 if isinstance(d, list) else False, "events"),
        ("Overview Risk", "/risk/index", lambda d: len(d.get("data", [])) >= 5, "risk data"),
        ("Overview Cost", "/cost/trend", lambda d: len(d) >= 3 if isinstance(d, list) else False, "cost trend"),
        ("Overview Anomaly Chart", "/anomalies/trend", lambda d: len(d) >= 3 if isinstance(d, list) else False, "anomaly trend"),
        ("Anomaly Center", "/anomalies", lambda d: len(d) >= 10 if isinstance(d, list) else False, "anomalies"),
        ("Compliance Policies", "/policies", lambda d: len(d.get("policies", [])) >= 3, "policies"),
        ("Compliance Violations", "/policy/violations", lambda d: len(d.get("violations", [])) >= 1, "violations"),
        ("Compliance Trend", "/compliance/trend", lambda d: len(d) >= 3 if isinstance(d, list) else False, "compliance trend"),
        ("Compliance Summary", "/compliance/summary", lambda d: d.get("policiesMonitored", 0) >= 3, "compliance summary"),
        ("Causal Links", "/causal/links", lambda d: len(d) >= 5 if isinstance(d, list) else False, "causal links"),
        ("Insight Feed", "/insights?limit=20", lambda d: len(d.get("insights", [])) >= 5, "insights"),
        ("System Graph Risk", "/risk/index", lambda d: len(d.get("data", [])) >= 8, "risk history"),
        ("Workflow Onboarding", "/workflow/wf_onboarding_17/timeline", lambda d: len(d.get("nodes", [])) >= 5, "timeline nodes"),
        ("Workflow Deployment", "/workflow/wf_deployment_03/timeline", lambda d: len(d.get("nodes", [])) >= 5, "timeline nodes"),
        ("Resources", "/resources", lambda d: len(d.get("resources", [])) >= 3, "resources"),
        ("Resource Trends", "/resources/trend", lambda d: len(d.get("resources", {})) >= 3, "resource trends"),
        ("Scenarios", "/scenarios", lambda d: len(d.get("scenarios", [])) >= 3, "scenarios"),
        ("Scenario History", "/scenarios/executions", lambda d: len(d.get("executions", [])) >= 1, "executions"),
        ("Agent Activity", "/agents/activity?limit=10", lambda d: len(d.get("activity", [])) >= 3, "activities"),
    ]

    passed = 0
    total = len(checks)
    for name, path, check, desc in checks:
        data = get(path)
        if data and check(data):
            passed += 1
            print(f"  PASS  {name} ({desc})", flush=True)
        else:
            print(f"  SPARSE {name} ({desc})", flush=True)

    print(f"\n  Result: {passed}/{total} checks passed", flush=True)
    return passed == total


def main():
    print("=" * 60)
    print("  IICWMS Demo Data Seeder — Per-Page Data Generator")
    print("=" * 60)

    health = get("/health")
    if not health:
        print("ERROR: Backend not running at http://localhost:8000")
        sys.exit(1)
    print(f"Backend: OK ({health.get('cycles_completed', 0)} cycles already)", flush=True)

    seed_workflow_events()
    seed_compliance_events()
    seed_resource_metrics()
    run_scenarios()
    run_analysis_cycles(6)
    run_additional_scenarios()
    ok = verify()

    print("\n" + "=" * 60)
    if ok:
        print("  ALL PAGES READY FOR DEMO — Full real-time data")
    else:
        print("  Most pages ready — run seed script again for remaining")
    print("=" * 60)


if __name__ == "__main__":
    main()
