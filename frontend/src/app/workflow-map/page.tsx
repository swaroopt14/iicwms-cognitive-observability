'use client';

import React, { useState, useMemo, useCallback, useEffect } from 'react';
import {
  GitBranch,
  ZoomIn,
  ZoomOut,
  Download,
  Layers,
  Filter,
  X,
  ExternalLink,
  CheckCircle,
  Clock,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Minus,
  ChevronDown,
  Info,
  Zap,
  ArrowRight,
  Loader2,
} from 'lucide-react';
import { formatTime } from '@/lib/utils';
import { DonutChart, Sparkline } from '@/components/Charts';
import {
  fetchWorkflowTimeline,
  fetchWorkflows,
  type TimelineData,
} from '@/lib/api';

// ============================================
// Types adapted to IICWMS problem statement
// ============================================
type EventNodeStatus = 'success' | 'delayed' | 'failed' | 'retry' | 'skipped' | 'warning' | 'in_progress' | 'pending' | 'missing';
type EventLaneId = 'code' | 'workflow' | 'resource' | 'human' | 'compliance';

interface EventNode {
  id: string;
  laneId: EventLaneId;
  name: string;
  status: EventNodeStatus;
  timestamp: string;
  timestampMs: number;
  durationMs?: number;
  confidence?: number;
  details: Record<string, unknown>;
  error?: { code: string; message: string; recovery?: string };
  attempt?: number;
  dependsOn?: string[];
  slaDeadlineMs?: number;
  isMissing?: boolean;
  agentSource?: string;
}

interface EventGraphData {
  workflowId: string;
  workflowLabel: string;
  startTime: number;
  endTime: number;
  totalDurationMs: number;
  lanes: { id: EventLaneId; label: string; order: number; visible: boolean }[];
  nodes: EventNode[];
  overallConfidence: number;
  outcomeSummary?: string;
}

interface WorkflowOption {
  id: string;
  label: string;
  projectId: string;
  projectName: string;
  environment: string;
  contextTag: string;
  status: string;
  inputSource: string;
  issueCategory: string;
}

const REQUIRED_WORKFLOWS: Omit<WorkflowOption, 'status'>[] = [
  {
    id: 'wf_policy_compliance_monitoring',
    label: 'Policy Compliance Monitoring',
    projectId: 'proj_compliance',
    projectName: 'Governance & Compliance',
    environment: 'production',
    contextTag: 'compliance_governance',
    inputSource: 'system_internal',
    issueCategory: 'compliance_or_data_risk',
  },
  {
    id: 'wf_security_posture_assessment',
    label: 'Security Posture Assessment',
    projectId: 'proj_secops',
    projectName: 'Security Operations',
    environment: 'production',
    contextTag: 'security_posture',
    inputSource: 'system_internal',
    issueCategory: 'compliance_or_data_risk',
  },
  {
    id: 'wf_resource_utilization_cost_optimization',
    label: 'Resource Utilization & Cost Optimization',
    projectId: 'proj_infra_efficiency',
    projectName: 'Infrastructure Efficiency',
    environment: 'production',
    contextTag: 'resource_cost',
    inputSource: 'server_failure',
    issueCategory: 'server_failure',
  },
  {
    id: 'wf_change_risk_analysis',
    label: 'Change Risk Analysis',
    projectId: 'proj_release_risk',
    projectName: 'Release Engineering',
    environment: 'production',
    contextTag: 'change_risk',
    inputSource: 'github',
    issueCategory: 'deployment_pipeline',
  },
  {
    id: 'wf_incident_response_alert_correlation',
    label: 'Incident Response & Alert Correlation',
    projectId: 'proj_incident_ops',
    projectName: 'SRE Incident Management',
    environment: 'production',
    contextTag: 'incident_management',
    inputSource: 'server_failure',
    issueCategory: 'server_failure',
  },
  {
    id: 'wf_api_service_performance_monitoring',
    label: 'API & Service Performance Monitoring',
    projectId: 'proj_api_perf',
    projectName: 'Service Reliability',
    environment: 'production',
    contextTag: 'api_performance',
    inputSource: 'client_side',
    issueCategory: 'client_side_error',
  },
];

function mergeRequiredWorkflows(input: WorkflowOption[]): WorkflowOption[] {
  const filtered = input.filter((w) => w.label.trim().toLowerCase() !== 'expense reimbursement');
  const byLabel = new Map(filtered.map((w) => [w.label.trim().toLowerCase(), w]));

  for (const req of REQUIRED_WORKFLOWS) {
    const key = req.label.toLowerCase();
    if (!byLabel.has(key)) {
      filtered.push({
        ...req,
        status: 'active',
      });
    }
  }

  return filtered;
}

type TimeRangePreset = '5m' | '15m' | '1h' | '6h' | '24h';

// ============================================
// Status Configuration
// ============================================
const STATUS_CONFIG: Record<EventNodeStatus, {
  icon: typeof CheckCircle;
  color: string;
  bg: string;
  label: string;
  confidence: number;
}> = {
  success:     { icon: CheckCircle,   color: '#10b981', bg: 'bg-emerald-500', label: 'Success',     confidence: 100 },
  delayed:     { icon: Clock,         color: '#f59e0b', bg: 'bg-amber-500',   label: 'Delayed',     confidence: 60  },
  failed:      { icon: XCircle,       color: '#ef4444', bg: 'bg-red-500',     label: 'Failed',      confidence: 0   },
  retry:       { icon: RefreshCw,     color: '#06b6d4', bg: 'bg-cyan-500',    label: 'Retry',       confidence: 55  },
  skipped:     { icon: Minus,         color: '#94a3b8', bg: 'bg-slate-400',   label: 'Skipped',     confidence: 0   },
  warning:     { icon: AlertTriangle, color: '#f97316', bg: 'bg-orange-500',  label: 'Warning',     confidence: 75  },
  in_progress: { icon: Clock,         color: '#3b82f6', bg: 'bg-blue-500',    label: 'In Progress', confidence: 50  },
  pending:     { icon: Clock,         color: '#94a3b8', bg: 'bg-slate-300',   label: 'Pending',     confidence: 50  },
  missing:     { icon: XCircle,       color: '#ef4444', bg: 'bg-red-300',     label: 'Missing',     confidence: 0   },
};

const LANE_CONFIG: Record<EventLaneId, { label: string; color: string }> = {
  code:       { label: 'Code & CI',   color: '#0ea5e9' },
  workflow:   { label: 'Workflow',   color: '#6366f1' },
  resource:   { label: 'Resource',   color: '#10b981' },
  human:      { label: 'Human',      color: '#f59e0b' },
  compliance: { label: 'Compliance', color: '#8b5cf6' },
};

