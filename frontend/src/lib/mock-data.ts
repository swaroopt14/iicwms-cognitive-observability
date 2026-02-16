/**
 * IICWMS — Comprehensive Mock Data for Video Demo
 * =================================================
 * Rich, realistic data for all 10 pages. No backend needed.
 */

import type {
  SystemHealth, Insight, Event, Anomaly, AnomalySummary,
  Policy, PolicyViolation, ComplianceSummary, CausalLink,
  RiskDataPoint, RiskIndexResponse, ResourceData, TimelineData,
  OverviewStats, AnomalyTrendPoint, ComplianceTrendPoint, CostTrendPoint,
} from './api';

const now = new Date();
const ts = (minAgo: number) => new Date(now.getTime() - minAgo * 60000).toISOString();

// ============================================
// OVERVIEW PAGE
// ============================================

export const mockSystemHealth: SystemHealth = {
  status: 'DEGRADED',
  active_workflows: 3,
  total_events: 4287,
  active_anomalies: 12,
  risk_level: 'AT_RISK',
  last_update: ts(0),
};

export const mockOverviewStats: OverviewStats = {
  active_workflows: 3,
  total_events: 4287,
  total_metrics: 12450,
  active_anomalies: 12,
  total_anomalies: 847,
  total_violations: 23,
  compliance_rate: 82,
  cycles_completed: 156,
  agents_active: 9,
};

export const mockInsights: Insight[] = [
  {
    insight_id: 'ins_001',
    summary: 'Cascading failure detected — network latency on vm_api_01 is causing workflow deployment delays across 3 pipelines',
    why_it_matters: 'Network latency on vm_api_01 has risen from 45ms to 650ms over the last 15 minutes. This is causing build step timeouts in wf_deployment_03, which triggers automatic retries that further stress CPU on vm_2 (currently at 96%). If not addressed, this creates a feedback loop.',
    what_happens_if_ignored: 'SLA breach within 10-15 minutes for wf_deployment_03. Cascading resource saturation may spread to vm_web_01 and affect user-facing services. Estimated $420/hr in wasted compute from retry loops.',
    recommended_actions: [
      'Immediately throttle non-critical background jobs on vm_api_01',
      'Route traffic through backup CDN (net_backup_01) to reduce latency',
      'Pause non-urgent deployments until network stabilizes',
      'Pre-notify SRE team of potential escalation',
    ],
    severity: 'critical',
    confidence: 0.94,
    evidence_ids: ['evt_1201', 'evt_1202', 'metric_892', 'metric_893'],
    timestamp: ts(2),
  },
  {
    insight_id: 'ins_002',
    summary: 'Silent compliance violation — 3 after-hours write operations detected from unusual VPN location',
    why_it_matters: 'User bob performed 3 write operations to sensitive_db between 1:00 AM and 3:15 AM from IP 192.168.99.1 (unknown VPN). This pattern matches the NO_AFTER_HOURS_WRITE and NO_UNUSUAL_LOCATION policies. The writes succeeded (hence "silent") but create audit and security risk.',
    what_happens_if_ignored: 'Potential data exfiltration risk. Quarterly audit will flag this pattern. If this is a compromised account, sensitive data may already be exposed.',
    recommended_actions: [
      'Review access logs for user_bob for the last 7 days',
      'Temporarily restrict user_bob write access pending review',
      'Enable MFA enforcement for after-hours access',
    ],
    severity: 'high',
    confidence: 0.91,
    evidence_ids: ['evt_1045', 'evt_1046', 'evt_1047'],
    timestamp: ts(5),
  },
  {
    insight_id: 'ins_003',
    summary: 'Resource drift detected — vm_8 CPU trending from 60% to 99% over the last hour with no corresponding workload increase',
    why_it_matters: 'AdaptiveBaselineAgent detected a gradual CPU drift on vm_8 that exceeds the learned baseline by 2.3 standard deviations. Static threshold (80%) was only breached 12 minutes ago, but the adaptive model flagged this 25 minutes earlier. No new deployments or workload changes explain this drift.',
    what_happens_if_ignored: 'vm_8 will reach saturation within 8 minutes. Build pipeline wf_deployment_03 depends on vm_8 and will fail. Recovery will require manual intervention and ~20 minutes of downtime.',
    recommended_actions: [
      'Investigate vm_8 for runaway processes or memory leaks',
      'Pre-provision vm_8_backup as failover',
      'Consider horizontal scaling for build workloads',
    ],
    severity: 'high',
    confidence: 0.87,
    evidence_ids: ['metric_901', 'metric_902', 'anom_drift_01'],
    timestamp: ts(8),
  },
  {
    insight_id: 'ins_004',
    summary: 'Approval step skipped in wf_deployment_03 due to SLA pressure — compliance risk elevated',
    why_it_matters: 'admin_dave manually skipped the APPROVAL step citing "HOTFIX_URGENCY". While the deployment succeeded, this bypasses the mandatory review gate. Combined with the after-hours access pattern, this increases the compliance risk score from 20% to 65%.',
    what_happens_if_ignored: 'Audit finding guaranteed. If the hotfix introduced a bug, there is no approval trail for rollback decisions. Pattern may encourage others to skip approvals.',
    recommended_actions: [
      'Require post-hoc approval from 2 reviewers within 4 hours',
      'Add the skip event to the compliance review queue',
      'Consider automated SLA-pressure detection with conditional fast-track (not skip)',
    ],
    severity: 'medium',
    confidence: 0.85,
    evidence_ids: ['evt_1180', 'evt_1181'],
    timestamp: ts(12),
  },
  {
    insight_id: 'ins_005',
    summary: 'Workflow wf_onboarding_17 DEPLOY step took 480ms (4x expected) — correlated with vm_2 CPU saturation',
    why_it_matters: 'CausalAgent linked the DEPLOY delay to vm_2 CPU at 96%, which in turn correlates with retry loops from network latency. This is part of the cascading failure chain: latency → retries → CPU saturation → deployment delays → SLA risk.',
    what_happens_if_ignored: 'User onboarding SLA (< 5 min total) will be breached. Customer impact if onboarding flow is user-facing.',
    recommended_actions: [
      'Address root cause: network latency on vm_api_01',
      'Implement circuit breaker for retry loops',
      'Add resource-aware scheduling to avoid deploying during saturation',
    ],
    severity: 'medium',
    confidence: 0.82,
    evidence_ids: ['evt_1150', 'metric_880', 'causal_chain_01'],
    timestamp: ts(15),
  },
];

