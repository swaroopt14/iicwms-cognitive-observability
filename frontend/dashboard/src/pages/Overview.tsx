import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { 
  CheckCircle, 
  AlertTriangle, 
  XCircle, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  ArrowRight,
  Info,
  Shield,
  GitBranch,
  Cpu
} from 'lucide-react'
import { api, SystemHealth, SignalSummary, Insight } from '../api'

export function Overview() {
  const navigate = useNavigate()

  const { data: health } = useQuery({
    queryKey: ['system-health'],
    queryFn: api.getSystemHealth,
  })

  const { data: signals } = useQuery({
    queryKey: ['signals-summary'],
    queryFn: api.getSignalsSummary,
  })

  const { data: insights } = useQuery({
    queryKey: ['insights', { limit: 3 }],
    queryFn: () => api.getInsights({ limit: 3 }),
  })

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">System Intelligence Summary</h1>
        <p className="text-gray-400 mt-1">Real-time cognitive observability status</p>
      </div>

      {/* System Status Strip */}
      <SystemStatusStrip health={health} />

      {/* Cognitive Signals */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Cognitive Signals</h2>
        <div className="grid grid-cols-3 gap-4">
          <SignalCard
            title="Workflow Integrity"
            icon={GitBranch}
            signal={signals?.workflow_integrity}
            onClick={() => navigate('/workflow-map')}
          />
          <SignalCard
            title="Policy Risk"
            icon={Shield}
            signal={signals?.policy_risk}
            onClick={() => navigate('/compliance-view')}
          />
          <SignalCard
            title="Resource Stability"
            icon={Cpu}
            signal={signals?.resource_stability}
            onClick={() => navigate('/anomaly-center')}
          />
        </div>
      </div>

      {/* Active Insights Feed */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Active Insights</h2>
          <button
            onClick={() => navigate('/insight-feed')}
            className="text-sm text-accent-purple hover:text-purple-400 flex items-center gap-1"
          >
            View all <ArrowRight className="w-4 h-4" />
          </button>
        </div>
        
        <div className="space-y-3">
          {insights?.insights?.length === 0 ? (
            <div className="card p-8 text-center">
              <CheckCircle className="w-12 h-12 text-status-healthy mx-auto mb-3" />
              <p className="text-gray-300">No active insights</p>
              <p className="text-sm text-gray-500">System is operating normally</p>
            </div>
          ) : (
            insights?.insights?.slice(0, 3).map((insight: Insight) => (
              <InsightRow
                key={insight.id}
                insight={insight}
                onClick={() => navigate(`/causal-analysis/${insight.id}`)}
              />
            ))
          )}
        </div>
      </div>
    </div>
  )
}

function SystemStatusStrip({ health }: { health?: SystemHealth }) {
  const statusConfig = {
    healthy: { icon: CheckCircle, color: 'text-status-healthy', bg: 'bg-status-healthy/10', label: 'Normal' },
    degraded: { icon: AlertTriangle, color: 'text-status-degraded', bg: 'bg-status-degraded/10', label: 'Degraded' },
    critical: { icon: XCircle, color: 'text-status-critical', bg: 'bg-status-critical/10', label: 'Critical' },
  }

  const config = statusConfig[health?.status || 'healthy']
  const Icon = config.icon

  return (
    <div className={`card p-4 ${config.bg} border-l-4 ${config.color.replace('text-', 'border-')}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Icon className={`w-8 h-8 ${config.color}`} />
          <div>
            <div className="flex items-center gap-2">
              <span className={`text-xl font-bold ${config.color}`}>{config.label}</span>
              <span className="text-gray-400">•</span>
              <span className="text-gray-300">{health?.active_insights || 0} active insights</span>
            </div>
            <p className="text-gray-400 text-sm mt-0.5">{health?.summary}</p>
          </div>
        </div>
        
        {health?.highest_severity && health.highest_severity !== 'INFO' && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400">Highest Severity:</span>
            <SeverityBadge severity={health.highest_severity} />
          </div>
        )}
      </div>
    </div>
  )
}

function SignalCard({ 
  title, 
  icon: Icon, 
  signal, 
  onClick 
}: { 
  title: string
  icon: typeof GitBranch
  signal?: { status: string; trend: string; reason: string }
  onClick: () => void
}) {
  const statusColors: Record<string, string> = {
    healthy: 'text-status-healthy',
    degraded: 'text-status-degraded',
    at_risk: 'text-status-degraded',
    critical: 'text-status-critical',
  }

  const trendIcons: Record<string, typeof TrendingUp> = {
    up: TrendingUp,
    down: TrendingDown,
    stable: Minus,
  }

  const TrendIcon = trendIcons[signal?.trend || 'stable']
  const statusColor = statusColors[signal?.status || 'healthy']

  return (
    <button
      onClick={onClick}
      className="card p-4 text-left hover:bg-surface-elevated transition-colors group"
    >
      <div className="flex items-start justify-between mb-3">
        <Icon className="w-5 h-5 text-gray-400" />
        <div className="flex items-center gap-1">
          <span className={`text-sm font-medium capitalize ${statusColor}`}>
            {signal?.status?.replace('_', ' ') || 'Unknown'}
          </span>
          <TrendIcon className={`w-4 h-4 ${statusColor}`} />
        </div>
      </div>
      
      <h3 className="font-semibold text-white mb-2 group-hover:text-accent-purple transition-colors">
        {title}
      </h3>
      
      <p className="text-sm text-gray-400 line-clamp-2">{signal?.reason || 'No data available'}</p>
      
      <div className="mt-3 flex items-center text-xs text-accent-purple opacity-0 group-hover:opacity-100 transition-opacity">
        Investigate <ArrowRight className="w-3 h-3 ml-1" />
      </div>
    </button>
  )
}

function InsightRow({ insight, onClick }: { insight: Insight; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="card p-4 w-full text-left hover:bg-surface-elevated transition-colors group"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-1">
            <SeverityBadge severity={insight.severity} />
            <span className="text-xs text-gray-500">{insight.category.replace(/_/g, ' ')}</span>
          </div>
          <h3 className="font-medium text-white group-hover:text-accent-purple transition-colors">
            {insight.title}
          </h3>
          <p className="text-sm text-gray-400 mt-1 line-clamp-1">{insight.summary}</p>
        </div>
        
        <div className="flex flex-col items-end gap-2 ml-4">
          <div className="text-right">
            <div className="text-xs text-gray-500">Confidence</div>
            <div className="text-sm font-medium text-white">{(insight.confidence * 100).toFixed(0)}%</div>
          </div>
          <span className="text-xs text-accent-purple opacity-0 group-hover:opacity-100 transition-opacity flex items-center">
            Investigate <ArrowRight className="w-3 h-3 ml-1" />
          </span>
        </div>
      </div>
    </button>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const config: Record<string, { bg: string; text: string }> = {
    CRITICAL: { bg: 'bg-severity-critical/20', text: 'text-severity-critical' },
    HIGH: { bg: 'bg-severity-high/20', text: 'text-severity-high' },
    MEDIUM: { bg: 'bg-severity-medium/20', text: 'text-severity-medium' },
    LOW: { bg: 'bg-severity-low/20', text: 'text-severity-low' },
    INFO: { bg: 'bg-severity-info/20', text: 'text-severity-info' },
  }

  const { bg, text } = config[severity] || config.INFO

  return (
    <span className={`status-badge ${bg} ${text}`}>
      {severity}
    </span>
  )
}
