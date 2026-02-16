'use client';

import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  ChevronRight,
  ChevronDown,
  Clock,
  Zap,
  Info,
  ArrowUpRight,
  BarChart3,
  Shield,
  GitBranch,
  Sparkles,
} from 'lucide-react';
import {
  fetchSystemHealth,
  fetchInsights,
  fetchEvents,
  fetchRiskIndex,
  fetchAnomalyTrend,
  fetchOverviewStats,
  type Insight,
} from '@/lib/api';
import { formatTime } from '@/lib/utils';
import { AreaChart, RiskGraph } from '@/components/Charts';

// Insight Card Component
function InsightCard({ insight, index }: { insight: Insight; index: number }) {
  const [expanded, setExpanded] = useState(false);

  const severityConfig: Record<string, { badge: string; icon: string; glow: string }> = {
    critical: { badge: 'badge-critical', icon: 'bg-red-500', glow: 'shadow-[0_0_20px_rgba(239,68,68,0.15)]' },
    high: { badge: 'badge-warning', icon: 'bg-amber-500', glow: 'shadow-[0_0_20px_rgba(245,158,11,0.15)]' },
    medium: { badge: 'badge-info', icon: 'bg-blue-500', glow: '' },
    low: { badge: 'badge-neutral', icon: 'bg-slate-400', glow: '' },
  };

  const config = severityConfig[insight.severity] || severityConfig.low;

  return (
    <div
      className={`group relative p-5 rounded-2xl border transition-all duration-300 cursor-pointer ${
        expanded 
          ? `bg-white border-[var(--color-primary)] ${config.glow}` 
          : 'bg-[var(--color-surface-hover)] border-transparent hover:bg-white hover:border-[var(--color-border)]'
      }`}
      onClick={() => setExpanded(!expanded)}
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <div className="flex items-start gap-4">
        <div className={`w-10 h-10 ${config.icon} rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg`}>
          <AlertTriangle className="w-5 h-5 text-white" />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className={`badge ${config.badge}`}>
              <span className="badge-dot"></span>
              {insight.severity}
            </span>
            <span className="text-xs font-medium text-[var(--color-text-muted)]">
              {Math.round(insight.confidence * 100)}% confidence
            </span>
          </div>
          <p className="font-medium text-[var(--color-text-primary)] leading-snug">
            {insight.summary}
          </p>
        </div>

        <ChevronDown className={`w-5 h-5 text-[var(--color-text-muted)] transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`} />
      </div>

      {expanded && (
        <div className="mt-5 pt-5 border-t border-[var(--color-border)] space-y-4 animate-fade-in">
          <div className="p-4 bg-[var(--color-surface-tertiary)] rounded-xl">
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-text-primary)] mb-2">
              <Info className="w-4 h-4 text-[var(--color-primary)]" />
              Why it matters
            </div>
            <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
              {insight.why_it_matters}
            </p>
          </div>

          <div className="p-4 bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl border border-amber-200">
            <div className="flex items-center gap-2 text-sm font-semibold text-amber-800 mb-2">
              <AlertTriangle className="w-4 h-4" />
              If ignored
            </div>
            <p className="text-sm text-amber-700 leading-relaxed">{insight.what_happens_if_ignored}</p>
          </div>

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
        </div>
      )}
    </div>
  );
}