export const mockEvents: Event[] = [
  { event_id: 'evt_1201', type: 'LATENCY_SPIKE', workflow_id: null, actor: 'vm_api_01', resource: 'network', timestamp: ts(1), metadata: { value: 650, threshold: 200 } },
  { event_id: 'evt_1200', type: 'RESOURCE_SPIKE', workflow_id: null, actor: 'vm_2', resource: 'cpu', timestamp: ts(2), metadata: { value: 96, threshold: 80 } },
  { event_id: 'evt_1199', type: 'WORKFLOW_STEP_COMPLETE', workflow_id: 'wf_deployment_03', actor: 'system', resource: 'vm_8', timestamp: ts(3), metadata: { step: 'DEPLOY', actual_duration: 480 } },
  { event_id: 'evt_1198', type: 'WORKFLOW_STEP_SKIP', workflow_id: 'wf_deployment_03', actor: 'admin_dave', resource: null, timestamp: ts(4), metadata: { step: 'APPROVAL', reason: 'HOTFIX_URGENCY' } },
  { event_id: 'evt_1197', type: 'ACCESS_WRITE', workflow_id: null, actor: 'user_bob', resource: 'sensitive_db', timestamp: ts(5), metadata: { ip: '192.168.99.1', hour: 2 } },
  { event_id: 'evt_1196', type: 'WORKFLOW_STEP_START', workflow_id: 'wf_onboarding_17', actor: 'svc_account_01', resource: 'vm_2', timestamp: ts(6), metadata: { step: 'VERIFY' } },
  { event_id: 'evt_1195', type: 'CREDENTIAL_ACCESS', workflow_id: null, actor: 'user_carol', resource: 'admin_credentials', timestamp: ts(7), metadata: { ip: '192.168.99.1' } },
  { event_id: 'evt_1194', type: 'WORKFLOW_START', workflow_id: 'wf_surge_01', actor: 'user_alice', resource: null, timestamp: ts(8), metadata: { workflow_name: 'Deploy Pipeline' } },
  { event_id: 'evt_1193', type: 'RESOURCE_SPIKE', workflow_id: null, actor: 'vm_8', resource: 'memory', timestamp: ts(9), metadata: { value: 91, threshold: 85 } },
  { event_id: 'evt_1192', type: 'ACCESS_WRITE', workflow_id: 'wf_onboarding_17', actor: 'user_alice', resource: 'repo_A', timestamp: ts(10), metadata: { ip: '10.0.1.55' } },
];

