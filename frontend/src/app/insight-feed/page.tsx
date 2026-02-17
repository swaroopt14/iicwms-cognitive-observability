'use client';

import { useMemo, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  Lightbulb,
  Search,
  Filter,
  Clock,
  CheckCircle2,
  ShieldCheck,
  ExternalLink,
  X,
} from 'lucide-react';

import { fetchInsights, type Insight } from '@/lib/api';
import { formatDateTime, formatRelativeTime } from '@/lib/utils';
import { DonutChart } from '@/components/Charts';

type Severity = 'critical' | 'high' | 'medium' | 'low';

type TimeRange = '1h' | '24h' | '7d' | 'all';

type InsightStatus = 'open' | 'acknowledged' | 'resolved';

type LocalInsightState = {
  status: InsightStatus;
  updated_at: string;
};

type LocalStateStore = Record<string, LocalInsightState>;

const LOCAL_STORE_KEY = 'chronos.insights.local_state.v1';

function safeParseJson<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function loadLocalStore(): LocalStateStore {
  if (typeof window === 'undefined') return {};
  return safeParseJson<LocalStateStore>(window.localStorage.getItem(LOCAL_STORE_KEY), {});
}

function saveLocalStore(store: LocalStateStore) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(LOCAL_STORE_KEY, JSON.stringify(store));
}

function severityBadgeClass(sev: string): string {
  const s = (sev || '').toLowerCase();
  if (s === 'critical') return 'badge-critical';
  if (s === 'high') return 'badge-warning';
  if (s === 'medium') return 'badge-info';
  return 'badge-neutral';
}

function severityColor(sev: string): string {
  const s = (sev || '').toLowerCase();
  if (s === 'critical') return '#ef4444';
  if (s === 'high') return '#f97316';
  if (s === 'medium') return '#3b82f6';
  return '#64748b';
}

function riskBandFromSeverity(sev: string): string {
  const s = (sev || '').toLowerCase();
  if (s === 'critical') return 'INCIDENT';
  if (s === 'high') return 'VIOLATION';
  if (s === 'medium') return 'AT_RISK';
  return 'NORMAL';
}

function statusBadge(status: InsightStatus) {
  const cls =
    status === 'resolved'
      ? 'badge-success'
      : status === 'acknowledged'
      ? 'badge-purple'
      : 'badge-neutral';
  const label = status === 'resolved' ? 'RESOLVED' : status === 'acknowledged' ? 'ACK' : 'OPEN';
  return (
    <span className={`badge ${cls}`}>
      <span className="badge-dot" />
      {label}
    </span>
  );
}

function msForRange(range: TimeRange): number {
  if (range === '1h') return 60 * 60 * 1000;
  if (range === '24h') return 24 * 60 * 60 * 1000;
  if (range === '7d') return 7 * 24 * 60 * 60 * 1000;
  return Number.POSITIVE_INFINITY;
}

function normalizeSeverity(s: string): Severity {
  const x = (s || '').toLowerCase();
  if (x === 'critical' || x === 'high' || x === 'medium') return x;
  return 'low';
}

function coerceConfidence01(v: number): number {
  const x = Number.isFinite(v) ? v : 0;
  // backend uses 0..1
  return Math.max(0, Math.min(1, x));
}

function EmptyState({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="text-center py-16 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
      <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4">
        <Lightbulb className="w-8 h-8 text-slate-400" />
      </div>
      <h3 className="font-semibold text-[var(--color-text-primary)] mb-1">{title}</h3>
      <p className="text-sm text-[var(--color-text-muted)]">{subtitle}</p>
    </div>
  );
}

function LoadingTable() {
  return (
    <div className="table-container">
      <div className="section-header">
        <div className="section-title">Loading insights...</div>
      </div>
      <div className="p-4 space-y-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-12 rounded-xl bg-slate-100 animate-pulse" />
        ))}
      </div>
    </div>
  );
}

