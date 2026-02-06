import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { 
  Clock,
  AlertTriangle,
  ArrowRight,
  Newspaper,
  CheckCircle
} from 'lucide-react'
import { api, Insight } from '../api'

export function InsightFeed() {
  const navigate = useNavigate()

  const { data: insightsData, isLoading } = useQuery({
    queryKey: ['insights', { limit: 50 }],
    queryFn: () => api.getInsights({ limit: 50 }),
  })

  const insights = insightsData?.insights || []

  // Group by date
  const groupedInsights = insights.reduce((acc: Record<string, Insight[]>, insight: Insight) => {
    const date = new Date(insight.timestamp).toLocaleDateString()
    if (!acc[date]) acc[date] = []
    acc[date].push(insight)
    return acc
  }, {})

  return (
    <div className="max-w-3xl mx-auto">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Insight Feed</h1>
        <p className="text-gray-400 mt-1">Executive view of system intelligence</p>
      </div>

      {/* Feed */}
      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-purple mx-auto"></div>
          <p className="text-gray-400 mt-4">Loading insights...</p>
        </div>
      ) : insights.length === 0 ? (
        <div className="card p-12 text-center">
          <CheckCircle className="w-16 h-16 text-status-healthy mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">All Clear</h3>
          <p className="text-gray-400">No active insights requiring attention</p>
          <p className="text-sm text-gray-500 mt-1">System is operating within expected parameters</p>
        </div>
      ) : (
        <div className="space-y-8">
          {Object.entries(groupedInsights).map(([date, dateInsights]) => (
            <div key={date}>
              <div className="flex items-center gap-3 mb-4">
                <div className="h-px flex-1 bg-gray-700" />
                <span className="text-sm text-gray-500">{date}</span>
                <div className="h-px flex-1 bg-gray-700" />
              </div>

              <div className="space-y-4">
                {dateInsights.map((insight: Insight) => (
                  <InsightCard
                    key={insight.id}
                    insight={insight}
                    onClick={() => navigate(`/causal-analysis/${insight.id}`)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function InsightCard({ insight, onClick }: { insight: Insight; onClick: () => void }) {
  const severityConfig: Record<string, { icon: typeof AlertTriangle; color: string; bg: string }> = {
    CRITICAL: { icon: AlertTriangle, color: 'text-severity-critical', bg: 'bg-severity-critical/20' },
    HIGH: { icon: AlertTriangle, color: 'text-severity-high', bg: 'bg-severity-high/20' },
    MEDIUM: { icon: AlertTriangle, color: 'text-severity-medium', bg: 'bg-severity-medium/20' },
    LOW: { icon: AlertTriangle, color: 'text-severity-low', bg: 'bg-severity-low/20' },
    INFO: { icon: Newspaper, color: 'text-gray-400', bg: 'bg-gray-500/20' },
  }

  const config = severityConfig[insight.severity] || severityConfig.INFO
  const Icon = config.icon

  const time = new Date(insight.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <button
      onClick={onClick}
      className="card p-5 w-full text-left hover:bg-surface-elevated transition-colors group"
    >
      <div className="flex gap-4">
        {/* Timeline indicator */}
        <div className="flex flex-col items-center">
          <div className={`w-10 h-10 rounded-full ${config.bg} flex items-center justify-center`}>
            <Icon className={`w-5 h-5 ${config.color}`} />
          </div>
          <div className="w-0.5 flex-1 bg-gray-700 mt-2" />
        </div>

        {/* Content */}
        <div className="flex-1 pb-4">
          <div className="flex items-center gap-3 mb-2">
            <span className={`status-badge ${config.bg} ${config.color}`}>
              {insight.severity}
            </span>
            <span className="text-xs text-gray-500 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {time}
            </span>
          </div>

          <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-accent-purple transition-colors">
            {insight.title}
          </h3>

          <p className="text-gray-400 mb-4 leading-relaxed">
            {insight.summary}
          </p>

          {/* Key metrics */}
          <div className="flex items-center gap-6 text-sm">
            <div>
              <span className="text-gray-500">Confidence: </span>
              <span className="text-white font-medium">{(insight.confidence * 100).toFixed(0)}%</span>
            </div>
            <div>
              <span className="text-gray-500">Category: </span>
              <span className="text-white">{insight.category?.replace(/_/g, ' ')}</span>
            </div>
          </div>

          {/* Action hint */}
          <div className="mt-4 flex items-center text-sm text-accent-purple opacity-0 group-hover:opacity-100 transition-opacity">
            <span>View causal analysis</span>
            <ArrowRight className="w-4 h-4 ml-1" />
          </div>
        </div>
      </div>
    </button>
  )
}