export const mockCostTrend: CostTrendPoint[] = [
  { timestamp: ts(55), cost: 32.50, avg_utilization: 45 },
  { timestamp: ts(50), cost: 35.20, avg_utilization: 50 },
  { timestamp: ts(45), cost: 38.80, avg_utilization: 58 },
  { timestamp: ts(40), cost: 42.30, avg_utilization: 65 },
  { timestamp: ts(35), cost: 48.70, avg_utilization: 72 },
  { timestamp: ts(30), cost: 55.20, avg_utilization: 78 },
  { timestamp: ts(25), cost: 62.80, avg_utilization: 82 },
  { timestamp: ts(20), cost: 68.50, avg_utilization: 85 },
  { timestamp: ts(15), cost: 72.30, avg_utilization: 88 },
  { timestamp: ts(10), cost: 78.90, avg_utilization: 91 },
  { timestamp: ts(5), cost: 82.40, avg_utilization: 93 },
  { timestamp: ts(0), cost: 85.60, avg_utilization: 95 },
];

export const mockAnomalyTrend: AnomalyTrendPoint[] = [
  { cycle_id: 'c_001', timestamp: ts(55), total: 8, critical: 2, high: 3, medium: 2, low: 1 },
  { cycle_id: 'c_002', timestamp: ts(50), total: 12, critical: 3, high: 4, medium: 3, low: 2 },
  { cycle_id: 'c_003', timestamp: ts(45), total: 6, critical: 1, high: 2, medium: 2, low: 1 },
  { cycle_id: 'c_004', timestamp: ts(40), total: 18, critical: 6, high: 5, medium: 4, low: 3 },
  { cycle_id: 'c_005', timestamp: ts(35), total: 15, critical: 4, high: 5, medium: 3, low: 3 },
  { cycle_id: 'c_006', timestamp: ts(30), total: 22, critical: 7, high: 6, medium: 5, low: 4 },
  { cycle_id: 'c_007', timestamp: ts(25), total: 14, critical: 3, high: 5, medium: 4, low: 2 },
  { cycle_id: 'c_008', timestamp: ts(20), total: 28, critical: 9, high: 8, medium: 6, low: 5 },
  { cycle_id: 'c_009', timestamp: ts(15), total: 20, critical: 5, high: 7, medium: 5, low: 3 },
  { cycle_id: 'c_010', timestamp: ts(10), total: 25, critical: 8, high: 7, medium: 6, low: 4 },
  { cycle_id: 'c_011', timestamp: ts(5), total: 32, critical: 10, high: 9, medium: 8, low: 5 },
  { cycle_id: 'c_012', timestamp: ts(0), total: 35, critical: 12, high: 10, medium: 8, low: 5 },
];

// ============================================
// ANOMALY CENTER
// ============================================

const anomalyTypes = [
  { type: 'SUSTAINED_CPU_SPIKE', agent: 'ResourceAgent', severity: 'critical' },
  { type: 'NETWORK_LATENCY_SPIKE', agent: 'ResourceAgent', severity: 'critical' },
  { type: 'SEQUENCE_VIOLATION', agent: 'WorkflowAgent', severity: 'high' },
  { type: 'WORKFLOW_DELAY', agent: 'WorkflowAgent', severity: 'high' },
  { type: 'MISSING_STEP', agent: 'WorkflowAgent', severity: 'critical' },
  { type: 'RESOURCE_DRIFT', agent: 'AdaptiveBaselineAgent', severity: 'medium' },
  { type: 'BASELINE_DEVIATION', agent: 'AdaptiveBaselineAgent', severity: 'medium' },
  { type: 'SUSTAINED_MEMORY_WARNING', agent: 'ResourceAgent', severity: 'high' },
  { type: 'POLICY_VIOLATION_CLUSTER', agent: 'ComplianceAgent', severity: 'critical' },
];

export const mockAnomalies: Anomaly[] = Array.from({ length: 35 }, (_, i) => {
  const at = anomalyTypes[i % anomalyTypes.length];
  const resources = ['vm_2', 'vm_3', 'vm_8', 'vm_api_01', 'vm_web_01', 'net_3', 'storage_7'];
  const res = resources[i % resources.length];
  return {
    anomaly_id: `anom_${String(i).padStart(3, '0')}`,
    type: at.type,
    severity: at.severity,
    confidence: 65 + Math.round(Math.sin(i) * 15 + 15),
    agent: at.agent,
    timestamp: ts(i * 2),
    details: `${at.type.replace(/_/g, ' ')} detected on ${res} — confidence ${65 + Math.round(Math.sin(i) * 15 + 15)}%`,
    evidence_ids: [`evt_${1100 + i}`, `metric_${800 + i}`],
  };
});