function DetailPanel({
  insight,
  status,
  onSetStatus,
  onClose,
  onOpenAudit,
}: {
  insight: Insight;
  status: InsightStatus;
  onSetStatus: (s: InsightStatus) => void;
  onClose: () => void;
  onOpenAudit: () => void;
}) {
  const sev = normalizeSeverity(insight.severity);
  const color = severityColor(sev);
  const confidence = Math.round(coerceConfidence01(insight.confidence) * 100);

  return (
    <div className="card h-full flex flex-col overflow-hidden">
      <div className="p-4 border-b border-[var(--color-border)] bg-gradient-to-b from-slate-50 to-white flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`badge ${severityBadgeClass(sev)}`}>
              <span className="badge-dot" />
              {sev.toUpperCase()}
            </span>
            {statusBadge(status)}
            <span className="badge badge-neutral">{riskBandFromSeverity(sev)}</span>
          </div>
          <div className="mt-2">
            <div className="text-sm font-semibold text-[var(--color-text-primary)] leading-snug break-words">
              {insight.summary}
            </div>
            <div className="mt-1 text-xs text-[var(--color-text-muted)] font-mono break-all">
              {insight.insight_id}
            </div>
          </div>
        </div>
        <button className="btn btn-ghost" onClick={onClose} aria-label="Close detail">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <div className="p-3 rounded-xl border border-[var(--color-border)] bg-white">
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] font-semibold">Confidence</div>
            <div className="mt-1 flex items-center gap-2">
              <DonutChart value={confidence} total={100} color={color} size={34} strokeWidth={4} showLabel={false} />
              <div className="text-sm font-semibold" style={{ color }}>{confidence}%</div>
            </div>
          </div>
          <div className="p-3 rounded-xl border border-[var(--color-border)] bg-white">
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] font-semibold">Evidence</div>
            <div className="mt-1 text-sm font-semibold text-[var(--color-text-primary)]">
              {(insight.evidence_ids || []).length}
            </div>
          </div>
          <div className="p-3 rounded-xl border border-[var(--color-border)] bg-white">
            <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] font-semibold">Generated</div>
            <div className="mt-1 text-sm font-semibold text-[var(--color-text-primary)]">
              {formatRelativeTime(insight.timestamp)}
            </div>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-[var(--color-border)] bg-white">
          <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Why It Matters</div>
          <p className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">{insight.why_it_matters}</p>
        </div>

        <div className="p-4 rounded-xl border border-amber-200 bg-gradient-to-r from-amber-50 to-orange-50">
          <div className="text-xs font-semibold text-amber-800 uppercase tracking-wider">Impact If Ignored</div>
          <p className="mt-2 text-sm text-amber-700 leading-relaxed">{insight.what_happens_if_ignored}</p>
        </div>

        <div className="p-4 rounded-xl border border-[var(--color-border)] bg-white">
          <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Recommended Actions</div>
          <div className="mt-2 space-y-2">
            {(insight.recommended_actions || []).map((a, i) => (
              <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-slate-50 border border-slate-200">
                <span className="text-[10px] font-bold text-slate-600 w-5 h-5 rounded-full bg-white border border-slate-200 flex items-center justify-center flex-shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <span className="text-sm text-[var(--color-text-secondary)]">{a}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="p-4 rounded-xl border border-[var(--color-border)] bg-white">
          <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Evidence IDs</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {(insight.evidence_ids || []).slice(0, 14).map((id) => (
              <span key={id} className="text-xs font-mono px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 border border-slate-200">
                {id}
              </span>
            ))}
            {(insight.evidence_ids || []).length > 14 && (
              <span className="text-xs px-2.5 py-1 rounded-lg bg-white text-slate-600 border border-slate-200">
                +{(insight.evidence_ids || []).length - 14} more
              </span>
            )}
          </div>
        </div>

        <div className="p-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-tertiary)] flex items-center gap-3">
          <Clock className="w-4 h-4 text-slate-500" />
          <div>
            <div className="text-[10px] text-[var(--color-text-muted)]">Timestamp</div>
            <div className="text-sm font-semibold text-[var(--color-text-primary)]">{formatDateTime(insight.timestamp)}</div>
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-[var(--color-border)] bg-white">
        <div className="flex items-center gap-2 flex-wrap">
          <button className="btn btn-secondary" onClick={onOpenAudit}>
            <ShieldCheck className="w-4 h-4" />
            Open Audit
          </button>
          <a className="btn btn-secondary" href={`/insight/${encodeURIComponent(insight.insight_id)}`}>
            <ExternalLink className="w-4 h-4" />
            Open Full Page
          </a>
          <button
            className="btn btn-secondary"
            onClick={() => onSetStatus(status === 'acknowledged' ? 'open' : 'acknowledged')}
            title="Acknowledge for triage"
          >
            <CheckCircle2 className="w-4 h-4" />
            {status === 'acknowledged' ? 'Unack' : 'Acknowledge'}
          </button>
          <button
            className={status === 'resolved' ? 'btn btn-secondary' : 'btn btn-success'}
            onClick={() => onSetStatus(status === 'resolved' ? 'open' : 'resolved')}
            title="Resolve (local UI state)"
          >
            {status === 'resolved' ? 'Reopen' : 'Resolve'}
          </button>
          <a className="btn btn-ghost ml-auto" href="#" onClick={(e) => e.preventDefault()}>
            <ExternalLink className="w-4 h-4" />
            Export
          </a>
        </div>
      </div>
    </div>
  );
}

export default function InsightFeedPage() {
  const router = useRouter();

  const [query, setQuery] = useState('');
  const [severity, setSeverity] = useState<Severity | 'all'>('all');
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [statusFilter, setStatusFilter] = useState<InsightStatus | 'all'>('all');

  const [localStore, setLocalStore] = useState<LocalStateStore>({});
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: insights, isLoading } = useQuery({
    queryKey: ['insights'],
    queryFn: () => fetchInsights(60),
    refetchInterval: 10000,
  });

  useEffect(() => {
    setLocalStore(loadLocalStore());
  }, []);

  const displayInsights = insights || [];

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const cutoffMs = msForRange(timeRange);
    const now = Date.now();

    return displayInsights
      .slice()
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .filter((i) => {
        const sev = normalizeSeverity(i.severity);
        if (severity !== 'all' && sev !== severity) return false;

        const ts = new Date(i.timestamp).getTime();
        if (Number.isFinite(cutoffMs) && cutoffMs !== Number.POSITIVE_INFINITY) {
          if (now - ts > cutoffMs) return false;
        }

        const local = localStore[i.insight_id];
        const status: InsightStatus = local?.status || 'open';
        if (statusFilter !== 'all' && status !== statusFilter) return false;

        if (!q) return true;
        const hay = `${i.insight_id} ${i.summary} ${i.why_it_matters} ${(i.evidence_ids || []).join(' ')}`.toLowerCase();
        return hay.includes(q);
      });
  }, [displayInsights, query, severity, timeRange, statusFilter, localStore]);

  const selected = useMemo(() => {
    if (!filtered.length) return null;
    if (selectedId) {
      return filtered.find((x) => x.insight_id === selectedId) || filtered[0];
    }
    return filtered[0];
  }, [filtered, selectedId]);

  useEffect(() => {
    if (!selectedId && filtered.length) {
      setSelectedId(filtered[0].insight_id);
      return;
    }
    if (selectedId && filtered.length && !filtered.some((x) => x.insight_id === selectedId)) {
      setSelectedId(filtered[0].insight_id);
    }
  }, [filtered, selectedId]);

  const stats = useMemo(() => {
    const all = displayInsights;
    const openCount = all.filter((i) => (localStore[i.insight_id]?.status || 'open') !== 'resolved').length;

    const bySev = { critical: 0, high: 0, medium: 0, low: 0 } as Record<Severity, number>;
    for (const i of all) {
      bySev[normalizeSeverity(i.severity)] += 1;
    }

    return {
      total: all.length,
      open: openCount,
      ...bySev,
    };
  }, [displayInsights, localStore]);

  const setStatus = (id: string, s: InsightStatus) => {
    const next: LocalStateStore = {
      ...localStore,
      [id]: { status: s, updated_at: new Date().toISOString() },
    };
    setLocalStore(next);
    saveLocalStore(next);
  };

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="icon-container icon-container-lg bg-gradient-to-br from-slate-900 to-slate-700 shadow-lg">
            <Lightbulb className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="page-title">Enterprise Insight Center</h1>
            <p className="page-subtitle">Triage-ready insights with audit links, status, and governance-friendly evidence</p>
          </div>
        </div>
        <div className="hidden md:flex items-center gap-2">
          <button className="btn btn-secondary" onClick={() => router.push('/audit')}>
            <ShieldCheck className="w-4 h-4" />
            Audit
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <div className="stats-card md:col-span-2">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Open (Local)</div>
              <div className="stats-value">{stats.open}</div>
              <div className="stats-trend stats-trend-up">Governance view</div>
            </div>
            <DonutChart value={stats.open} total={stats.total || 1} color="#0f172a" size={44} strokeWidth={4} />
          </div>
        </div>
        <div className="stats-card cursor-pointer hover:ring-2 hover:ring-red-200" onClick={() => setSeverity(severity === 'critical' ? 'all' : 'critical')}
          title="Filter critical"
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Critical</div>
              <div className="stats-value text-red-500">{stats.critical}</div>
            </div>
            <DonutChart value={stats.critical} total={stats.total || 1} color="#ef4444" size={44} strokeWidth={4} />
          </div>
        </div>
        <div className="stats-card cursor-pointer hover:ring-2 hover:ring-orange-200" onClick={() => setSeverity(severity === 'high' ? 'all' : 'high')}
          title="Filter high"
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">High</div>
              <div className="stats-value text-orange-500">{stats.high}</div>
            </div>
            <DonutChart value={stats.high} total={stats.total || 1} color="#f97316" size={44} strokeWidth={4} />
          </div>
        </div>
        <div className="stats-card cursor-pointer hover:ring-2 hover:ring-blue-200" onClick={() => setSeverity(severity === 'medium' ? 'all' : 'medium')}
          title="Filter medium"
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Medium</div>
              <div className="stats-value text-blue-500">{stats.medium}</div>
            </div>
            <DonutChart value={stats.medium} total={stats.total || 1} color="#3b82f6" size={44} strokeWidth={4} />
          </div>
        </div>
        <div className="stats-card cursor-pointer hover:ring-2 hover:ring-slate-200" onClick={() => setSeverity(severity === 'low' ? 'all' : 'low')}
          title="Filter low"
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Low</div>
              <div className="stats-value text-slate-600">{stats.low}</div>
            </div>
            <DonutChart value={stats.low} total={stats.total || 1} color="#64748b" size={44} strokeWidth={4} />
          </div>
        </div>
      </div>

      <div className="card p-4">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="w-4 h-4 text-[var(--color-text-muted)] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              className="input input-search"
              placeholder="Search by summary, evidence id, insight id..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-[var(--color-text-muted)]" />
            <select className="input w-[160px]" value={severity} onChange={(e) => setSeverity(e.target.value as any)}>
              <option value="all">All severity</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          <select className="input w-[160px]" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as any)}>
            <option value="all">All status</option>
            <option value="open">Open</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="resolved">Resolved</option>
          </select>

          <select className="input w-[160px]" value={timeRange} onChange={(e) => setTimeRange(e.target.value as any)}>
            <option value="1h">Last 1 hour</option>
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="all">All time</option>
          </select>

          <button
            className="btn btn-secondary"
            onClick={() => {
              setQuery('');
              setSeverity('all');
              setTimeRange('24h');
              setStatusFilter('all');
            }}
          >
            Clear
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3">
          {isLoading ? (
            <LoadingTable />
          ) : filtered.length === 0 ? (
            <EmptyState
              title="No insights match your filters"
              subtitle="Try widening time range or clearing severity/status filters."
            />
          ) : (
            <div className="table-container">
              <div className="section-header">
                <div className="section-title">
                  <span className="font-semibold">Insights</span>
                  <span className="badge badge-neutral">{filtered.length}</span>
                </div>
                <div className="text-xs text-[var(--color-text-muted)]">Click a row to view detail</div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="table-header">
                    <tr>
                      <th>Severity</th>
                      <th>Summary</th>
                      <th className="hidden md:table-cell">Confidence</th>
                      <th className="hidden md:table-cell">Evidence</th>
                      <th className="hidden md:table-cell">Time</th>
                      <th className="text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="table-body">
                    {filtered.map((i) => {
                      const sev = normalizeSeverity(i.severity);
                      const isSelected = i.insight_id === selected?.insight_id;
                      const local = localStore[i.insight_id];
                      const st: InsightStatus = local?.status || 'open';
                      const conf = Math.round(coerceConfidence01(i.confidence) * 100);

                      return (
                        <tr
                          key={i.insight_id}
                          className={isSelected ? 'bg-slate-50' : ''}
                          onClick={() => setSelectedId(i.insight_id)}
                          style={{ cursor: 'pointer' }}
                        >
                          <td>
                            <span className={`badge ${severityBadgeClass(sev)}`}>
                              <span className="badge-dot" />
                              {sev.toUpperCase()}
                            </span>
                          </td>
                          <td>
                            <div className="min-w-[260px]">
                              <div className="text-sm font-semibold text-[var(--color-text-primary)] line-clamp-2">{i.summary}</div>
                              <div className="text-xs text-[var(--color-text-muted)] font-mono">{i.insight_id}</div>
                            </div>
                          </td>
                          <td className="hidden md:table-cell">
                            <span className="badge badge-neutral">{conf}%</span>
                          </td>
                          <td className="hidden md:table-cell">
                            <span className="badge badge-neutral">{(i.evidence_ids || []).length}</span>
                          </td>
                          <td className="hidden md:table-cell">
                            <span className="text-xs text-[var(--color-text-muted)]">{formatRelativeTime(i.timestamp)}</span>
                          </td>
                          <td className="text-right" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center justify-end gap-2">
                              {statusBadge(st)}
                              <button className="btn btn-ghost" onClick={() => setStatus(i.insight_id, st === 'acknowledged' ? 'open' : 'acknowledged')} title="Ack">
                                ACK
                              </button>
                              <button className="btn btn-ghost" onClick={() => setStatus(i.insight_id, st === 'resolved' ? 'open' : 'resolved')} title="Resolve">
                                DONE
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-2">
          {selected ? (
            <DetailPanel
              insight={selected}
              status={localStore[selected.insight_id]?.status || 'open'}
              onSetStatus={(s) => setStatus(selected.insight_id, s)}
              onClose={() => setSelectedId(null)}
              onOpenAudit={() => router.push('/audit')}
            />
          ) : (
            <EmptyState title="Select an insight" subtitle="Pick a row from the left to see full enterprise detail." />
          )}
        </div>
      </div>

      <div className="p-5 bg-gradient-to-r from-slate-50 via-white to-slate-50 rounded-2xl border border-slate-200">
        <div className="flex items-start gap-4">
          <div className="icon-container icon-container-md bg-gradient-to-br from-slate-900 to-slate-700 shadow-lg flex-shrink-0">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-semibold text-slate-900 mb-1">Enterprise Notes</div>
            <p className="text-sm text-slate-700 leading-relaxed">
              This page is designed for triage and governance.
              Status (Open/Ack/Resolved) is stored locally in the browser for demo workflow.
              For immutable proof and evidence replay, use the Audit view.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
