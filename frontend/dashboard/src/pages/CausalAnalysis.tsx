import { useState, useRef, useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  ArrowLeft,
  AlertTriangle,
  CheckCircle,
  Bot,
  GitBranch,
  FileText,
  Lightbulb,
  ChevronRight,
  User,
  Zap,
  Database,
  Shield,
  Activity
} from 'lucide-react'
import { api, GraphPath, GraphNode, Hypothesis } from '../api'

export function CausalAnalysis() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)

  const { data: graphData } = useQuery({
    queryKey: ['graph-path', id],
    queryFn: () => api.getGraphPath(id || 'default'),
  })

  const { data: hypothesesData } = useQuery({
    queryKey: ['hypotheses'],
    queryFn: () => api.getHypotheses(),
  })

  const hypotheses = hypothesesData?.hypotheses || []

  // Mock insight for demo
  const insight = {
    id: id || 'insight-001',
    title: 'Mandatory Approval Step Bypassed',
    severity: 'HIGH',
    confidence: 0.92,
    summary: 'A financial workflow completed without the required approval step, violating the Mandatory Approval Policy.',
    recommended_action: 'Review the workflow execution logs and verify the user permissions that allowed this bypass.',
    problem_statement: 'The Finance Approval step was skipped in the Expense Reimbursement workflow, resulting in unauthorized payment processing.',
  }

  return (
    <div className="h-full flex flex-col">
      {/* Page Header */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => navigate(-1)}
          className="p-2 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">Causal Analysis</h1>
          <p className="text-gray-400 mt-1">Reasoning & traceability for detected insights</p>
        </div>
      </div>

      {/* Main Content - Three Columns */}
      <div className="flex-1 flex gap-6 min-h-0">
        {/* Left - Insight Summary */}
        <div className="w-80 flex flex-col gap-4">
          <InsightSummaryPanel insight={insight} />
          <RecommendedActionPanel action={insight.recommended_action} />
        </div>

        {/* Center - Graph View */}
        <div className="flex-1 card p-4 flex flex-col">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">
            Causal Graph Path
          </h3>
          <div className="flex-1 min-h-0">
            <CausalGraph 
              graphData={graphData} 
              selectedNode={selectedNode}
              onSelectNode={setSelectedNode}
            />
          </div>
          <div className="mt-4 text-center">
            <p className="text-xs text-gray-500">
              Click nodes to inspect. Highlighted path shows probable causation chain.
            </p>
          </div>
        </div>

        {/* Right - Evidence Panel */}
        <div className="w-80">
          <EvidencePanel 
            hypotheses={hypotheses} 
            selectedNode={selectedNode}
          />
        </div>
      </div>
    </div>
  )
}