// ============================================
// COMPLIANCE
// ============================================

export const mockPolicies: Policy[] = [
  { policy_id: 'NO_AFTER_HOURS_WRITE', name: 'No After-Hours Write Operations', condition: 'WRITE && hour(timestamp) NOT IN [9..18]', severity: 'HIGH', rationale: 'Reduces audit risk and prevents unauthorized data modification during off-hours' },
  { policy_id: 'NO_UNUSUAL_LOCATION', name: 'No Unusual Location Access', condition: 'IP_RANGE NOT IN approved_list', severity: 'HIGH', rationale: 'Prevents access from compromised or unauthorized networks' },
  { policy_id: 'SLA_APPROVAL_REQUIRED', name: 'SLA Approval Required for Deploy', condition: 'DEPLOY step requires preceding APPROVAL', severity: 'MEDIUM', rationale: 'Ensures proper authorization before production changes' },
  { policy_id: 'NO_SVC_ACCOUNT_WRITE', name: 'No Service Account Direct Writes', condition: 'actor STARTS_WITH svc_ && type == WRITE', severity: 'MEDIUM', rationale: 'Service accounts should use APIs, not direct writes' },
  { policy_id: 'CREDENTIAL_ACCESS_AUDIT', name: 'Credential Access Must Be Audited', condition: 'type == CREDENTIAL_ACCESS && !audit_logged', severity: 'CRITICAL', rationale: 'All credential access must have audit trail for SOC2 compliance' },
];

export const mockViolations: PolicyViolation[] = [
  { violation_id: 'v_001', policy_id: 'NO_AFTER_HOURS_WRITE', policy_name: 'No After-Hours Write Operations', event_id: 'evt_1045', type: 'SILENT', severity: 'HIGH', status: 'ACTIVE', timestamp: ts(5), details: 'Write to sensitive_db at 2:15 AM from unknown VPN (192.168.99.1). 3rd occurrence this week from user_bob.', workflow_id: undefined },
  { violation_id: 'v_002', policy_id: 'NO_UNUSUAL_LOCATION', policy_name: 'No Unusual Location Access', event_id: 'evt_1046', type: 'SILENT', severity: 'HIGH', status: 'ACTIVE', timestamp: ts(6), details: 'Access from IP 192.168.99.1 (unrecognized VPN) — not in approved IP whitelist. Same source as after-hours writes.', workflow_id: undefined },
  { violation_id: 'v_003', policy_id: 'SLA_APPROVAL_REQUIRED', policy_name: 'SLA Approval Required for Deploy', event_id: 'evt_1180', type: 'EXPLICIT', severity: 'MEDIUM', status: 'ACTIVE', timestamp: ts(4), details: 'admin_dave skipped APPROVAL step in wf_deployment_03 citing "HOTFIX_URGENCY". No post-hoc approval recorded.', workflow_id: 'wf_deployment_03' },
  { violation_id: 'v_004', policy_id: 'CREDENTIAL_ACCESS_AUDIT', policy_name: 'Credential Access Must Be Audited', event_id: 'evt_1195', type: 'SILENT', severity: 'CRITICAL', status: 'ACTIVE', timestamp: ts(7), details: 'user_carol accessed admin_credentials from unknown VPN at 2:30 AM without audit log entry.', workflow_id: undefined },
  { violation_id: 'v_005', policy_id: 'NO_SVC_ACCOUNT_WRITE', policy_name: 'No Service Account Direct Writes', event_id: 'evt_1190', type: 'SILENT', severity: 'MEDIUM', status: 'RESOLVED', timestamp: ts(20), details: 'svc_account_01 performed direct write to production_db at 10:00 PM.', workflow_id: undefined },
];

export const mockComplianceSummary: ComplianceSummary = {
  policiesMonitored: 5,
  activeViolations: 4,
  silentViolations: 3,
  riskExposure: 65,
  auditReadiness: 78,
};

