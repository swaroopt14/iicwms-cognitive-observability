import axios from 'axios'

const BASE_URL = '/api'

const client = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const api = {
  // Health check
  health: async () => {
    const { data } = await client.get('/health')
    return data
  },

  // Insights
  getInsights: async (params?: { severity?: string; category?: string; limit?: number }) => {
    const { data } = await client.get('/insights', { params })
    return data
  },

  getInsight: async (id: string) => {
    const { data } = await client.get(`/insights/${id}`)
    return data
  },

  analyze: async (request: { workflow_id?: string; resource_id?: string; event_ids?: string[] }) => {
    const { data } = await client.post('/insights/analyze', request)
    return data
  },

  // Hypotheses (Agent Opinions)
  getHypotheses: async (params?: { agent?: string; opinion_type?: string; confidence_min?: number }) => {
    const { data } = await client.get('/hypotheses', { params })
    return data
  },

  getHypothesis: async (id: string) => {
    const { data } = await client.get(`/hypotheses/${id}`)
    return data
  },

  // Events
  getEvents: async (params?: { workflow_id?: string; event_type?: string; limit?: number }) => {
    const { data } = await client.get('/events', { params })
    return data
  },

  createEvent: async (event: {
    event_type: string
    source: string
    workflow_id?: string
    step_id?: string
    resource_id?: string
    metadata?: Record<string, unknown>
  }) => {
    const { data } = await client.post('/events', event)
    return data
  },

  // Stats
  getStats: async () => {
    const { data } = await client.get('/stats')
    return data
  },
}
