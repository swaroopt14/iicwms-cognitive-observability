import axios from 'axios'

const BASE_URL = '/api'

const client = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types
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
}

export interface Hypothesis {
  id: string
  agent: string
  opinion_type: string
  confidence: number
  timestamp: string
  evidence: Record<string, unknown>
  explanation: string
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'critical'
  active_insights: number
  highest_severity: string
  summary: string
}

export interface SignalSummary {
  workflow_integrity: { status: string; trend: string; reason: string }
  policy_risk: { status: string; trend: string; reason: string }
  resource_stability: { status: string; trend: string; reason: string }
}

export interface Workflow {
  id: string
  name: string
  status: string
  steps: WorkflowStep[]
}

export interface WorkflowStep {
  id: string
  name: string
  sequence: number
  status: 'complete' | 'pending' | 'skipped' | 'failed'
  duration_ms?: number
  deviation?: boolean
}

export interface Policy {
  id: string
  name: string
  description: string
  severity: string
  status: 'compliant' | 'violated' | 'at_risk'
  violations: number
}

export interface GraphPath {
  nodes: GraphNode[]
  edges: GraphEdge[]
  highlighted_path: string[]
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

// API Functions
export const api = {
  // Health & Status
  getHealth: async (): Promise<{ status: string; timestamp: string }> => {
    const { data } = await client.get('/health')
    return data
  },

  getSystemHealth: async (): Promise<SystemHealth> => {
    // Simulated for demo - would be GET /system/health
    try {
      const insights = await api.getInsights({ limit: 10 })
      const criticalCount = insights.insights?.filter((i: Insight) => 
        i.severity === 'CRITICAL' || i.severity === 'HIGH'
      ).length || 0
      
      return {
        status: criticalCount > 2 ? 'critical' : criticalCount > 0 ? 'degraded' : 'healthy',
        active_insights: insights.insights?.length || 0,
        highest_severity: insights.insights?.[0]?.severity || 'INFO',
        summary: insights.insights?.[0]?.summary || 'System operating normally'
      }
    } catch {
      return {
        status: 'healthy',
        active_insights: 0,
        highest_severity: 'INFO',
        summary: 'System operating normally'
      }
    }
  },

  getSignalsSummary: async (): Promise<SignalSummary> => {
    // Simulated for demo - would be GET /signals/summary
    return {
      workflow_integrity: {
        status: 'degraded',
        trend: 'down',
        reason: 'Mandatory approval step bypassed in 2 workflows'
      },
      policy_risk: {
        status: 'at_risk',
        trend: 'up',
        reason: 'Credential access from unusual location detected'
      },
      resource_stability: {
        status: 'healthy',
        trend: 'stable',
        reason: 'All resources within normal thresholds'
      }
    }
  },

  // Insights
  getInsights: async (params?: { severity?: string; category?: string; limit?: number }) => {
    const { data } = await client.get('/insights', { params })
    return data
  },

  getInsight: async (id: string): Promise<{ insight: Insight; evidence: Hypothesis[] }> => {
    const { data } = await client.get(`/insights/${id}`)
    return data
  },

  analyze: async (request: { workflow_id?: string; resource_id?: string; event_ids?: string[] }) => {
    const { data } = await client.post('/insights/analyze', request)
    return data
  },

  // Hypotheses (Anomalies)
  getHypotheses: async (params?: { agent?: string; opinion_type?: string; confidence_min?: number }) => {
    const { data } = await client.get('/hypotheses', { params })
    return data
  },

  getHypothesis: async (id: string) => {
    const { data } = await client.get(`/hypotheses/${id}`)
    return data
  },

  // Workflows
  getWorkflows: async (): Promise<{ workflows: Workflow[] }> => {
    // Simulated for demo
    return {
      workflows: [
        {
          id: 'wf-expense-001',
          name: 'Expense Reimbursement',
          status: 'anomaly',
          steps: [
            { id: 's1', name: 'Request Submitted', sequence: 1, status: 'complete' },
            { id: 's2', name: 'Manager Review', sequence: 2, status: 'complete' },
            { id: 's3', name: 'Finance Approval', sequence: 3, status: 'skipped', deviation: true },
            { id: 's4', name: 'Payment Processing', sequence: 4, status: 'complete' },
          ]
        },
        {
          id: 'wf-access-002',
          name: 'Access Request',
          status: 'healthy',
          steps: [
            { id: 's1', name: 'Request Created', sequence: 1, status: 'complete' },
            { id: 's2', name: 'Security Review', sequence: 2, status: 'complete' },
            { id: 's3', name: 'Provisioning', sequence: 3, status: 'complete' },
          ]
        }
      ]
    }
  },

  getWorkflowGraph: async (id: string): Promise<{ nodes: WorkflowStep[]; edges: { source: string; target: string }[] }> => {
    const workflows = await api.getWorkflows()
    const workflow = workflows.workflows.find(w => w.id === id)
    if (!workflow) throw new Error('Workflow not found')
    
    const edges = workflow.steps.slice(0, -1).map((step, i) => ({
      source: step.id,
      target: workflow.steps[i + 1].id
    }))
    
    return { nodes: workflow.steps, edges }
  },

  // Policies
  getPolicies: async (): Promise<{ policies: Policy[] }> => {
    return {
      policies: [
        {
          id: 'pol-001',
          name: 'Mandatory Approval Policy',
          description: 'All financial transactions require approval',
          severity: 'HIGH',
          status: 'violated',
          violations: 2
        },
        {
          id: 'pol-002',
          name: 'Access Control Baseline',
          description: 'Credential access must match normal patterns',
          severity: 'CRITICAL',
          status: 'at_risk',
          violations: 1
        },
        {
          id: 'pol-003',
          name: 'Resource Usage Limits',
          description: 'Resource consumption within defined thresholds',
          severity: 'MEDIUM',
          status: 'compliant',
          violations: 0
        }
      ]
    }
  },

  getPolicyViolations: async (): Promise<{ violations: Array<{ policy_id: string; entity: string; timestamp: string; details: string }> }> => {
    return {
      violations: [
        {
          policy_id: 'pol-001',
          entity: 'workflow/expense-001',
          timestamp: new Date().toISOString(),
          details: 'Finance approval step was bypassed'
        },
        {
          policy_id: 'pol-002',
          entity: 'credential/svc-account-01',
          timestamp: new Date().toISOString(),
          details: 'Access from unknown-external location'
        }
      ]
    }
  },

  // Graph / Causal Analysis
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

  // Events
  getEvents: async (params?: { workflow_id?: string; event_type?: string; limit?: number }) => {
    const { data } = await client.get('/events', { params })
    return data
  },

  // Stats
  getStats: async () => {
    const { data } = await client.get('/stats')
    return data
  },
}