export const mockComplianceTrend: ComplianceTrendPoint[] = [
  { cycle_id: 'c_001', timestamp: ts(55), violations: 0, compliance_rate: 100, risk_exposure: 0 },
  { cycle_id: 'c_002', timestamp: ts(50), violations: 1, compliance_rate: 80, risk_exposure: 15 },
  { cycle_id: 'c_003', timestamp: ts(45), violations: 1, compliance_rate: 80, risk_exposure: 15 },
  { cycle_id: 'c_004', timestamp: ts(40), violations: 2, compliance_rate: 60, risk_exposure: 30 },
  { cycle_id: 'c_005', timestamp: ts(35), violations: 3, compliance_rate: 60, risk_exposure: 42 },
  { cycle_id: 'c_006', timestamp: ts(30), violations: 3, compliance_rate: 60, risk_exposure: 45 },
  { cycle_id: 'c_007', timestamp: ts(25), violations: 4, compliance_rate: 60, risk_exposure: 50 },
  { cycle_id: 'c_008', timestamp: ts(20), violations: 5, compliance_rate: 40, risk_exposure: 58 },
  { cycle_id: 'c_009', timestamp: ts(15), violations: 4, compliance_rate: 60, risk_exposure: 55 },
  { cycle_id: 'c_010', timestamp: ts(10), violations: 5, compliance_rate: 40, risk_exposure: 62 },
  { cycle_id: 'c_011', timestamp: ts(5), violations: 4, compliance_rate: 60, risk_exposure: 60 },
  { cycle_id: 'c_012', timestamp: ts(0), violations: 4, compliance_rate: 60, risk_exposure: 65 },
];

// ============================================
// CAUSAL ANALYSIS
// ============================================

export const mockCausalLinks: CausalLink[] = [
  { link_id: 'cl_001', cause: 'NETWORK_LATENCY_SPIKE (vm_api_01)', effect: 'WORKFLOW_DELAY (wf_deployment_03)', confidence: 92, agent: 'CausalAgent', evidence_ids: ['evt_1201', 'evt_1199'], timestamp: ts(2) },
  { link_id: 'cl_002', cause: 'WORKFLOW_DELAY (wf_deployment_03)', effect: 'RETRY_LOOP (vm_2)', confidence: 88, agent: 'CausalAgent', evidence_ids: ['evt_1199', 'metric_892'], timestamp: ts(3) },
  { link_id: 'cl_003', cause: 'RETRY_LOOP (vm_2)', effect: 'CPU_SATURATION (vm_2)', confidence: 95, agent: 'CausalAgent', evidence_ids: ['metric_892', 'metric_893'], timestamp: ts(3) },
  { link_id: 'cl_004', cause: 'CPU_SATURATION (vm_2)', effect: 'DEPLOY_DELAY (wf_onboarding_17)', confidence: 85, agent: 'CausalAgent', evidence_ids: ['metric_893', 'evt_1150'], timestamp: ts(5) },
  { link_id: 'cl_005', cause: 'SLA_PRESSURE', effect: 'APPROVAL_SKIP (wf_deployment_03)', confidence: 78, agent: 'CausalAgent', evidence_ids: ['evt_1180'], timestamp: ts(4) },
  { link_id: 'cl_006', cause: 'APPROVAL_SKIP', effect: 'COMPLIANCE_VIOLATION', confidence: 97, agent: 'CausalAgent', evidence_ids: ['evt_1180', 'v_003'], timestamp: ts(4) },
  { link_id: 'cl_007', cause: 'AFTER_HOURS_ACCESS (user_bob)', effect: 'SILENT_VIOLATION (NO_AFTER_HOURS_WRITE)', confidence: 99, agent: 'CausalAgent', evidence_ids: ['evt_1045', 'v_001'], timestamp: ts(5) },
  { link_id: 'cl_008', cause: 'UNKNOWN_VPN_ACCESS', effect: 'LOCATION_VIOLATION', confidence: 96, agent: 'CausalAgent', evidence_ids: ['evt_1046', 'v_002'], timestamp: ts(6) },
  { link_id: 'cl_009', cause: 'RESOURCE_DRIFT (vm_8)', effect: 'BUILD_SLOWDOWN', confidence: 72, agent: 'CausalAgent', evidence_ids: ['metric_901', 'evt_1199'], timestamp: ts(8) },
  { link_id: 'cl_010', cause: 'WORKLOAD_SURGE', effect: 'CONCURRENT_WORKFLOW_CONTENTION', confidence: 80, agent: 'CausalAgent', evidence_ids: ['evt_1194', 'metric_895'], timestamp: ts(10) },
  { link_id: 'cl_011', cause: 'MEMORY_PRESSURE (vm_8)', effect: 'GC_PAUSE_SPIKE', confidence: 75, agent: 'CausalAgent', evidence_ids: ['metric_905', 'metric_906'], timestamp: ts(12) },
  { link_id: 'cl_012', cause: 'NETWORK_DEGRADATION', effect: 'API_TIMEOUT_CLUSTER', confidence: 88, agent: 'CausalAgent', evidence_ids: ['evt_1201', 'evt_1210'], timestamp: ts(1) },
];

