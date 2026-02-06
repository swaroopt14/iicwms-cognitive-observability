import { useState, useRef, useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { 
  ChevronDown, 
  Clock, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  SkipForward,
  ArrowRight
} from 'lucide-react'
import { api, Workflow, WorkflowStep } from '../api'

export function WorkflowMap() {
  const navigate = useNavigate()
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null)
  const [selectedStep, setSelectedStep] = useState<WorkflowStep | null>(null)
  const [showDropdown, setShowDropdown] = useState(false)

  const { data: workflowsData } = useQuery({
    queryKey: ['workflows'],
    queryFn: api.getWorkflows,
  })

  const workflows = workflowsData?.workflows || []
  const currentWorkflow = workflows.find(w => w.id === selectedWorkflow) || workflows[0]

  useEffect(() => {
    if (workflows.length > 0 && !selectedWorkflow) {
      setSelectedWorkflow(workflows[0].id)
    }
  }, [workflows, selectedWorkflow])

  return (
    <div className="h-full flex flex-col">
      {/* Page Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Workflow Map</h1>
          <p className="text-gray-400 mt-1">Visualize execution paths and deviations</p>
        </div>

        {/* Workflow Selector */}
        <div className="relative">
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-2 px-4 py-2 bg-surface-secondary rounded-lg text-gray-300 hover:text-white transition-colors border border-gray-700"
          >
            <span>{currentWorkflow?.name || 'Select Workflow'}</span>
            <ChevronDown className="w-4 h-4" />
          </button>
          
          {showDropdown && (
            <div className="absolute top-full right-0 mt-1 w-64 bg-surface-elevated rounded-lg border border-gray-600 shadow-xl z-50">
              {workflows.map((wf) => (
                <button
                  key={wf.id}
                  onClick={() => { setSelectedWorkflow(wf.id); setShowDropdown(false); setSelectedStep(null) }}
                  className={`w-full text-left px-4 py-3 hover:bg-gray-600 first:rounded-t-lg last:rounded-b-lg flex items-center justify-between ${
                    wf.id === selectedWorkflow ? 'text-accent-purple' : 'text-gray-300'
                  }`}
                >
                  <span>{wf.name}</span>
                  {wf.status === 'anomaly' && (
                    <AlertTriangle className="w-4 h-4 text-severity-high" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-6">
        {/* Graph Canvas */}
        <div className="flex-1 card p-6">
          {currentWorkflow ? (
            <WorkflowGraph 
              workflow={currentWorkflow} 
              selectedStep={selectedStep}
              onSelectStep={setSelectedStep}
              onNavigateToAnalysis={(stepId) => navigate(`/causal-analysis?step=${stepId}`)}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500">
              Select a workflow to visualize
            </div>
          )}
        </div>

        {/* Step Inspector */}
        <div className="w-80">
          <StepInspector 
            step={selectedStep} 
            onInvestigate={() => selectedStep?.deviation && navigate('/causal-analysis')}
          />
        </div>
      </div>
    </div>
  )
}

function WorkflowGraph({ 
  workflow, 
  selectedStep, 
  onSelectStep,
  onNavigateToAnalysis 
}: { 
  workflow: Workflow
  selectedStep: WorkflowStep | null
  onSelectStep: (step: WorkflowStep) => void
  onNavigateToAnalysis: (stepId: string) => void
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 400 })

  useEffect(() => {
    if (containerRef.current) {
      const { width, height } = containerRef.current.getBoundingClientRect()
      setDimensions({ width: width - 48, height: height - 48 })
    }
  }, [])

  const stepPositions = workflow.steps.map((_, i) => ({
    x: 100 + (i * (dimensions.width - 200)) / Math.max(workflow.steps.length - 1, 1),
    y: dimensions.height / 2
  }))

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Clear
    ctx.clearRect(0, 0, dimensions.width, dimensions.height)

    // Draw edges
    ctx.strokeStyle = '#374151'
    ctx.lineWidth = 2
    for (let i = 0; i < workflow.steps.length - 1; i++) {
      const from = stepPositions[i]
      const to = stepPositions[i + 1]
      
      // Check if this edge involves a deviation
      if (workflow.steps[i + 1].deviation) {
        ctx.strokeStyle = '#ef4444'
        ctx.setLineDash([5, 5])
      } else {
        ctx.strokeStyle = '#374151'
        ctx.setLineDash([])
      }
      
      ctx.beginPath()
      ctx.moveTo(from.x + 30, from.y)
      ctx.lineTo(to.x - 30, to.y)
      ctx.stroke()

      // Arrow
      const angle = Math.atan2(to.y - from.y, to.x - from.x)
      const arrowX = to.x - 35
      const arrowY = to.y
      ctx.beginPath()
      ctx.moveTo(arrowX, arrowY)
      ctx.lineTo(arrowX - 8 * Math.cos(angle - Math.PI / 6), arrowY - 8 * Math.sin(angle - Math.PI / 6))
      ctx.moveTo(arrowX, arrowY)
      ctx.lineTo(arrowX - 8 * Math.cos(angle + Math.PI / 6), arrowY - 8 * Math.sin(angle + Math.PI / 6))
      ctx.stroke()
    }
    ctx.setLineDash([])

    // Draw nodes
    workflow.steps.forEach((step, i) => {
      const pos = stepPositions[i]
      const isSelected = selectedStep?.id === step.id

      // Node circle
      ctx.beginPath()
      ctx.arc(pos.x, pos.y, 25, 0, 2 * Math.PI)
      
      // Fill based on status
      const statusColors: Record<string, string> = {
        complete: '#10b981',
        pending: '#6b7280',
        skipped: '#ef4444',
        failed: '#ef4444',
      }
      ctx.fillStyle = statusColors[step.status] || '#6b7280'
      ctx.fill()

      // Border
      ctx.strokeStyle = isSelected ? '#7c3aed' : '#1f2937'
      ctx.lineWidth = isSelected ? 3 : 2
      ctx.stroke()

      // Label
      ctx.fillStyle = '#e5e7eb'
      ctx.font = '12px Inter, sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(step.name, pos.x, pos.y + 45)

      // Status icon indicator
      if (step.deviation) {
        ctx.fillStyle = '#fbbf24'
        ctx.beginPath()
        ctx.arc(pos.x + 20, pos.y - 20, 8, 0, 2 * Math.PI)
        ctx.fill()
        ctx.fillStyle = '#1f2937'
        ctx.font = 'bold 10px sans-serif'
        ctx.fillText('!', pos.x + 20, pos.y - 17)
      }
    })
  }, [workflow, selectedStep, dimensions, stepPositions])

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    // Find clicked step
    for (let i = 0; i < workflow.steps.length; i++) {
      const pos = stepPositions[i]
      const dist = Math.sqrt(Math.pow(x - pos.x, 2) + Math.pow(y - pos.y, 2))
      if (dist <= 25) {
        onSelectStep(workflow.steps[i])
        return
      }
    }
  }, [workflow, stepPositions, onSelectStep])

  return (
    <div ref={containerRef} className="h-full">
      <canvas
        ref={canvasRef}
        width={dimensions.width}
        height={dimensions.height}
        onClick={handleClick}
        className="cursor-pointer"
      />
      
      {/* Legend */}
      <div className="flex items-center gap-6 mt-4 justify-center text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-status-healthy" />
          <span className="text-gray-400">Complete</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-gray-500" />
          <span className="text-gray-400">Pending</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-severity-critical" />
          <span className="text-gray-400">Skipped/Failed</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-yellow-400 flex items-center justify-center text-[8px] font-bold text-gray-900">!</div>
          <span className="text-gray-400">Deviation</span>
        </div>
      </div>
    </div>
  )
}

function StepInspector({ 
  step, 
  onInvestigate 
}: { 
  step: WorkflowStep | null
  onInvestigate: () => void
}) {
  if (!step) {
    return (
      <div className="card p-6 h-full flex flex-col items-center justify-center text-center">
        <div className="w-16 h-16 rounded-full bg-surface-elevated flex items-center justify-center mb-4">
          <Clock className="w-8 h-8 text-gray-500" />
        </div>
        <p className="text-gray-400">Click a step to inspect</p>
        <p className="text-sm text-gray-500 mt-1">View details and deviations</p>
      </div>
    )
  }

  const statusConfig: Record<string, { icon: typeof CheckCircle; color: string; label: string }> = {
    complete: { icon: CheckCircle, color: 'text-status-healthy', label: 'Completed' },
    pending: { icon: Clock, color: 'text-gray-400', label: 'Pending' },
    skipped: { icon: SkipForward, color: 'text-severity-critical', label: 'Skipped' },
    failed: { icon: XCircle, color: 'text-severity-critical', label: 'Failed' },
  }

  const config = statusConfig[step.status] || statusConfig.pending
  const StatusIcon = config.icon

  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Step Inspector</h3>
      
      <div className="space-y-4">
        <div>
          <label className="text-xs text-gray-500 uppercase tracking-wide">Step Name</label>
          <p className="text-white font-medium mt-1">{step.name}</p>
        </div>

        <div>
          <label className="text-xs text-gray-500 uppercase tracking-wide">Status</label>
          <div className={`flex items-center gap-2 mt-1 ${config.color}`}>
            <StatusIcon className="w-4 h-4" />
            <span className="font-medium">{config.label}</span>
          </div>
        </div>

        <div>
          <label className="text-xs text-gray-500 uppercase tracking-wide">Sequence</label>
          <p className="text-white mt-1">Step {step.sequence} of workflow</p>
        </div>

        {step.duration_ms && (
          <div>
            <label className="text-xs text-gray-500 uppercase tracking-wide">Duration</label>
            <p className="text-white mt-1">{step.duration_ms}ms</p>
          </div>
        )}

        {step.deviation && (
          <div className="p-3 bg-severity-high/10 border border-severity-high/30 rounded-lg">
            <div className="flex items-center gap-2 text-severity-high mb-2">
              <AlertTriangle className="w-4 h-4" />
              <span className="font-medium">Deviation Detected</span>
            </div>
            <p className="text-sm text-gray-300">
              This step shows abnormal behavior that may indicate a workflow integrity issue.
            </p>
          </div>
        )}

        {step.deviation && (
          <button
            onClick={onInvestigate}
            className="w-full btn-primary flex items-center justify-center gap-2"
          >
            Investigate Cause <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  )
}
