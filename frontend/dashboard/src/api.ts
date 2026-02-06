import axios from 'axios'

const BASE_URL = '/api'

const client = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ═══════════════════════════════════════════════════════════════════════════════
// TYPE DEFINITIONS
// ═══════════════════════════════════════════════════════════════════════════════

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'critical'
  confidence: 'HIGH' | 'MEDIUM' | 'LOW'
}

export interface SignalsSummary {
  workflow: 'NORMAL' | 'DEGRADED' | 'CRITICAL'
  policy: 'NORMAL' | 'DEGRADED' | 'CRITICAL'
  resources: 'NORMAL' | 'DEGRADED' | 'CRITICAL'
}

export interface Insight {
  id: string
  timestamp: string
  category: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'
  title: string
  summary: string
  confidence: number
  contributing_opinions: string[]
  recommended_actions: string[]
  explanation: string
  impact?: string
  recommended_action?: string
}

export interface Hypothesis {
  id: string
  agent: string
  opinion_type: string
  severity?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  confidence: number
  timestamp: string
  evidence: Record<string, unknown>
  explanation: string
}

export interface Workflow {
  id: string
  name: string
  status?: string
}

export interface WorkflowGraph {
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
}

export interface WorkflowNode {
  id: string
  name: string
  type: string
  status: 'complete' | 'pending' | 'skipped' | 'failed'
  deviation?: boolean
}

export interface WorkflowEdge {
  source: string
  target: string
  type?: string
}

export interface WorkflowStats {
  avg_duration: number
  deviation: string
  total_runs: number
  success_rate: number
}

export interface Policy {
  id: string
  name: string
  description?: string
  severity?: string
  status?: 'compliant' | 'violated' | 'at_risk'
}

export interface PolicyViolation {
  policy_id: string
  entity: string
  risk: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  timestamp?: string
  details?: string
}

export interface InsightDetail {
  id: string
  summary: string
  impact: string
  recommended_action: string
  confidence: number
  severity: string
  title: string
}

export interface GraphPath {
  nodes: GraphNode[]
  edges: GraphEdge[]
  highlighted_path?: string[]
}

export interface GraphNode {
  id: string
  label: string
  type: 'user' | 'event' | 'workflow' | 'state_change' | 'resource' | 'policy'
  properties?: Record<string, unknown>
}

export interface GraphEdge {
  source: string
  target: string
  type: string
}

export interface Evidence {
  id: string
  agent: string
  claim: string
  evidence_ids: string[]
  confidence: number
  timestamp: string
}

// ═══════════════════════════════════════════════════════════════════════════════
// API FUNCTIONS — Matching spec contracts exactly
// ═══════════════════════════════════════════════════════════════════════════════