// ============================================
// RISK / SYSTEM GRAPH
// ============================================

export const mockRiskData: RiskIndexResponse = {
  history: Array.from({ length: 20 }, (_, i) => ({
    timestamp: ts(95 - i * 5),
    cycle_id: `cycle_${i}`,
    risk_score: Math.min(100, 25 + i * 3.5 + Math.sin(i / 2) * 8),
    workflow_risk: Math.min(100, 30 + i * 4 + Math.sin(i / 3) * 10),
    resource_risk: Math.min(100, 20 + i * 3 + Math.cos(i / 2) * 8),
    compliance_risk: i < 8 ? 10 + i * 2 : 30 + (i - 8) * 5,
    risk_state: i < 5 ? 'NORMAL' : i < 12 ? 'DEGRADED' : 'AT_RISK',
    contributions: [
      { agent: 'WorkflowAgent', contribution: 30 + i, reason: 'Sequence violations and delays' },
      { agent: 'ResourceAgent', contribution: 25 + i * 0.5, reason: 'CPU/memory saturation trending up' },
      { agent: 'ComplianceAgent', contribution: 10 + (i > 8 ? (i - 8) * 5 : 0), reason: 'Policy violations detected' },
    ],
  })),
  current_risk: 78.5,
  trend: 'increasing',
};

// ============================================
// RESOURCES
// ============================================

export const mockResources: ResourceData[] = [
  { resource_id: 'vm_2', name: 'Deploy Server', type: 'compute', metrics: { cpu: 96, memory: 82, network_latency: 55 }, trend: [45, 52, 58, 67, 78, 85, 91, 96], status: 'critical', cost_per_hour: 2.45, associated_workflows: ['wf_onboarding_17', 'wf_deployment_03'], anomalies: ['CPU saturation >5min', 'Retry loop detected'], agent_source: 'ResourceAgent' },
  { resource_id: 'vm_3', name: 'API Gateway', type: 'compute', metrics: { cpu: 72, memory: 58, network_latency: 420 }, trend: [80, 95, 120, 180, 240, 350, 400, 420], status: 'warning', cost_per_hour: 1.80, associated_workflows: ['wf_onboarding_17'], anomalies: ['Latency 3x baseline'], agent_source: 'ResourceAgent' },
  { resource_id: 'vm_8', name: 'Build Runner', type: 'compute', metrics: { cpu: 99, memory: 91, network_latency: 250 }, trend: [60, 65, 72, 78, 85, 90, 94, 99], status: 'critical', cost_per_hour: 3.20, associated_workflows: ['wf_deployment_03'], anomalies: ['CPU drift (60%→99%)', 'Memory pressure'], agent_source: 'AdaptiveBaselineAgent' },
  { resource_id: 'vm_api_01', name: 'Primary API', type: 'compute', metrics: { cpu: 88, memory: 72, network_latency: 650 }, trend: [200, 250, 320, 400, 480, 550, 620, 650], status: 'critical', cost_per_hour: 4.50, associated_workflows: ['wf_deployment_03', 'wf_onboarding_17'], anomalies: ['Sustained latency spike', 'Network degradation'], agent_source: 'ResourceAgent' },
  { resource_id: 'net_3', name: 'CDN Edge', type: 'network', metrics: { cpu: 45, memory: 38, network_latency: 85 }, trend: [40, 42, 55, 60, 68, 72, 80, 85], status: 'warning', cost_per_hour: 1.10, associated_workflows: ['wf_onboarding_17'], anomalies: ['Latency drift detected'], agent_source: 'ResourceAgent' },
  { resource_id: 'storage_7', name: 'Log Archive', type: 'storage', metrics: { cpu: 15, memory: 20, network_latency: 10 }, trend: [20, 21, 21, 22, 22, 23, 23, 23], status: 'normal', cost_per_hour: 0.45, associated_workflows: [], anomalies: [], agent_source: 'ResourceAgent' },
  { resource_id: 'vm_web_01', name: 'Web Frontend', type: 'compute', metrics: { cpu: 78, memory: 65, network_latency: 35 }, trend: [50, 55, 62, 70, 75, 78, 78, 78], status: 'warning', cost_per_hour: 2.80, associated_workflows: ['wf_onboarding_17'], anomalies: ['CPU trending up'], agent_source: 'ResourceAgent' },
];

