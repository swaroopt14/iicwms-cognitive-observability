/**
 * IICWMS API Layer — LIVE MODE (Real Backend + Mock Fallback)
 * ============================================================
 * Calls the real backend at NEXT_PUBLIC_API_URL (default: http://localhost:8000).
 * Falls back to mock data if the backend is unreachable.
 */

import axios from 'axios';
import {
  mockSystemHealth, mockInsights, mockEvents, mockAnomalies,
  mockPolicies, mockViolations, mockComplianceSummary, mockCausalLinks,
  mockRiskData, mockResources, mockResourceTrend, mockTimelines,
  mockOverviewStats, mockAnomalyTrend, mockComplianceTrend, mockCostTrend,
  mockScenarios,
} from './mock-data';

// ============================================
// Axios instance — points to real backend
// ============================================
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 8000,
  headers: { 'Content-Type': 'application/json' },
});

// Helper: try real API, fall back to mock
async function tryApi<T>(fn: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await fn();
  } catch {
    console.warn('[API] Backend unavailable, using mock data');
    return fallback;
  }
}

// ============================================
// Type Definitions
// ============================================

export interface SystemHealth {
  status: string;
  active_workflows: number;
  total_events: number;
  active_anomalies: number;
  risk_level: string;
  last_update: string;
}

export interface SignalsSummary {
  workflow_integrity: { status: string; trend: string; why: string };
  policy_risk: { status: string; trend: string; why: string };
  resource_stability: { status: string; trend: string; why: string };
}

export interface Insight {
  insight_id: string;
  summary: string;
  why_it_matters: string;
  what_happens_if_ignored: string;
  recommended_actions: string[];
  severity: string;
  confidence: number;
  evidence_ids: string[];
  timestamp: string;
}

