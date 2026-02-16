'use client';

import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Zap,
  AlertTriangle,
  Filter,
  X,
  Clock,
  Sparkles,
  Info,
  FileText,
  GitMerge,
  Activity,
} from 'lucide-react';
import { fetchAnomalies, type Anomaly } from '@/lib/api';
import { formatTime, formatDateTime } from '@/lib/utils';
import { DonutChart, BarChart, Sparkline } from '@/components/Charts';

// Confidence Bar Component
function ConfidenceBar({ confidence }: { confidence: number }) {
  const color = confidence > 80 ? '#10b981' : confidence > 60 ? '#f59e0b' : '#ef4444';

  return (
    <div className="flex items-center gap-3">
      <div className="w-20 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${confidence}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-sm font-semibold" style={{ color }}>
        {confidence}%
      </span>
    </div>
  );
}

// Severity Config
const severityConfig: Record<string, { color: string; bg: string; border: string }> = {
  critical: { color: '#ef4444', bg: 'bg-red-50', border: 'border-red-200' },
  high: { color: '#f97316', bg: 'bg-orange-50', border: 'border-orange-200' },
  medium: { color: '#f59e0b', bg: 'bg-amber-50', border: 'border-amber-200' },
  low: { color: '#3b82f6', bg: 'bg-blue-50', border: 'border-blue-200' },
};

function displayAnomalyType(type: string): string {
  const map: Record<string, string> = {
    SEQUENCE_VIOLATION: 'Workflow Order Deviation',
    MISSING_STEP: 'Missing Workflow Step',
    WORKFLOW_DELAY: 'Workflow Delay',
    SUSTAINED_RESOURCE_CRITICAL: 'Sustained Resource Critical',
    SUSTAINED_RESOURCE_WARNING: 'Sustained Resource Warning',
    BASELINE_DEVIATION: 'Baseline Deviation',
  };
  return map[type] || type.replace(/_/g, ' ');
}

function displayAnomalySummary(anomaly: Anomaly): string {
  if (anomaly.type === 'SEQUENCE_VIOLATION') {
    return 'Workflow steps executed in an unexpected order. This can skip required checks and increase failure/compliance risk.';
  }
  if (anomaly.type === 'WORKFLOW_DELAY') {
    return 'Workflow execution exceeded expected duration and may affect SLA commitments.';
  }
  if (anomaly.type === 'SUSTAINED_RESOURCE_CRITICAL') {
    return 'Resource usage stayed above critical threshold for a sustained window.';
  }
  return anomaly.details;
}

function detectionMethod(anomaly: Anomaly): string {
  switch (anomaly.type) {
    case 'SEQUENCE_VIOLATION':
      return 'WorkflowAgent compared observed step order against expected workflow definition and flagged an out-of-order transition.';
    case 'MISSING_STEP':
      return 'WorkflowAgent validated required workflow checkpoints and detected that a mandatory step was not executed.';
    case 'WORKFLOW_DELAY':
      return 'WorkflowAgent measured step duration against SLA targets and detected sustained overrun.';
    case 'SUSTAINED_RESOURCE_CRITICAL':
      return 'ResourceAgent evaluated consecutive resource samples and detected sustained threshold breach (not a transient spike).';
    case 'SUSTAINED_RESOURCE_WARNING':
      return 'ResourceAgent detected repeated warning-level utilization/latency above configured limits.';
    case 'BASELINE_DEVIATION':
      return 'AdaptiveBaselineAgent compared current signal window against learned baseline and detected statistically significant deviation.';
    default:
      return `${anomaly.agent} applied configured anomaly rules and confidence checks to detect this signal.`;
  }
}

function detectedScope(anomaly: Anomaly): string {
  if (anomaly.evidence_ids && anomaly.evidence_ids.length > 0) {
    return `Detected anomaly scope is linked to ${anomaly.evidence_ids.length} evidence item(s): ${anomaly.evidence_ids.slice(0, 3).join(', ')}${anomaly.evidence_ids.length > 3 ? ', ...' : ''}.`;
  }
  return 'Detected anomaly scope is currently limited to the anomaly record; no linked evidence IDs were provided yet.';
}

