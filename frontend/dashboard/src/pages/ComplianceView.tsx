import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { 
  Shield, 
  CheckCircle, 
  AlertTriangle, 
  XCircle,
  ArrowRight,
  AlertOctagon,
  FileWarning
} from 'lucide-react'
import { api, Policy } from '../api'

export function ComplianceView() {
  const navigate = useNavigate()

  const { data: policiesData } = useQuery({
    queryKey: ['policies'],
    queryFn: api.getPolicies,
  })

  const { data: violationsData } = useQuery({
    queryKey: ['policy-violations'],
    queryFn: api.getPolicyViolations,
  })

  const policies = policiesData?.policies || []
  const violations = violationsData?.violations || []

  const compliantCount = policies.filter(p => p.status === 'compliant').length
  const violatedCount = policies.filter(p => p.status === 'violated').length
  const atRiskCount = policies.filter(p => p.status === 'at_risk').length

  const overallStatus = violatedCount > 0 ? 'violated' : atRiskCount > 0 ? 'at_risk' : 'compliant'

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Compliance View</h1>
        <p className="text-gray-400 mt-1">Policy intelligence and risk assessment</p>
      </div>

      {/* Compliance Summary */}
      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-16 h-16 rounded-xl flex items-center justify-center ${
              overallStatus === 'compliant' ? 'bg-status-healthy/20' :
              overallStatus === 'at_risk' ? 'bg-status-degraded/20' : 'bg-status-critical/20'
            }`}>
              {overallStatus === 'compliant' ? (
                <CheckCircle className="w-8 h-8 text-status-healthy" />
              ) : overallStatus === 'at_risk' ? (
                <AlertTriangle className="w-8 h-8 text-status-degraded" />
              ) : (
                <XCircle className="w-8 h-8 text-status-critical" />
              )}
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white capitalize">
                {overallStatus === 'at_risk' ? 'At Risk' : overallStatus}
              </h2>
              <p className="text-gray-400">
                {violatedCount > 0 
                  ? `${violatedCount} policy violation${violatedCount > 1 ? 's' : ''} detected`
                  : atRiskCount > 0
                    ? `${atRiskCount} high-risk combination${atRiskCount > 1 ? 's' : ''} identified`
                    : 'All policies are in compliance'
                }
              </p>
            </div>
          </div>

          <div className="flex gap-6">
            <StatusCounter label="Compliant" count={compliantCount} color="text-status-healthy" />
            <StatusCounter label="At Risk" count={atRiskCount} color="text-status-degraded" />
            <StatusCounter label="Violated" count={violatedCount} color="text-status-critical" />
          </div>
        </div>
      </div>

      {/* Policy Cards */}
      <div>
        <h3 className="text-lg font-semibold text-white mb-4">Policies</h3>
        <div className="grid grid-cols-2 gap-4">
          {policies.map((policy) => (
            <PolicyCard
              key={policy.id}
              policy={policy}
              onClick={() => navigate('/causal-analysis')}
            />
          ))}
        </div>
      </div>

      {/* Active Violations */}
      {violations.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">Active Violations</h3>
          <div className="space-y-3">
            {violations.map((violation, i) => (
              <ViolationCard
                key={i}
                violation={violation}
                policy={policies.find(p => p.id === violation.policy_id)}
                onClick={() => navigate('/causal-analysis')}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function StatusCounter({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div className="text-center">
      <div className={`text-2xl font-bold ${color}`}>{count}</div>
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
    </div>
  )
}

function PolicyCard({ policy, onClick }: { policy: Policy; onClick: () => void }) {
  const statusConfig: Record<string, { icon: typeof Shield; color: string; bg: string }> = {
    compliant: { icon: CheckCircle, color: 'text-status-healthy', bg: 'bg-status-healthy/10' },
    at_risk: { icon: AlertTriangle, color: 'text-status-degraded', bg: 'bg-status-degraded/10' },
    violated: { icon: XCircle, color: 'text-status-critical', bg: 'bg-status-critical/10' },
  }

  const config = statusConfig[policy.status] || statusConfig.compliant
  const StatusIcon = config.icon

  const severityColors: Record<string, string> = {
    CRITICAL: 'bg-severity-critical/20 text-severity-critical',
    HIGH: 'bg-severity-high/20 text-severity-high',
    MEDIUM: 'bg-severity-medium/20 text-severity-medium',
    LOW: 'bg-severity-low/20 text-severity-low',
  }

  return (
    <button
      onClick={onClick}
      className={`card p-4 text-left hover:bg-surface-elevated transition-colors group ${
        policy.status !== 'compliant' ? `border-l-4 ${config.color.replace('text-', 'border-')}` : ''
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-gray-400" />
          <span className={`status-badge ${severityColors[policy.severity] || severityColors.LOW}`}>
            {policy.severity}
          </span>
        </div>
        <div className={`flex items-center gap-1 ${config.color}`}>
          <StatusIcon className="w-4 h-4" />
          <span className="text-sm font-medium capitalize">{policy.status.replace('_', ' ')}</span>
        </div>
      </div>

      <h4 className="font-semibold text-white mb-1 group-hover:text-accent-purple transition-colors">
        {policy.name}
      </h4>
      <p className="text-sm text-gray-400 mb-3">{policy.description}</p>

      {policy.violations > 0 && (
        <div className={`text-sm ${config.color}`}>
          {policy.violations} violation{policy.violations > 1 ? 's' : ''} detected
        </div>
      )}

      <div className="mt-3 flex items-center text-xs text-accent-purple opacity-0 group-hover:opacity-100 transition-opacity">
        View Details <ArrowRight className="w-3 h-3 ml-1" />
      </div>
    </button>
  )
}

function ViolationCard({ 
  violation, 
  policy,
  onClick 
}: { 
  violation: { policy_id: string; entity: string; timestamp: string; details: string }
  policy?: Policy
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="card p-4 w-full text-left hover:bg-surface-elevated transition-colors group border-l-4 border-severity-critical"
    >
      <div className="flex items-start gap-4">
        <div className="p-2 rounded-lg bg-severity-critical/20">
          <AlertOctagon className="w-5 h-5 text-severity-critical" />
        </div>
        
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <h4 className="font-semibold text-white group-hover:text-accent-purple transition-colors">
              {policy?.name || 'Unknown Policy'}
            </h4>
            <span className="text-xs text-gray-500">
              {new Date(violation.timestamp).toLocaleTimeString()}
            </span>
          </div>
          
          <p className="text-sm text-gray-400 mb-2">{violation.details}</p>
          
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <FileWarning className="w-3 h-3" />
            <span className="font-mono">{violation.entity}</span>
          </div>
        </div>

        <ArrowRight className="w-4 h-4 text-gray-500 group-hover:text-accent-purple transition-colors" />
      </div>
    </button>
  )
}
