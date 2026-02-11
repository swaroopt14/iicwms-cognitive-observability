I'll explain the Event Graph Timeline page structure and code in detail.
Event Graph Timeline - Code Structure & Explanation
File Organization
app/timeline/
├── page.tsx                          # Main page component
├── components/
│   ├── event-graph-header.tsx        # Header with title & intent selector
│   ├── event-graph-toolbar.tsx       # Time range, zoom, filters, export
│   ├── timeline-canvas.tsx           # Main chart visualization
│   ├── event-node.tsx                # Individual event node component
│   ├── event-details-panel.tsx       # Right sidebar details
│   ├── event-graph-legend.tsx        # Status legend at bottom
│   └── event-graph-empty-state.tsx   # Empty state when no intent selected
└── lib/
    ├── event-graph-types.ts          # TypeScript type definitions
    └── event-graph-data.ts           # Mock data & data fetching
app/timeline/├── page.tsx                          # Main page component├── components/│   ├── event-graph-header.tsx        # Header with title & intent selector│   ├── event-graph-toolbar.tsx       # Time range, zoom, filters, export│   ├── timeline-canvas.tsx           # Main chart visualization│   ├── event-node.tsx                # Individual event node component│   ├── event-details-panel.tsx       # Right sidebar details│   ├── event-graph-legend.tsx        # Status legend at bottom│   └── event-graph-empty-state.tsx   # Empty state when no intent selected└── lib/    ├── event-graph-types.ts          # TypeScript type definitions    └── event-graph-data.ts           # Mock data & data fetching
1. Types Definition (lib/event-graph-types.ts)
event-graph-types.ts
Lines 1-63
// Event Graph Timeline - Types

export type EventNodeStatus =
  | 'success'
  | 'failed'
  | 'pending'
  | 'warning'
  | 'retry'
  | 'skipped'
  | 'missing'

export type EventLaneId = 'user-intent' | 'psp' | 'bank' | 'system'

export type DependencyType = 'direct' | 'async' | 'retry' | 'fork'

export interface EventNode {
  id: string
  laneId: EventLaneId
  name: string
  status: EventNodeStatus
  timestamp: string // ISO or "HH:MM:SS.mmm"
  timestampMs: number
  durationMs?: number
  confidence?: number
  details: Record<string, string | number | boolean>
  error?: {
    code: string
    message: string
    recovery?: string
  }
  attempt?: number // e.g. 2 of 3 for retries
  dependsOn?: string[] // IDs of predecessor nodes
  slaDeadlineMs?: number
  isMissing?: boolean // Expected but never arrived
}

export interface EventLane {
  id: EventLaneId
  label: string
  order: number
  visible: boolean
}

export interface EventGraphData {
  intentId: string
  intentLabel?: string
  startTime: number
  endTime: number
  totalDurationMs: number
  lanes: EventLane[]
  nodes: EventNode[]
  overallConfidence?: number
  outcomeSummary?: string
}

export type TimeRangePreset = '1h' | '6h' | '24h' | '7d' | 'custom'

export interface TimeRangeState {
  preset: TimeRangePreset
  from?: Date
  to?: Date
}
// Event Graph Timeline - Typesexport type EventNodeStatus =  | 'success'  | 'failed'  | 'pending'  | 'warning'  | 'retry'  | 'skipped'  | 'missing'export type EventLaneId = 'user-intent' | 'psp' | 'bank' | 'system'export type DependencyType = 'direct' | 'async' | 'retry' | 'fork'export interface EventNode {  id: string  laneId: EventLaneId  name: string  status: EventNodeStatus  timestamp: string // ISO or "HH:MM:SS.mmm"  timestampMs: number  durationMs?: number  confidence?: number  details: Record<string, string | number | boolean>  error?: {    code: string    message: string    recovery?: string  }  attempt?: number // e.g. 2 of 3 for retries  dependsOn?: string[] // IDs of predecessor nodes  slaDeadlineMs?: number  isMissing?: boolean // Expected but never arrived}export interface EventLane {  id: EventLaneId  label: string  order: number  visible: boolean}export interface EventGraphData {  intentId: string  intentLabel?: string  startTime: number  endTime: number  totalDurationMs: number  lanes: EventLane[]  nodes: EventNode[]  overallConfidence?: number  outcomeSummary?: string}export type TimeRangePreset = '1h' | '6h' | '24h' | '7d' | 'custom'export interface TimeRangeState {  preset: TimeRangePreset  from?: Date  to?: Date}
Key Types:
EventNodeStatus - 7 possible statuses for events
EventLaneId - 4 swimlanes (user-intent, psp, bank, system)
EventNode - Complete event data structure with error handling, retry attempts, dependencies
EventGraphData - Full graph data including all nodes, lanes, and metadata
2. Main Page Component (page.tsx)
page.tsx
Lines 1-56
'use client'

