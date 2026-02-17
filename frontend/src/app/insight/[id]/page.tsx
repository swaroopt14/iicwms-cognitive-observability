'use client';

import { useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, ShieldCheck, Lightbulb, Clock } from 'lucide-react';

import { fetchInsightById, type Insight } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';
import { DonutChart } from '@/components/Charts';

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

function coerceConfidence01(v: number): number {
  const x = Number.isFinite(v) ? v : 0;
  return Math.max(0, Math.min(1, x));
}

function InsightDetail({ insight }: { insight: Insight }) {
  const sev = (insight.severity || 'low').toLowerCase();
  const conf = Math.round(coerceConfidence01(insight.confidence) * 100);
  const color = severityColor(sev);

  return (
    <div className="space-y-4">
      <div className="card p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`badge ${severityBadgeClass(sev)}`}>
                <span className="badge-dot" />
                {sev.toUpperCase()}
              </span>
              <span className="badge badge-neutral font-mono">{insight.insight_id}</span>
            </div>
            <h2 className="mt-3 text-lg font-semibold text-[var(--color-text-primary)] leading-snug">{insight.summary}</h2>
            <div className="mt-2 flex items-center gap-3 text-xs text-[var(--color-text-muted)]">
              <span className="inline-flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                {formatDateTime(insight.timestamp)}
              </span>
              <span className="badge badge-neutral">evidence {(insight.evidence_ids || []).length}</span>
              <span className="badge badge-neutral">actions {(insight.recommended_actions || []).length}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <DonutChart value={conf} total={100} color={color} size={54} strokeWidth={5} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Why It Matters</div>
          <p className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">{insight.why_it_matters}</p>
        </div>
        <div className="card p-5 border-amber-200 bg-gradient-to-r from-amber-50 to-orange-50">
          <div className="text-xs font-semibold text-amber-800 uppercase tracking-wider">Impact If Ignored</div>
          <p className="mt-2 text-sm text-amber-700 leading-relaxed">{insight.what_happens_if_ignored}</p>
        </div>
      </div>

      <div className="card p-5">
        <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Recommended Actions</div>
        <div className="mt-3 space-y-2">
          {(insight.recommended_actions || []).map((a, i) => (
            <div key={i} className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 bg-slate-50">
              <span className="w-7 h-7 rounded-full bg-white border border-slate-200 flex items-center justify-center text-xs font-bold text-slate-700 flex-shrink-0">
                {i + 1}
              </span>
              <div className="text-sm text-[var(--color-text-secondary)]">{a}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card p-5">
        <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Evidence IDs</div>
        <div className="mt-3 flex flex-wrap gap-2">
          {(insight.evidence_ids || []).map((id) => (
            <span key={id} className="text-xs font-mono px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 border border-slate-200">
              {id}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function InsightDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = typeof params?.id === 'string' ? params.id : Array.isArray(params?.id) ? params.id[0] : '';

  const { data } = useQuery({
    queryKey: ['insight', id],
    queryFn: () => fetchInsightById(id),
    enabled: !!id,
    refetchInterval: 12000,
  });

  const insight = useMemo(() => data || null, [data]);

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="icon-container icon-container-lg bg-gradient-to-br from-slate-900 to-slate-700 shadow-lg">
            <Lightbulb className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="page-title">Insight Detail</h1>
            <p className="page-subtitle">Executive summary with evidence IDs for audit-grade traceability</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn btn-secondary" onClick={() => router.push('/insight-feed')}>
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <button className="btn btn-secondary" onClick={() => router.push('/audit')}>
            <ShieldCheck className="w-4 h-4" />
            Open Audit
          </button>
        </div>
      </div>

      {!insight ? (
        <div className="card p-6">
          <div className="text-sm text-[var(--color-text-muted)]">Loading insight `{id}`...</div>
        </div>
      ) : (
        <InsightDetail insight={insight} />
      )}
    </div>
  );
}