export const mockResourceTrend: Record<string, Array<{metric: string; value: number; timestamp: string}>> = {
  vm_2: [
    ...Array.from({length: 12}, (_, i) => ({ metric: 'cpu_percent', value: 55 + i * 3.5, timestamp: ts(60 - i * 5) })),
    ...Array.from({length: 12}, (_, i) => ({ metric: 'memory_percent', value: 45 + i * 3, timestamp: ts(60 - i * 5) })),
    ...Array.from({length: 12}, (_, i) => ({ metric: 'network_latency_ms', value: 15 + i * 3.5, timestamp: ts(60 - i * 5) })),
  ],
  vm_8: [
    ...Array.from({length: 12}, (_, i) => ({ metric: 'cpu_percent', value: 60 + i * 3.2, timestamp: ts(60 - i * 5) })),
    ...Array.from({length: 12}, (_, i) => ({ metric: 'memory_percent', value: 50 + i * 3.5, timestamp: ts(60 - i * 5) })),
    ...Array.from({length: 12}, (_, i) => ({ metric: 'network_latency_ms', value: 20 + i * 20, timestamp: ts(60 - i * 5) })),
  ],
  vm_api_01: [
    ...Array.from({length: 12}, (_, i) => ({ metric: 'cpu_percent', value: 40 + i * 4, timestamp: ts(60 - i * 5) })),
    ...Array.from({length: 12}, (_, i) => ({ metric: 'memory_percent', value: 35 + i * 3, timestamp: ts(60 - i * 5) })),
    ...Array.from({length: 12}, (_, i) => ({ metric: 'network_latency_ms', value: 200 + i * 40, timestamp: ts(60 - i * 5) })),
  ],
};

// ============================================
// WORKFLOW TIMELINE
// ============================================

function buildTimeline(wfId: string, label: string): TimelineData {
  const start = now.getTime() - 600000;
  const lanes = [
    { id: 'workflow', label: 'Workflow Steps', order: 0, visible: true },
    { id: 'resource', label: 'Resource Events', order: 1, visible: true },
    { id: 'human', label: 'Human Actions', order: 2, visible: true },
    { id: 'compliance', label: 'Compliance', order: 3, visible: true },
  ];

  const nodes = [
    { id: `${wfId}_n1`, laneId: 'workflow' as const, name: 'INIT', status: 'success', timestamp: new Date(start).toISOString(), timestampMs: start, durationMs: 500, confidence: 99, details: { step: 'INIT' }, agentSource: 'WorkflowAgent', dependsOn: [] },
    { id: `${wfId}_n2`, laneId: 'workflow' as const, name: 'PROVISION', status: 'success', timestamp: new Date(start + 30000).toISOString(), timestampMs: start + 30000, durationMs: 120000, confidence: 95, details: { step: 'PROVISION', expected_duration: 60000 }, agentSource: 'WorkflowAgent', dependsOn: [`${wfId}_n1`] },
    { id: `${wfId}_n3`, laneId: 'resource' as const, name: 'CPU Spike (vm_2)', status: 'failed', timestamp: new Date(start + 60000).toISOString(), timestampMs: start + 60000, durationMs: 300000, confidence: 15, details: { metric: 'cpu', value: 96, resource: 'vm_2' }, agentSource: 'ResourceAgent', dependsOn: [] },
    { id: `${wfId}_n4`, laneId: 'workflow' as const, name: 'BUILD', status: 'success', timestamp: new Date(start + 150000).toISOString(), timestampMs: start + 150000, durationMs: 180000, confidence: 88, details: { step: 'BUILD', expected_duration: 60000 }, agentSource: 'WorkflowAgent', dependsOn: [`${wfId}_n2`] },
    { id: `${wfId}_n5`, laneId: 'resource' as const, name: 'Latency Spike (net)', status: 'warning', timestamp: new Date(start + 180000).toISOString(), timestampMs: start + 180000, durationMs: 240000, confidence: 72, details: { metric: 'latency', value: 450, resource: 'vm_api_01' }, agentSource: 'ResourceAgent', dependsOn: [] },
    { id: `${wfId}_n6`, laneId: 'workflow' as const, name: 'DEPLOY', status: 'delayed', timestamp: new Date(start + 330000).toISOString(), timestampMs: start + 330000, durationMs: 480000, confidence: 62, details: { step: 'DEPLOY', expected_duration: 120000 }, agentSource: 'WorkflowAgent', dependsOn: [`${wfId}_n4`] },
    { id: `${wfId}_n7`, laneId: 'human' as const, name: 'Skip Approval', status: 'warning', timestamp: new Date(start + 400000).toISOString(), timestampMs: start + 400000, durationMs: null, confidence: 40, details: { actor: 'admin_dave', reason: 'SLA_PRESSURE' }, agentSource: 'WorkflowAgent', dependsOn: [] },
    { id: `${wfId}_n8`, laneId: 'compliance' as const, name: 'Policy Violation', status: 'failed', timestamp: new Date(start + 410000).toISOString(), timestampMs: start + 410000, durationMs: null, confidence: 8, details: { policy: 'SLA_APPROVAL_REQUIRED', severity: 'MEDIUM' }, agentSource: 'ComplianceAgent', dependsOn: [`${wfId}_n7`] },
    { id: `${wfId}_n9`, laneId: 'workflow' as const, name: 'VERIFY', status: 'in_progress', timestamp: new Date(start + 500000).toISOString(), timestampMs: start + 500000, durationMs: null, confidence: 55, details: { step: 'VERIFY' }, agentSource: 'WorkflowAgent', dependsOn: [`${wfId}_n6`] },
  ];

  return {
    workflowId: wfId,
    workflowLabel: label,
    nodes,
    overallConfidence: 62,
    startTime: start,
    endTime: now.getTime(),
    lanes,
    outcomeSummary: 'Workflow experiencing delays due to cascading resource issues. Approval step was skipped under SLA pressure.',
  };
}

