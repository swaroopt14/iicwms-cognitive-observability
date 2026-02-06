import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { 
  Filter, 
  Search, 
  ChevronDown, 
  AlertTriangle,
  Bot,
  ArrowRight,
  Clock,
  CheckCircle,
  Eye
} from 'lucide-react'
import { api, Hypothesis } from '../api'

type FilterState = {
  severity: string[]
  agent: string[]
  status: string[]
}

export function AnomalyCenter() {
  const navigate = useNavigate()
  const [filters, setFilters] = useState<FilterState>({
    severity: [],
    agent: [],
    status: [],
  })
  const [searchQuery, setSearchQuery] = useState('')
  const [showFilters, setShowFilters] = useState(true)

  const { data: hypothesesData, isLoading } = useQuery({
    queryKey: ['hypotheses'],
    queryFn: () => api.getHypotheses(),
  })

  const hypotheses = hypothesesData?.hypotheses || []

  // Filter hypotheses
  const filteredHypotheses = hypotheses.filter((h: Hypothesis) => {
    if (searchQuery && !h.explanation.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false
    }
    if (filters.agent.length > 0 && !filters.agent.includes(h.agent)) {
      return false
    }
    return true
  })

  const agents = [...new Set(hypotheses.map((h: Hypothesis) => h.agent))]

  return (
    <div className="h-full flex flex-col">
      {/* Page Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Anomaly Center</h1>
          <p className="text-gray-400 mt-1">Central hub for all detected anomalies</p>
        </div>

        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search anomalies..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4 py-2 bg-surface-secondary border border-gray-700 rounded-lg text-gray-300 placeholder-gray-500 focus:outline-none focus:border-accent-purple w-64"
            />
          </div>

          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`btn-secondary flex items-center gap-2 ${showFilters ? 'bg-accent-purple/20 border-accent-purple' : ''}`}
          >
            <Filter className="w-4 h-4" />
            Filters
          </button>
        </div>
      </div>

      <div className="flex-1 flex gap-6">
        {/* Filters Panel */}
        {showFilters && (
          <div className="w-64 space-y-4">
            <FilterSection
              title="Agent Source"
              options={agents}
              selected={filters.agent}
              onChange={(selected) => setFilters({ ...filters, agent: selected })}
              renderOption={(agent) => (
                <div className="flex items-center gap-2">
                  <Bot className="w-3 h-3" />
                  <span className="capitalize">{agent.replace('_', ' ')}</span>
                </div>
              )}
            />

            <FilterSection
              title="Status"
              options={['Open', 'Investigating', 'Resolved']}
              selected={filters.status}
              onChange={(selected) => setFilters({ ...filters, status: selected })}
            />

            <button
              onClick={() => setFilters({ severity: [], agent: [], status: [] })}
              className="text-sm text-gray-400 hover:text-white"
            >
              Clear all filters
            </button>
          </div>
        )}

        {/* Anomaly Table */}
        <div className="flex-1 card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Type</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Source Agent</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Confidence</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Timestamp</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Status</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/50">
                {isLoading ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      Loading anomalies...
                    </td>
                  </tr>
                ) : filteredHypotheses.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center">
                      <CheckCircle className="w-12 h-12 text-status-healthy mx-auto mb-3" />
                      <p className="text-gray-300">No anomalies detected</p>
                      <p className="text-sm text-gray-500">System is operating normally</p>
                    </td>
                  </tr>
                ) : (
                  filteredHypotheses.map((hypothesis: Hypothesis) => (
                    <AnomalyRow
                      key={hypothesis.id}
                      hypothesis={hypothesis}
                      onClick={() => navigate(`/causal-analysis/${hypothesis.id}`)}
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

function FilterSection({ 
  title, 
  options, 
  selected, 
  onChange,
  renderOption
}: { 
  title: string
  options: string[]
  selected: string[]
  onChange: (selected: string[]) => void
  renderOption?: (option: string) => React.ReactNode
}) {
  const [isOpen, setIsOpen] = useState(true)

  const toggleOption = (option: string) => {
    if (selected.includes(option)) {
      onChange(selected.filter(s => s !== option))
    } else {
      onChange([...selected, option])
    }
  }

  return (
    <div className="card p-4">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full text-left"
      >
        <span className="text-sm font-semibold text-white">{title}</span>
        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      
      {isOpen && (
        <div className="mt-3 space-y-2">
          {options.map((option) => (
            <label key={option} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={selected.includes(option)}
                onChange={() => toggleOption(option)}
                className="w-4 h-4 rounded border-gray-600 bg-surface-tertiary text-accent-purple focus:ring-accent-purple"
              />
              <span className="text-sm text-gray-300">
                {renderOption ? renderOption(option) : option}
              </span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

function AnomalyRow({ hypothesis, onClick }: { hypothesis: Hypothesis; onClick: () => void }) {
  const agentColors: Record<string, string> = {
    workflow_agent: 'bg-purple-500/20 text-purple-400',
    policy_agent: 'bg-blue-500/20 text-blue-400',
    resource_agent: 'bg-green-500/20 text-green-400',
    rca_agent: 'bg-orange-500/20 text-orange-400',
  }

  const confidenceColor = hypothesis.confidence >= 0.8 
    ? 'text-status-healthy' 
    : hypothesis.confidence >= 0.5 
      ? 'text-status-degraded' 
      : 'text-gray-400'

  return (
    <tr 
      className="hover:bg-surface-elevated cursor-pointer transition-colors"
      onClick={onClick}
    >
      <td className="px-4 py-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-severity-high" />
          <span className="text-white font-medium">
            {hypothesis.opinion_type?.replace(/_/g, ' ')}
          </span>
        </div>
        <p className="text-sm text-gray-400 mt-1 line-clamp-1 max-w-xs">
          {hypothesis.explanation}
        </p>
      </td>
      <td className="px-4 py-4">
        <span className={`status-badge ${agentColors[hypothesis.agent] || 'bg-gray-500/20 text-gray-400'}`}>
          <Bot className="w-3 h-3" />
          {hypothesis.agent?.replace('_', ' ')}
        </span>
      </td>
      <td className="px-4 py-4">
        <div className="flex items-center gap-2">
          <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div 
              className={`h-full rounded-full ${
                hypothesis.confidence >= 0.8 ? 'bg-status-healthy' : 
                hypothesis.confidence >= 0.5 ? 'bg-status-degraded' : 'bg-gray-500'
              }`}
              style={{ width: `${hypothesis.confidence * 100}%` }}
            />
          </div>
          <span className={`text-sm font-medium ${confidenceColor}`}>
            {(hypothesis.confidence * 100).toFixed(0)}%
          </span>
        </div>
      </td>
      <td className="px-4 py-4">
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <Clock className="w-4 h-4" />
          {new Date(hypothesis.timestamp).toLocaleTimeString()}
        </div>
      </td>
      <td className="px-4 py-4">
        <span className="status-badge bg-severity-high/20 text-severity-high">
          Open
        </span>
      </td>
      <td className="px-4 py-4 text-right">
        <button className="p-2 text-gray-400 hover:text-accent-purple transition-colors">
          <Eye className="w-4 h-4" />
        </button>
      </td>
    </tr>
  )
}