function InsightSummaryPanel({ insight }: { insight: any }) {
  const severityColors: Record<string, { bg: string; text: string; border: string }> = {
    CRITICAL: { bg: 'bg-severity-critical/20', text: 'text-severity-critical', border: 'border-severity-critical' },
    HIGH: { bg: 'bg-severity-high/20', text: 'text-severity-high', border: 'border-severity-high' },
    MEDIUM: { bg: 'bg-severity-medium/20', text: 'text-severity-medium', border: 'border-severity-medium' },
    LOW: { bg: 'bg-severity-low/20', text: 'text-severity-low', border: 'border-severity-low' },
  }

  const config = severityColors[insight.severity] || severityColors.MEDIUM

  return (
    <div className={`card p-4 border-l-4 ${config.border}`}>
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className={`w-5 h-5 ${config.text}`} />
        <span className={`status-badge ${config.bg} ${config.text}`}>
          {insight.severity}
        </span>
      </div>

      <h3 className="font-semibold text-white mb-2">{insight.title}</h3>
      
      <div className="space-y-3 text-sm">
        <div>
          <label className="text-xs text-gray-500 uppercase tracking-wide">Problem Statement</label>
          <p className="text-gray-300 mt-1">{insight.problem_statement}</p>
        </div>

        <div>
          <label className="text-xs text-gray-500 uppercase tracking-wide">Confidence</label>
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div 
                className="h-full bg-accent-purple rounded-full"
                style={{ width: `${insight.confidence * 100}%` }}
              />
            </div>
            <span className="text-white font-medium">{(insight.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      <div className="mt-4 p-3 bg-surface-tertiary rounded-lg">
        <p className="text-xs text-gray-400 italic">
          "This represents a <span className="text-gray-300">probable causal relationship</span>, not formal proof. 
          Further investigation recommended."
        </p>
      </div>
    </div>
  )
}

function RecommendedActionPanel({ action }: { action: string }) {
  return (
    <div className="card p-4 bg-accent-purple/10 border-accent-purple/30">
      <div className="flex items-center gap-2 mb-3">
        <Lightbulb className="w-5 h-5 text-accent-purple" />
        <h3 className="font-semibold text-white">Recommended Action</h3>
      </div>
      <p className="text-sm text-gray-300">{action}</p>
    </div>
  )
}

function CausalGraph({ 
  graphData, 
  selectedNode,
  onSelectNode 
}: { 
  graphData?: GraphPath
  selectedNode: GraphNode | null
  onSelectNode: (node: GraphNode | null) => void
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 600, height: 400 })

  useEffect(() => {
    if (containerRef.current) {
      const { width, height } = containerRef.current.getBoundingClientRect()
      setDimensions({ width, height })
    }
  }, [])

  const nodeTypeIcons: Record<string, string> = {
    user: '👤',
    event: '⚡',
    workflow: '🔄',
    state_change: '📊',
    resource: '💾',
    policy: '🛡️',
  }

  const nodeTypeColors: Record<string, string> = {
    user: '#3b82f6',
    event: '#8b5cf6',
    workflow: '#06b6d4',
    state_change: '#f59e0b',
    resource: '#10b981',
    policy: '#ef4444',
  }

  // Calculate positions in a force-directed-ish layout
  const nodes = graphData?.nodes || []
  const edges = graphData?.edges || []
  const highlightedPath = graphData?.highlighted_path || []

  const nodePositions = nodes.map((_, i) => {
    const cols = 3
    const row = Math.floor(i / cols)
    const col = i % cols
    const xSpacing = dimensions.width / (cols + 1)
    const ySpacing = dimensions.height / (Math.ceil(nodes.length / cols) + 1)
    return {
      x: xSpacing * (col + 1),
      y: ySpacing * (row + 1)
    }
  })

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || nodes.length === 0) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, dimensions.width, dimensions.height)

    // Draw edges
    edges.forEach((edge) => {
      const sourceIdx = nodes.findIndex(n => n.id === edge.source)
      const targetIdx = nodes.findIndex(n => n.id === edge.target)
      if (sourceIdx === -1 || targetIdx === -1) return

      const from = nodePositions[sourceIdx]
      const to = nodePositions[targetIdx]

      // Check if this edge is in the highlighted path
      const isHighlighted = highlightedPath.includes(edge.source) && highlightedPath.includes(edge.target)

      ctx.strokeStyle = isHighlighted ? '#7c3aed' : '#374151'
      ctx.lineWidth = isHighlighted ? 3 : 1.5
      ctx.setLineDash(isHighlighted ? [] : [])

      ctx.beginPath()
      ctx.moveTo(from.x, from.y)
      ctx.lineTo(to.x, to.y)
      ctx.stroke()

      // Arrow
      const angle = Math.atan2(to.y - from.y, to.x - from.x)
      const arrowDist = 35
      const arrowX = to.x - Math.cos(angle) * arrowDist
      const arrowY = to.y - Math.sin(angle) * arrowDist

      ctx.beginPath()
      ctx.moveTo(arrowX, arrowY)
      ctx.lineTo(arrowX - 8 * Math.cos(angle - Math.PI / 6), arrowY - 8 * Math.sin(angle - Math.PI / 6))
      ctx.moveTo(arrowX, arrowY)
      ctx.lineTo(arrowX - 8 * Math.cos(angle + Math.PI / 6), arrowY - 8 * Math.sin(angle + Math.PI / 6))
      ctx.stroke()

      // Edge label
      const midX = (from.x + to.x) / 2
      const midY = (from.y + to.y) / 2
      ctx.fillStyle = '#6b7280'
      ctx.font = '10px Inter, sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(edge.type, midX, midY - 5)
    })

    // Draw nodes
    nodes.forEach((node, i) => {
      const pos = nodePositions[i]
      const isSelected = selectedNode?.id === node.id
      const isInPath = highlightedPath.includes(node.id)
      const color = nodeTypeColors[node.type] || '#6b7280'

      // Glow for highlighted nodes
      if (isInPath) {
        ctx.shadowColor = color
        ctx.shadowBlur = 15
      }

      // Node circle
      ctx.beginPath()
      ctx.arc(pos.x, pos.y, 28, 0, 2 * Math.PI)
      ctx.fillStyle = isInPath ? color : '#1f2937'
      ctx.fill()
      ctx.strokeStyle = isSelected ? '#fff' : isInPath ? color : '#374151'
      ctx.lineWidth = isSelected ? 3 : 2
      ctx.shadowBlur = 0
      ctx.stroke()

      // Icon/emoji
      ctx.fillStyle = isInPath ? '#fff' : color
      ctx.font = '16px sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(nodeTypeIcons[node.type] || '●', pos.x, pos.y)

      // Label
      ctx.fillStyle = '#e5e7eb'
      ctx.font = '11px Inter, sans-serif'
      ctx.textBaseline = 'top'
      ctx.fillText(node.label.split(':')[0], pos.x, pos.y + 35)
      if (node.label.includes(':')) {
        ctx.fillStyle = '#9ca3af'
        ctx.font = '10px Inter, sans-serif'
        ctx.fillText(node.label.split(':')[1]?.trim() || '', pos.x, pos.y + 48)
      }
    })
  }, [nodes, edges, highlightedPath, selectedNode, dimensions, nodePositions])

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    for (let i = 0; i < nodes.length; i++) {
      const pos = nodePositions[i]
      const dist = Math.sqrt(Math.pow(x - pos.x, 2) + Math.pow(y - pos.y, 2))
      if (dist <= 28) {
        onSelectNode(nodes[i])
        return
      }
    }
    onSelectNode(null)
  }, [nodes, nodePositions, onSelectNode])

  return (
    <div ref={containerRef} className="h-full w-full">
      {nodes.length === 0 ? (
        <div className="h-full flex items-center justify-center text-gray-500">
          <div className="text-center">
            <GitBranch className="w-12 h-12 mx-auto mb-3 text-gray-600" />
            <p>No causal graph available</p>
            <p className="text-sm text-gray-600">Select an insight to view its reasoning path</p>
          </div>
        </div>
      ) : (
        <canvas
          ref={canvasRef}
          width={dimensions.width}
          height={dimensions.height}
          onClick={handleClick}
          className="cursor-pointer"
        />
      )}
    </div>
  )
}

