'use client';

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Zap,
  AlertTriangle,
  Filter,
  X,
  ExternalLink,
  Clock,
  ChevronRight,
  Sparkles,
  Info,
  FileText,
  GitMerge,
  Activity,
  Network,
  ArrowRight,
  CheckCircle,
  Shield,
  TrendingUp,
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

// Anomaly Card
function AnomalyCard({
  anomaly,
  onClick,
}: {
  anomaly: Anomaly;
  onClick: () => void;
}) {
  const config = severityConfig[anomaly.severity] || severityConfig.low;

  return (
    <div
      className={`p-5 rounded-xl border transition-all cursor-pointer group hover:shadow-lg ${config.bg} ${config.border}`}
      onClick={onClick}
    >
      <div className="flex items-start gap-4">
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 shadow-md"
          style={{ backgroundColor: config.color }}
        >
          <AlertTriangle className="w-6 h-6 text-white" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span
              className="px-2.5 py-1 text-xs font-semibold rounded-full"
              style={{ backgroundColor: `${config.color}20`, color: config.color }}
            >
              {anomaly.severity.toUpperCase()}
            </span>
            <span className="text-xs text-[var(--color-text-muted)] flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatTime(anomaly.timestamp)}
            </span>
          </div>

          <h3 className="font-semibold text-[var(--color-text-primary)] mb-1 group-hover:text-[var(--color-primary)] transition-colors">
            {anomaly.type.replace(/_/g, ' ')}
          </h3>

          <p className="text-sm text-[var(--color-text-secondary)] line-clamp-2 mb-3">
            {anomaly.details}
          </p>

          <div className="flex items-center justify-between">
            <ConfidenceBar confidence={anomaly.confidence} />
            <span className="badge badge-neutral text-xs">{anomaly.agent}</span>
          </div>
        </div>

        <ChevronRight className="w-5 h-5 text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </div>
  );
}

// Evidence Detail View
function EvidenceDetailView({
  anomaly,
  onClose,
  onBack,
}: {
  anomaly: Anomaly;
  onClose: () => void;
  onBack: () => void;
}) {
  const config = severityConfig[anomaly.severity] || severityConfig.low;

  // Rich mock evidence data based on anomaly
  const evidenceTimeline = [
    { time: '-5m', event: 'Baseline metric recorded', value: 'Normal range', status: 'normal' as const },
    { time: '-3m', event: 'Metric deviation detected', value: `+1.5σ above baseline`, status: 'warning' as const },
    { time: '-2m', event: 'Threshold breach triggered', value: `Exceeded ${anomaly.confidence}% confidence`, status: 'critical' as const },
    { time: '-1m', event: `${anomaly.agent} flagged anomaly`, value: anomaly.type.replace(/_/g, ' '), status: 'critical' as const },
    { time: 'Now', event: 'Anomaly confirmed & correlated', value: `Linked to ${anomaly.evidence_ids?.length || 0} evidence items`, status: 'info' as const },
  ];

  const relatedMetrics = [
    { name: 'CPU Utilization', value: 96, unit: '%', trend: [45, 52, 61, 78, 85, 92, 96], status: 'critical' },
    { name: 'Memory Usage', value: 78, unit: '%', trend: [55, 58, 62, 65, 70, 74, 78], status: 'warning' },
    { name: 'Network Latency', value: 420, unit: 'ms', trend: [80, 95, 150, 220, 310, 380, 420], status: 'critical' },
    { name: 'Error Rate', value: 12.5, unit: '%', trend: [0.5, 1, 2, 4, 7, 10, 12.5], status: 'warning' },
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
            <button onClick={onBack} className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors">
              <ChevronRight className="w-4 h-4 rotate-180" />
            </button>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shadow-md" style={{ backgroundColor: config.color }}>
              <FileText className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-lg text-[var(--color-text-primary)]">Evidence Chain</h2>
              <p className="text-xs text-[var(--color-text-muted)]">{anomaly.anomaly_id} · {anomaly.type.replace(/_/g, ' ')}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-slate-100 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Evidence Summary Card */}
          <div className="p-4 rounded-xl border border-[var(--color-border)] bg-gradient-to-r from-slate-50 to-white">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider font-semibold">Evidence Summary</span>
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full" style={{ backgroundColor: `${config.color}15`, color: config.color }}>
                {anomaly.evidence_ids?.length || 0} items
              </span>
            </div>
            <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">{anomaly.details}</p>
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

          {/* Related Metrics */}
          <div>
            <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-3 font-semibold">Correlated Metrics</div>
            <div className="grid grid-cols-2 gap-3">
              {relatedMetrics.map((m) => (
                <div key={m.name} className="p-3 rounded-xl border border-[var(--color-border)]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-[var(--color-text-muted)]">{m.name}</span>
                    <span className={`text-xs font-bold ${m.status === 'critical' ? 'text-red-500' : 'text-amber-500'}`}>
                      {m.value}{m.unit}
                    </span>
                  </div>
                  <Sparkline data={m.trend} color={m.status === 'critical' ? '#ef4444' : '#f59e0b'} width={120} height={24} />
                </div>
              ))}
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
        </div>
      </div>
    </>
  );
}