// Event Type Badge
function EventTypeBadge({ type }: { type: string }) {
  const typeConfig: Record<string, { bg: string; text: string; dot: string }> = {
    WORKFLOW_START: { bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-500' },
    WORKFLOW_STEP: { bg: 'bg-indigo-50', text: 'text-indigo-700', dot: 'bg-indigo-500' },
    WORKFLOW_COMPLETE: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500' },
    ACCESS_WRITE: { bg: 'bg-violet-50', text: 'text-violet-700', dot: 'bg-violet-500' },
    ACCESS_READ: { bg: 'bg-slate-100', text: 'text-slate-600', dot: 'bg-slate-400' },
    RESOURCE_SPIKE: { bg: 'bg-orange-50', text: 'text-orange-700', dot: 'bg-orange-500' },
    LATENCY_SPIKE: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500' },
    MANUAL_OVERRIDE: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500' },
  };

  const config = typeConfig[type] || { bg: 'bg-slate-100', text: 'text-slate-600', dot: 'bg-slate-400' };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-lg ${config.bg} ${config.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`}></span>
      {type.replace(/_/g, ' ')}
    </span>
  );
}

export default function OverviewPage() {
  const [nowMs, setNowMs] = useState<number>(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNowMs(Date.now()), 10000);
    return () => clearInterval(id);
  }, []);

  const { data: health } = useQuery({
    queryKey: ['systemHealth'],
    queryFn: fetchSystemHealth,
    refetchInterval: 10000,
  });

  const { data: insights } = useQuery({
    queryKey: ['insights'],
    queryFn: () => fetchInsights(5),
    refetchInterval: 10000,
  });

  const { data: events } = useQuery({
    queryKey: ['events'],
    queryFn: () => fetchEvents(10),
    refetchInterval: 5000,
  });

  const { data: riskData } = useQuery({
    queryKey: ['riskIndex'],
    queryFn: fetchRiskIndex,
    refetchInterval: 10000,
  });

  const { data: anomalyTrend } = useQuery({
    queryKey: ['anomalyTrend'],
    queryFn: fetchAnomalyTrend,
    refetchInterval: 10000,
  });

  const { data: overviewStats } = useQuery({
    queryKey: ['overviewStats'],
    queryFn: fetchOverviewStats,
    refetchInterval: 5000,
  });

  const displayInsights = insights?.length ? insights : [];
  const displayEvents = events?.length ? events : [];
  const displayRiskData = riskData?.history?.length ? riskData.history : [];
  const riskFallbackFromAnomalyTrend = anomalyTrend?.length
    ? anomalyTrend.map((p) => ({
        timestamp: p.ts,
        risk_score: Math.max(0, Math.min(100, 25 + p.total * 6)),
        state: p.total >= 10 ? 'VIOLATION' : p.total >= 7 ? 'AT_RISK' : p.total >= 4 ? 'DEGRADED' : 'NORMAL',
      }))
    : [];
  const systemHealthTrendData = displayRiskData.length ? displayRiskData : riskFallbackFromAnomalyTrend;
  // Use rolling real-time timestamps for chart X-axis so labels move every refresh.
  const systemHealthTrendRealtime = useMemo(() => {
    const base = systemHealthTrendData;
    if (!base.length) return base;
    const now = nowMs;
    const stepMs = 10_000; // matches refetch interval (10s)
    return base.map((point, idx) => ({
      ...point,
      timestamp: new Date(now - (base.length - 1 - idx) * stepMs).toISOString(),
    }));
  }, [systemHealthTrendData, nowMs]);
  const systemHealthArea = systemHealthTrendData.length
    ? systemHealthTrendData.map((d) => d.risk_score)
    : [22, 24, 28, 31, 35, 33, 30, 27, 25, 23, 21, 20];

  return (
    <div className="animate-fade-in space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="icon-container icon-container-lg bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-accent-violet)] shadow-lg">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="page-title">Cognitive Observability Center</h1>
            <p className="page-subtitle">Real-time system intelligence and reasoning insights</p>
          </div>
        </div>

        {/* System Status */}
        <div className="flex items-center gap-3 px-5 py-3 bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-2xl">
          <div className="status-indicator status-indicator-online"></div>
          <div>
            <div className="text-sm font-semibold text-emerald-700">{health?.status || 'System Normal'}</div>
            <div className="text-xs text-emerald-600">All agents operational</div>
          </div>
        </div>
      </div>

      {/* Value Proposition */}
      <div className="p-5 bg-gradient-to-r from-indigo-50 via-violet-50 to-purple-50 rounded-2xl border border-indigo-100">
        <div className="flex items-start gap-4">
          <div className="icon-container icon-container-md bg-gradient-to-br from-indigo-500 to-violet-500 shadow-lg flex-shrink-0">
            <Info className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-semibold text-indigo-900 mb-1">This is Cognitive Observability</div>
            <p className="text-sm text-indigo-700 leading-relaxed">
              Unlike traditional dashboards, this page shows <strong>reasoning insights</strong> — not just metrics.
              Each insight is backed by evidence, produced by specialized AI agents, and includes actionable
              recommendations with confidence scores. We don&apos;t just tell you what happened — we explain <strong>why</strong>.
            </p>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4">
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Active Workflows</div>
              <div className="stats-value">{overviewStats?.active_workflows ?? health?.active_workflows ?? 0}</div>
            </div>
            <div className="icon-container icon-container-md bg-blue-100">
              <GitBranch className="w-5 h-5 text-blue-600" />
            </div>
          </div>
          <div className="stats-trend stats-trend-up mt-3">
            <TrendingUp className="w-3 h-3" /> {overviewStats?.cycles_completed ?? 0} cycles completed
          </div>
        </div>

        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Total Events</div>
              <div className="stats-value">{(overviewStats?.total_events ?? 0).toLocaleString()}</div>
            </div>
            <div className="icon-container icon-container-md bg-violet-100">
              <BarChart3 className="w-5 h-5 text-violet-600" />
            </div>
          </div>
          <div className="stats-trend stats-trend-up mt-3">
            <TrendingUp className="w-3 h-3" /> {(overviewStats?.total_metrics ?? 0).toLocaleString()} metrics
          </div>
        </div>

        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Active Anomalies</div>
              <div className="stats-value text-[var(--color-warning)]">{overviewStats?.active_anomalies ?? health?.active_anomalies ?? 0}</div>
            </div>
            <div className="icon-container icon-container-md bg-amber-100">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
            </div>
          </div>
          <div className="stats-trend stats-trend-down mt-3">
            <TrendingDown className="w-3 h-3" /> {overviewStats?.total_anomalies ?? 0} total detected
          </div>
        </div>

        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Compliance Score</div>
              <div className="stats-value text-[var(--color-success)]">{overviewStats?.compliance_rate ?? 0}%</div>
            </div>
            <div className="icon-container icon-container-md bg-emerald-100">
              <Shield className="w-5 h-5 text-emerald-600" />
            </div>
          </div>
          <div className="stats-trend stats-trend-up mt-3">
            <TrendingUp className="w-3 h-3" /> {overviewStats?.total_violations ?? 0} violations found
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Recent Events */}
        <div className="col-span-5">
          <div className="table-container h-[400px] flex flex-col">
            <div className="section-header">
              <h3 className="section-title">
                <Clock className="w-4 h-4 text-[var(--color-text-muted)]" />
                Recent Events
              </h3>
              <span className="badge badge-info">
                <span className="badge-dot"></span>
                Live
              </span>
            </div>
            <div className="overflow-y-auto flex-1">
              <table className="w-full">
                <thead className="table-header sticky top-0">
                  <tr>
                    <th>Time</th>
                    <th>Event</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody className="table-body">
                  {displayEvents.map((event) => (
                    <tr key={event.event_id} className="group cursor-pointer">
                      <td className="text-[var(--color-text-muted)] text-xs font-mono whitespace-nowrap">
                        {formatTime(event.timestamp)}
                      </td>
                      <td>
                        <EventTypeBadge type={event.type} />
                      </td>
                      <td className="text-sm">
                        <span className="text-[var(--color-text-secondary)]">
                          {event.workflow_id || event.actor}
                        </span>
                        <ArrowUpRight className="w-3 h-3 inline ml-1 opacity-0 group-hover:opacity-100 text-[var(--color-primary)] transition-opacity" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* System Health Trend */}
        <div className="col-span-7">
          <div className="chart-container h-[400px]">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="chart-title">
                  <TrendingUp className="w-4 h-4 text-violet-600" />
                  System Health Trend
                </h3>
                <p className="chart-subtitle">Live risk trajectory over time (auto-refresh every 10s)</p>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-[var(--color-text-primary)]">
                  {typeof riskData?.current_risk === 'number' ? riskData.current_risk.toFixed(1) : '—'}
                </div>
                <div className="flex items-center gap-1 text-sm text-violet-600 font-medium">
                  <TrendingUp className="w-4 h-4" />
                  {systemHealthTrendRealtime.length} data points
                </div>
              </div>
            </div>
            {systemHealthTrendRealtime.length > 0 ? (
              <RiskGraph
                data={systemHealthTrendRealtime}
                height={280}
                showZones={true}
              />
            ) : (
              <AreaChart
                data={systemHealthArea}
                color="#8b5cf6"
                gradientFrom="rgba(139, 92, 246, 0.25)"
                gradientTo="rgba(139, 92, 246, 0)"
                height={280}
                showGrid={true}
                showDots={false}
                animated={true}
              />
            )}
          </div>
        </div>

        {/* Critical Insights */}
        <div className="col-span-12">
          <div className="card p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="icon-container icon-container-md bg-gradient-to-br from-amber-100 to-orange-100">
                  <Sparkles className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">Critical Insights</h3>
                  <p className="text-sm text-[var(--color-text-secondary)]">AI-generated reasoning from multi-agent analysis</p>
                </div>
              </div>
              <span className="badge badge-warning">
                <span className="badge-dot"></span>
                {displayInsights.length} Active
              </span>
            </div>
            <div className="space-y-4">
              {displayInsights.map((insight, index) => (
                <InsightCard key={insight.insight_id} insight={insight} index={index} />
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