function getConfidence(node: EventNode): number {
  if (node.confidence != null) return node.confidence;
  return STATUS_CONFIG[node.status]?.confidence ?? 50;
}

function mapTimelineToGraph(timeline: TimelineData): EventGraphData {
  const nodes: EventNode[] = timeline.nodes.map((n) => ({
    id: n.id,
    laneId: n.laneId as EventLaneId,
    name: n.name,
    status: n.status as EventNodeStatus,
    timestamp: n.timestamp,
    timestampMs: n.timestampMs,
    durationMs: n.durationMs ?? undefined,
    confidence: n.confidence,
    details: (n.details || {}) as Record<string, unknown>,
    dependsOn: n.dependsOn || [],
    agentSource: n.agentSource || 'system',
    error: n.error,
  }));

  return {
    workflowId: timeline.workflowId,
    workflowLabel: timeline.workflowLabel,
    startTime: timeline.startTime,
    endTime: timeline.endTime,
    totalDurationMs: timeline.endTime - timeline.startTime,
    lanes: timeline.lanes.map((l) => ({
      id: l.id as EventLaneId,
      label: l.label,
      order: l.order,
      visible: l.visible,
    })),
    nodes,
    overallConfidence: timeline.overallConfidence,
    outcomeSummary: timeline.outcomeSummary,
  };
}

function formatContextTag(tag?: string): string {
  if (!tag) return 'workflow';
  return tag.replace(/_/g, ' ');
}

function formatChipLabel(s?: string): string {
  if (!s) return 'unknown';
  return s.replace(/_/g, ' ');
}

function formatInputSource(s?: string): string {
  const v = (s || '').toLowerCase();
  if (!v) return 'system';
  if (v === 'github') return 'GitHub';
  if (v === 'client_side') return 'Client';
  if (v === 'server_failure') return 'Server';
  if (v === 'deployment_pipeline') return 'CI/CD';
  if (v === 'system_internal') return 'System';
  return formatChipLabel(v);
}

function formatIssueCategory(s?: string): string {
  const v = (s || '').toLowerCase();
  if (!v) return 'workflow anomaly';
  if (v === 'deployment_pipeline') return 'deployment';
  if (v === 'code_error_or_bug') return 'code bug';
  if (v === 'client_side_error') return 'client error';
  if (v === 'server_failure') return 'infra/server';
  if (v === 'compliance_or_data_risk') return 'compliance/data';
  return formatChipLabel(v);
}

function statusDotClass(status: string): string {
  const s = status.toLowerCase();
  if (s.includes('fail') || s.includes('critical')) return 'bg-red-500';
  if (s.includes('delay') || s.includes('degrad')) return 'bg-amber-500';
  if (s.includes('active') || s.includes('run')) return 'bg-emerald-500';
  return 'bg-slate-400';
}

// ============================================
// Mock Data — IT Operations Workflow Events
// ============================================
function generateMockData(workflowId: string): EventGraphData {
  const now = Date.now();
  const startTime = now - 600000; // 10 min ago

  const nodes: EventNode[] = [
    // Workflow Lane
    { id: 'evt_01', laneId: 'workflow', name: 'INIT', status: 'success', timestamp: new Date(startTime).toISOString(), timestampMs: startTime, durationMs: 1500, confidence: 100, details: { step: 'INIT', workflow: workflowId }, agentSource: 'WorkflowAgent' },
    { id: 'evt_02', laneId: 'workflow', name: 'VALIDATE', status: 'success', timestamp: new Date(startTime + 60000).toISOString(), timestampMs: startTime + 60000, durationMs: 3200, confidence: 95, details: { step: 'VALIDATE', validations: 12, passed: 12 }, agentSource: 'WorkflowAgent' },
    { id: 'evt_03', laneId: 'workflow', name: 'PROVISION', status: 'success', timestamp: new Date(startTime + 150000).toISOString(), timestampMs: startTime + 150000, durationMs: 8500, confidence: 88, details: { step: 'PROVISION', resources_allocated: 3 }, agentSource: 'WorkflowAgent' },
    { id: 'evt_04', laneId: 'workflow', name: 'DEPLOY', status: 'delayed', timestamp: new Date(startTime + 300000).toISOString(), timestampMs: startTime + 300000, durationMs: 25000, confidence: 62, details: { step: 'DEPLOY', expected_duration: '120s', actual_duration: '250s', sla_risk: true }, error: { code: 'SLA_BREACH_RISK', message: 'Step exceeded expected duration by 108%', recovery: 'Awaiting completion' }, agentSource: 'WorkflowAgent', slaDeadlineMs: 12000 },
    { id: 'evt_05', laneId: 'workflow', name: 'VERIFY', status: 'in_progress', timestamp: new Date(startTime + 450000).toISOString(), timestampMs: startTime + 450000, confidence: 55, details: { step: 'VERIFY', checks_pending: 4 }, dependsOn: ['evt_04'], agentSource: 'WorkflowAgent' },
    { id: 'evt_06', laneId: 'workflow', name: 'NOTIFY', status: 'pending', timestamp: new Date(startTime + 550000).toISOString(), timestampMs: startTime + 550000, confidence: 50, details: { step: 'NOTIFY' }, dependsOn: ['evt_05'], agentSource: 'WorkflowAgent' },

    // Resource Lane
    { id: 'evt_07', laneId: 'resource', name: 'CPU Normal', status: 'success', timestamp: new Date(startTime + 30000).toISOString(), timestampMs: startTime + 30000, confidence: 98, details: { metric: 'cpu_percent', value: 42, threshold: 80 }, agentSource: 'ResourceAgent' },
    { id: 'evt_08', laneId: 'resource', name: 'Latency Spike', status: 'warning', timestamp: new Date(startTime + 200000).toISOString(), timestampMs: startTime + 200000, confidence: 72, details: { metric: 'network_latency_ms', value: 240, baseline: 80, resource: 'vm_3' }, agentSource: 'ResourceAgent' },
    { id: 'evt_09', laneId: 'resource', name: 'CPU Spike', status: 'failed', timestamp: new Date(startTime + 350000).toISOString(), timestampMs: startTime + 350000, confidence: 15, details: { metric: 'cpu_percent', value: 96, threshold: 80, sustained: '5min', resource: 'vm_2' }, error: { code: 'CPU_SATURATION', message: 'CPU utilization at 96% for >5 minutes' }, agentSource: 'ResourceAgent' },
    { id: 'evt_10', laneId: 'resource', name: 'Memory Pressure', status: 'warning', timestamp: new Date(startTime + 420000).toISOString(), timestampMs: startTime + 420000, confidence: 68, details: { metric: 'memory_percent', value: 82, threshold: 85, resource: 'vm_2' }, agentSource: 'ResourceAgent' },

    // Human Action Lane
    { id: 'evt_11', laneId: 'human', name: 'Manual Override', status: 'warning', timestamp: new Date(startTime + 280000).toISOString(), timestampMs: startTime + 280000, confidence: 75, details: { action: 'MANUAL_OVERRIDE', actor: 'user_42', reason: 'SLA pressure' }, agentSource: 'WorkflowAgent' },
    { id: 'evt_12', laneId: 'human', name: 'Retry Triggered', status: 'retry', timestamp: new Date(startTime + 380000).toISOString(), timestampMs: startTime + 380000, confidence: 60, details: { action: 'MANUAL_RETRY', actor: 'user_42', attempt: 2, max_attempts: 3 }, attempt: 2, agentSource: 'WorkflowAgent' },

    // Compliance Lane
    { id: 'evt_13', laneId: 'compliance', name: 'Policy Check OK', status: 'success', timestamp: new Date(startTime + 90000).toISOString(), timestampMs: startTime + 90000, confidence: 100, details: { policy: 'DEPLOY_APPROVAL', result: 'PASSED' }, agentSource: 'ComplianceAgent' },
    { id: 'evt_14', laneId: 'compliance', name: 'After-Hours Write', status: 'failed', timestamp: new Date(startTime + 320000).toISOString(), timestampMs: startTime + 320000, confidence: 8, details: { policy: 'NO_AFTER_HOURS_WRITE', violation_type: 'SILENT', event_id: 'evt_11' }, error: { code: 'POLICY_VIOLATION', message: 'Write access outside business hours (9AM-6PM)', recovery: 'Revoke access, audit trail generated' }, agentSource: 'ComplianceAgent' },
    { id: 'evt_15', laneId: 'compliance', name: 'SLA Warning', status: 'warning', timestamp: new Date(startTime + 470000).toISOString(), timestampMs: startTime + 470000, confidence: 45, details: { policy: 'SLA_COMPLIANCE', risk_level: 'HIGH', time_remaining: '5min' }, agentSource: 'ComplianceAgent' },
  ];

  return {
    workflowId,
    workflowLabel: workflowId === 'wf_onboarding_17' ? 'User Onboarding #17' : 'Service Deployment #03',
    startTime,
    endTime: now,
    totalDurationMs: now - startTime,
    lanes: [
      { id: 'workflow', label: 'Workflow Steps', order: 0, visible: true },
      { id: 'resource', label: 'Resource Impact', order: 1, visible: true },
      { id: 'human', label: 'Human Actions', order: 2, visible: true },
      { id: 'compliance', label: 'Compliance', order: 3, visible: true },
    ],
    nodes,
    overallConfidence: 62,
    outcomeSummary: 'Workflow degraded — deploy step delayed due to network latency spike, manual override under SLA pressure',
  };
}