export interface Event {
  event_id: string;
  type: string;
  workflow_id: string | null;
  actor: string;
  resource: string | null;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export interface Hypothesis {
  hypothesis_id: string;
  agent: string;
  claim: string;
  evidence_ids: string[];
  confidence: number;
  timestamp: string;
  type: string;
}

export interface Policy {
  policy_id: string;
  name: string;
  condition: string;
  severity: string;
  rationale: string;
}

export interface PolicyViolation {
  violation_id: string;
  policy_id: string;
  policy_name: string;
  event_id: string;
  type: string;
  severity: string;
  status: string;
  timestamp: string;
  details: string;
  workflow_id?: string;
}

export interface Workflow {
  workflow_id: string;
  name: string;
  status: string;
  current_step: string;
  started_at: string;
  expected_duration: number;
  actual_duration: number;
  project_id?: string;
  project_name?: string;
  environment?: string;
  context_tag?: string;
  input_source?: string;
  issue_category?: string;
}

export interface WorkflowNode {
  id: string;
  step: string;
  status: string;
  timestamp: string;
  duration_ms: number;
  confidence: number;
  lane: string;
}

export interface WorkflowEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface WorkflowGraph {
  workflow_id: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  overall_confidence: number;
}

export interface WorkflowStats {
  workflow_id: string;
  total_steps: number;
  completed_steps: number;
  delayed_steps: number;
  failed_steps: number;
  avg_confidence: number;
  health_index: number;
}

export interface CausalLink {
  link_id: string;
  cause: string;
  effect: string;
  confidence: number;
  agent: string;
  reasoning?: string;
  easy_summary?: string;
  recommended_actions?: string[];
  checklist?: {
    do_now: Array<{ owner: string; action: string }>;
    do_next: Array<{ owner: string; action: string }>;
    verify: Array<{ owner: string; action: string }>;
  };
  evidence_ids: string[];
  timestamp: string;
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  properties: Record<string, unknown>;
}

export interface CausalPath {
  nodes: GraphNode[];
  edges: GraphEdge[];
  confidence: number;
}

export interface Evidence {
  id: string;
  type: string;
  source: string;
  content: string;
  timestamp: string;
  confidence: number;
}

export interface RAGResponse {
  answer: string;
  supporting_evidence: string[];
  evidence_details: Evidence[];
  confidence: number;
  uncertainty: string;
  query_decomposition: {
    original_query: string;
    sub_queries: string[];
    reasoning_approach: string;
  };
}

export interface RiskContribution {
  agent: string;
  contribution: number;
  reason: string;
  signal_type?: string;
  evidence_id?: string;
}

export interface RiskDataPoint {
  timestamp: string;
  cycle_id: string;
  risk_score: number;
  workflow_risk: number;
  resource_risk: number;
  compliance_risk: number;
  risk_state: string;
  contributions: RiskContribution[];
}

export interface RiskIndexResponse {
  history: RiskDataPoint[];
  current_risk: number;
  trend: string;
  last_updated?: string;
  top_drivers?: RiskContribution[];
}

export interface ComplianceSummary {
  policiesMonitored: number;
  activeViolations: number;
  silentViolations: number;
  riskExposure: number;
  auditReadiness: number;
}

export interface Anomaly {
  anomaly_id: string;
  type: string;
  severity: string;
  confidence: number;
  agent: string;
  timestamp: string;
  details: string;
  evidence_ids?: string[];
}

export interface AnomalySummary {
  total: number;
  byAgent: Record<string, number>;
  bySeverity: Record<string, number>;
  trend: string;
}

export interface WorkflowStep {
  step_id: string;
  name: string;
  status: string;
  confidence?: number;
  duration_ms?: number;
  expected_duration_ms?: number;
  evidence_ids?: string[];
}

export interface ResourceData {
  resource_id: string;
  name: string;
  type: 'compute' | 'network' | 'storage';
  metrics: {
    cpu: number;
    memory: number;
    network_latency: number;
  };
  trend: number[];
  status: 'normal' | 'warning' | 'critical';
  cost_per_hour: number;
  associated_workflows: string[];
  anomalies: string[];
  agent_source: string;
}

export interface TimelineNode {
  id: string;
  laneId: 'code' | 'workflow' | 'resource' | 'human' | 'compliance';
  name: string;
  status: string;
  timestamp: string;
  timestampMs: number;
  durationMs?: number | null;
  confidence: number;
  details: Record<string, unknown>;
  agentSource?: string;
  dependsOn?: string[];
  error?: { code: string; message: string; recovery?: string };
}

export interface TimelineData {
  workflowId: string;
  workflowLabel: string;
  nodes: TimelineNode[];
  overallConfidence: number;
  startTime: number;
  endTime: number;
  lanes: Array<{ id: string; label: string; order: number; visible: boolean }>;
  outcomeSummary?: string;
}

export interface AnomalyTrendPoint {
  cycle_id: string;
  timestamp: string;
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface ComplianceTrendPoint {
  cycle_id: string;
  timestamp: string;
  violations: number;
  compliance_rate: number;
  risk_exposure: number;
}

export interface CostTrendPoint {
  timestamp: string;
  cost: number;
  avg_utilization: number;
}

export interface OverviewStats {
  active_workflows: number;
  total_events: number;
  total_metrics: number;
  active_anomalies: number;
  total_anomalies: number;
  total_violations: number;
  compliance_rate: number;
  cycles_completed: number;
  agents_active: number;
}

export interface AuditIncident {
  incident_id: string;
  cycle_id: string;
  timestamp: string;
  risk_score: number;
  risk_state: string;
  anomaly_count: number;
  policy_hit_count: number;
  causal_link_count: number;
  status: string;
}

export interface AuditIncidentDetail {
  incident_id: string;
  cycle_id: string;
  timestamp: string;
  counts: {
    anomalies: number;
    policy_hits: number;
    risk_signals: number;
    causal_links: number;
    recommendations: number;
  };
  evidence_ids: string[];
  cycle_sha256: string;
  cycle: Record<string, unknown>;
}

export interface AuditTimelineItem {
  ts: string;
  kind: 'anomaly' | 'policy_hit' | 'risk_signal' | 'causal_link' | 'recommendation';
  id: string;
  agent: string;
  summary: string;
  confidence: number;
  evidence_ids: string[];
}

export interface RawAuditEvent {
  event_id: string;
  type: string;
  workflow_id: string | null;
  actor: string;
  resource: string | null;
  timestamp: string;
  metadata: Record<string, unknown>;
  observed_at: string;
}

// ============================================
// RAG / Search types (for search page)
// ============================================
export interface SearchRAGEvidence {
  id: string;
  type: string;
  summary: string;
  confidence: number;
  agent: string;
}

export interface SearchCausalStep {
  label: string;
  type: 'cause' | 'effect' | 'risk' | 'outcome';
}

export interface SearchRecommendedAction {
  action: string;
  expected_impact: string;
  priority: 'high' | 'medium' | 'low';
}

export interface SearchRAGResponse {
  answer: string;
  why_it_matters: string[];
  supporting_evidence: SearchRAGEvidence[];
  causal_chain: SearchCausalStep[];
  recommended_actions: SearchRecommendedAction[];
  confidence: number;
  time_horizon: string;
  uncertainty: string;
  follow_up_queries: string[];
  agents_used: string[];
}

export interface WhatIfRunResponse {
  scenario_id: string;
  scenario_type: string;
  parameters: Record<string, unknown>;
  baseline: {
    sla_violations: number;
    compliance_violations: number;
    risk_index: number;
  };
  simulated: {
    sla_violations: number;
    compliance_violations: number;
    risk_index: number;
  };
  impact_score: number;
  confidence: number;
  confidence_reason: string;
  assumptions: string[];
  related_cycle_id?: string | null;
  created_at: string;
}

export interface WhatIfSandboxResponse {
  mode: 'sandbox';
  scenario_type: string;
  parameters: Record<string, unknown>;
  baseline: {
    sla_violations: number;
    compliance_violations: number;
    risk_index: number;
  };
  simulated: {
    sla_violations: number;
    compliance_violations: number;
    risk_index: number;
  };
  impact_score: number;
  confidence: number;
  confidence_reason: string;
  assumptions: string[];
  persisted: false;
  created_at: string;
}

export interface CompositeWhatIfSandboxResponse {
  mode: 'sandbox';
  simulation_type: 'COMPOSITE_CHANGE_IMPACT';
  persisted: false;
  parameters: {
    latency_magnitude: number;
    workload_multiplier: number;
    policy_extension_minutes: number;
    history_window_cycles: number;
  };
  baseline: {
    sla_violations: number;
    compliance_violations: number;
    risk_index: number;
  };
  simulated: {
    sla_violations: number;
    compliance_violations: number;
    risk_index: number;
    projected_state: string;
  };
  impact_score: number;
  confidence: number;
  confidence_reason: string;
  logic: {
    equation: string;
    wf_components: Record<string, number>;
    cv_components: Record<string, number>;
    risk_components: Record<string, number>;
    normalized_terms: Record<string, number>;
  };
  assumptions: string[];
  created_at: string;
}

export interface IndustryIncidentBrief {
  generated_at: string;
  cycle_id?: string | null;
  risk_state: string;
  risk_score: number;
  top_change: {
    change_type: string;
    repository?: string | null;
    deployment_id?: string | null;
    pr_number?: number | string | null;
    event_id?: string | null;
    timestamp?: string | null;
  };
  impacted_workflows: Array<{
    workflow_id: string;
    anomaly_count: number;
    anomaly_types: string[];
    confidence: number;
  }>;
  policy_exposure: {
    total_policy_hits: number;
    top_policies: Array<{ policy_id: string; hits: number }>;
  };
  business_impact: {
    estimated_revenue_impact_inr: number;
    cart_abandon_rate?: number | null;
    impact_source: string;
  };
  top_recommendation: {
    action: string;
    urgency: string;
    confidence?: number;
    source: string;
  };
}

export interface RunbookAction {
  action_code: string;
  title: string;
  priority: string;
  owner_team: string;
  rationale: string;
  evidence_ids: string[];
  automation_possible: boolean;
}

export interface IncidentTaskResponse {
  task_id: string;
  provider: 'jira' | 'servicenow';
  status: string;
  created_at: string;
  payload: Record<string, unknown>;
}

// ============================================
// LIVE API Functions — real backend with mock fallback
// ============================================

export const fetchSystemHealth = async (): Promise<SystemHealth> => {
  return tryApi(async () => {
    const { data } = await api.get('/system/health');
    return data;
  }, mockSystemHealth);
};

export const fetchSignalsSummary = async (): Promise<SignalsSummary> => {
  return tryApi(async () => {
    const { data } = await api.get('/signals/summary');
    return data;
  }, {
    workflow_integrity: { status: 'DEGRADED', trend: 'declining', why: 'Workflow delays from resource saturation' },
    policy_risk: { status: 'AT_RISK', trend: 'increasing', why: '4 active policy violations' },
    resource_stability: { status: 'CRITICAL', trend: 'declining', why: 'Multiple resources above 90% utilization' },
  });
};

export const fetchInsights = async (limit = 10): Promise<Insight[]> => {
  return tryApi(async () => {
    const { data } = await api.get('/insights', { params: { limit } });
    return Array.isArray(data) ? data : data.insights || [];
  }, mockInsights.slice(0, limit));
};

export const fetchInsightById = async (id: string): Promise<Insight> => {
  return tryApi(async () => {
    const { data } = await api.get(`/insight/${id}`);
    return data;
  }, mockInsights.find(i => i.insight_id === id) || mockInsights[0]);
};

export const fetchEvents = async (limit = 50): Promise<Event[]> => {
  return tryApi(async () => {
    const { data } = await api.get('/events', { params: { limit } });
    return Array.isArray(data) ? data : data.events || [];
  }, mockEvents.slice(0, limit));
};

export const fetchHypotheses = async (): Promise<Hypothesis[]> => {
  return tryApi(async () => {
    const { data } = await api.get('/hypotheses');
    return Array.isArray(data) ? data : data.hypotheses || [];
  }, []);
};

export const fetchAnomalies = async (): Promise<Anomaly[]> => {
  return tryApi(async () => {
    const { data } = await api.get('/anomalies');
    return Array.isArray(data) ? data : data.anomalies || [];
  }, mockAnomalies);
};

export const fetchAnomalySummary = async (): Promise<AnomalySummary> => {
  return tryApi(async () => {
    const { data } = await api.get('/anomalies/summary');
    return data;
  }, (() => {
    const byAgent: Record<string, number> = {};
    const bySeverity: Record<string, number> = {};
    mockAnomalies.forEach(a => { byAgent[a.agent] = (byAgent[a.agent] || 0) + 1; bySeverity[a.severity] = (bySeverity[a.severity] || 0) + 1; });
    return { total: mockAnomalies.length, byAgent, bySeverity, trend: 'increasing' };
  })());
};

export const fetchPolicies = async (): Promise<Policy[]> => {
  return tryApi(async () => {
    const { data } = await api.get('/policies');
    return Array.isArray(data) ? data : data.policies || [];
  }, mockPolicies);
};

export const fetchPolicyViolations = async (): Promise<PolicyViolation[]> => {
  return tryApi(async () => {
    const { data } = await api.get('/policy/violations');
    return Array.isArray(data) ? data : data.violations || [];
  }, mockViolations);
};

export const fetchComplianceSummary = async (): Promise<ComplianceSummary> => {
  return tryApi(async () => {
    const { data } = await api.get('/compliance/summary');
    return data;
  }, mockComplianceSummary);
};

export const fetchWorkflows = async (): Promise<Workflow[]> => {
  return tryApi(async () => {
    const { data } = await api.get('/workflows');
    const rows = Array.isArray(data) ? data : data.workflows || [];
    return rows.map((w: Record<string, unknown>) => ({
      workflow_id: String(w.workflow_id || w.id || ''),
      name: String(w.name || w.workflow_id || w.id || 'workflow'),
      status: String(w.status || 'unknown'),
      current_step: String(w.current_step || ''),
      started_at: String(w.started_at || new Date().toISOString()),
      expected_duration: Number(w.expected_duration) || 0,
      actual_duration: Number(w.actual_duration) || 0,
      project_id: w.project_id ? String(w.project_id) : undefined,
      project_name: w.project_name ? String(w.project_name) : undefined,
      environment: w.environment ? String(w.environment) : undefined,
      context_tag: w.context_tag ? String(w.context_tag) : undefined,
      input_source: w.input_source ? String(w.input_source) : undefined,
      issue_category: w.issue_category ? String(w.issue_category) : undefined,
    }));
  }, [
    {
      workflow_id: 'wf_onboarding_17',
      name: 'User Onboarding',
      status: 'running',
      current_step: 'VERIFY',
      started_at: new Date(Date.now() - 600000).toISOString(),
      expected_duration: 300,
      actual_duration: 580,
      project_id: 'proj_customer_onboarding',
      project_name: 'Customer Onboarding Platform',
      environment: 'production',
      context_tag: 'new_update',
      input_source: 'client_side',
      issue_category: 'client_side_error',
    },
    {
      workflow_id: 'wf_deployment_03',
      name: 'Service Deployment',
      status: 'delayed',
      current_step: 'DEPLOY',
      started_at: new Date(Date.now() - 500000).toISOString(),
      expected_duration: 240,
      actual_duration: 480,
      project_id: 'proj_platform_release',
      project_name: 'Platform Release Engineering',
      environment: 'production',
      context_tag: 'deployment_workflow',
      input_source: 'github',
      issue_category: 'deployment_pipeline',
    },
  ]);
};

export const fetchWorkflowGraph = async (id: string): Promise<WorkflowGraph> => {
  return tryApi(async () => {
    const { data } = await api.get(`/workflow/${id}/graph`);
    return data;
  }, { workflow_id: id, nodes: [], edges: [], overall_confidence: 0.78 });
};

export const fetchWorkflowStats = async (id: string): Promise<WorkflowStats> => {
  return tryApi(async () => {
    const { data } = await api.get(`/workflow/${id}/stats`);
    return data;
  }, { workflow_id: id, total_steps: 7, completed_steps: 5, delayed_steps: 2, failed_steps: 0, avg_confidence: 0.82, health_index: 0.65 });
};

export const fetchCausalLinks = async (): Promise<CausalLink[]> => {
  return tryApi(async () => {
    const { data } = await api.get('/causal/links');
    return Array.isArray(data) ? data : data.links || [];
  }, mockCausalLinks);
};

export const fetchCausalPath = async (insightId?: string): Promise<CausalPath> => {
  return tryApi(async () => {
    const url = insightId ? `/graph/path/${insightId}` : '/causal/links';
    const { data } = await api.get(url);
    return data;
  }, { nodes: [], edges: [], confidence: 0 });
};

export const queryRAG = async (query?: string): Promise<RAGResponse> => {
  return tryApi(async () => {
    const { data } = await api.post('/rag/query', { query: query || '' });
    return data;
  }, { answer: '', supporting_evidence: [], evidence_details: [], confidence: 0, uncertainty: '', query_decomposition: { original_query: '', sub_queries: [], reasoning_approach: '' } });
};

export const fetchRAGExamples = async (): Promise<string[]> => {
  return tryApi(async () => {
    const { data } = await api.get('/rag/examples');
    return Array.isArray(data) ? data : data.examples || [];
  }, ['What caused the latency spike?', 'Why is vm_2 at 96% CPU?', 'Which workflows are at risk?']);
};

export const fetchRiskIndex = async (): Promise<RiskIndexResponse> => {
  return tryApi(async () => {
    const { data } = await api.get('/risk/index');
    return data;
  }, mockRiskData);
};

export const fetchCurrentRisk = async () => {
  return tryApi(async () => {
    const { data } = await api.get('/risk/current');
    return data;
  }, { risk_score: 78.5, risk_state: 'AT_RISK', breakdown: { workflow: 85, resource: 92, compliance: 65 } });
};

export const fetchDataSources = async () => {
  return tryApi(async () => {
    const { data } = await api.get('/data-sources');
    return data;
  }, []);
};

export const fetchResources = async (): Promise<ResourceData[]> => {
  return tryApi(async () => {
    const { data } = await api.get('/resources');
    return Array.isArray(data) ? data : data.resources || [];
  }, mockResources);
};

export const fetchResourceMetrics = async (resourceId: string) => {
  return tryApi(async () => {
    const { data } = await api.get(`/resources/${resourceId}/metrics`);
    return data;
  }, { resource_id: resourceId, metrics: [] });
};

export const fetchRecentEvents = async (limit = 50): Promise<Event[]> => {
  return tryApi(async () => {
    const { data } = await api.get('/events', { params: { limit } });
    return Array.isArray(data) ? data : data.events || [];
  }, mockEvents.slice(0, limit));
};

export const fetchRecentMetrics = async () => {
  return tryApi(async () => {
    const { data } = await api.get('/observe/metrics');
    return data;
  }, []);
};

export const fetchWorkflowTimeline = async (workflowId: string): Promise<TimelineData> => {
  return tryApi(async () => {
    const { data } = await api.get(`/workflow/${workflowId}/timeline`);
    return data;
  }, mockTimelines[workflowId] || mockTimelines['wf_onboarding_17']);
};

export const fetchScenarios = async () => {
  return tryApi(async () => {
    const { data } = await api.get('/scenarios');
    return Array.isArray(data) ? data : data.scenarios || [];
  }, mockScenarios);
};

export const injectScenario = async (scenarioId: string) => {
  return tryApi(async () => {
    const { data } = await api.post('/scenarios/inject', { scenario_type: scenarioId });
    return data;
  }, (() => {
    const s = mockScenarios.find(x => x.id === scenarioId);
    return {
      status: 'injected',
      execution: {
        execution_id: `exec_${Date.now()}`,
        scenario_type: scenarioId,
        name: s?.name || scenarioId,
        status: 'completed',
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        events_injected: s?.events_to_inject || 0,
        metrics_injected: s?.metrics_to_inject || 0,
        expected_agents: s?.expected_agents || [],
        system_response_summary: `Injected ${s?.events_to_inject || 0} events and ${s?.metrics_to_inject || 0} metrics.`,
      },
    };
  })());
};

export const triggerAnalysisCycle = async () => {
  return tryApi(async () => {
    const { data } = await api.post('/analysis/cycle');
    return data;
  }, { anomalies: 12, policy_hits: 3, risk_signals: 2, insight_generated: true });
};

export const fetchAnomalyTrend = async (): Promise<AnomalyTrendPoint[]> => {
  return tryApi(async () => {
    const { data } = await api.get('/anomalies/trend');
    return Array.isArray(data) ? data : data.trend || [];
  }, mockAnomalyTrend);
};

export const fetchComplianceTrend = async (): Promise<ComplianceTrendPoint[]> => {
  return tryApi(async () => {
    const { data } = await api.get('/compliance/trend');
    return Array.isArray(data) ? data : data.trend || [];
  }, mockComplianceTrend);
};

export const fetchCostTrend = async (): Promise<CostTrendPoint[]> => {
  return tryApi(async () => {
    const { data } = await api.get('/cost/trend');
    return Array.isArray(data) ? data : data.trend || [];
  }, mockCostTrend);
};

export const fetchOverviewStats = async (): Promise<OverviewStats> => {
  return tryApi(async () => {
    const { data } = await api.get('/overview/stats');
    return data;
  }, mockOverviewStats);
};

export const fetchResourceTrend = async (): Promise<Record<string, Array<{metric: string; value: number; timestamp: string}>>> => {
  return tryApi(async () => {
    const { data } = await api.get('/resources/trend');
    const resources = (data?.resources && typeof data.resources === 'object')
      ? data.resources
      : data;
    if (!resources || typeof resources !== 'object') {
      return {};
    }
    return Object.fromEntries(
      Object.entries(resources).map(([resourceId, points]) => [
        resourceId,
        Array.isArray(points) ? points : [],
      ])
    );
  }, mockResourceTrend);
};

// ============================================
// Search/RAG — Chronos AI query
// ============================================
export const queryChronosAI = async (query: string): Promise<SearchRAGResponse> => {
  const mapResponse = (data: Record<string, unknown>): SearchRAGResponse => {
    const evidence = (data.supporting_evidence || data.evidence || []) as Array<Record<string, unknown> | string>;
    const causal = (data.causal_chain || []) as Array<Record<string, unknown> | string>;
    const actions = (data.recommended_actions || data.recommendations || []) as Array<Record<string, unknown> | string>;
    return {
      answer: String(data.answer || data.response || ''),
      why_it_matters: (data.why_it_matters || data.reasoning || []) as string[],
      supporting_evidence: evidence.map((e) => {
        const obj = (typeof e === 'object' && e !== null) ? e as Record<string, unknown> : {};
        return {
          id: String(obj.id || obj.evidence_id || (typeof e === 'string' ? e : `ev_${Math.random().toString(36).slice(2, 8)}`)),
          type: String(obj.type || 'insight'),
          summary: String(obj.summary || obj.content || (typeof e === 'string' ? e : 'Evidence item')),
          confidence: Number(obj.confidence || 75),
          agent: String(obj.agent || obj.source || 'QueryAgent'),
        };
      }),
      causal_chain: causal.map((c) => {
        const obj = (typeof c === 'object' && c !== null) ? c as Record<string, unknown> : {};
        return {
          label: String(obj.label || obj.step || (typeof c === 'string' ? c : 'Causal step')),
          type: String(obj.type || 'effect') as 'cause' | 'effect' | 'risk' | 'outcome',
        };
      }),
      recommended_actions: actions.map((a) => {
        const obj = (typeof a === 'object' && a !== null) ? a as Record<string, unknown> : {};
        return {
          action: String(obj.action || (typeof a === 'string' ? a : 'Investigate further')),
          expected_impact: String(obj.expected_impact || obj.impact || ''),
          priority: String(obj.priority || obj.urgency || 'medium') as 'high' | 'medium' | 'low',
        };
      }),
      confidence: Number(data.confidence || 75),
      time_horizon: String(data.time_horizon || '5-15 minutes'),
      uncertainty: String(data.uncertainty || 'Based on current agent analysis.'),
      follow_up_queries: (data.follow_up_queries || data.suggestions || []) as string[],
      agents_used: (data.agents_used || data.target_agents || data.agents || ['QueryAgent']) as string[],
    };
  };

  try {
    // Prefer QueryAgent endpoint: includes causal_chain + recommended_actions.
    const { data } = await api.post('/query', { query });
    return mapResponse(data as Record<string, unknown>);
  } catch {
    // Fallback to baseline RAG endpoint.
    try {
      const { data } = await api.post('/rag/query', { query });
      return mapResponse(data as Record<string, unknown>);
    } catch {
      // If both fail, throw to let the search page handle it
      throw new Error('Backend unavailable');
    }
  }
};

export const runWhatIfSimulation = async (
  scenarioType: 'LATENCY_SPIKE' | 'WORKLOAD_SURGE' | 'COMPLIANCE_RELAX',
  parameters: Record<string, unknown>
): Promise<WhatIfRunResponse> => {
  return tryApi(async () => {
    const { data } = await api.post('/simulation/what-if', {
      scenario_type: scenarioType,
      parameters,
    });
    return data as WhatIfRunResponse;
  }, {
    scenario_id: `mock_${Date.now()}`,
    scenario_type: scenarioType,
    parameters,
    baseline: { sla_violations: 2, compliance_violations: 1, risk_index: 55 },
    simulated: { sla_violations: 3, compliance_violations: 2, risk_index: 68 },
    impact_score: 41,
    confidence: 0.7,
    confidence_reason: 'Mock fallback result',
    assumptions: ['Backend unavailable; using fallback simulation output'],
    related_cycle_id: null,
    created_at: new Date().toISOString(),
  });
};

export const runWhatIfSandbox = async (
  scenarioType: 'LATENCY_SPIKE' | 'WORKLOAD_SURGE' | 'COMPLIANCE_RELAX',
  parameters: Record<string, unknown>
): Promise<WhatIfSandboxResponse> => {
  return tryApi(async () => {
    const { data } = await api.post('/simulation/what-if/sandbox', {
      scenario_type: scenarioType,
      parameters,
    });
    return data as WhatIfSandboxResponse;
  }, {
    mode: 'sandbox',
    scenario_type: scenarioType,
    parameters,
    baseline: { sla_violations: 2, compliance_violations: 1, risk_index: 55 },
    simulated: { sla_violations: 3, compliance_violations: 2, risk_index: 68 },
    impact_score: 41,
    confidence: 0.7,
    confidence_reason: 'Mock fallback sandbox output',
    assumptions: ['Backend unavailable; using fallback sandbox'],
    persisted: false,
    created_at: new Date().toISOString(),
  });
};

export const runCompositeWhatIfSandbox = async (request: {
  latency_magnitude: number;
  workload_multiplier: number;
  policy_extension_minutes: number;
  history_window_cycles: number;
}): Promise<CompositeWhatIfSandboxResponse> => {
  return tryApi(async () => {
    const { data } = await api.post('/simulation/what-if/sandbox/composite', request);
    return data as CompositeWhatIfSandboxResponse;
  }, {
    mode: 'sandbox',
    simulation_type: 'COMPOSITE_CHANGE_IMPACT',
    persisted: false,
    parameters: request,
    baseline: { sla_violations: 1.2, compliance_violations: 0.7, risk_index: 34 },
    simulated: { sla_violations: 5.3, compliance_violations: 3.1, risk_index: 73, projected_state: 'VIOLATION' },
    impact_score: 64,
    confidence: 0.82,
    confidence_reason: 'Fallback composite output',
    logic: {
      equation: 'Impact=100*(0.4*WF_norm + 0.35*CV_norm + 0.25*RISK_norm)',
      wf_components: { latency_component: 2.1, workload_component: 3.6, policy_component: 0.6 },
      cv_components: { policy_component: 1.8, workload_component: 0.8, latency_component: 0.4 },
      risk_components: { latency_component: 9.8, workload_component: 12.0, policy_component: 6.0 },
      normalized_terms: { WF_norm: 0.5, CV_norm: 0.45, RISK_norm: 0.62 },
    },
    assumptions: ['Fallback'],
    created_at: new Date().toISOString(),
  });
};

export const fetchIndustryIncidentBrief = async (): Promise<IndustryIncidentBrief> => {
  return tryApi(async () => {
    const { data } = await api.get('/industry/incident-brief');
    return data as IndustryIncidentBrief;
  }, {
    generated_at: new Date().toISOString(),
    cycle_id: null,
    risk_state: 'AT_RISK',
    risk_score: 68,
    top_change: { change_type: 'PR_CLOSED', repository: 'paytm/payment-api', deployment_id: 'deploy_paytm_hotfix_847', pr_number: 847 },
    impacted_workflows: [{ workflow_id: 'wf_deployment_paytm_847', anomaly_count: 3, anomaly_types: ['WORKFLOW_DELAY'], confidence: 0.85 }],
    policy_exposure: { total_policy_hits: 2, top_policies: [{ policy_id: 'NO_AFTER_HOURS_WRITE', hits: 1 }] },
    business_impact: { estimated_revenue_impact_inr: 85620, cart_abandon_rate: 14.7, impact_source: 'mock' },
    top_recommendation: { action: 'Throttle concurrent deploy jobs on vmapi01.', urgency: 'HIGH', confidence: 0.88, source: 'REC_RES_CPU_01' },
  });
};

export const fetchRunbookActions = async (cycleId?: string): Promise<{ cycle_id: string | null; actions: RunbookAction[] }> => {
  return tryApi(async () => {
    const { data } = await api.get('/runbook/actions', { params: cycleId ? { cycle_id: cycleId } : undefined });
    return data as { cycle_id: string | null; actions: RunbookAction[] };
  }, {
    cycle_id: cycleId || null,
    actions: [
      {
        action_code: 'THROTTLE_DEPLOYS',
        title: 'Throttle concurrent deploy jobs on vmapi01.',
        priority: 'P1',
        owner_team: 'devops',
        rationale: 'CPU saturation detected during deployment window.',
        evidence_ids: ['anom_001', 'evt_042'],
        automation_possible: true,
      },
    ],
  });
};

export const createIncidentTask = async (request: {
  provider: 'jira' | 'servicenow';
  title: string;
  description: string;
  priority?: 'P1' | 'P2' | 'P3' | 'P4';
  action_code?: string;
  cycle_id?: string;
  metadata?: Record<string, unknown>;
}): Promise<IncidentTaskResponse> => {
  return tryApi(async () => {
    const { data } = await api.post('/incident/tasks/create', request);
    return data as IncidentTaskResponse;
  }, {
    task_id: `task_mock_${Date.now()}`,
    provider: request.provider,
    status: 'created',
    created_at: new Date().toISOString(),
    payload: { mock: true, ...request },
  });
};

// ============================================
// Scenario executions from backend
// ============================================
export const fetchScenarioExecutions = async () => {
  return tryApi(async () => {
    const { data } = await api.get('/scenarios/executions');
    return Array.isArray(data) ? data : data.executions || [];
  }, []);
};

// ============================================
// Audit APIs
// ============================================
export const fetchAuditIncidents = async (limit = 25): Promise<AuditIncident[]> => {
  return tryApi(async () => {
    const { data } = await api.get('/audit/incidents', { params: { limit } });
    return Array.isArray(data) ? data : data.incidents || [];
  }, []);
};

export const fetchAuditIncident = async (incidentId: string): Promise<AuditIncidentDetail> => {
  return tryApi(async () => {
    const { data } = await api.get(`/audit/incident/${incidentId}`);
    return data;
  }, {
    incident_id: incidentId,
    cycle_id: incidentId,
    timestamp: new Date().toISOString(),
    counts: { anomalies: 0, policy_hits: 0, risk_signals: 0, causal_links: 0, recommendations: 0 },
    evidence_ids: [],
    cycle_sha256: '',
    cycle: {},
  });
};

export const fetchAuditTimeline = async (incidentId: string): Promise<AuditTimelineItem[]> => {
  return tryApi(async () => {
    const { data } = await api.get(`/audit/incident/${incidentId}/timeline`);
    return Array.isArray(data) ? data : data.timeline || [];
  }, []);
};

export const fetchRawAuditEvent = async (eventId: string): Promise<RawAuditEvent> => {
  return tryApi(async () => {
    const { data } = await api.get(`/audit/event/${eventId}/raw`);
    return data;
  }, {
    event_id: eventId,
    type: 'UNKNOWN',
    workflow_id: null,
    actor: 'n/a',
    resource: null,
    timestamp: new Date().toISOString(),
    metadata: {},
    observed_at: new Date().toISOString(),
  });
};

export const exportAuditReport = async (incidentId: string, format: 'json' | 'csv' = 'json') => {
  return tryApi(async () => {
    const { data } = await api.post('/audit/export', { incident_id: incidentId, format });
    return data;
  }, { status: 'ok', format, report: {} });
};

export default api;
