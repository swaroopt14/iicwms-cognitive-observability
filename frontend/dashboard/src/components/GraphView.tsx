import { useRef, useEffect, useState } from 'react'

// Note: react-force-graph-2d is used for graph visualization
// This is a simplified implementation for the demo

interface GraphNode {
  id: string
  name: string
  type: 'workflow' | 'step' | 'resource' | 'event' | 'policy'
  status?: string
}

interface GraphLink {
  source: string
  target: string
  type: string
}

const sampleGraphData = {
  nodes: [
    { id: 'w1', name: 'Expense Workflow', type: 'workflow' as const },
    { id: 's1', name: 'Request', type: 'step' as const, status: 'complete' },
    { id: 's2', name: 'Validation', type: 'step' as const, status: 'complete' },
    { id: 's3', name: 'Approval', type: 'step' as const, status: 'skipped' },
    { id: 's4', name: 'Execution', type: 'step' as const, status: 'complete' },
    { id: 'p1', name: 'Approval Required', type: 'policy' as const },
    { id: 'r1', name: 'Finance DB', type: 'resource' as const },
  ],
  links: [
    { source: 'w1', target: 's1', type: 'HAS_STEP' },
    { source: 'w1', target: 's2', type: 'HAS_STEP' },
    { source: 'w1', target: 's3', type: 'HAS_STEP' },
    { source: 'w1', target: 's4', type: 'HAS_STEP' },
    { source: 's1', target: 's2', type: 'NEXT' },
    { source: 's2', target: 's3', type: 'NEXT' },
    { source: 's3', target: 's4', type: 'NEXT' },
    { source: 'p1', target: 's3', type: 'APPLIES_TO' },
    { source: 's4', target: 'r1', type: 'USES' },
  ],
}

const nodeColors: Record<string, string> = {
  workflow: '#3B82F6', // blue
  step: '#10B981', // green
  resource: '#F59E0B', // amber
  event: '#8B5CF6', // purple
  policy: '#EF4444', // red
}

const statusColors: Record<string, string> = {
  complete: '#10B981',
  pending: '#6B7280',
  skipped: '#EF4444',
  failed: '#EF4444',
}

export function GraphView() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [nodePositions, setNodePositions] = useState<Map<string, { x: number; y: number }>>(new Map())

  // Initialize node positions
  useEffect(() => {
    const positions = new Map<string, { x: number; y: number }>()
    const centerX = 400
    const centerY = 250
    const radius = 180

    sampleGraphData.nodes.forEach((node, i) => {
      const angle = (i / sampleGraphData.nodes.length) * 2 * Math.PI
      positions.set(node.id, {
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
      })
    })

    setNodePositions(positions)
  }, [])

  // Draw graph
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Draw links
    ctx.strokeStyle = '#D1D5DB'
    ctx.lineWidth = 2
    sampleGraphData.links.forEach((link) => {
      const sourcePos = nodePositions.get(link.source)
      const targetPos = nodePositions.get(link.target)
      if (sourcePos && targetPos) {
        ctx.beginPath()
        ctx.moveTo(sourcePos.x, sourcePos.y)
        ctx.lineTo(targetPos.x, targetPos.y)
        ctx.stroke()

        // Draw arrow
        const angle = Math.atan2(targetPos.y - sourcePos.y, targetPos.x - sourcePos.x)
        const arrowLength = 10
        const arrowX = targetPos.x - Math.cos(angle) * 25
        const arrowY = targetPos.y - Math.sin(angle) * 25

        ctx.beginPath()
        ctx.moveTo(arrowX, arrowY)
        ctx.lineTo(
          arrowX - arrowLength * Math.cos(angle - Math.PI / 6),
          arrowY - arrowLength * Math.sin(angle - Math.PI / 6)
        )
        ctx.moveTo(arrowX, arrowY)
        ctx.lineTo(
          arrowX - arrowLength * Math.cos(angle + Math.PI / 6),
          arrowY - arrowLength * Math.sin(angle + Math.PI / 6)
        )
        ctx.stroke()
      }
    })

    // Draw nodes
    sampleGraphData.nodes.forEach((node) => {
      const pos = nodePositions.get(node.id)
      if (!pos) return

      // Node circle
      ctx.beginPath()
      ctx.arc(pos.x, pos.y, 20, 0, 2 * Math.PI)
      ctx.fillStyle = node.status ? statusColors[node.status] || nodeColors[node.type] : nodeColors[node.type]
      ctx.fill()
      ctx.strokeStyle = selectedNode?.id === node.id ? '#1F2937' : '#fff'
      ctx.lineWidth = selectedNode?.id === node.id ? 3 : 2
      ctx.stroke()

      // Node label
      ctx.fillStyle = '#374151'
      ctx.font = '12px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(node.name, pos.x, pos.y + 35)
    })
  }, [nodePositions, selectedNode])

  // Handle click
  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    // Find clicked node
    for (const node of sampleGraphData.nodes) {
      const pos = nodePositions.get(node.id)
      if (pos) {
        const dist = Math.sqrt(Math.pow(x - pos.x, 2) + Math.pow(y - pos.y, 2))
        if (dist <= 20) {
          setSelectedNode(node)
          return
        }
      }
    }
    setSelectedNode(null)
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Graph View</h2>
        <p className="text-sm text-gray-500">
          Visual representation of workflow structure and relationships. Click nodes to see details.
        </p>
      </div>

      <div className="flex gap-4">
        {/* Graph Canvas */}
        <div className="flex-1 bg-white rounded-lg border border-gray-200 p-4">
          <canvas
            ref={canvasRef}
            width={800}
            height={500}
            onClick={handleClick}
            className="w-full cursor-pointer"
          />

          {/* Legend */}
          <div className="flex gap-6 mt-4 justify-center text-sm">
            {Object.entries(nodeColors).map(([type, color]) => (
              <div key={type} className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: color }} />
                <span className="text-gray-600 capitalize">{type}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Node Details */}
        {selectedNode && (
          <div className="w-64 bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="font-semibold text-gray-900 mb-2">{selectedNode.name}</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Type:</span>
                <span className="text-gray-900 capitalize">{selectedNode.type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">ID:</span>
                <span className="text-gray-900 font-mono text-xs">{selectedNode.id}</span>
              </div>
              {selectedNode.status && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Status:</span>
                  <span
                    className={`capitalize font-medium ${
                      selectedNode.status === 'complete'
                        ? 'text-green-600'
                        : selectedNode.status === 'skipped'
                        ? 'text-red-600'
                        : 'text-gray-600'
                    }`}
                  >
                    {selectedNode.status}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
