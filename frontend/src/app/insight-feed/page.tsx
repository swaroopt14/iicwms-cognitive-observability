'use client';

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Lightbulb,
  AlertTriangle,
  ChevronRight,
  ChevronDown,
  Info,
  Zap,
  Clock,
  ExternalLink,
  Filter,
  TrendingUp,
  X,
  CheckCircle,
  Activity,
  FileText,
  GitMerge,
  Shield,
} from 'lucide-react';
import { fetchInsights, type Insight } from '@/lib/api';
import { formatRelativeTime, formatDateTime } from '@/lib/utils';
import { DonutChart, Sparkline } from '@/components/Charts';

// Severity configurations
const severityConfig: Record<string, { color: string; bg: string; border: string; gradient: string }> = {
  critical: { color: '#ef4444', bg: 'bg-red-50', border: 'border-red-200', gradient: 'from-red-500 to-rose-600' },
  high: { color: '#f59e0b', bg: 'bg-amber-50', border: 'border-amber-200', gradient: 'from-amber-500 to-orange-600' },
  medium: { color: '#3b82f6', bg: 'bg-blue-50', border: 'border-blue-200', gradient: 'from-blue-500 to-indigo-600' },
  low: { color: '#10b981', bg: 'bg-emerald-50', border: 'border-emerald-200', gradient: 'from-emerald-500 to-teal-600' },
};