// ============================================
// SVG Timeline Canvas (Stock-market style)
// ============================================
function TimelineCanvas({
  data,
  zoom,
  selectedNodeId,
  onSelectNode,
  visibleLanes,
}: {
  data: EventGraphData;
  zoom: number;
  selectedNodeId: string | null;
  onSelectNode: (node: EventNode | null) => void;
  visibleLanes: Set<EventLaneId>;
}) {
  const { startTime, endTime, nodes } = data;
  const totalMs = endTime - startTime || 1;
  const GRID_COLS = 8;

  // Internal padding (%) to keep nodes from overflowing edges
  const PAD_X = 2;
  const PAD_TOP = 6;
  const PAD_BOTTOM = 6;

  const visibleNodes = useMemo(
    () => nodes.filter((n) => visibleLanes.has(n.laneId)),
    [nodes, visibleLanes]
  );

  // Map timestamp → x% with horizontal padding
  const toX = useCallback(
    (ts: number) => PAD_X + ((ts - startTime) / totalMs) * (100 - PAD_X * 2),
    [startTime, totalMs]
  );

  // Map confidence (0-100) → y% with vertical padding (high confidence = top)
  const toY = useCallback(
    (conf: number) => PAD_TOP + ((100 - conf) / 100) * (100 - PAD_TOP - PAD_BOTTOM),
    []
  );

  const sortedNodes = useMemo(
    () => [...visibleNodes].sort((a, b) => a.timestampMs - b.timestampMs),
    [visibleNodes]
  );

  // SVG confidence polyline points
  const linePath = useMemo(() => {
    if (sortedNodes.length < 2) return '';
    return sortedNodes
      .map((n) => {
        const x = toX(n.timestampMs);
        const y = toY(getConfidence(n));
        return `${x},${y}`;
      })
      .join(' ');
  }, [sortedNodes, toX, toY]);

  // Fill path (area under line)
  const fillPath = useMemo(() => {
    if (sortedNodes.length < 2) return '';
    const first = toX(sortedNodes[0].timestampMs);
    const last = toX(sortedNodes[sortedNodes.length - 1].timestampMs);
    const bottom = PAD_TOP + (100 - PAD_TOP - PAD_BOTTOM); // y for 0% confidence
    return `${first},${bottom} ${linePath} ${last},${bottom}`;
  }, [sortedNodes, linePath, toX]);

  const formatTimeLabel = (ms: number) => {
    const d = new Date(ms);
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
  };

  return (
    <div className="h-full flex flex-col" style={{ minWidth: `${zoom}%` }}>
      {/* Chart Header — Ticker-style */}
      <div className="flex items-center justify-between border-b border-[var(--color-border)] bg-gradient-to-r from-slate-50 to-white px-5 py-3">
        <div className="flex items-center gap-4">
          <span className="font-mono text-sm font-semibold text-[var(--color-primary)]">
            {data.workflowLabel}
          </span>
          <span className="px-2 py-0.5 bg-slate-100 rounded text-xs font-mono text-[var(--color-text-muted)]">
            Confidence
          </span>
          <span
            className="font-mono text-sm font-bold tabular-nums"
            style={{ color: data.overallConfidence >= 80 ? '#10b981' : data.overallConfidence >= 50 ? '#f59e0b' : '#ef4444' }}
          >
            {data.overallConfidence}%
          </span>
          {data.overallConfidence < 80 && (
            <span className="text-xs text-amber-600 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Degraded
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
          <span className="font-mono tabular-nums">{formatTimeLabel(startTime)}</span>
          <ArrowRight className="w-3 h-3" />
          <span className="font-mono tabular-nums">{formatTimeLabel(endTime)}</span>
          <span className="ml-2 text-[var(--color-text-muted)]">({Math.round((endTime - startTime) / 60000)}m)</span>
        </div>
      </div>

      {/* Main Chart Area */}
      <div className="flex-1 flex">
        {/* Y-Axis Labels */}
        <div className="w-14 flex flex-col justify-between py-4 pr-2 text-right border-r border-[var(--color-border)] bg-slate-50/50">
          {[100, 75, 50, 25, 0].map((val) => (
            <span key={val} className="text-[10px] font-mono tabular-nums text-[var(--color-text-muted)]">
              {val}%
            </span>
          ))}
        </div>

        {/* Chart Body */}
        <div className="flex-1 relative overflow-hidden">
          {/* Risk Zone Bands */}
          <div className="absolute inset-0 flex flex-col">
            <div className="flex-[30] bg-gradient-to-b from-emerald-50/40 to-transparent" />
            <div className="flex-[20] bg-gradient-to-b from-transparent to-amber-50/30" />
            <div className="flex-[20] bg-gradient-to-b from-amber-50/30 to-orange-50/30" />
            <div className="flex-[30] bg-gradient-to-b from-orange-50/30 to-red-50/40" />
          </div>

          {/* SVG Grid */}
          <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
            {/* Horizontal grid lines */}
            {Array.from({ length: 6 }).map((_, i) => (
              <line
                key={`h-${i}`}
                x1="0" y1={`${(i / 5) * 100}%`}
                x2="100%" y2={`${(i / 5) * 100}%`}
                stroke="#e2e8f0" strokeWidth="0.5"
                vectorEffect="non-scaling-stroke"
                strokeDasharray={i === 0 || i === 5 ? '0' : '4 4'}
              />
            ))}
            {/* Vertical grid lines */}
            {Array.from({ length: GRID_COLS + 1 }).map((_, i) => (
              <line
                key={`v-${i}`}
                x1={`${(i / GRID_COLS) * 100}%`} y1="0"
                x2={`${(i / GRID_COLS) * 100}%`} y2="100%"
                stroke="#e2e8f0" strokeWidth="0.5"
                vectorEffect="non-scaling-stroke"
                strokeDasharray="4 4"
              />
            ))}
          </svg>

          {/* SVG Confidence Line + Area Fill */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
            <defs>
              <linearGradient id="confidence-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="rgba(99, 102, 241, 0.25)" />
                <stop offset="100%" stopColor="rgba(99, 102, 241, 0)" />
              </linearGradient>
              <linearGradient id="line-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#6366f1" />
                <stop offset="50%" stopColor="#8b5cf6" />
                <stop offset="100%" stopColor="#6366f1" />
              </linearGradient>
            </defs>
            {fillPath && (
              <polygon fill="url(#confidence-gradient)" points={fillPath} />
            )}
            {linePath && (
              <polyline
                fill="none"
                stroke="url(#line-gradient)"
                strokeWidth="0.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={linePath}
              />
            )}
          </svg>

          {/* Dependency Lines */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
            {visibleNodes.filter(n => n.dependsOn?.length).map((node) => {
              return node.dependsOn?.map((depId) => {
                const dep = visibleNodes.find((n) => n.id === depId);
                if (!dep) return null;
                const x1 = toX(dep.timestampMs);
                const y1 = toY(getConfidence(dep));
                const x2 = toX(node.timestampMs);
                const y2 = toY(getConfidence(node));
                return (
                  <line
                    key={`${depId}-${node.id}`}
                    x1={x1} y1={y1} x2={x2} y2={y2}
                    stroke="#cbd5e1" strokeWidth="0.3"
                    strokeDasharray="2 2"
                    vectorEffect="non-scaling-stroke"
                  />
                );
              });
            })}
          </svg>

          {/* Event Nodes */}
          {visibleNodes.map((node) => {
            const leftPercent = toX(node.timestampMs);
            const conf = getConfidence(node);
            const topPercent = toY(conf);
            const isSelected = selectedNodeId === node.id;
            const StatusIcon = STATUS_CONFIG[node.status].icon;
            const laneColor = LANE_CONFIG[node.laneId]?.color || '#94a3b8';

            return (
              <div
                key={node.id}
                className="absolute -translate-x-1/2 -translate-y-1/2 z-10"
                style={{ left: `${leftPercent}%`, top: `${topPercent}%` }}
              >
                <button
                  onClick={() => onSelectNode(isSelected ? null : node)}
                  className={`flex flex-col items-center gap-1 transition-all duration-200 group focus:outline-none ${
                    isSelected ? 'scale-125 z-20' : 'hover:scale-110'
                  }`}
                  title={`${node.name} — ${STATUS_CONFIG[node.status].label} (${conf}%)`}
                >
                  {/* Node circle */}
                  <div className={`relative flex items-center justify-center text-white shadow-lg transition-transform ${
                    isSelected ? 'w-8 h-8 rounded-xl' : 'w-6 h-6 rounded-lg'
                  } ${node.isMissing ? 'border-2 border-dashed' : ''}`}
                    style={{ 
                      backgroundColor: STATUS_CONFIG[node.status].color,
                      boxShadow: isSelected ? `0 0 16px ${STATUS_CONFIG[node.status].color}60` : undefined,
                    }}
                  >
                    <StatusIcon className={isSelected ? 'w-4 h-4' : 'w-3 h-3'} />
                    {/* Lane indicator dot */}
                    <div
                      className="absolute -bottom-1 -right-1 w-2.5 h-2.5 rounded-full border-2 border-white"
                      style={{ backgroundColor: laneColor }}
                    />
                  </div>
                  {/* Label (on hover or selected) */}
                  <span className={`text-[9px] font-semibold max-w-[60px] truncate text-center transition-opacity ${
                    isSelected ? 'opacity-100 text-[var(--color-text-primary)]' : 'opacity-0 group-hover:opacity-100 text-[var(--color-text-muted)]'
                  }`}>
                    {node.name}
                  </span>
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* X-Axis Time Labels */}
      <div className="flex border-t border-[var(--color-border)] bg-slate-50/50">
        <div className="w-14" />
        <div className="flex-1 flex justify-between px-2 py-2">
          {Array.from({ length: GRID_COLS + 1 }).map((_, i) => {
            const ms = startTime + (totalMs / GRID_COLS) * i;
            return (
              <span key={i} className="text-[10px] font-mono tabular-nums text-[var(--color-text-muted)]">
                {formatTimeLabel(ms)}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ============================================
// Event Details Panel
// ============================================
function EventDetailsPanel({
  node,
  onClose,
}: {
  node: EventNode | null;
  onClose: () => void;
}) {
  void onClose;
  if (!node) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center">
        <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
          <div className="h-8 w-8 rounded-full border-2 border-dashed border-slate-300" />
        </div>
        <p className="text-sm text-[var(--color-text-muted)] max-w-[240px]">
          No event selected. Click a node on the timeline to view full details.
        </p>
      </div>
    );
  }

  const config = STATUS_CONFIG[node.status];
  const StatusIcon = config.icon;
  const laneConfig = LANE_CONFIG[node.laneId];
  const conf = getConfidence(node);
  const confColor = conf >= 80 ? '#10b981' : conf >= 50 ? '#f59e0b' : '#ef4444';

  // Deterministic confidence trend to keep renders pure.
  const confTrend = Array.from({ length: 6 }, (_, i) => Math.max(0, Math.min(100, conf - i * 4)));

  const details = node.details || {};
  const enterpriseCtx = details['enterprise_context'];
  const actorCtx = details['actor_context'];
  const sourceSig = details['source_signature'];
  const normalized = details['normalized_event'];
  const traceId = details['trace_id'];
  const tenantKey = details['tenant_key'];
  const eventPayload = details['event_payload'];
  const logPayload = details['log_payload'];

  const toJson = (v: unknown): string => {
    try {
      return JSON.stringify(v, null, 2);
    } catch {
      return String(v);
    }
  };

  const isScalar = (v: unknown) =>
    v == null || typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean';

  const scalarDetailsEntries = Object.entries(details).filter(([k, v]) => {
    if (k === 'enterprise_context') return false;
    if (k === 'actor_context') return false;
    if (k === 'source_signature') return false;
    if (k === 'normalized_event') return false;
    if (k === 'event_payload') return false;
    if (k === 'log_payload') return false;
    return isScalar(v);
  });

  const whatHappened = (() => {
    const base = `${LANE_CONFIG[node.laneId].label}: ${node.name} is ${STATUS_CONFIG[node.status].label.toLowerCase()}.`;
    const dur = node.durationMs ? ` Duration ${(node.durationMs / 1000).toFixed(1)}s.` : '';
    const step = typeof details['step'] === 'string' ? ` Step: ${details['step']}.` : '';
    const metric = typeof details['metric'] === 'string' ? ` Metric: ${details['metric']}.` : '';
    const value = typeof details['value'] === 'number' ? ` Value: ${details['value']}.` : '';
    const policy = typeof details['policy'] === 'string' ? ` Policy: ${details['policy']}.` : '';
    return `${base}${dur}${step}${metric}${value}${policy}`.trim();
  })();

  const howItHappened = (() => {
    const srcTool =
      typeof sourceSig === 'object' && sourceSig !== null && 'tool_name' in sourceSig && typeof (sourceSig as { tool_name?: unknown }).tool_name === 'string'
        ? String((sourceSig as { tool_name?: unknown }).tool_name)
        : undefined;
    const srcType =
      typeof sourceSig === 'object' && sourceSig !== null && 'tool_type' in sourceSig && typeof (sourceSig as { tool_type?: unknown }).tool_type === 'string'
        ? String((sourceSig as { tool_type?: unknown }).tool_type)
        : undefined;
    const actorRole =
      typeof actorCtx === 'object' && actorCtx !== null && 'role' in actorCtx && typeof (actorCtx as { role?: unknown }).role === 'string'
        ? String((actorCtx as { role?: unknown }).role)
        : undefined;
    const actorTeam =
      typeof actorCtx === 'object' && actorCtx !== null && 'team' in actorCtx && typeof (actorCtx as { team?: unknown }).team === 'string'
        ? String((actorCtx as { team?: unknown }).team)
        : undefined;
    const nType =
      typeof normalized === 'object' && normalized !== null && 'event_type' in normalized && typeof (normalized as { event_type?: unknown }).event_type === 'string'
        ? String((normalized as { event_type?: unknown }).event_type)
        : undefined;
    const parts = [
      srcTool || srcType ? `Source: ${[srcTool, srcType].filter(Boolean).join(' / ')}` : null,
      actorRole || actorTeam ? `Actor: ${[actorRole, actorTeam].filter(Boolean).join(' @ ')}` : null,
      nType ? `Normalized: ${nType}` : null,
    ].filter(Boolean);
    return parts.length ? parts.join(' | ') : 'Source/actor context not available for this event.';
  })();

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-5 space-y-5">
        {/* Enterprise Narrative */}
        <div className="p-4 rounded-xl border border-[var(--color-border)] bg-white">
          <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">What Happened</div>
          <p className="text-sm text-[var(--color-text-primary)]">{whatHappened}</p>
          <div className="mt-3 text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">How It Happened</div>
          <p className="text-xs text-[var(--color-text-secondary)]">{howItHappened}</p>
          {(traceId != null || tenantKey != null) && (
            <div className="mt-3 flex flex-wrap gap-2">
              {traceId != null && (
                <span className="text-[10px] px-2 py-1 rounded-md bg-slate-50 text-slate-700 border border-slate-200">
                  trace_id: <span className="font-mono">{String(traceId)}</span>
                </span>
              )}
              {tenantKey != null && (
                <span className="text-[10px] px-2 py-1 rounded-md bg-slate-50 text-slate-700 border border-slate-200">
                  tenant: <span className="font-mono">{String(tenantKey)}</span>
                </span>
              )}
            </div>
          )}
        </div>

        {/* Header Card */}
        <div className="p-4 rounded-xl border border-[var(--color-border)] bg-gradient-to-br from-slate-50 to-white space-y-4">
          {/* Event Name & ID */}
          <div>
            <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Event</div>
            <div className="mt-0.5 text-base font-semibold text-[var(--color-text-primary)]">{node.name}</div>
            <code className="text-[10px] text-[var(--color-text-muted)]">{node.id}</code>
          </div>

          {/* Status & Lane */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Status</div>
              <span
                className="mt-1 inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold"
                style={{ backgroundColor: `${config.color}15`, color: config.color }}
              >
                <StatusIcon className="w-3 h-3" />
                {config.label}
              </span>
            </div>
            <div>
              <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Lane</div>
              <span
                className="mt-1 inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold"
                style={{ backgroundColor: `${laneConfig.color}15`, color: laneConfig.color }}
              >
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: laneConfig.color }} />
                {laneConfig.label}
              </span>
            </div>
          </div>

          {/* Confidence */}
          <div>
            <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Confidence</div>
            <div className="flex items-center gap-3">
              <DonutChart value={conf} total={100} color={confColor} size={48} strokeWidth={5} />
              <div>
                <div className="text-2xl font-bold tabular-nums" style={{ color: confColor }}>{conf}%</div>
                <Sparkline data={confTrend} color={confColor} width={60} height={20} />
              </div>
            </div>
          </div>

          {/* Timing */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-slate-50 rounded-lg">
              <div className="text-[10px] text-[var(--color-text-muted)]">Timestamp</div>
              <div className="text-xs font-mono font-semibold text-[var(--color-text-primary)] mt-0.5">
                {formatTime(node.timestamp)}
              </div>
            </div>
            {node.durationMs && (
              <div className="p-3 bg-slate-50 rounded-lg">
                <div className="text-[10px] text-[var(--color-text-muted)]">Duration</div>
                <div className="text-xs font-mono font-semibold text-[var(--color-text-primary)] mt-0.5">
                  {node.durationMs >= 1000 ? `${(node.durationMs / 1000).toFixed(1)}s` : `${node.durationMs}ms`}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Details Key-Value */}
        {scalarDetailsEntries.length > 0 && (
          <div className="p-4 rounded-xl border border-[var(--color-border)]">
            <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">Details</div>
            <div className="space-y-2 text-xs">
              {scalarDetailsEntries.map(([key, value]) => (
                <div key={key} className="flex justify-between gap-4 py-1 border-b border-[var(--color-border-light)] last:border-0">
                  <span className="text-[var(--color-text-muted)] flex-shrink-0">{key}</span>
                  <span className="text-[var(--color-text-primary)] text-right font-mono">{String(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Enterprise Context Blocks */}
        {enterpriseCtx != null && (
          <div className="p-4 rounded-xl border border-[var(--color-border)]">
            <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">Enterprise Context</div>
            <pre className="text-[11px] overflow-auto max-h-56 bg-slate-50 rounded-lg p-3 border border-[var(--color-border-light)]">
              {toJson(enterpriseCtx)}
            </pre>
          </div>
        )}
        {actorCtx != null && (
          <div className="p-4 rounded-xl border border-[var(--color-border)]">
            <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">Actor Context</div>
            <pre className="text-[11px] overflow-auto max-h-56 bg-slate-50 rounded-lg p-3 border border-[var(--color-border-light)]">
              {toJson(actorCtx)}
            </pre>
          </div>
        )}
        {sourceSig != null && (
          <div className="p-4 rounded-xl border border-[var(--color-border)]">
            <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">Source Signature</div>
            <pre className="text-[11px] overflow-auto max-h-56 bg-slate-50 rounded-lg p-3 border border-[var(--color-border-light)]">
              {toJson(sourceSig)}
            </pre>
          </div>
        )}
        {normalized != null && (
          <div className="p-4 rounded-xl border border-[var(--color-border)]">
            <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">Normalized Event</div>
            <pre className="text-[11px] overflow-auto max-h-56 bg-slate-50 rounded-lg p-3 border border-[var(--color-border-light)]">
              {toJson(normalized)}
            </pre>
          </div>
        )}
        {(eventPayload != null || logPayload != null) && (
          <div className="p-4 rounded-xl border border-[var(--color-border)]">
            <div className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-3">Raw Payload</div>
            {eventPayload != null && (
              <pre className="text-[11px] overflow-auto max-h-56 bg-slate-50 rounded-lg p-3 border border-[var(--color-border-light)] mb-3">
                {toJson(eventPayload)}
              </pre>
            )}
            {logPayload != null && (
              <pre className="text-[11px] overflow-auto max-h-56 bg-slate-50 rounded-lg p-3 border border-[var(--color-border-light)]">
                {toJson(logPayload)}
              </pre>
            )}
          </div>
        )}

        {/* Error Block */}
        {node.error && (
          <div className="p-4 rounded-xl bg-red-50 border border-red-200">
            <div className="flex items-center gap-2 text-xs font-semibold text-red-700 mb-2">
              <XCircle className="w-3.5 h-3.5" />
              Error — {node.error.code}
            </div>
            <p className="text-xs text-red-600">{node.error.message}</p>
            {node.error.recovery && (
              <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded-lg">
                <span className="text-[10px] font-semibold text-amber-700">Recovery: </span>
                <span className="text-xs text-amber-600">{node.error.recovery}</span>
              </div>
            )}
          </div>
        )}

        {/* Agent Source */}
        {node.agentSource && (
          <div className="p-3 bg-slate-50 rounded-xl">
            <div className="text-[10px] text-[var(--color-text-muted)]">Detected By</div>
            <div className="text-sm font-semibold text-[var(--color-text-primary)] mt-0.5">{node.agentSource}</div>
          </div>
        )}

        {/* Dependencies */}
        {node.dependsOn && node.dependsOn.length > 0 && (
          <div className="p-3 bg-slate-50 rounded-xl">
            <div className="text-[10px] text-[var(--color-text-muted)] mb-1">Depends On</div>
            <div className="flex flex-wrap gap-1">
              {node.dependsOn.map((id) => (
                <code key={id} className="text-[10px] bg-white px-2 py-0.5 rounded-md border border-[var(--color-border)]">{id}</code>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="space-y-2 pt-2">
          <button className="btn btn-primary btn-sm w-full">
            <ExternalLink className="w-3.5 h-3.5" />
            View Evidence Explorer
          </button>
          <button className="btn btn-secondary btn-sm w-full">
            Jump to System Graph
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================
// Legend
// ============================================
function EventGraphLegend() {
  return (
    <div className="flex items-center justify-center gap-5 flex-wrap">
      <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mr-2">Status</span>
      {Object.entries(STATUS_CONFIG).slice(0, 7).map(([status, config]) => {
        const Icon = config.icon;
        return (
          <div key={status} className="flex items-center gap-1.5">
            <div
              className="w-5 h-5 rounded-md flex items-center justify-center text-white"
              style={{ backgroundColor: config.color }}
            >
              <Icon className="w-3 h-3" />
            </div>
            <span className="text-[11px] text-[var(--color-text-muted)]">{config.label}</span>
          </div>
        );
      })}
      <div className="h-4 w-px bg-[var(--color-border)] mx-2" />
      <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mr-2">Lanes</span>
      {Object.entries(LANE_CONFIG).map(([id, config]) => (
        <div key={id} className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full" style={{ backgroundColor: config.color }} />
          <span className="text-[11px] text-[var(--color-text-muted)]">{config.label}</span>
        </div>
      ))}
    </div>
  );
}

// ============================================
// Empty State
// ============================================
function EmptyState({
  workflows,
  onSelectWorkflow,
}: {
  workflows: WorkflowOption[];
  onSelectWorkflow: (id: string) => void;
}) {
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return workflows;
    return workflows.filter((w) => {
      const hay = [
        w.id,
        w.label,
        w.projectName,
        w.environment,
        w.contextTag,
        w.inputSource,
        w.issueCategory,
        w.status,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return hay.includes(q);
    });
  }, [workflows, query]);

  const tableRows = filtered;

  return (
    <div className="flex-1 flex flex-col bg-gradient-to-b from-slate-50 to-white min-h-0">
      <div className="px-6 pt-6 pb-4 border-b border-[var(--color-border)] bg-white/70 backdrop-blur">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-100 to-violet-100 flex items-center justify-center shadow-sm">
              <GitBranch className="w-7 h-7 text-indigo-500" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">Workflows</h2>
              <p className="text-sm text-[var(--color-text-secondary)]">
                Enterprise context is modeled at ingestion: project, environment, ownership, and input origin.
              </p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">
                Input origin examples: GitHub deploy triggers, client-side errors, server failures, code bugs.
              </p>
            </div>
          </div>
          <div className="w-full max-w-sm">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="input w-full"
              placeholder="Search workflow, project, env, source, issue..."
            />
            <div className="mt-2 flex items-center gap-2 text-[11px] text-[var(--color-text-muted)]">
              <span className="badge badge-neutral text-[10px]">{tableRows.length} shown</span>
              <span className="badge badge-info text-[10px]">{workflows.length} total</span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-auto">
        <div className="min-w-[980px] px-6 py-5">
          <div className="rounded-2xl border border-[var(--color-border)] bg-white shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="sticky top-0 z-10 bg-white border-b border-[var(--color-border)]">
                <tr className="text-[11px] uppercase tracking-wider text-[var(--color-text-muted)]">
                  <th className="text-left font-semibold px-4 py-3">Workflow</th>
                  <th className="text-left font-semibold px-4 py-3">Project</th>
                  <th className="text-left font-semibold px-4 py-3">Env</th>
                  <th className="text-left font-semibold px-4 py-3">Context</th>
                  <th className="text-left font-semibold px-4 py-3">Input Origin</th>
                  <th className="text-left font-semibold px-4 py-3">Issue Type</th>
                  <th className="text-left font-semibold px-4 py-3">Status</th>
                  <th className="text-right font-semibold px-4 py-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {tableRows.map((wf) => (
                  <tr
                    key={wf.id}
                    className="border-b border-[var(--color-border-light)] last:border-0 hover:bg-slate-50/70"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className={`w-2.5 h-2.5 rounded-full ${statusDotClass(wf.status)}`} />
                        <div className="min-w-0">
                          <div className="font-semibold text-[var(--color-text-primary)] truncate">{wf.label}</div>
                          <div className="text-[11px] font-mono text-[var(--color-text-muted)] truncate">{wf.id}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-[var(--color-text-primary)] font-medium">{wf.projectName}</div>
                      <div className="text-[11px] font-mono text-[var(--color-text-muted)]">{wf.projectId}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[11px] px-2 py-1 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-100">
                        {wf.environment}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[11px] px-2 py-1 rounded-md bg-amber-50 text-amber-800 border border-amber-100">
                        {formatContextTag(wf.contextTag)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[11px] px-2 py-1 rounded-md bg-slate-50 text-slate-700 border border-slate-200">
                        {formatInputSource(wf.inputSource)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[11px] px-2 py-1 rounded-md bg-rose-50 text-rose-800 border border-rose-100">
                        {formatIssueCategory(wf.issueCategory)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[11px] px-2 py-1 rounded-md bg-slate-100 text-slate-700">
                        {formatChipLabel(wf.status)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => onSelectWorkflow(wf.id)}
                        className="btn btn-primary btn-sm"
                      >
                        View Timeline
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
                {tableRows.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-10 text-center text-sm text-[var(--color-text-muted)]">
                      No workflows match this search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="mt-4 text-xs text-[var(--color-text-muted)] flex items-start gap-2">
            <Zap className="w-4 h-4 text-indigo-500 mt-0.5" />
            <p>
              This table is the primary enterprise view. Selecting a row opens the real-time timeline graph and evidence panel.
              The backend auto-refreshes the list every 15s; the selected workflow timeline refreshes every 10s when live.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================
// Main Page
// ============================================
export default function WorkflowMapPage() {
  const ALL_LANES: Set<EventLaneId> = new Set(['code', 'workflow', 'resource', 'human', 'compliance']);

  const [workflows, setWorkflows] = useState<WorkflowOption[]>([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<EventGraphData | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRangePreset>('15m');
  const [zoom, setZoom] = useState(100);
  const [visibleLanes, setVisibleLanes] = useState<Set<EventLaneId>>(ALL_LANES);
  const [selectedNode, setSelectedNode] = useState<EventNode | null>(null);
  const [showLaneDropdown, setShowLaneDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    let mounted = true;
    const loadWorkflows = async () => {
      try {
        const list = await fetchWorkflows();
        const mapped: WorkflowOption[] = (list || [])
          .map((w) => {
            const id = String((w as unknown as { workflow_id?: string; id?: string }).workflow_id || (w as unknown as { workflow_id?: string; id?: string }).id || '');
            return {
              id,
              label: String(w.name || id),
              projectId: String(w.project_id || 'proj_unknown'),
              projectName: String(w.project_name || 'Unassigned Project'),
              environment: String(w.environment || 'production'),
              contextTag: String(w.context_tag || 'workflow'),
              status: String(w.status || 'unknown'),
              inputSource: String(w.input_source || 'system_internal'),
              issueCategory: String(w.issue_category || 'workflow_anomaly'),
            };
          })
          .filter((w) => Boolean(w.id));
        const normalized = mergeRequiredWorkflows(mapped);
        if (mounted && normalized.length > 0) {
          setWorkflows(normalized);
        }
      } catch {
        // keep previous values
      }
    };

    loadWorkflows();
    const interval = setInterval(loadWorkflows, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  // Auto-refresh every 10s when a workflow is selected and live
  useEffect(() => {
    if (!selectedWorkflowId || !isLive) return;
    const interval = setInterval(async () => {
      try {
        const timeline = await fetchWorkflowTimeline(selectedWorkflowId);
        setGraphData(mapTimelineToGraph(timeline));
      } catch {
        // Silent refresh failure
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [selectedWorkflowId, isLive]);

  // Load graph data from backend when workflow changes
  const selectWorkflow = useCallback(async (id: string) => {
    setSelectedWorkflowId(id);
    setSelectedNode(null);
    setLoading(true);
    
    try {
      const timeline = await fetchWorkflowTimeline(id);
      setGraphData(mapTimelineToGraph(timeline));
      setIsLive(true);
    } catch {
      // Fallback to local mock data
      const mock = generateMockData(id);
      setGraphData(mock);
      setIsLive(false);
    } finally {
      setLoading(false);
    }
  }, []);

  const toggleLane = useCallback((laneId: EventLaneId) => {
    setVisibleLanes((prev) => {
      const next = new Set(prev);
      if (next.has(laneId)) next.delete(laneId);
      else next.add(laneId);
      return next;
    });
  }, []);

  const TIME_PRESETS: { value: TimeRangePreset; label: string }[] = [
    { value: '5m', label: '5m' },
    { value: '15m', label: '15m' },
    { value: '1h', label: '1h' },
    { value: '6h', label: '6h' },
    { value: '24h', label: '24h' },
  ];

  const workflowsByProject = useMemo(() => {
    const grouped: Record<string, WorkflowOption[]> = {};
    for (const wf of workflows) {
      const key = `${wf.projectName} (${wf.environment})`;
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(wf);
    }
    return grouped;
  }, [workflows]);

  return (
    <div className="animate-fade-in flex flex-col" style={{ height: 'calc(100vh - 100px)' }}>
      {/* Page Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <div className="icon-container icon-container-lg bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg">
            <GitBranch className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="page-title">Workflow Event Timeline</h1>
            <p className="page-subtitle">Visualize workflow execution, dependencies, and risk over time</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {loading && <Loader2 className="w-4 h-4 animate-spin text-indigo-500" />}
          {isLive && !loading && (
            <span className="flex items-center gap-1.5 text-xs text-emerald-600 font-medium">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live from backend
            </span>
          )}
          <select
            value={selectedWorkflowId || ''}
            onChange={(e) => e.target.value && selectWorkflow(e.target.value)}
            className="input w-80"
          >
            <option value="">Select Workflow...</option>
            {Object.entries(workflowsByProject).map(([project, projectWorkflows]) => (
              <optgroup key={project} label={project}>
                {projectWorkflows.map((wf) => (
                  <option key={wf.id} value={wf.id}>
                    {wf.id} — {wf.label} [{formatContextTag(wf.contextTag)}]
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
      </div>

      {/* Toolbar — only when workflow selected */}
      {graphData && (
        <div className="flex items-center gap-5 p-3 bg-white rounded-xl border border-[var(--color-border)] mb-4">
          {/* Time Range */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Time</span>
            <div className="flex rounded-lg border border-[var(--color-border)] bg-slate-50 p-0.5">
              {TIME_PRESETS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setTimeRange(p.value)}
                  className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                    timeRange === p.value
                      ? 'bg-white text-[var(--color-text-primary)] shadow-sm border border-[var(--color-border)]'
                      : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Zoom */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Zoom</span>
            <button onClick={() => setZoom(Math.max(50, zoom - 25))} className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors">
              <ZoomOut className="w-4 h-4 text-[var(--color-text-muted)]" />
            </button>
            <input
              type="range"
              min={50}
              max={200}
              step={10}
              value={zoom}
              onChange={(e) => setZoom(Number(e.target.value))}
              className="w-24 accent-[var(--color-primary)]"
            />
            <button onClick={() => setZoom(Math.min(200, zoom + 25))} className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors">
              <ZoomIn className="w-4 h-4 text-[var(--color-text-muted)]" />
            </button>
            <span className="text-xs font-mono tabular-nums text-[var(--color-text-muted)] w-8 text-right">{zoom}%</span>
          </div>

          {/* Lane Toggles */}
          <div className="relative">
            <button
              onClick={() => setShowLaneDropdown(!showLaneDropdown)}
              className="btn btn-secondary btn-sm"
            >
              <Layers className="w-4 h-4" />
              Lanes
              <ChevronDown className={`w-3 h-3 transition-transform ${showLaneDropdown ? 'rotate-180' : ''}`} />
            </button>
            {showLaneDropdown && (
              <div className="absolute top-full left-0 mt-1 w-48 bg-white rounded-xl border border-[var(--color-border)] shadow-lg z-50 p-2">
                {Object.entries(LANE_CONFIG).map(([id, config]) => (
                  <label
                    key={id}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-50 cursor-pointer text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={visibleLanes.has(id as EventLaneId)}
                      onChange={() => toggleLane(id as EventLaneId)}
                      className="accent-[var(--color-primary)]"
                    />
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: config.color }} />
                    <span className="text-[var(--color-text-primary)]">{config.label}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Separator */}
          <div className="h-6 w-px bg-[var(--color-border)]" />

          {/* Filter Badges */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-[var(--color-text-muted)]" />
            <span className="badge badge-neutral text-[10px]">
              {graphData.nodes.length} events
            </span>
            <span className="badge badge-info text-[10px]">
              {visibleLanes.size} / {Object.keys(LANE_CONFIG).length} lanes
            </span>
          </div>

          {/* Export */}
          <div className="ml-auto">
            <button className="btn btn-secondary btn-sm">
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex rounded-2xl border border-[var(--color-border)] bg-white overflow-hidden shadow-sm min-h-0">
        {!graphData ? (
          <EmptyState workflows={workflows} onSelectWorkflow={selectWorkflow} />
        ) : (
          <>
            {/* Chart area */}
            <div className="flex-1 flex flex-col overflow-hidden min-w-0">
              <div className="flex-1 overflow-auto">
                <TimelineCanvas
                  data={graphData}
                  zoom={zoom}
                  selectedNodeId={selectedNode?.id ?? null}
                  onSelectNode={setSelectedNode}
                  visibleLanes={visibleLanes}
                />
              </div>
              {/* Legend */}
              <div className="border-t border-[var(--color-border)] bg-slate-50/50 px-5 py-3">
                <EventGraphLegend />
              </div>
            </div>

            {/* Right: Details Panel */}
            <aside className="hidden lg:block w-[380px] shrink-0 border-l border-[var(--color-border)] bg-white">
              <div className="sticky top-0 z-10 border-b border-[var(--color-border)] bg-gradient-to-r from-slate-50 to-white px-5 py-4 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">Event Details</h3>
                  <p className="text-[11px] text-[var(--color-text-muted)]">
                    Click a node on the timeline
                  </p>
                </div>
                {selectedNode && (
                  <button onClick={() => setSelectedNode(null)} className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors">
                    <X className="w-4 h-4 text-[var(--color-text-muted)]" />
                  </button>
                )}
              </div>
              <div style={{ height: 'calc(100% - 72px)' }}>
                <EventDetailsPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
              </div>
            </aside>
          </>
        )}
      </div>

      {/* Summary Bar (when data loaded) */}
      {graphData && graphData.outcomeSummary && (
        <div className="mt-4 p-4 bg-gradient-to-r from-amber-50 via-orange-50 to-yellow-50 rounded-xl border border-amber-200">
          <div className="flex items-start gap-3">
            <div className="icon-container icon-container-sm bg-amber-100 flex-shrink-0">
              <Info className="w-4 h-4 text-amber-600" />
            </div>
            <div>
              <div className="text-xs font-semibold text-amber-800 mb-0.5">Outcome Summary</div>
              <p className="text-sm text-amber-700">{graphData.outcomeSummary}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