// Anomaly Detail Modal
function AnomalyDetailModal({
  anomaly,
  onClose,
  onViewEvidence,
  onNavigate,
}: {
  anomaly: Anomaly;
  onClose: () => void;
  onViewEvidence: () => void;
  onNavigate: (path: string) => void;
}) {
  const config = severityConfig[anomaly.severity] || severityConfig.low;

  // Deterministic trend data (render-safe, no random in component body)
  const base = Math.max(20, Math.min(90, Math.round(anomaly.confidence * 100)));
  const trendData = Array.from({ length: 8 }, (_, i) =>
    Math.max(0, Math.min(100, base - 10 + i * 2 + (i % 2 === 0 ? 3 : -2)))
  );

  return (
    <>
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
        <div
          className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-hidden animate-scale-in"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between bg-gradient-to-r from-slate-50 to-white">
            <div className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center shadow-md"
                style={{ backgroundColor: config.color }}
              >
                <AlertTriangle className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="font-semibold text-lg text-[var(--color-text-primary)]">
                  {anomaly.type.replace(/_/g, ' ')}
                </h2>
                <p className="text-sm text-[var(--color-text-muted)]">Anomaly Details</p>
              </div>
            </div>
            <button onClick={onClose} className="p-2 rounded-xl hover:bg-slate-100 transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-5 space-y-5 overflow-y-auto max-h-[calc(90vh-140px)]">
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
                  <DonutChart
                    value={anomaly.confidence}
                    total={100}
                    color={config.color}
                    size={40}
                    strokeWidth={4}
                  />
                  <span className="text-lg font-bold" style={{ color: config.color }}>
                    {anomaly.confidence}%
                  </span>
                </div>
              </div>
            </div>

            {/* Trend */}
            <div className="p-4 rounded-xl border border-[var(--color-border)]">
              <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-3">
                Related Metric Trend
              </div>
              <Sparkline data={trendData} color={config.color} width={320} height={48} />
            </div>

            {/* Details */}
            <div>
              <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Details</div>
              <p className="text-sm text-[var(--color-text-primary)] leading-relaxed p-4 bg-slate-50 rounded-xl">
                {anomaly.details}
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

            {/* Actions */}
            <div className="pt-4 border-t border-[var(--color-border)] space-y-3">
              <button className="btn btn-primary w-full" onClick={() => onNavigate('/causal-analysis')}>
                <GitMerge className="w-4 h-4" />
                View Causal Analysis
              </button>
              <button className="btn btn-secondary w-full" onClick={onViewEvidence}>
                <FileText className="w-4 h-4" />
                View Evidence Chain
              </button>
              <button className="btn btn-secondary w-full" onClick={() => onNavigate('/system-graph')}>
                <Network className="w-4 h-4" />
                Jump to System Graph
              </button>
            </div>
          </div>
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

  const { data: anomalies } = useQuery({
    queryKey: ['anomalies'],
    queryFn: fetchAnomalies,
    refetchInterval: 10000,
  });

  const displayAnomalies = anomalies || [];

  // Filter anomalies
  const filteredAnomalies = displayAnomalies.filter((a) => {
    if (filterAgent !== 'all' && a.agent !== filterAgent) return false;
    if (filterSeverity !== 'all' && a.severity !== filterSeverity) return false;
    return true;
  });

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

      <div className="grid grid-cols-12 gap-6">
        {/* Filters & Chart */}
        <div className="col-span-3 space-y-4">
          {/* Filters */}
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Filter className="w-4 h-4 text-[var(--color-text-muted)]" />
              <h3 className="font-semibold text-[var(--color-text-primary)]">Filters</h3>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-2 block">
                  Agent Source
                </label>
                <select value={filterAgent} onChange={(e) => setFilterAgent(e.target.value)} className="input w-full">
                  <option value="all">All Agents</option>
                  {agents.map((a) => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-2 block">
                  Severity
                </label>
                <select value={filterSeverity} onChange={(e) => setFilterSeverity(e.target.value)} className="input w-full">
                  <option value="all">All Severities</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
          </div>

          {/* Severity Distribution Chart */}
          <div className="chart-container">
            <h3 className="chart-title mb-4">Severity Distribution</h3>
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
            <div className="flex items-center justify-center gap-4 mt-4">
              <div className="flex items-center gap-1.5 text-xs">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                Critical
              </div>
              <div className="flex items-center gap-1.5 text-xs">
                <span className="w-2.5 h-2.5 rounded-full bg-orange-500"></span>
                High
              </div>
              <div className="flex items-center gap-1.5 text-xs">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                Medium
              </div>
              <div className="flex items-center gap-1.5 text-xs">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span>
                Low
              </div>
            </div>
          </div>
        </div>

        {/* Anomaly List */}
        <div className="col-span-9">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-[var(--color-text-primary)]">
                {filteredAnomalies.length} Anomalies
                {filterAgent !== 'all' || filterSeverity !== 'all' ? ' (filtered)' : ''}
              </h3>
            </div>

            <div className="grid grid-cols-1 gap-4">
              {filteredAnomalies.length > 0 ? (
                filteredAnomalies.map((anomaly) => (
                  <AnomalyCard
                    key={anomaly.anomaly_id}
                    anomaly={anomaly}
                    onClick={() => setSelectedAnomaly(anomaly)}
                  />
                ))
              ) : (
                <div className="text-center py-12 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                  <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4">
                    <Sparkles className="w-8 h-8 text-slate-400" />
                  </div>
                  <p className="text-[var(--color-text-muted)]">No anomalies match your filters</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Info */}
      <div className="p-5 bg-gradient-to-r from-amber-50 via-orange-50 to-yellow-50 rounded-2xl border border-amber-100">
        <div className="flex items-start gap-4">
          <div className="icon-container icon-container-md bg-gradient-to-br from-amber-500 to-orange-500 shadow-lg flex-shrink-0">
            <Info className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-semibold text-amber-900 mb-1">About Anomaly Detection</div>
            <p className="text-sm text-amber-700 leading-relaxed">
              Anomalies are detected by specialized agents: <strong>ResourceAgent</strong> monitors infrastructure metrics,
              <strong> WorkflowAgent</strong> tracks workflow execution patterns, and <strong>ComplianceAgent</strong> validates policy adherence.
              Each anomaly includes confidence scores and evidence links for full traceability.
            </p>
          </div>
        </div>
      </div>

      {/* Modal / Evidence View */}
      {selectedAnomaly && viewMode === 'detail' && (
        <AnomalyDetailModal
          anomaly={selectedAnomaly}
          onClose={() => { setSelectedAnomaly(null); setViewMode('detail'); }}
          onViewEvidence={() => setViewMode('evidence')}
          onNavigate={(path) => { setSelectedAnomaly(null); router.push(path); }}
        />
      )}
      {selectedAnomaly && viewMode === 'evidence' && (
        <EvidenceDetailView
          anomaly={selectedAnomaly}
          onClose={() => { setSelectedAnomaly(null); setViewMode('detail'); }}
          onBack={() => setViewMode('detail')}
        />
      )}
    </div>
  );
}