// Insight Detail Drawer
function InsightDetailDrawer({ insight, onClose, onNavigate }: { insight: Insight; onClose: () => void; onNavigate: (path: string) => void }) {
  const config = severityConfig[insight.severity] || severityConfig.low;
  const trendData = Array.from({ length: 12 }, () => 30 + Math.random() * 50);
  const confidencePercent = Math.round(insight.confidence * 100);

  // Map severity to risk level
  const riskLevel = insight.severity === 'critical' ? 'CRITICAL' : insight.severity === 'high' ? 'HIGH' : insight.severity === 'medium' ? 'ELEVATED' : 'LOW';

  return (
    <>
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40" onClick={onClose} />
      <div className="fixed inset-y-0 right-0 w-[600px] bg-white shadow-2xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between bg-gradient-to-r from-slate-50 to-white flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${config.gradient} flex items-center justify-center shadow-md`}>
              <Lightbulb className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-lg text-[var(--color-text-primary)]">Insight Detail</h2>
              <p className="text-xs text-[var(--color-text-muted)]">{insight.insight_id} · {formatRelativeTime(insight.timestamp)}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-slate-100 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Summary */}
          <div className={`p-4 rounded-xl border ${config.border} ${config.bg}`}>
            <h3 className="font-semibold text-[var(--color-text-primary)] leading-snug mb-3">{insight.summary}</h3>
            <div className="flex items-center gap-4">
              <span className="px-2.5 py-1 text-xs font-semibold rounded-full" style={{ backgroundColor: `${config.color}15`, color: config.color }}>
                {insight.severity.toUpperCase()}
              </span>
              <div className="flex items-center gap-2">
                <DonutChart value={confidencePercent} total={100} color={config.color} size={28} strokeWidth={3} showLabel={false} />
                <span className="text-xs font-semibold" style={{ color: config.color }}>{confidencePercent}% confidence</span>
              </div>
            </div>
          </div>

          {/* Risk & Impact Grid */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-xl border border-[var(--color-border)] text-center">
              <div className="text-lg font-bold" style={{ color: config.color }}>{riskLevel}</div>
              <div className="text-[10px] text-[var(--color-text-muted)] font-medium">Risk Level</div>
            </div>
            <div className="p-3 rounded-xl border border-[var(--color-border)] text-center">
              <div className="text-lg font-bold text-indigo-600">{insight.evidence_ids?.length || 0}</div>
              <div className="text-[10px] text-[var(--color-text-muted)] font-medium">Evidence Items</div>
            </div>
            <div className="p-3 rounded-xl border border-[var(--color-border)] text-center">
              <div className="text-lg font-bold text-amber-600">{insight.recommended_actions.length}</div>
              <div className="text-[10px] text-[var(--color-text-muted)] font-medium">Actions</div>
            </div>
          </div>

          {/* Metric Trend */}
          <div className="p-4 rounded-xl border border-[var(--color-border)]">
            <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-3 font-semibold">Related Metric Trend</div>
            <Sparkline data={trendData} color={config.color} width={500} height={60} />
          </div>

          {/* Why it matters */}
          <div className="p-4 bg-white rounded-xl border border-[var(--color-border)]">
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-text-primary)] mb-3">
              <Info className="w-4 h-4" style={{ color: config.color }} />
              Why This Matters
            </div>
            <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">{insight.why_it_matters}</p>
          </div>

          {/* What happens if ignored */}
          <div className="p-4 bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl border border-amber-200">
            <div className="flex items-center gap-2 text-sm font-semibold text-amber-800 mb-3">
              <AlertTriangle className="w-4 h-4" />
              Impact If Ignored
            </div>
            <p className="text-sm text-amber-700 leading-relaxed">{insight.what_happens_if_ignored}</p>
          </div>

          {/* Recommended Actions */}
          <div className="p-4 bg-gradient-to-r from-emerald-50 to-teal-50 rounded-xl border border-emerald-200">
            <div className="flex items-center gap-2 text-sm font-semibold text-emerald-800 mb-3">
              <CheckCircle className="w-4 h-4" />
              Recommended Actions
            </div>
            <div className="space-y-2">
              {insight.recommended_actions.map((action, i) => (
                <div key={i} className="flex items-start gap-3 p-2.5 bg-white rounded-lg border border-emerald-200">
                  <span className="w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0 mt-0.5 text-[10px] font-bold text-emerald-700">{i + 1}</span>
                  <span className="text-sm text-emerald-700">{action}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Evidence Chain */}
          {insight.evidence_ids && insight.evidence_ids.length > 0 && (
            <div>
              <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-3 font-semibold">Evidence Chain</div>
              <div className="space-y-2">
                {insight.evidence_ids.map((id) => (
                  <div key={id} className="flex items-center gap-3 p-3 rounded-xl border border-[var(--color-border)] hover:border-indigo-200 transition-colors cursor-pointer">
                    <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                      <FileText className="w-4 h-4 text-indigo-600" />
                    </div>
                    <div className="flex-1">
                      <code className="text-sm font-bold text-[var(--color-primary)]">{id}</code>
                      <p className="text-xs text-[var(--color-text-muted)]">
                        {id.startsWith('evt_') ? 'System Event' : id.startsWith('metric_') ? 'Resource Metric' : id.startsWith('anom_') ? 'Anomaly Detection' : 'Causal Chain'}
                      </p>
                    </div>
                    <span className="text-[10px] bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full font-semibold">
                      {id.startsWith('evt_') ? 'EVENT' : id.startsWith('metric_') ? 'METRIC' : id.startsWith('anom_') ? 'ANOMALY' : 'CHAIN'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Timestamp */}
          <div className="p-3 bg-[var(--color-surface-tertiary)] rounded-xl flex items-center gap-3">
            <Clock className="w-5 h-5 text-slate-500" />
            <div>
              <div className="text-[10px] text-[var(--color-text-muted)]">Generated</div>
              <div className="text-sm font-semibold">{formatDateTime(insight.timestamp)}</div>
            </div>
          </div>

          {/* Navigation Actions */}
          <div className="pt-4 border-t border-[var(--color-border)] space-y-3">
            <button className="btn btn-primary w-full" onClick={() => onNavigate('/causal-analysis')}>
              <GitMerge className="w-4 h-4" />
              View Causal Analysis
            </button>
            <button className="btn btn-secondary w-full" onClick={() => onNavigate('/anomaly-center')}>
              <Zap className="w-4 h-4" />
              View Related Anomalies
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

// Insight Card Component
function InsightCard({ insight, index, onViewDetail }: { insight: Insight; index: number; onViewDetail: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const config = severityConfig[insight.severity] || severityConfig.low;

  // Mock trend data
  const trendData = Array.from({ length: 8 }, () => 30 + Math.random() * 50);

  return (
    <div
      className={`rounded-2xl border transition-all duration-300 overflow-hidden ${
        expanded ? `${config.bg} ${config.border} shadow-lg` : 'bg-white border-[var(--color-border)] hover:shadow-md'
      }`}
      style={{ animationDelay: `${index * 100}ms` }}
    >
      {/* Main content - clickable */}
      <div
        className="p-5 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start gap-4">
          {/* Icon */}
          <div
            className={`w-12 h-12 rounded-xl bg-gradient-to-br ${config.gradient} flex items-center justify-center flex-shrink-0 shadow-lg`}
          >
            <AlertTriangle className="w-6 h-6 text-white" />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <span
                className="px-2.5 py-1 text-xs font-semibold rounded-full"
                style={{ backgroundColor: `${config.color}15`, color: config.color }}
              >
                {insight.severity.toUpperCase()}
              </span>
              <span className="text-xs text-[var(--color-text-muted)] flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatRelativeTime(insight.timestamp)}
              </span>
            </div>

            <h3 className="font-semibold text-[var(--color-text-primary)] mb-2 leading-snug">
              {insight.summary}
            </h3>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <DonutChart
                  value={Math.round(insight.confidence * 100)}
                  total={100}
                  color={config.color}
                  size={28}
                  strokeWidth={3}
                  showLabel={false}
                />
                <span className="text-xs font-semibold" style={{ color: config.color }}>
                  {Math.round(insight.confidence * 100)}% confidence
                </span>
              </div>
              <Sparkline data={trendData} color={config.color} width={60} height={20} />
            </div>
          </div>

          {/* Expand indicator */}
          <ChevronDown className={`w-5 h-5 text-[var(--color-text-muted)] transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`} />
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="px-5 pb-5 animate-fade-in">
          <div className="pl-16 space-y-4">
            {/* Why it matters */}
            <div className="p-4 bg-white rounded-xl border border-[var(--color-border)]">
              <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-text-primary)] mb-2">
                <Info className="w-4 h-4" style={{ color: config.color }} />
                Why it matters
              </div>
              <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                {insight.why_it_matters}
              </p>
            </div>

            {/* What happens if ignored */}
            <div className="p-4 bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl border border-amber-200">
              <div className="flex items-center gap-2 text-sm font-semibold text-amber-800 mb-2">
                <AlertTriangle className="w-4 h-4" />
                If ignored
              </div>
              <p className="text-sm text-amber-700 leading-relaxed">{insight.what_happens_if_ignored}</p>
            </div>

            {/* Recommended Actions */}
            <div className="p-4 bg-gradient-to-r from-emerald-50 to-teal-50 rounded-xl border border-emerald-200">
              <div className="flex items-center gap-2 text-sm font-semibold text-emerald-800 mb-2">
                <Zap className="w-4 h-4" />
                Recommended Actions
              </div>
              <ul className="space-y-2">
                {insight.recommended_actions.map((action, i) => (
                  <li key={i} className="text-sm text-emerald-700 flex items-start gap-2">
                    <ChevronRight className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    {action}
                  </li>
                ))}
              </ul>
            </div>

            {/* Evidence */}
            {insight.evidence_ids && insight.evidence_ids.length > 0 && (
              <div>
                <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Evidence</div>
                <div className="flex flex-wrap gap-2">
                  {insight.evidence_ids.map((id) => (
                    <code key={id} className="text-xs bg-white px-3 py-1.5 rounded-lg border">{id}</code>
                  ))}
                </div>
              </div>
            )}

            {/* Quick Actions */}
            <div className="flex items-center gap-3 pt-2">
              <button className="btn btn-primary btn-sm" onClick={(e) => { e.stopPropagation(); onViewDetail(); }}>
                <ExternalLink className="w-3.5 h-3.5" />
                View Full Detail
              </button>
              <button className="btn btn-secondary btn-sm">
                Mark Resolved
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function InsightFeedPage() {
  const router = useRouter();
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [selectedInsight, setSelectedInsight] = useState<Insight | null>(null);

  const { data: insights } = useQuery({
    queryKey: ['insights'],
    queryFn: () => fetchInsights(20),
    refetchInterval: 10000,
  });

  const displayInsights = insights || [];

  // Filter
  const filteredInsights = filterSeverity === 'all'
    ? displayInsights
    : displayInsights.filter((i) => i.severity === filterSeverity);

  // Stats
  const stats = {
    total: displayInsights.length,
    critical: displayInsights.filter((i) => i.severity === 'critical').length,
    high: displayInsights.filter((i) => i.severity === 'high').length,
    medium: displayInsights.filter((i) => i.severity === 'medium').length,
    low: displayInsights.filter((i) => i.severity === 'low').length,
  };

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="icon-container icon-container-lg bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg">
            <Lightbulb className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="page-title">Executive Insight Feed</h1>
            <p className="page-subtitle">High-level intelligence for leadership decision-making</p>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-5 gap-4">
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Total Insights</div>
              <div className="stats-value">{stats.total}</div>
            </div>
            <div className="icon-container icon-container-md bg-violet-100">
              <Lightbulb className="w-5 h-5 text-violet-600" />
            </div>
          </div>
        </div>
        <div className="stats-card cursor-pointer hover:ring-2 hover:ring-red-200" onClick={() => setFilterSeverity(filterSeverity === 'critical' ? 'all' : 'critical')}>
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Critical</div>
              <div className="stats-value text-red-500">{stats.critical}</div>
            </div>
            <DonutChart value={stats.critical} total={stats.total || 1} color="#ef4444" size={40} strokeWidth={4} />
          </div>
        </div>
        <div className="stats-card cursor-pointer hover:ring-2 hover:ring-amber-200" onClick={() => setFilterSeverity(filterSeverity === 'high' ? 'all' : 'high')}>
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">High</div>
              <div className="stats-value text-amber-500">{stats.high}</div>
            </div>
            <DonutChart value={stats.high} total={stats.total || 1} color="#f59e0b" size={40} strokeWidth={4} />
          </div>
        </div>
        <div className="stats-card cursor-pointer hover:ring-2 hover:ring-blue-200" onClick={() => setFilterSeverity(filterSeverity === 'medium' ? 'all' : 'medium')}>
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Medium</div>
              <div className="stats-value text-blue-500">{stats.medium}</div>
            </div>
            <DonutChart value={stats.medium} total={stats.total || 1} color="#3b82f6" size={40} strokeWidth={4} />
          </div>
        </div>
        <div className="stats-card cursor-pointer hover:ring-2 hover:ring-emerald-200" onClick={() => setFilterSeverity(filterSeverity === 'low' ? 'all' : 'low')}>
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Low</div>
              <div className="stats-value text-emerald-500">{stats.low}</div>
            </div>
            <DonutChart value={stats.low} total={stats.total || 1} color="#10b981" size={40} strokeWidth={4} />
          </div>
        </div>
      </div>

      {/* Filter indicator */}
      {filterSeverity !== 'all' && (
        <div className="flex items-center gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
          <Filter className="w-4 h-4 text-[var(--color-text-muted)]" />
          <span className="text-sm text-[var(--color-text-secondary)]">
            Showing <strong>{filterSeverity}</strong> severity insights
          </span>
          <button
            onClick={() => setFilterSeverity('all')}
            className="ml-auto text-sm text-[var(--color-primary)] hover:underline"
          >
            Clear filter
          </button>
        </div>
      )}

      {/* Insight Cards */}
      <div className="space-y-4">
        {filteredInsights.length > 0 ? (
          filteredInsights.map((insight, index) => (
            <InsightCard key={insight.insight_id} insight={insight} index={index} onViewDetail={() => setSelectedInsight(insight)} />
          ))
        ) : (
          <div className="text-center py-16 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
            <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4">
              <Lightbulb className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="font-semibold text-[var(--color-text-primary)] mb-1">No Insights Found</h3>
            <p className="text-sm text-[var(--color-text-muted)]">
              {filterSeverity !== 'all' ? 'Try changing your filter' : 'System is running optimally'}
            </p>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-5 bg-gradient-to-r from-violet-50 via-purple-50 to-fuchsia-50 rounded-2xl border border-violet-100">
        <div className="flex items-start gap-4">
          <div className="icon-container icon-container-md bg-gradient-to-br from-violet-500 to-purple-500 shadow-lg flex-shrink-0">
            <Info className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-semibold text-violet-900 mb-1">About the Insight Feed</div>
            <p className="text-sm text-violet-700 leading-relaxed">
              Each insight is generated by the <strong>Master Agent</strong> and <strong>Explanation Engine</strong>.
              Insights are synthesized from multiple agent outputs and include: a clear summary, <em>why it matters</em>,
              <em>what happens if ignored</em>, and <em>recommended actions</em>. All insights are traceable to evidence.
            </p>
          </div>
        </div>
      </div>

      {/* Insight Detail Drawer */}
      {selectedInsight && (
        <InsightDetailDrawer
          insight={selectedInsight}
          onClose={() => setSelectedInsight(null)}
          onNavigate={(path) => { setSelectedInsight(null); router.push(path); }}
        />
      )}
    </div>
  );
}