import React, { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { useSidebar } from '@/app/context/sidebar-context'
import { EventGraphHeader } from './components/event-graph-header'
import { EventGraphToolbar } from './components/event-graph-toolbar'
import { TimelineCanvas } from './components/timeline-canvas'
import { EventDetailsPanel } from './components/event-details-panel'
import { EventGraphLegend } from './components/event-graph-legend'
import { EventGraphEmptyState } from './components/event-graph-empty-state'
import { getEventGraphData } from './lib/event-graph-data'
import type { EventGraphData, TimeRangePreset } from './lib/event-graph-types'
import type { EventLaneId } from './lib/event-graph-types'
import type { EventNode } from './lib/event-graph-types'
import { cn } from '@/lib/utils'

const ALL_LANES: Set<EventLaneId> = new Set(['user-intent', 'psp', 'bank', 'system'])

function EventGraphContent() {
  const { isOpen } = useSidebar()
  const searchParams = useSearchParams()
  const intentFromUrl = searchParams.get('intent')

  // STATE MANAGEMENT
  const [selectedIntentId, setSelectedIntentId] = useState<string | null>(null)
  const [graphData, setGraphData] = useState<EventGraphData | null>(null)
  const [timeRange, setTimeRange] = useState<TimeRangePreset>('24h')
  const [zoom, setZoom] = useState(100)
  const [visibleLanes, setVisibleLanes] = useState<Set<EventLaneId>>(ALL_LANES)
  const [selectedNode, setSelectedNode] = useState<EventNode | null>(null)

  // Sync URL intent to selection (deep linking support)
  useEffect(() => {
    if (intentFromUrl) {
      const data = getEventGraphData(intentFromUrl)
      if (data) {
        setSelectedIntentId(intentFromUrl)
        setGraphData(data)
      }
    }
  }, [intentFromUrl])

  // Load graph data when intent selected
  useEffect(() => {
    if (selectedIntentId) {
      const data = getEventGraphData(selectedIntentId)
      setGraphData(data)
      setSelectedNode(null)
    } else {
      setGraphData(null)
      setSelectedNode(null)
    }
  }, [selectedIntentId])
  // ...
}
'use client'import React, { useState, useEffect, Suspense } from 'react'import { useSearchParams } from 'next/navigation'import { useSidebar } from '@/app/context/sidebar-context'import { EventGraphHeader } from './components/event-graph-header'import { EventGraphToolbar } from './components/event-graph-toolbar'import { TimelineCanvas } from './components/timeline-canvas'import { EventDetailsPanel } from './components/event-details-panel'import { EventGraphLegend } from './components/event-graph-legend'import { EventGraphEmptyState } from './components/event-graph-empty-state'import { getEventGraphData } from './lib/event-graph-data'import type { EventGraphData, TimeRangePreset } from './lib/event-graph-types'import type { EventLaneId } from './lib/event-graph-types'import type { EventNode } from './lib/event-graph-types'import { cn } from '@/lib/utils'const ALL_LANES: Set<EventLaneId> = new Set(['user-intent', 'psp', 'bank', 'system'])function EventGraphContent() {  const { isOpen } = useSidebar()  const searchParams = useSearchParams()  const intentFromUrl = searchParams.get('intent')  // STATE MANAGEMENT  const [selectedIntentId, setSelectedIntentId] = useState<string | null>(null)  const [graphData, setGraphData] = useState<EventGraphData | null>(null)  const [timeRange, setTimeRange] = useState<TimeRangePreset>('24h')  const [zoom, setZoom] = useState(100)  const [visibleLanes, setVisibleLanes] = useState<Set<EventLaneId>>(ALL_LANES)  const [selectedNode, setSelectedNode] = useState<EventNode | null>(null)  // Sync URL intent to selection (deep linking support)  useEffect(() => {    if (intentFromUrl) {      const data = getEventGraphData(intentFromUrl)      if (data) {        setSelectedIntentId(intentFromUrl)        setGraphData(data)      }    }  }, [intentFromUrl])  // Load graph data when intent selected  useEffect(() => {    if (selectedIntentId) {      const data = getEventGraphData(selectedIntentId)      setGraphData(data)      setSelectedNode(null)    } else {      setGraphData(null)      setSelectedNode(null)    }  }, [selectedIntentId])  // ...}
State Variables:
State	Type	Purpose
selectedIntentId	string \| null	Currently selected intent ID
graphData	EventGraphData \| null	Full graph data for visualization
timeRange	TimeRangePreset	Selected time filter (1h, 6h, 24h, 7d)
zoom	number	Zoom level (25-200%)
visibleLanes	Set<EventLaneId>	Which lanes are visible
selectedNode	EventNode \| null	Currently selected node for details panel
Key Functions:
page.tsx
Lines 55-76
  const toggleLane = (laneId: EventLaneId) => {
    setVisibleLanes((prev) => {
      const next = new Set(prev)
      if (next.has(laneId)) {
        next.delete(laneId)
      } else {
        next.add(laneId)
      }
      return next
    })
  }

  const handleDownloadSvg = () => {
    // Placeholder - would export canvas as SVG
    console.log('Download SVG')
  }
  const handleDownloadCsv = () => {
    console.log('Download CSV')
  }
  const handlePrint = () => {
    window.print()
  }
  const toggleLane = (laneId: EventLaneId) => {    setVisibleLanes((prev) => {      const next = new Set(prev)      if (next.has(laneId)) {        next.delete(laneId)      } else {        next.add(laneId)      }      return next    })  }  const handleDownloadSvg = () => {    // Placeholder - would export canvas as SVG    console.log('Download SVG')  }  const handleDownloadCsv = () => {    console.log('Download CSV')  }  const handlePrint = () => {    window.print()  }
Page Layout (JSX):
page.tsx
Lines 78-146
  return (
    <div className="flex h-screen flex-col bg-[#0d0d0d]">
      {/* HEADER - Always visible */}
      <EventGraphHeader
        selectedIntentId={selectedIntentId}
        onSelectIntent={setSelectedIntentId}
      />

      {/* TOOLBAR - Only when intent selected */}
      {selectedIntentId && graphData && (
        <EventGraphToolbar
          timeRange={timeRange}
          onTimeRangeChange={setTimeRange}
          zoom={zoom}
          onZoomChange={setZoom}
          visibleLanes={visibleLanes}
          onToggleLane={toggleLane}
          onDownloadSvg={handleDownloadSvg}
          onDownloadCsv={handleDownloadCsv}
          onPrint={handlePrint}
        />
      )}

      {/* MAIN CONTENT AREA */}
      <div
        className={cn(
          'flex flex-1 overflow-hidden transition-[margin]',
          isOpen ? 'md:ml-64' : 'md:ml-20'  // Sidebar-aware margins
        )}
      >
        {/* Left: Main chart or empty state */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {!graphData ? (
            <EventGraphEmptyState onSelectIntent={setSelectedIntentId} />
          ) : (
            <>
              <div className="flex-1 overflow-auto">
                <TimelineCanvas
                  data={graphData}
                  zoom={zoom}
                  selectedNodeId={selectedNode?.id ?? null}
                  onSelectNode={setSelectedNode}
                  visibleLanes={visibleLanes}
                />
              </div>
              <div className="border-t border-zinc-800/60 bg-zinc-950/30 px-6 py-4">
                <EventGraphLegend />
              </div>
            </>
          )}
        </div>

        {/* Right: Details panel (desktop only) */}
        {graphData && (
          <aside className="hidden w-[400px] shrink-0 border-l border-zinc-800/80 bg-zinc-950/80 backdrop-blur-sm lg:block">
            <div className="sticky top-0 z-10 border-b border-zinc-800/60 bg-zinc-950/90 px-5 py-4">
              <h3 className="text-sm font-semibold text-white">Event Details</h3>
              <p className="mt-0.5 text-xs text-zinc-500">
                Click a node on the timeline to view full details
              </p>
            </div>
            <div className="h-[calc(100%-80px)]">
              <EventDetailsPanel
                node={selectedNode}
                intentId={selectedIntentId}
              />
            </div>
          </aside>
        )}
      </div>
    </div>
  )
  return (    <div className="flex h-screen flex-col bg-[#0d0d0d]">      {/* HEADER - Always visible */}      <EventGraphHeader        selectedIntentId={selectedIntentId}        onSelectIntent={setSelectedIntentId}      />      {/* TOOLBAR - Only when intent selected */}      {selectedIntentId && graphData && (        <EventGraphToolbar          timeRange={timeRange}          onTimeRangeChange={setTimeRange}          zoom={zoom}          onZoomChange={setZoom}          visibleLanes={visibleLanes}          onToggleLane={toggleLane}          onDownloadSvg={handleDownloadSvg}          onDownloadCsv={handleDownloadCsv}          onPrint={handlePrint}        />      )}      {/* MAIN CONTENT AREA */}      <div        className={cn(          'flex flex-1 overflow-hidden transition-[margin]',          isOpen ? 'md:ml-64' : 'md:ml-20'  // Sidebar-aware margins        )}      >        {/* Left: Main chart or empty state */}        <div className="flex flex-1 flex-col overflow-hidden">          {!graphData ? (            <EventGraphEmptyState onSelectIntent={setSelectedIntentId} />          ) : (            <>              <div className="flex-1 overflow-auto">                <TimelineCanvas                  data={graphData}                  zoom={zoom}                  selectedNodeId={selectedNode?.id ?? null}                  onSelectNode={setSelectedNode}                  visibleLanes={visibleLanes}                />              </div>              <div className="border-t border-zinc-800/60 bg-zinc-950/30 px-6 py-4">                <EventGraphLegend />              </div>            </>          )}        </div>        {/* Right: Details panel (desktop only) */}        {graphData && (          <aside className="hidden w-[400px] shrink-0 border-l border-zinc-800/80 bg-zinc-950/80 backdrop-blur-sm lg:block">            <div className="sticky top-0 z-10 border-b border-zinc-800/60 bg-zinc-950/90 px-5 py-4">              <h3 className="text-sm font-semibold text-white">Event Details</h3>              <p className="mt-0.5 text-xs text-zinc-500">                Click a node on the timeline to view full details              </p>            </div>            <div className="h-[calc(100%-80px)]">              <EventDetailsPanel                node={selectedNode}                intentId={selectedIntentId}              />            </div>          </aside>        )}      </div>    </div>  )
3. Timeline Canvas (components/timeline-canvas.tsx)
This is the core visualization component - a stock-market style chart.
Confidence Calculation:
timeline-canvas.tsx
Lines 16-36
/** Derive confidence for Y-axis: success=100, failed=0, pending=50, etc. */
function getConfidence(node: EventNodeType): number {
  if (node.confidence != null) return node.confidence
  switch (node.status) {
    case 'success':
      return 100
    case 'failed':
    case 'missing':
      return 0
    case 'pending':
      return 50
    case 'warning':
      return 75
    case 'retry':
      return 60
    case 'skipped':
      return 0
    default:
      return 80
  }
}
/** Derive confidence for Y-axis: success=100, failed=0, pending=50, etc. */function getConfidence(node: EventNodeType): number {  if (node.confidence != null) return node.confidence  switch (node.status) {    case 'success':      return 100    case 'failed':    case 'missing':      return 0    case 'pending':      return 50    case 'warning':      return 75    case 'retry':      return 60    case 'skipped':      return 0    default:      return 80  }}
Position Calculations:
timeline-canvas.tsx
Lines 40-83
export function TimelineCanvas({
  data,
  zoom,
  selectedNodeId,
  onSelectNode,
  visibleLanes,
}: TimelineCanvasProps) {
  const { startTime, endTime, nodes } = data
  const totalMs = endTime - startTime || 1

  // Filter nodes by visible lanes
  const visibleNodes = useMemo(
    () => nodes.filter((n) => visibleLanes.has(n.laneId)),
    [nodes, visibleLanes]
  )

  // Convert timestamp to percentage position (X-axis)
  const toPercent = (ts: number) => ((ts - startTime) / totalMs) * 100

  // Sort nodes by time for confidence line
  const sortedNodes = useMemo(
    () => [...visibleNodes].sort((a, b) => a.timestampMs - b.timestampMs),
    [visibleNodes]
  )

  // Generate confidence line path for SVG
  const linePath = useMemo(() => {
    if (sortedNodes.length < 2) return ''
    return sortedNodes
      .map((n) => {
        const x = toPercent(n.timestampMs)
        const conf = getConfidence(n)
        const y = 100 - conf // 0% at bottom, 100% at top
        return `${x},${y}`
      })
      .join(' ')
  }, [sortedNodes, totalMs, startTime])
  // ...
}
export function TimelineCanvas({  data,  zoom,  selectedNodeId,  onSelectNode,  visibleLanes,}: TimelineCanvasProps) {  const { startTime, endTime, nodes } = data  const totalMs = endTime - startTime || 1  // Filter nodes by visible lanes  const visibleNodes = useMemo(    () => nodes.filter((n) => visibleLanes.has(n.laneId)),    [nodes, visibleLanes]  )  // Convert timestamp to percentage position (X-axis)  const toPercent = (ts: number) => ((ts - startTime) / totalMs) * 100  // Sort nodes by time for confidence line  const sortedNodes = useMemo(    () => [...visibleNodes].sort((a, b) => a.timestampMs - b.timestampMs),    [visibleNodes]  )  // Generate confidence line path for SVG  const linePath = useMemo(() => {    if (sortedNodes.length < 2) return ''    return sortedNodes      .map((n) => {        const x = toPercent(n.timestampMs)        const conf = getConfidence(n)        const y = 100 - conf // 0% at bottom, 100% at top        return `${x},${y}`      })      .join(' ')  }, [sortedNodes, totalMs, startTime])  // ...}
Chart Structure:
timeline-canvas.tsx
Lines 95-139
        {/* Stock-market-style chart container */}
        <div className="rounded-xl border border-zinc-800/80 bg-[#0a0a0a] shadow-2xl overflow-hidden">
          {/* Chart header - ticker style */}
          <div className="flex items-center justify-between border-b border-zinc-800/80 bg-zinc-950/90 px-5 py-3">
            <div className="flex items-center gap-4">
              {/* Intent label */}
              <span className="font-mono text-sm font-semibold text-emerald-400">
                {data.intentLabel ?? data.intentId}
              </span>
              <span className="rounded bg-zinc-800/80 px-2 py-0.5 font-mono text-xs text-zinc-400">
                Confidence
              </span>
              {/* Overall confidence with color coding */}
              {data.overallConfidence != null && (
                <span
                  className={cn(
                    'font-mono text-sm font-bold tabular-nums',
                    data.overallConfidence >= 80
                      ? 'text-emerald-400'      // Green for high confidence
                      : data.overallConfidence >= 50
                        ? 'text-amber-400'      // Yellow for medium
                        : 'text-red-400'        // Red for low
                  )}
                >
                  {data.overallConfidence}%
                </span>
              )}
            </div>
            {/* Time range display */}
            <div className="flex items-center gap-2 text-xs text-zinc-500">
              <span className="font-mono tabular-nums">
                {new Date(startTime).toLocaleTimeString('en-IN', {
                  hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
                })}
              </span>
              <span className="text-zinc-600">→</span>
              <span className="font-mono tabular-nums">
                {new Date(endTime).toLocaleTimeString('en-IN', {
                  hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
                })}
              </span>
            </div>
          </div>
        {/* Stock-market-style chart container */}        <div className="rounded-xl border border-zinc-800/80 bg-[#0a0a0a] shadow-2xl overflow-hidden">          {/* Chart header - ticker style */}          <div className="flex items-center justify-between border-b border-zinc-800/80 bg-zinc-950/90 px-5 py-3">            <div className="flex items-center gap-4">              {/* Intent label */}              <span className="font-mono text-sm font-semibold text-emerald-400">                {data.intentLabel ?? data.intentId}              </span>              <span className="rounded bg-zinc-800/80 px-2 py-0.5 font-mono text-xs text-zinc-400">                Confidence              </span>              {/* Overall confidence with color coding */}              {data.overallConfidence != null && (                <span                  className={cn(                    'font-mono text-sm font-bold tabular-nums',                    data.overallConfidence >= 80                      ? 'text-emerald-400'      // Green for high confidence                      : data.overallConfidence >= 50                        ? 'text-amber-400'      // Yellow for medium                        : 'text-red-400'        // Red for low                  )}                >                  {data.overallConfidence}%                </span>              )}            </div>            {/* Time range display */}            <div className="flex items-center gap-2 text-xs text-zinc-500">              <span className="font-mono tabular-nums">                {new Date(startTime).toLocaleTimeString('en-IN', {                  hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,                })}              </span>              <span className="text-zinc-600">→</span>              <span className="font-mono tabular-nums">                {new Date(endTime).toLocaleTimeString('en-IN', {                  hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,                })}              </span>            </div>          </div>
SVG Grid Pattern:
timeline-canvas.tsx
Lines 158-201
                {/* Grid lines - stock market style */}
                <svg
                  className="absolute inset-0 w-full h-full"
                  preserveAspectRatio="none"
                >
                  <defs>
                    <pattern
                      id="grid-pattern"
                      width="100%"
                      height="100%"
                      patternUnits="userSpaceOnUse"
                    >
                      {/* Horizontal grid lines (5 lines for 100%, 75%, 50%, 25%, 0%) */}
                      {Array.from({ length: 6 }).map((_, i) => (
                        <line
                          key={`h-${i}`}
                          x1="0"
                          y1={`${(i / 5) * 100}%`}
                          x2="100%"
                          y2={`${(i / 5) * 100}%`}
                          stroke="rgb(63 63 70 / 0.25)"
                          strokeWidth="0.5"
                          vectorEffect="non-scaling-stroke"
                        />
                      ))}
                      {/* Vertical grid lines (8 columns) */}
                      {Array.from({ length: GRID_COLS + 1 }).map((_, i) => (
                        <line
                          key={`v-${i}`}
                          x1={`${(i / GRID_COLS) * 100}%`}
                          y1="0"
                          x2={`${(i / GRID_COLS) * 100}%`}
                          y2="100%"
                          stroke="rgb(63 63 70 / 0.25)"
                          strokeWidth="0.5"
                          vectorEffect="non-scaling-stroke"
                        />
                      ))}
                    </pattern>
                  </defs>
                  <rect width="100%" height="100%" fill="url(#grid-pattern)" />
                </svg>
                {/* Grid lines - stock market style */}                <svg                  className="absolute inset-0 w-full h-full"                  preserveAspectRatio="none"                >                  <defs>                    <pattern                      id="grid-pattern"                      width="100%"                      height="100%"                      patternUnits="userSpaceOnUse"                    >                      {/* Horizontal grid lines (5 lines for 100%, 75%, 50%, 25%, 0%) */}                      {Array.from({ length: 6 }).map((_, i) => (                        <line                          key={`h-${i}`}                          x1="0"                          y1={`${(i / 5) * 100}%`}                          x2="100%"                          y2={`${(i / 5) * 100}%`}                          stroke="rgb(63 63 70 / 0.25)"                          strokeWidth="0.5"                          vectorEffect="non-scaling-stroke"                        />                      ))}                      {/* Vertical grid lines (8 columns) */}                      {Array.from({ length: GRID_COLS + 1 }).map((_, i) => (                        <line                          key={`v-${i}`}                          x1={`${(i / GRID_COLS) * 100}%`}                          y1="0"                          x2={`${(i / GRID_COLS) * 100}%`}                          y2="100%"                          stroke="rgb(63 63 70 / 0.25)"                          strokeWidth="0.5"                          vectorEffect="non-scaling-stroke"                        />                      ))}                    </pattern>                  </defs>                  <rect width="100%" height="100%" fill="url(#grid-pattern)" />                </svg>
Confidence Line with Gradient Fill:
timeline-canvas.tsx
Lines 203-237
                {/* Confidence line - stock price style with area fill */}
                <svg
                  className="absolute inset-0 w-full h-full pointer-events-none"
                  viewBox="0 0 100 100"
                  preserveAspectRatio="none"
                >
                  <defs>
                    <linearGradient
                      id="confidence-gradient"
                      x1="0%" y1="0%" x2="0%" y2="100%"
                    >
                      <stop offset="0%" stopColor="rgb(16 185 129 / 0.2)" />
                      <stop offset="100%" stopColor="rgb(16 185 129 / 0)" />
                    </linearGradient>
                  </defs>
                  {linePath && (
                    <>
                      {/* Filled area under the line */}
                      <polygon
                        fill="url(#confidence-gradient)"
                        points={`0,100 ${linePath} 100,100`}
                      />
                      {/* The confidence line itself */}
                      <polyline
                        fill="none"
                        stroke="rgb(16 185 129 / 0.85)"
                        strokeWidth="0.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        points={linePath}
                      />
                    </>
                  )}
                </svg>
                {/* Confidence line - stock price style with area fill */}                <svg                  className="absolute inset-0 w-full h-full pointer-events-none"                  viewBox="0 0 100 100"                  preserveAspectRatio="none"                >                  <defs>                    <linearGradient                      id="confidence-gradient"                      x1="0%" y1="0%" x2="0%" y2="100%"                    >                      <stop offset="0%" stopColor="rgb(16 185 129 / 0.2)" />                      <stop offset="100%" stopColor="rgb(16 185 129 / 0)" />                    </linearGradient>                  </defs>                  {linePath && (                    <>                      {/* Filled area under the line */}                      <polygon                        fill="url(#confidence-gradient)"                        points={`0,100 ${linePath} 100,100`}                      />                      {/* The confidence line itself */}                      <polyline                        fill="none"                        stroke="rgb(16 185 129 / 0.85)"                        strokeWidth="0.8"                        strokeLinecap="round"                        strokeLinejoin="round"                        points={linePath}                      />                    </>                  )}                </svg>
Event Nodes Positioning:
timeline-canvas.tsx
Lines 239-266
                {/* Event nodes - positioned by time (x) and confidence (y) */}
                {visibleNodes.map((node) => {
                  const leftPercent = toPercent(node.timestampMs)  // X position
                  const conf = getConfidence(node)
                  const topPercent = 100 - conf                    // Y position (inverted)
                  return (
                    <div
                      key={node.id}
                      className="absolute -translate-x-1/2 -translate-y-1/2 z-10"
                      style={{
                        left: `${leftPercent}%`,
                        top: `${topPercent}%`,
                      }}
                    >
                      <EventNode
                        node={node}
                        leftPercent={0}
                        onClick={() =>
                          onSelectNode(
                            selectedNodeId === node.id ? null : node
                          )
                        }
                        isSelected={selectedNodeId === node.id}
                        variant="chart"
                      />
                    </div>
                  )
                })}
                {/* Event nodes - positioned by time (x) and confidence (y) */}                {visibleNodes.map((node) => {                  const leftPercent = toPercent(node.timestampMs)  // X position                  const conf = getConfidence(node)                  const topPercent = 100 - conf                    // Y position (inverted)                  return (                    <div                      key={node.id}                      className="absolute -translate-x-1/2 -translate-y-1/2 z-10"                      style={{                        left: `${leftPercent}%`,                        top: `${topPercent}%`,                      }}                    >                      <EventNode                        node={node}                        leftPercent={0}                        onClick={() =>                          onSelectNode(                            selectedNodeId === node.id ? null : node                          )                        }                        isSelected={selectedNodeId === node.id}                        variant="chart"                      />                    </div>                  )                })}
4. Event Node Component (components/event-node.tsx)
Status Configuration:
event-node.tsx
Lines 14-60
const STATUS_CONFIG: Record<
  EventNodeStatus,
  { icon: React.ReactNode; color: string; bg: string; border: string }
> = {
  success: {
    icon: <Check className="h-2.5 w-2.5" />,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500',
    border: 'border-emerald-500',
  },
  failed: {
    icon: <X className="h-2.5 w-2.5" />,
    color: 'text-red-400',
    bg: 'bg-red-500',
    border: 'border-red-500',
  },
  pending: {
    icon: <Clock className="h-2.5 w-2.5" />,
    color: 'text-amber-400',
    bg: 'bg-amber-500',
    border: 'border-amber-500',
  },
  // ... warning, retry, skipped, missing
}
const STATUS_CONFIG: Record<  EventNodeStatus,  { icon: React.ReactNode; color: string; bg: string; border: string }> = {  success: {    icon: <Check className="h-2.5 w-2.5" />,    color: 'text-emerald-400',    bg: 'bg-emerald-500',    border: 'border-emerald-500',  },  failed: {    icon: <X className="h-2.5 w-2.5" />,    color: 'text-red-400',    bg: 'bg-red-500',    border: 'border-red-500',  },  pending: {    icon: <Clock className="h-2.5 w-2.5" />,    color: 'text-amber-400',    bg: 'bg-amber-500',    border: 'border-amber-500',  },  // ... warning, retry, skipped, missing}
Node Rendering with Tooltip:
event-node.tsx
Lines 90-133
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={onClick}
            className={cn(
              'flex flex-col items-center gap-0.5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-zinc-500 focus:ring-offset-2 focus:ring-offset-zinc-950 rounded-lg group',
              variant === 'default' && 'absolute top-1/2 -translate-y-1/2',
              isSelected && 'ring-2 ring-emerald-400/80 ring-offset-2 ring-offset-zinc-950 scale-110 z-10'
            )}
            style={variant === 'default' ? { left: `${leftPercent}%` } : undefined}
            aria-label={`Event: ${node.name}`}
          >
            <div
              className={cn(
                'border-2 flex items-center justify-center text-white shadow-lg transition-transform group-hover:scale-105',
                variant === 'chart' ? 'w-5 h-5 rounded-md' : 'w-7 h-7 rounded-lg',
                config.bg,
                config.border,
                node.isMissing && 'border-dashed'  // Dashed border for missing events
              )}
            >
              {config.icon}
            </div>
            {/* Labels only for default variant */}
            {variant === 'default' && (
              <>
                <span className="text-[10px] font-medium text-zinc-400 max-w-[72px] truncate text-center group-hover:text-zinc-200">
                  {node.name}
                </span>
                {node.confidence != null && (
                  <span className="text-[9px] tabular-nums text-zinc-500">{node.confidence}%</span>
                )}
              </>
            )}
          </button>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-[220px] border-zinc-800 bg-zinc-950">
          {tooltipContent}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
  return (    <TooltipProvider>      <Tooltip>        <TooltipTrigger asChild>          <button            type="button"            onClick={onClick}            className={cn(              'flex flex-col items-center gap-0.5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-zinc-500 focus:ring-offset-2 focus:ring-offset-zinc-950 rounded-lg group',              variant === 'default' && 'absolute top-1/2 -translate-y-1/2',              isSelected && 'ring-2 ring-emerald-400/80 ring-offset-2 ring-offset-zinc-950 scale-110 z-10'            )}            style={variant === 'default' ? { left: `${leftPercent}%` } : undefined}            aria-label={`Event: ${node.name}`}          >            <div              className={cn(                'border-2 flex items-center justify-center text-white shadow-lg transition-transform group-hover:scale-105',                variant === 'chart' ? 'w-5 h-5 rounded-md' : 'w-7 h-7 rounded-lg',                config.bg,                config.border,                node.isMissing && 'border-dashed'  // Dashed border for missing events              )}            >              {config.icon}            </div>            {/* Labels only for default variant */}            {variant === 'default' && (              <>                <span className="text-[10px] font-medium text-zinc-400 max-w-[72px] truncate text-center group-hover:text-zinc-200">                  {node.name}                </span>                {node.confidence != null && (                  <span className="text-[9px] tabular-nums text-zinc-500">{node.confidence}%</span>                )}              </>            )}          </button>        </TooltipTrigger>        <TooltipContent side="top" className="max-w-[220px] border-zinc-800 bg-zinc-950">          {tooltipContent}        </TooltipContent>      </Tooltip>    </TooltipProvider>  )
5. Event Details Panel (components/event-details-panel.tsx)
Empty State:
event-details-panel.tsx
Lines 27-39
export function EventDetailsPanel({ node, intentId, onClose }: EventDetailsPanelProps) {
  if (!node) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center">
        <div className="rounded-full bg-zinc-800/60 p-4 mb-4">
          <div className="h-8 w-8 rounded-full border-2 border-dashed border-zinc-600" />
        </div>
        <p className="text-sm text-zinc-500 max-w-[240px]">
          No event selected. Click a node on the timeline to view details.
        </p>
      </div>
    )
  }
export function EventDetailsPanel({ node, intentId, onClose }: EventDetailsPanelProps) {  if (!node) {    return (      <div className="flex h-full flex-col items-center justify-center p-8 text-center">        <div className="rounded-full bg-zinc-800/60 p-4 mb-4">          <div className="h-8 w-8 rounded-full border-2 border-dashed border-zinc-600" />        </div>        <p className="text-sm text-zinc-500 max-w-[240px]">          No event selected. Click a node on the timeline to view details.        </p>      </div>    )  }
Details Display with Error Handling:
event-details-panel.tsx
Lines 45-112
  return (
    <ScrollArea className="h-full">
      <div className="p-5 space-y-5">
        <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-4 space-y-4">
            {/* Event name, ID, Type */}
            <div>
              <div className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Event</div>
              <div className="mt-0.5 text-sm font-medium text-white">{node.name}</div>
            </div>
            
            {/* Status badge with color coding */}
            <div>
              <div className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Status</div>
              <span
                className={cn(
                  'mt-0.5 inline-flex items-center rounded-md px-2.5 py-1 text-xs font-semibold',
                  isSuccess && 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/30',
                  isFailed && 'bg-red-500/20 text-red-400 ring-1 ring-red-500/30',
                  !isSuccess && !isFailed && 'bg-amber-500/20 text-amber-400 ring-1 ring-amber-500/30'
                )}
              >
                {statusLabel}
              </span>
            </div>

            {/* Dynamic key-value details */}
            {Object.keys(node.details).length > 0 && (
              <div>
                <div className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-2">Details</div>
                <div className="space-y-1.5 rounded-lg bg-zinc-950/50 p-3 text-xs">
                  {Object.entries(node.details).map(([key, value]) => (
                    <div key={key} className="flex justify-between gap-4">
                      <span className="text-zinc-500 shrink-0">{key}</span>
                      <span className="text-zinc-300 text-right">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Error block (only for failed events) */}
            {node.error && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3">
                <div className="text-xs font-medium text-red-400">Error</div>
                <div className="text-xs text-red-300 mt-1">{node.error.message}</div>
                {node.error.code && (
                  <div className="text-xs text-zinc-500 mt-1">Code: {node.error.code}</div>
                )}
                {node.error.recovery && (
                  <div className="text-xs text-amber-400 mt-1">Recovery: {node.error.recovery}</div>
                )}
              </div>
            )}
        </div>
      </div>
    </ScrollArea>
  )
  return (    <ScrollArea className="h-full">      <div className="p-5 space-y-5">        <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-4 space-y-4">            {/* Event name, ID, Type */}            <div>              <div className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Event</div>              <div className="mt-0.5 text-sm font-medium text-white">{node.name}</div>            </div>                        {/* Status badge with color coding */}            <div>              <div className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Status</div>              <span                className={cn(                  'mt-0.5 inline-flex items-center rounded-md px-2.5 py-1 text-xs font-semibold',                  isSuccess && 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/30',                  isFailed && 'bg-red-500/20 text-red-400 ring-1 ring-red-500/30',                  !isSuccess && !isFailed && 'bg-amber-500/20 text-amber-400 ring-1 ring-amber-500/30'                )}              >                {statusLabel}              </span>            </div>            {/* Dynamic key-value details */}            {Object.keys(node.details).length > 0 && (              <div>                <div className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-2">Details</div>                <div className="space-y-1.5 rounded-lg bg-zinc-950/50 p-3 text-xs">                  {Object.entries(node.details).map(([key, value]) => (                    <div key={key} className="flex justify-between gap-4">                      <span className="text-zinc-500 shrink-0">{key}</span>                      <span className="text-zinc-300 text-right">{String(value)}</span>                    </div>                  ))}                </div>              </div>            )}            {/* Error block (only for failed events) */}            {node.error && (              <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3">                <div className="text-xs font-medium text-red-400">Error</div>                <div className="text-xs text-red-300 mt-1">{node.error.message}</div>                {node.error.code && (                  <div className="text-xs text-zinc-500 mt-1">Code: {node.error.code}</div>                )}                {node.error.recovery && (                  <div className="text-xs text-amber-400 mt-1">Recovery: {node.error.recovery}</div>                )}              </div>            )}        </div>      </div>    </ScrollArea>  )
6. Toolbar Component (components/event-graph-toolbar.tsx)
Time Range Toggle Buttons:
event-graph-toolbar.tsx
Lines 59-79
    <div className="flex flex-wrap items-center gap-6 border-b border-zinc-800/60 bg-zinc-900/40 px-6 py-3">
      {/* Time range */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Time</span>
        <div className="flex rounded-lg border border-zinc-700/60 bg-zinc-900/50 p-0.5">
          {TIME_PRESETS.map((p) => (
            <button
              key={p.value}
              type="button"
              onClick={() => onTimeRangeChange(p.value)}
              className={cn(
                'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                timeRange === p.value
                  ? 'bg-zinc-700/80 text-white shadow-sm'      // Active state
                  : 'text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200'
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
    <div className="flex flex-wrap items-center gap-6 border-b border-zinc-800/60 bg-zinc-900/40 px-6 py-3">      {/* Time range */}      <div className="flex items-center gap-3">        <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Time</span>        <div className="flex rounded-lg border border-zinc-700/60 bg-zinc-900/50 p-0.5">          {TIME_PRESETS.map((p) => (            <button              key={p.value}              type="button"              onClick={() => onTimeRangeChange(p.value)}              className={cn(                'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',                timeRange === p.value                  ? 'bg-zinc-700/80 text-white shadow-sm'      // Active state                  : 'text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200'              )}            >              {p.label}            </button>          ))}        </div>      </div>
Zoom Slider:
event-graph-toolbar.tsx
Lines 83-113
      {/* Zoom */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Zoom</span>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-zinc-400 hover:bg-zinc-800/60 hover:text-white"
            onClick={() => onZoomChange(Math.max(25, zoom - 25))}  // Min 25%
          >
            <Minus className="h-4 w-4" />
          </Button>
          <Slider
            value={[zoom]}
            min={25}
            max={200}
            step={10}
            className="w-28"
            onValueChange={([v]) => onZoomChange(v ?? 100)}
          />
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-zinc-400 hover:bg-zinc-800/60 hover:text-white"
            onClick={() => onZoomChange(Math.min(200, zoom + 25))}  // Max 200%
          >
            <Plus className="h-4 w-4" />
          </Button>
          <span className="min-w-[3ch] text-right text-xs tabular-nums text-zinc-500">{zoom}%</span>
        </div>
      </div>
      {/* Zoom */}      <div className="flex items-center gap-3">        <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Zoom</span>        <div className="flex items-center gap-2">          <Button            variant="ghost"            size="icon"            className="h-8 w-8 text-zinc-400 hover:bg-zinc-800/60 hover:text-white"            onClick={() => onZoomChange(Math.max(25, zoom - 25))}  // Min 25%          >            <Minus className="h-4 w-4" />          </Button>          <Slider            value={[zoom]}            min={25}            max={200}            step={10}            className="w-28"            onValueChange={([v]) => onZoomChange(v ?? 100)}          />          <Button            variant="ghost"            size="icon"            className="h-8 w-8 text-zinc-400 hover:bg-zinc-800/60 hover:text-white"            onClick={() => onZoomChange(Math.min(200, zoom + 25))}  // Max 200%          >            <Plus className="h-4 w-4" />          </Button>          <span className="min-w-[3ch] text-right text-xs tabular-nums text-zinc-500">{zoom}%</span>        </div>      </div>
Lane Visibility Checkboxes:
event-graph-toolbar.tsx
Lines 117-142
      {/* Lane visibility & Filter */}
      <div className="flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="h-8 border-zinc-700/80 bg-zinc-900/50 text-zinc-300 hover:bg-zinc-800/60 hover:text-white">
              <Layers className="h-4 w-4 mr-2" />
              Lanes
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-48 border-zinc-800 bg-zinc-950">
            {(Object.keys(LANE_LABELS) as EventLaneId[]).map((id) => (
              <DropdownMenuCheckboxItem
                key={id}
                checked={visibleLanes.has(id)}
                onCheckedChange={() => onToggleLane(id)}
                className="focus:bg-zinc-800"
              >
                {LANE_LABELS[id]}
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      {/* Lane visibility & Filter */}      <div className="flex items-center gap-2">        <DropdownMenu>          <DropdownMenuTrigger asChild>            <Button variant="outline" size="sm" className="h-8 border-zinc-700/80 bg-zinc-900/50 text-zinc-300 hover:bg-zinc-800/60 hover:text-white">              <Layers className="h-4 w-4 mr-2" />              Lanes            </Button>          </DropdownMenuTrigger>          <DropdownMenuContent align="start" className="w-48 border-zinc-800 bg-zinc-950">            {(Object.keys(LANE_LABELS) as EventLaneId[]).map((id) => (              <DropdownMenuCheckboxItem                key={id}                checked={visibleLanes.has(id)}                onCheckedChange={() => onToggleLane(id)}                className="focus:bg-zinc-800"              >                {LANE_LABELS[id]}              </DropdownMenuCheckboxItem>            ))}          </DropdownMenuContent>        </DropdownMenu>      </div>
7. Data Flow Summary
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA FLOW                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  URL (?intent=xxx)  ───────┐                                            │
│                            ▼                                            │
│  Header Dropdown ────► selectedIntentId (state)                         │
│                            │                                            │
│                            ▼                                            │
│              getEventGraphData(intentId)                                │
│                            │                                            │
│                            ▼                                            │
│                    graphData (state)                                    │
│                            │                                            │
│          ┌─────────────────┼─────────────────┐                         │
│          ▼                 ▼                 ▼                         │
│   TimelineCanvas    EventDetailsPanel    Toolbar                       │
│          │                 ▲                 │                         │
│          │                 │                 │                         │
│   Click on node ───► selectedNode (state)   │                         │
│                                              │                         │
│   zoom, timeRange, visibleLanes ◄───────────┘                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────┐│                           DATA FLOW                                      │├─────────────────────────────────────────────────────────────────────────┤│                                                                          ││  URL (?intent=xxx)  ───────┐                                            ││                            ▼                                            ││  Header Dropdown ────► selectedIntentId (state)                         ││                            │                                            ││                            ▼                                            ││              getEventGraphData(intentId)                                ││                            │                                            ││                            ▼                                            ││                    graphData (state)                                    ││                            │                                            ││          ┌─────────────────┼─────────────────┐                         ││          ▼                 ▼                 ▼                         ││   TimelineCanvas    EventDetailsPanel    Toolbar                       ││          │                 ▲                 │                         ││          │                 │                 │                         ││   Click on node ───► selectedNode (state)   │                         ││                                              │                         ││   zoom, timeRange, visibleLanes ◄───────────┘                         ││                                                                          │└─────────────────────────────────────────────────────────────────────────┘
Key Design Patterns Used
Lifted State - All state managed in parent page.tsx, passed down as props
Controlled Components - Toolbar controls are fully controlled via props
Computed Values with useMemo - Line paths, visible nodes computed efficiently
URL Deep Linking - useSearchParams for intent selection from URL
Conditional Rendering - Empty state vs chart based on graphData
Responsive Sidebar - useSidebar context for margin adjustments
SVG for Charts - Using viewBox and preserveAspectRatio for responsive charts