function EvidencePanel({ 
  hypotheses, 
  selectedNode 
}: { 
  hypotheses: Hypothesis[]
  selectedNode: GraphNode | null
}) {
  return (
    <div className="card p-4 h-full flex flex-col">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">
        Evidence Trail
      </h3>

      {selectedNode ? (
        <div className="mb-4 p-3 bg-accent-purple/10 rounded-lg">
          <h4 className="text-sm font-medium text-white mb-1">Selected: {selectedNode.label}</h4>
          <p className="text-xs text-gray-400 capitalize">Type: {selectedNode.type.replace('_', ' ')}</p>
        </div>
      ) : null}

      <div className="flex-1 overflow-y-auto space-y-3">
        {hypotheses.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <FileText className="w-8 h-8 mx-auto mb-2 text-gray-600" />
            <p className="text-sm">No evidence available</p>
          </div>
        ) : (
          hypotheses.slice(0, 5).map((h) => (
            <EvidenceCard key={h.id} hypothesis={h} />
          ))
        )}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-700">
        <p className="text-xs text-gray-500 text-center">
          Each hypothesis is backed by immutable evidence entries in the Blackboard.
        </p>
      </div>
    </div>
  )
}

function EvidenceCard({ hypothesis }: { hypothesis: Hypothesis }) {
  const [expanded, setExpanded] = useState(false)

  const agentIcons: Record<string, typeof Bot> = {
    workflow_agent: GitBranch,
    policy_agent: Shield,
    resource_agent: Database,
    rca_agent: Activity,
  }

  const AgentIcon = agentIcons[hypothesis.agent] || Bot

  return (
    <div className="p-3 bg-surface-tertiary rounded-lg">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left"
      >
        <div className="flex items-start gap-2">
          <AgentIcon className="w-4 h-4 text-gray-400 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-gray-400 capitalize">
                {hypothesis.agent?.replace('_', ' ')}
              </span>
              <span className="text-xs text-gray-500">
                {(hypothesis.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-sm text-gray-300 line-clamp-2">
              {hypothesis.explanation}
            </p>
          </div>
          <ChevronRight className={`w-4 h-4 text-gray-500 transition-transform ${expanded ? 'rotate-90' : ''}`} />
        </div>
      </button>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-gray-700">
          <div className="text-xs space-y-2">
            <div>
              <span className="text-gray-500">Evidence ID: </span>
              <span className="text-gray-400 font-mono">{hypothesis.id.slice(0, 8)}...</span>
            </div>
            <div>
              <span className="text-gray-500">Type: </span>
              <span className="text-gray-400">{hypothesis.opinion_type?.replace(/_/g, ' ')}</span>
            </div>
            <div className="mt-2">
              <span className="text-gray-500 block mb-1">Raw Evidence:</span>
              <pre className="text-xs text-gray-400 bg-surface-primary p-2 rounded overflow-x-auto">
                {JSON.stringify(hypothesis.evidence, null, 2).slice(0, 200)}...
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