export const mockTimelines: Record<string, TimelineData> = {
  'wf_onboarding_17': buildTimeline('wf_onboarding_17', 'User Onboarding Pipeline'),
  'wf_deployment_03': buildTimeline('wf_deployment_03', 'Service Deployment Pipeline'),
};

// ============================================
// SCENARIOS
// ============================================

export const mockScenarios = [
  { id: 'LATENCY_SPIKE', name: 'Network Latency Spike', description: 'Injects sustained network latency on vm_api_01 (300ms→650ms). Tests ResourceAgent detection and WorkflowAgent cascade.', severity: 'high', expected_agents: ['ResourceAgent', 'WorkflowAgent', 'RiskForecastAgent', 'CausalAgent'], events_to_inject: 0, metrics_to_inject: 8, estimated_detection_time: '1-2 cycles' },
  { id: 'COMPLIANCE_BREACH', name: 'Compliance Breach Pattern', description: 'Injects after-hours writes from unusual locations. Tests ComplianceAgent policy violation detection.', severity: 'high', expected_agents: ['ComplianceAgent', 'RiskForecastAgent'], events_to_inject: 5, metrics_to_inject: 0, estimated_detection_time: '1 cycle' },
  { id: 'WORKLOAD_SURGE', name: 'Workload Surge', description: 'Injects burst of 8 concurrent workflow starts + CPU spike. Tests WorkflowAgent and ResourceAgent under load.', severity: 'medium', expected_agents: ['WorkflowAgent', 'ResourceAgent', 'RiskForecastAgent'], events_to_inject: 12, metrics_to_inject: 4, estimated_detection_time: '1-2 cycles' },
  { id: 'CASCADING_FAILURE', name: 'Cascading Failure', description: 'Full cascade: latency → workflow delay → SLA pressure → human override → compliance risk. Tests ALL agents.', severity: 'critical', expected_agents: ['ResourceAgent', 'WorkflowAgent', 'ComplianceAgent', 'RiskForecastAgent', 'CausalAgent', 'AdaptiveBaselineAgent'], events_to_inject: 8, metrics_to_inject: 10, estimated_detection_time: '2-3 cycles' },
  { id: 'RESOURCE_DRIFT', name: 'Gradual Resource Drift', description: 'Gradual CPU drift (40%→72%) over time. Tests AdaptiveBaselineAgent trend detection vs static thresholds.', severity: 'medium', expected_agents: ['ResourceAgent', 'AdaptiveBaselineAgent', 'RiskForecastAgent'], events_to_inject: 0, metrics_to_inject: 15, estimated_detection_time: '3-5 cycles' },
];