// Evidence Detail View
function EvidenceDetailView({
  anomaly,
  onClose,
  viewMode,
  onViewMode,
  onNavigate,
}: {
  anomaly: Anomaly;
  onClose: () => void;
  viewMode: 'detail' | 'evidence';
  onViewMode: (m: 'detail' | 'evidence') => void;
  onNavigate: (path: string) => void;
}) {
  const config = severityConfig[anomaly.severity] || severityConfig.low;

  // Rich mock evidence data based on anomaly
  const evidenceTimeline = [
    { time: '-5m', event: 'Baseline state observed', value: 'System signals were within normal operating range.', status: 'normal' as const },
    { time: '-3m', event: 'Deviation observed', value: 'One or more signals moved away from baseline trend.', status: 'warning' as const },
    { time: '-2m', event: 'Rule threshold crossed', value: `Detection threshold crossed at ${anomaly.confidence}% confidence.`, status: 'critical' as const },
    { time: '-1m', event: `${anomaly.agent} raised anomaly`, value: displayAnomalyType(anomaly.type), status: 'critical' as const },
    { time: 'Now', event: 'Evidence correlated', value: `${anomaly.evidence_ids?.length || 0} evidence item(s) linked for investigation.`, status: 'info' as const },
  ];

  const statusColors = {
    normal: '#10b981',
    warning: '#f59e0b',
    critical: '#ef4444',
    info: '#6366f1',
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50" onClick={onClose} />
      <div className="fixed inset-y-0 right-0 w-[600px] bg-white shadow-2xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between bg-gradient-to-r from-slate-50 to-white flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shadow-md" style={{ backgroundColor: config.color }}>
              <FileText className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-lg text-[var(--color-text-primary)]">
                {viewMode === 'detail' ? 'Anomaly Details' : 'Evidence Chain'}
              </h2>
              <p className="text-xs text-[var(--color-text-muted)]">{anomaly.anomaly_id} · {displayAnomalyType(anomaly.type)}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-slate-100 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="px-5 pt-4 pb-3 border-b border-[var(--color-border)] flex items-center gap-2 bg-white flex-shrink-0">
          <button
            className={`px-3 py-1.5 rounded-xl text-sm font-semibold border transition-colors ${
              viewMode === 'detail'
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-white text-[var(--color-text-primary)] border-[var(--color-border)] hover:bg-slate-50'
            }`}
            onClick={() => onViewMode('detail')}
          >
            Details
          </button>
          <button
            className={`px-3 py-1.5 rounded-xl text-sm font-semibold border transition-colors ${
              viewMode === 'evidence'
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-white text-[var(--color-text-primary)] border-[var(--color-border)] hover:bg-slate-50'
            }`}
            onClick={() => onViewMode('evidence')}
          >
            Evidence
          </button>
          <div className="ml-auto flex items-center gap-2">
            <button className="btn btn-secondary btn-sm" onClick={() => onNavigate('/causal-analysis')}>
              <GitMerge className="w-4 h-4" />
              Causal
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {viewMode === 'detail' && (
            <>
              {/* Status Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl border border-[var(--color-border)]">
                  <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Severity</div>
                  <span
                    className="px-3 py-1.5 rounded-full text-sm font-semibold"
                    style={{ backgroundColor: `${config.color}15`, color: config.color }}
                  >
                    {anomaly.severity.toUpperCase()}
                  </span>
                </div>
                <div className="p-4 rounded-xl border border-[var(--color-border)]">
                  <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Confidence</div>
                  <div className="flex items-center gap-2">
                    <DonutChart value={anomaly.confidence} total={100} color={config.color} size={40} strokeWidth={4} />
                    <span className="text-lg font-bold" style={{ color: config.color }}>
                      {anomaly.confidence}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Trend */}
              <div className="p-4 rounded-xl border border-[var(--color-border)]">
                <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-3">Related Trend</div>
                <Sparkline
                  data={Array.from({ length: 10 }, (_, i) =>
                    Math.max(0, Math.min(100, anomaly.confidence - 10 + i * 2 + (i % 2 ? -1 : 2)))
                  )}
                  color={config.color}
                  width={520}
                  height={56}
                />
              </div>

              {/* Details */}
              <div>
                <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Details</div>
                <p className="text-sm text-[var(--color-text-primary)] leading-relaxed p-4 bg-slate-50 rounded-xl">
                  {displayAnomalySummary(anomaly)}
                </p>
              </div>

              {/* Metadata */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-[var(--color-surface-tertiary)] rounded-xl">
                  <div className="text-xs text-[var(--color-text-muted)] mb-1">Agent</div>
                  <div className="text-sm font-semibold text-[var(--color-text-primary)]">{anomaly.agent}</div>
                </div>
                <div className="p-3 bg-[var(--color-surface-tertiary)] rounded-xl">
                  <div className="text-xs text-[var(--color-text-muted)] mb-1">Detected</div>
                  <div className="text-sm font-semibold text-[var(--color-text-primary)]">{formatDateTime(anomaly.timestamp)}</div>
                </div>
              </div>

              {/* Evidence */}
              {anomaly.evidence_ids && anomaly.evidence_ids.length > 0 && (
                <div>
                  <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Evidence</div>
                  <div className="flex flex-wrap gap-2">
                    {anomaly.evidence_ids.map((id) => (
                      <code key={id} className="text-xs bg-slate-100 px-3 py-1.5 rounded-lg">{id}</code>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {viewMode === 'evidence' && (
            <>
          {/* Evidence Summary Card */}
          <div className="p-4 rounded-xl border border-[var(--color-border)] bg-gradient-to-r from-slate-50 to-white">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider font-semibold">Evidence Summary</span>
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full" style={{ backgroundColor: `${config.color}15`, color: config.color }}>
                {anomaly.evidence_ids?.length || 0} items
              </span>
            </div>
            <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">{displayAnomalySummary(anomaly)}</p>
          </div>

          {/* Evidence IDs */}
          {anomaly.evidence_ids && anomaly.evidence_ids.length > 0 && (
            <div>
              <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-3 font-semibold">Linked Evidence</div>
              <div className="space-y-2">
                {anomaly.evidence_ids.map((id) => (
                  <div key={id} className="flex items-center gap-3 p-3 rounded-xl border border-[var(--color-border)] hover:border-indigo-200 hover:shadow-sm transition-all cursor-pointer">
                    <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                      <FileText className="w-4 h-4 text-indigo-600" />
                    </div>
                    <div className="flex-1">
                      <code className="text-sm font-bold text-[var(--color-primary)]">{id}</code>
                      <p className="text-xs text-[var(--color-text-muted)]">
                        {id.startsWith('evt_') ? 'System Event' : id.startsWith('metric_') ? 'Resource Metric' : 'Anomaly Detection'}
                      </p>
                    </div>
                    <span className="text-[10px] bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full font-semibold">
                      {id.startsWith('evt_') ? 'EVENT' : id.startsWith('metric_') ? 'METRIC' : 'ANOM'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Evidence Timeline */}
          <div>
            <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-3 font-semibold">Detection Timeline</div>
            <div className="space-y-0">
              {evidenceTimeline.map((item, i) => (
                <div key={i} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <div className="w-3 h-3 rounded-full border-2" style={{ borderColor: statusColors[item.status], backgroundColor: i === evidenceTimeline.length - 1 ? statusColors[item.status] : 'white' }} />
                    {i < evidenceTimeline.length - 1 && <div className="w-0.5 h-12 bg-slate-200" />}
                  </div>
                  <div className="pb-4 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-[var(--color-text-muted)]">{item.time}</span>
                      <span className="text-sm font-semibold text-[var(--color-text-primary)]">{item.event}</span>
                    </div>
                    <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{item.value}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* What This Means */}
          <div className="p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-tertiary)]">
            <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-2 font-semibold">What This Means</div>
            <p className="text-sm text-[var(--color-text-primary)] mb-2 leading-relaxed">
              This anomaly is a verified warning that normal system behavior was broken in a way that can affect uptime, SLA commitments, and audit traceability.
            </p>
            <ul className="text-sm text-[var(--color-text-secondary)] list-disc pl-5 space-y-2">
              <li>Start from the first linked evidence ID and confirm the exact first failure point (step, service, or resource).</li>
              <li>Check timeline order: verify whether customer impact, SLA delay, or policy risk started after this anomaly trigger.</li>
              <li>Validate blast radius before action: identify which workflows/services are impacted vs unaffected.</li>
              <li>Apply mitigation only after evidence validation, then re-check next cycle to confirm recovery and avoid false closure.</li>
            </ul>
          </div>

          {/* Agent Detection Summary */}
          <div>
            <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-3 font-semibold">Agent Detection Summary</div>
            <div className="space-y-3">
              <div className="p-3 rounded-xl border border-[var(--color-border)] bg-white">
                <div className="text-xs text-[var(--color-text-muted)] mb-1">Detected By</div>
                <div className="text-sm font-semibold text-[var(--color-text-primary)]">{anomaly.agent}</div>
              </div>
              <div className="p-3 rounded-xl border border-[var(--color-border)] bg-white">
                <div className="text-xs text-[var(--color-text-muted)] mb-1">How It Was Detected</div>
                <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">{detectionMethod(anomaly)}</p>
              </div>
              <div className="p-3 rounded-xl border border-[var(--color-border)] bg-white">
                <div className="text-xs text-[var(--color-text-muted)] mb-1">What Was Detected</div>
                <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">
                  {displayAnomalyType(anomaly.type)} with {anomaly.confidence}% confidence. {detectedScope(anomaly)}
                </p>
              </div>
              <div className="p-3 rounded-xl border border-[var(--color-border)] bg-white">
                <div className="text-xs text-[var(--color-text-muted)] mb-1">Operator Next Step</div>
                <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">
                  Open Evidence IDs, validate first failure cause, confirm impact timeline, then execute mitigation and verify in the next reasoning cycle.
                </p>
              </div>
            </div>
          </div>

          {/* Detection Agent */}
          <div className="p-4 bg-[var(--color-surface-tertiary)] rounded-xl">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center shadow-md">
                <Activity className="w-5 h-5 text-white" />
              </div>
              <div>
                <div className="text-xs text-[var(--color-text-muted)]">Detected By</div>
                <div className="text-sm font-semibold text-[var(--color-text-primary)]">{anomaly.agent}</div>
              </div>
              <div className="ml-auto text-right">
                <div className="text-xs text-[var(--color-text-muted)]">Detected At</div>
                <div className="text-sm font-semibold text-[var(--color-text-primary)]">{formatDateTime(anomaly.timestamp)}</div>
              </div>
            </div>
          </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}

export default function AnomalyCenterPage() {
  const router = useRouter();
  const [selectedAnomaly, setSelectedAnomaly] = useState<Anomaly | null>(null);
  const [viewMode, setViewMode] = useState<'detail' | 'evidence'>('detail');
  const [filterAgent, setFilterAgent] = useState<string>('all');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterText, setFilterText] = useState<string>('');

  const { data: anomalies } = useQuery({
    queryKey: ['anomalies'],
    queryFn: fetchAnomalies,
    refetchInterval: 10000,
  });

  const displayAnomalies = useMemo(() => anomalies || [], [anomalies]);

  // Filter anomalies
  const filteredAnomalies = useMemo(() => {
    const q = (filterText || '').trim().toLowerCase();
    return displayAnomalies.filter((a) => {
      if (filterAgent !== 'all' && a.agent !== filterAgent) return false;
      if (filterSeverity !== 'all' && a.severity !== filterSeverity) return false;
      if (!q) return true;
      const hay = [
        a.anomaly_id,
        a.type,
        displayAnomalyType(a.type),
        a.details,
        a.agent,
        ...(a.evidence_ids || []),
      ]
        .join(' ')
        .toLowerCase();
      return hay.includes(q);
    });
  }, [displayAnomalies, filterAgent, filterSeverity, filterText]);

  // Stats
  const stats = {
    total: displayAnomalies.length,
    critical: displayAnomalies.filter((a) => a.severity === 'critical').length,
    high: displayAnomalies.filter((a) => a.severity === 'high').length,
    medium: displayAnomalies.filter((a) => a.severity === 'medium').length,
    low: displayAnomalies.filter((a) => a.severity === 'low').length,
  };

  // Severity distribution for chart
  const severityData = [stats.critical, stats.high, stats.medium, stats.low];

  // Get unique agents
  const agents = [...new Set(displayAnomalies.map((a) => a.agent))];

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="icon-container icon-container-lg bg-gradient-to-br from-amber-500 to-orange-600 shadow-lg">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="page-title">Anomaly Center</h1>
            <p className="page-subtitle">Central hub for all detected anomalies across the system</p>
          </div>
        </div>
      </div>

      {/* About */}
      <div className="card p-5 bg-gradient-to-r from-slate-50 to-white border border-[var(--color-border)]">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center flex-shrink-0">
            <Info className="w-5 h-5 text-indigo-700" />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold text-[var(--color-text-primary)] mb-1">About Anomaly Detection</div>
            <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
              Anomalies are detected by specialized agents: ResourceAgent monitors infrastructure metrics, WorkflowAgent tracks workflow execution patterns,
              and ComplianceAgent validates policy adherence. Each anomaly includes confidence scores and evidence links for full traceability.
            </p>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-5 gap-4">
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Total Anomalies</div>
              <div className="stats-value">{stats.total}</div>
            </div>
            <div className="icon-container icon-container-md bg-slate-100">
              <Sparkles className="w-5 h-5 text-slate-600" />
            </div>
          </div>
        </div>
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Critical</div>
              <div className="stats-value text-red-500">{stats.critical}</div>
            </div>
            <DonutChart value={stats.critical} total={stats.total || 1} color="#ef4444" size={40} strokeWidth={4} />
          </div>
        </div>
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">High</div>
              <div className="stats-value text-orange-500">{stats.high}</div>
            </div>
            <DonutChart value={stats.high} total={stats.total || 1} color="#f97316" size={40} strokeWidth={4} />
          </div>
        </div>
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Medium</div>
              <div className="stats-value text-amber-500">{stats.medium}</div>
            </div>
            <DonutChart value={stats.medium} total={stats.total || 1} color="#f59e0b" size={40} strokeWidth={4} />
          </div>
        </div>
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Low</div>
              <div className="stats-value text-blue-500">{stats.low}</div>
            </div>
            <DonutChart value={stats.low} total={stats.total || 1} color="#3b82f6" size={40} strokeWidth={4} />
          </div>
        </div>
      </div>

      {/* Log View */}
      <div className="card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-[var(--color-text-muted)]" />
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">Anomaly Log</h2>
            <span className="text-sm text-[var(--color-text-muted)]">({filteredAnomalies.length})</span>
          </div>
          <div className="text-xs text-[var(--color-text-muted)] flex items-center gap-2">
            <Clock className="w-3 h-3" />
            Auto-refresh every 10s
          </div>
        </div>

        {/* Filter bar */}
        <div className="mt-4 grid grid-cols-12 gap-3">
          <div className="col-span-12 md:col-span-4">
            <label className="block text-xs font-semibold text-[var(--color-text-muted)] mb-2 uppercase tracking-wider">Search</label>
            <input
              className="input input-bordered w-full"
              placeholder="type, id, agent, evidence id..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
            />
          </div>
          <div className="col-span-6 md:col-span-4">
            <label className="block text-xs font-semibold text-[var(--color-text-muted)] mb-2 uppercase tracking-wider">Agent</label>
            <select className="input w-full" value={filterAgent} onChange={(e) => setFilterAgent(e.target.value)}>
              <option value="all">All Agents</option>
              {agents.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </div>
          <div className="col-span-6 md:col-span-3">
            <label className="block text-xs font-semibold text-[var(--color-text-muted)] mb-2 uppercase tracking-wider">Severity</label>
            <select className="input w-full" value={filterSeverity} onChange={(e) => setFilterSeverity(e.target.value)}>
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <div className="col-span-12 md:col-span-1 flex items-end">
            {(filterAgent !== 'all' || filterSeverity !== 'all' || filterText.trim()) && (
              <button
                className="btn btn-ghost btn-sm w-full"
                onClick={() => {
                  setFilterAgent('all');
                  setFilterSeverity('all');
                  setFilterText('');
                }}
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Table */}
        <div className="mt-5 table-container">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px]">
              <thead className="table-header">
              <tr>
                <th className="w-[150px]">Time</th>
                <th className="w-[140px]">Severity</th>
                <th>Type</th>
                <th className="w-[160px]">Agent</th>
                <th className="w-[170px]">Confidence</th>
                <th className="w-[140px]">Evidence</th>
              </tr>
              </thead>
              <tbody className="table-body">
                {filteredAnomalies.map((a) => {
                  const cfg = severityConfig[a.severity] || severityConfig.low;
                  const isSelected = selectedAnomaly?.anomaly_id === a.anomaly_id;
                  return (
                    <tr
                      key={a.anomaly_id}
                      className={`cursor-pointer ${isSelected ? 'bg-indigo-50' : ''}`}
                      onClick={() => {
                        setSelectedAnomaly(a);
                        setViewMode('detail');
                      }}
                    >
                      <td className="whitespace-nowrap text-xs font-mono text-[var(--color-text-muted)]">
                        {formatTime(a.timestamp)}
                      </td>
                      <td className="whitespace-nowrap">
                        <span
                          className="px-2.5 py-1 text-xs font-semibold rounded-full"
                          style={{ backgroundColor: `${cfg.color}20`, color: cfg.color }}
                        >
                          {a.severity.toUpperCase()}
                        </span>
                      </td>
                      <td className="min-w-[360px]">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4" style={{ color: cfg.color }} />
                          <div className="min-w-0">
                            <div className="text-sm font-semibold text-[var(--color-text-primary)]">{displayAnomalyType(a.type)}</div>
                            <div className="text-xs text-[var(--color-text-muted)] line-clamp-1">{displayAnomalySummary(a)}</div>
                          </div>
                        </div>
                      </td>
                      <td className="whitespace-nowrap">
                        <span className="badge badge-neutral text-xs">{a.agent}</span>
                      </td>
                      <td className="whitespace-nowrap">
                        <ConfidenceBar confidence={a.confidence} />
                      </td>
                      <td className="whitespace-nowrap text-xs text-[var(--color-text-muted)]">
                        {a.evidence_ids?.length ? `${a.evidence_ids.length} item(s)` : 'none'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {filteredAnomalies.length === 0 && (
          <div className="mt-5 text-center py-12 bg-slate-50 rounded-xl border border-dashed border-slate-200">
            <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-8 h-8 text-slate-400" />
            </div>
            <p className="text-[var(--color-text-muted)]">No anomalies match your filters</p>
          </div>
        )}

        {/* Severity Distribution (small, below table) */}
        <div className="mt-6 p-4 rounded-xl border border-[var(--color-border)]">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-semibold text-[var(--color-text-primary)]">Severity Distribution</div>
            <div className="text-xs text-[var(--color-text-muted)]">Current window</div>
          </div>
          <BarChart
            data={severityData}
            colors={['#ef4444', '#f97316', '#f59e0b', '#3b82f6']}
            height={170}
            showGrid={false}
            barRadius={6}
            animated={true}
            xLabels={['Critical', 'High', 'Medium', 'Low']}
            xAxisLabel="Severity Level"
            yAxisLabel="Anomaly Count"
            yFormatter={(v) => `${Math.round(v)}`}
          />
        </div>
      </div>

      {/* Right Drawer */}
      {selectedAnomaly && (
        <EvidenceDetailView
          anomaly={selectedAnomaly}
          viewMode={viewMode}
          onViewMode={setViewMode}
          onNavigate={(path) => { setSelectedAnomaly(null); router.push(path); }}
          onClose={() => { setSelectedAnomaly(null); setViewMode('detail'); }}
        />
      )}
    </div>
  );
}
