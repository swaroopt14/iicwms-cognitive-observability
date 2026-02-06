import { AlertTriangle, AlertCircle, Info, ChevronRight, Shield, Cpu } from 'lucide-react'

interface Insight {
  id: string
  timestamp: string
  category: string
  severity: string
  title: string
  summary: string
  confidence: number
  contributing_opinions: string[]
  recommended_actions: string[]
  explanation: string
}

interface InsightCardProps {
  insight: Insight
  onViewEvidence: () => void
}

const severityConfig = {
  CRITICAL: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    icon: AlertTriangle,
    iconColor: 'text-red-600',
    badge: 'bg-red-100 text-red-800',
  },
  HIGH: {
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    icon: AlertTriangle,
    iconColor: 'text-orange-600',
    badge: 'bg-orange-100 text-orange-800',
  },
  MEDIUM: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    icon: AlertCircle,
    iconColor: 'text-yellow-600',
    badge: 'bg-yellow-100 text-yellow-800',
  },
  LOW: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    icon: Info,
    iconColor: 'text-blue-600',
    badge: 'bg-blue-100 text-blue-800',
  },
  INFO: {
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    icon: Info,
    iconColor: 'text-gray-600',
    badge: 'bg-gray-100 text-gray-800',
  },
}

const categoryIcons = {
  COMPLIANCE_VIOLATION: Shield,
  WORKFLOW_ANOMALY: AlertTriangle,
  RESOURCE_ISSUE: Cpu,
  SECURITY_CONCERN: Shield,
  OPERATIONAL_WARNING: AlertCircle,
}

export function InsightCard({ insight, onViewEvidence }: InsightCardProps) {
  const config = severityConfig[insight.severity as keyof typeof severityConfig] || severityConfig.INFO
  const SeverityIcon = config.icon
  const CategoryIcon = categoryIcons[insight.category as keyof typeof categoryIcons] || AlertCircle

  return (
    <div className={`${config.bg} ${config.border} border rounded-lg p-4`}>
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className={`p-2 rounded-lg bg-white shadow-sm`}>
          <SeverityIcon className={`w-6 h-6 ${config.iconColor}`} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`px-2 py-0.5 text-xs font-medium rounded ${config.badge}`}>
              {insight.severity}
            </span>
            <span className="text-xs text-gray-500 flex items-center gap-1">
              <CategoryIcon className="w-3 h-3" />
              {insight.category.replace(/_/g, ' ')}
            </span>
          </div>

          <h3 className="text-lg font-semibold text-gray-900 mb-1">{insight.title}</h3>
          <p className="text-gray-700 mb-3">{insight.summary}</p>

          {/* Confidence */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-sm text-gray-500">Confidence:</span>
            <div className="flex-1 max-w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-600 rounded-full"
                style={{ width: `${insight.confidence * 100}%` }}
              />
            </div>
            <span className="text-sm font-medium text-gray-700">
              {(insight.confidence * 100).toFixed(0)}%
            </span>
          </div>

          {/* Recommended Actions */}
          {insight.recommended_actions?.length > 0 && (
            <div className="mb-3">
              <h4 className="text-sm font-medium text-gray-700 mb-1">Recommended Actions:</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                {insight.recommended_actions.slice(0, 3).map((action, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-brand-600">•</span>
                    {action}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between pt-3 border-t border-gray-200/50">
            <span className="text-xs text-gray-500">
              {insight.contributing_opinions?.length || 0} contributing opinions
            </span>
            <button
              onClick={onViewEvidence}
              className="text-sm text-brand-600 hover:text-brand-700 font-medium flex items-center gap-1"
            >
              View Evidence
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
