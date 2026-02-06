import { useState } from 'react'
import { ChevronDown, ChevronRight, FileText, Bot } from 'lucide-react'

interface Hypothesis {
  id: string
  agent: string
  opinion_type: string
  confidence: number
  timestamp: string
  evidence: Record<string, unknown>
  explanation: string
}

interface EvidencePanelProps {
  hypotheses: Hypothesis[]
  selectedInsightId: string | null
}

const agentColors: Record<string, string> = {
  workflow_agent: 'bg-purple-100 text-purple-800',
  policy_agent: 'bg-blue-100 text-blue-800',
  resource_agent: 'bg-green-100 text-green-800',
  rca_agent: 'bg-orange-100 text-orange-800',
  master_agent: 'bg-gray-100 text-gray-800',
}

export function EvidencePanel({ hypotheses, selectedInsightId }: EvidencePanelProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  // Group hypotheses by agent
  const groupedByAgent = hypotheses.reduce((acc, h) => {
    const agent = h.agent || 'unknown'
    if (!acc[agent]) acc[agent] = []
    acc[agent].push(h)
    return acc
  }, {} as Record<string, Hypothesis[]>)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Evidence Trail</h2>
        <p className="text-sm text-gray-500">
          All agent opinions are logged here with full provenance. Every insight traces back to specific evidence.
        </p>
      </div>

      {Object.entries(groupedByAgent).map(([agent, agentHypotheses]) => (
        <div key={agent} className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center gap-2">
            <Bot className="w-4 h-4 text-gray-500" />
            <span className={`px-2 py-0.5 text-xs font-medium rounded ${agentColors[agent] || 'bg-gray-100 text-gray-800'}`}>
              {agent.replace(/_/g, ' ').toUpperCase()}
            </span>
            <span className="text-sm text-gray-500">
              {agentHypotheses.length} opinion{agentHypotheses.length !== 1 ? 's' : ''}
            </span>
          </div>

          <div className="divide-y divide-gray-100">
            {agentHypotheses.map((hypothesis) => (
              <EvidenceItem
                key={hypothesis.id}
                hypothesis={hypothesis}
                expanded={expandedId === hypothesis.id}
                onToggle={() => setExpandedId(expandedId === hypothesis.id ? null : hypothesis.id)}
              />
            ))}
          </div>
        </div>
      ))}

      {hypotheses.length === 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
          <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No evidence recorded yet</p>
          <p className="text-sm text-gray-400 mt-1">Run analysis to generate agent opinions</p>
        </div>
      )}
    </div>
  )
}

function EvidenceItem({
  hypothesis,
  expanded,
  onToggle,
}: {
  hypothesis: Hypothesis
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <div className="px-4 py-3">
      <button
        onClick={onToggle}
        className="w-full flex items-start gap-3 text-left"
      >
        <span className="mt-1">
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )}
        </span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-gray-900">
              {hypothesis.opinion_type?.replace(/_/g, ' ')}
            </span>
            <span className="text-xs text-gray-500">
              {(hypothesis.confidence * 100).toFixed(0)}% confidence
            </span>
          </div>
          <p className="text-sm text-gray-600 line-clamp-2">{hypothesis.explanation}</p>
        </div>
      </button>

      {expanded && (
        <div className="mt-3 ml-7 pl-3 border-l-2 border-gray-200">
          <div className="text-xs text-gray-500 mb-2">
            ID: {hypothesis.id}
          </div>
          <div className="text-xs text-gray-500 mb-3">
            Timestamp: {new Date(hypothesis.timestamp).toLocaleString()}
          </div>
          
          <div className="bg-gray-50 rounded p-3">
            <h4 className="text-xs font-medium text-gray-700 mb-2">Evidence Data:</h4>
            <pre className="text-xs text-gray-600 overflow-x-auto whitespace-pre-wrap">
              {JSON.stringify(hypothesis.evidence, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