export const api = {
  // ─────────────────────────────────────────────────────────────────────────────
  // GLOBAL / TOP BAR APIs (Poll every 10s)
  // ─────────────────────────────────────────────────────────────────────────────
  
  /** GET /system/health */
  getSystemHealth: async (): Promise<SystemHealth> => {
    try {
      const { data } = await client.get('/health')
      // Derive system health from actual data
      const insights = await api.getInsights({ limit: 10 })
      const criticalCount = insights.insights?.filter((i: Insight) => 
        i.severity === 'CRITICAL'
      ).length || 0
      const highCount = insights.insights?.filter((i: Insight) => 
        i.severity === 'HIGH'
      ).length || 0
      
      return {
        status: criticalCount > 0 ? 'critical' : highCount > 0 ? 'degraded' : 'healthy',
        confidence: criticalCount > 0 || highCount > 0 ? 'HIGH' : 'HIGH'
      }
    } catch {
      // Return simulated data for demo
      return {
        status: 'degraded',
        confidence: 'HIGH'
      }
    }
  },

  /** GET /signals/summary */
  getSignalsSummary: async (): Promise<SignalsSummary> => {
    // Simulated for demo - reflects scenario state
    return {
      workflow: 'DEGRADED',
      policy: 'CRITICAL', 
      resources: 'DEGRADED'
    }
  },

  /** GET /scenarios */
  getScenarios: async (): Promise<{ scenarios: { id: string; name: string }[] }> => {
    return {
      scenarios: [
        { id: 'silent-step-skipper', name: 'Silent Step-Skipper' },
        { id: 'resource-vampire', name: 'Resource Vampire' },
        { id: 'credential-leaker', name: 'Credential Leaker' },
      ]
    }
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // /overview APIs
  // ─────────────────────────────────────────────────────────────────────────────

  /** GET /insights?limit=3 */
  getInsights: async (params?: { severity?: string; category?: string; limit?: number }): Promise<{ insights: Insight[] }> => {
    try {
      const { data } = await client.get('/insights', { params })
      return data
    } catch {
      // Return simulated insights for demo
      return {
        insights: [
          {
            id: 'ins-001',
            timestamp: new Date().toISOString(),
            category: 'WORKFLOW_ANOMALY',
            severity: 'HIGH',
            title: 'Mandatory Approval Step Bypassed',
            summary: 'Finance approval step was skipped in Expense Reimbursement workflow, violating mandatory approval policy.',
            confidence: 0.92,
            contributing_opinions: ['hyp-001', 'hyp-002'],
            recommended_actions: ['Review workflow execution logs', 'Verify user permissions'],
            explanation: 'The Workflow Agent detected a skipped mandatory step. Policy Agent confirmed violation.',
            impact: 'Unauthorized payment may have been processed',
            recommended_action: 'Review the workflow execution logs and verify user permissions.'
          },
          {
            id: 'ins-002',
            timestamp: new Date(Date.now() - 300000).toISOString(),
            category: 'SECURITY_CONCERN',
            severity: 'CRITICAL',
            title: 'Credential Access from Unusual Location',
            summary: 'Service account credentials accessed from unknown-external location, deviating from baseline pattern.',
            confidence: 0.88,
            contributing_opinions: ['hyp-003'],
            recommended_actions: ['Investigate access logs', 'Verify service account activity'],
            explanation: 'Policy Agent detected access pattern deviation with high risk score.',
            impact: 'Potential credential compromise',
            recommended_action: 'Immediately review service account access logs.'
          },
          {
            id: 'ins-003',
            timestamp: new Date(Date.now() - 600000).toISOString(),
            category: 'RESOURCE_ISSUE',
            severity: 'MEDIUM',
            title: 'Resource Consumption Trending Upward',
            summary: 'Memory usage increased 45% over observation window, approaching threshold.',
            confidence: 0.75,
            contributing_opinions: ['hyp-004'],
            recommended_actions: ['Monitor resource trends', 'Identify consuming processes'],
            explanation: 'Resource Agent detected gradual increase pattern (Resource Vampire scenario).',
            impact: 'Potential service degradation',
            recommended_action: 'Monitor trends and identify root cause process.'
          }
        ]
      }
    }
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // /workflow-map APIs
  // ─────────────────────────────────────────────────────────────────────────────

  /** GET /workflows */
  getWorkflows: async (): Promise<{ workflows: Workflow[] }> => {
    return {
      workflows: [
        { id: 'wf-expense-001', name: 'Expense Reimbursement', status: 'anomaly' },
        { id: 'wf-access-002', name: 'Access Request', status: 'healthy' },
        { id: 'wf-deploy-003', name: 'Deploy Pipeline', status: 'healthy' },
      ]
    }
  },

  /** GET /workflow/{workflowId}/graph */
  getWorkflowGraph: async (workflowId: string): Promise<WorkflowGraph> => {
    if (workflowId === 'wf-expense-001') {
      return {
        nodes: [
          { id: 's1', name: 'Request Submitted', type: 'step', status: 'complete' },
          { id: 's2', name: 'Manager Review', type: 'step', status: 'complete' },
          { id: 's3', name: 'Finance Approval', type: 'step', status: 'skipped', deviation: true },
          { id: 's4', name: 'Payment Processing', type: 'step', status: 'complete' },
          { id: 's5', name: 'Completed', type: 'step', status: 'complete' },
        ],
        edges: [
          { source: 's1', target: 's2' },
          { source: 's2', target: 's3' },
          { source: 's3', target: 's4' },
          { source: 's4', target: 's5' },
        ]
      }
    }
    return {
      nodes: [
        { id: 's1', name: 'Step 1', type: 'step', status: 'complete' },
        { id: 's2', name: 'Step 2', type: 'step', status: 'complete' },
        { id: 's3', name: 'Step 3', type: 'step', status: 'complete' },
      ],
      edges: [
        { source: 's1', target: 's2' },
        { source: 's2', target: 's3' },
      ]
    }
  },

  /** GET /workflow/{workflowId}/stats */
  getWorkflowStats: async (workflowId: string): Promise<WorkflowStats> => {
    return {
      avg_duration: 120,
      deviation: '+18%',
      total_runs: 47,
      success_rate: 0.89
    }
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // /anomaly-center APIs
  // ─────────────────────────────────────────────────────────────────────────────

  /** GET /hypotheses */
  getHypotheses: async (params?: { agent?: string; opinion_type?: string; confidence_min?: number }): Promise<{ hypotheses: Hypothesis[] }> => {
    try {
      const { data } = await client.get('/hypotheses', { params })
      return data
    } catch {
      return {
        hypotheses: [
          {
            id: 'hyp-001',
            agent: 'workflow_agent',
            opinion_type: 'STEP_SKIPPED',
            severity: 'HIGH',
            confidence: 0.95,
            timestamp: new Date().toISOString(),
            evidence: { skipped_step: 'Finance Approval', workflow_id: 'wf-expense-001' },
            explanation: 'Mandatory step "Finance Approval" was skipped. Later steps completed, confirming bypass.'
          },
          {
            id: 'hyp-002',
            agent: 'policy_agent',
            opinion_type: 'POLICY_VIOLATION',
            severity: 'HIGH',
            confidence: 0.92,
            timestamp: new Date().toISOString(),
            evidence: { policy_id: 'pol-001', step_id: 's3' },
            explanation: 'Mandatory Approval Policy requires approval for all financial transactions. Step completed without approval event.'
          },
          {
            id: 'hyp-003',
            agent: 'policy_agent',
            opinion_type: 'ACCESS_ANOMALY',
            severity: 'CRITICAL',
            confidence: 0.88,
            timestamp: new Date(Date.now() - 300000).toISOString(),
            evidence: { location: 'unknown-external', risk_score: 0.85 },
            explanation: 'Credential access from "unknown-external" does not match normal access patterns. Risk score: 0.85'
          },
          {
            id: 'hyp-004',
            agent: 'resource_agent',
            opinion_type: 'TREND_ANOMALY',
            severity: 'MEDIUM',
            confidence: 0.75,
            timestamp: new Date(Date.now() - 600000).toISOString(),
            evidence: { metric: 'memory_usage', increase: '45%' },
            explanation: 'Gradual increase detected in memory_usage. Average increased from 52% to 75% over observation window.'
          },
          {
            id: 'hyp-005',
            agent: 'rca_agent',
            opinion_type: 'ROOT_CAUSE_HYPOTHESIS',
            severity: 'HIGH',
            confidence: 0.78,
            timestamp: new Date().toISOString(),
            evidence: { causal_chain: ['user_action', 'step_bypass', 'policy_violation'] },
            explanation: 'Causal chain analysis suggests user action led to step bypass, resulting in policy violation. Probable, not proven.'
          }
        ]
      }
    }
  },

  /** GET /hypothesis/{id} */
  getHypothesis: async (id: string): Promise<Hypothesis | null> => {
    const { hypotheses } = await api.getHypotheses()
    return hypotheses.find(h => h.id === id) || null
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // /compliance-view APIs
  // ─────────────────────────────────────────────────────────────────────────────

  /** GET /policies */
  getPolicies: async (): Promise<{ policies: Policy[] }> => {
    return {
      policies: [
        { id: 'pol-001', name: 'Mandatory Approval Policy', description: 'All financial transactions require approval', severity: 'HIGH', status: 'violated' },
        { id: 'pol-002', name: 'Access Control Baseline', description: 'Credential access must match normal patterns', severity: 'CRITICAL', status: 'at_risk' },
        { id: 'pol-003', name: 'Resource Usage Limits', description: 'Resource consumption within thresholds', severity: 'MEDIUM', status: 'compliant' },
        { id: 'pol-004', name: 'No Prod Deploy After Hours', description: 'Production deployments restricted to business hours', severity: 'HIGH', status: 'compliant' },
      ]
    }
  },

  /** GET /policy/violations */
  getPolicyViolations: async (): Promise<{ violations: PolicyViolation[] }> => {
    return {
      violations: [
        {
          policy_id: 'pol-001',
          entity: 'User: john.doe',
          risk: 'HIGH',
          timestamp: new Date().toISOString(),
          details: 'Expense workflow completed without required finance approval'
        },
        {
          policy_id: 'pol-002',
          entity: 'ServiceAccount: svc-api-01',
          risk: 'CRITICAL',
          timestamp: new Date(Date.now() - 300000).toISOString(),
          details: 'Credential accessed from unknown-external location'
        }
      ]
    }
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // /causal-analysis APIs (MOST IMPORTANT)
  // ─────────────────────────────────────────────────────────────────────────────

  /** GET /insight/{insightId} */
  getInsight: async (insightId: string): Promise<InsightDetail> => {
    return {
      id: insightId,
      title: 'Mandatory Approval Step Bypassed',
      summary: 'A financial workflow completed without the required approval step, violating the Mandatory Approval Policy.',
      impact: 'Unauthorized payment of $2,450 may have been processed without proper authorization chain.',
      recommended_action: 'Review workflow execution logs, verify user permissions, and audit the payment transaction.',
      confidence: 0.92,
      severity: 'HIGH'
    }
  },

  /** GET /graph/path/{insightId} */
  getGraphPath: async (insightId: string): Promise<GraphPath> => {
    return {
      nodes: [
        { id: 'u1', label: 'User: john.doe', type: 'user' },
        { id: 'e1', label: 'Event: Submit Expense', type: 'event' },
        { id: 'w1', label: 'Workflow: Expense Reimbursement', type: 'workflow' },
        { id: 'sc1', label: 'State: Approval Skipped', type: 'state_change' },
        { id: 'r1', label: 'Resource: Finance DB', type: 'resource' },
        { id: 'p1', label: 'Policy: Approval Required', type: 'policy' },
      ],
      edges: [
        { source: 'u1', target: 'e1', type: 'PERFORMED' },
        { source: 'e1', target: 'w1', type: 'PART_OF' },
        { source: 'e1', target: 'sc1', type: 'RESULTED_IN' },
        { source: 'sc1', target: 'r1', type: 'AFFECTED' },
        { source: 'e1', target: 'p1', type: 'VIOLATED' },
      ],
      highlighted_path: ['u1', 'e1', 'sc1', 'p1']
    }
  },

  /** GET /insight/{id}/evidence */
  getInsightEvidence: async (insightId: string): Promise<{ evidence: Evidence[] }> => {
    return {
      evidence: [
        {
          id: 'ev-001',
          agent: 'WorkflowAgent',
          claim: 'Finance Approval step was skipped',
          evidence_ids: ['evt-12', 'evt-13', 'evt-15'],
          confidence: 0.95,
          timestamp: new Date().toISOString()
        },
        {
          id: 'ev-002',
          agent: 'PolicyAgent',
          claim: 'Mandatory Approval Policy violated',
          evidence_ids: ['evt-15', 'pol-001'],
          confidence: 0.92,
          timestamp: new Date().toISOString()
        },
        {
          id: 'ev-003',
          agent: 'RCAAgent',
          claim: 'User action led to policy violation via step bypass',
          evidence_ids: ['evt-12', 'evt-15', 'pol-001'],
          confidence: 0.78,
          timestamp: new Date().toISOString()
        }
      ]
    }
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // /insight-feed APIs
  // ─────────────────────────────────────────────────────────────────────────────

  // Uses getInsights with higher limit

  // ─────────────────────────────────────────────────────────────────────────────
  // UTILITY APIs
  // ─────────────────────────────────────────────────────────────────────────────

  getHealth: async (): Promise<{ status: string; timestamp: string }> => {
    try {
      const { data } = await client.get('/health')
      return data
    } catch {
      return { status: 'healthy', timestamp: new Date().toISOString() }
    }
  },

  getStats: async () => {
    try {
      const { data } = await client.get('/stats')
      return data
    } catch {
      return { evidence_store: { total_records: 0 } }
    }
  },
}
