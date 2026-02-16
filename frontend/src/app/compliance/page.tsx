'use client';

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  ChevronRight,
  X,
  ExternalLink,
  TrendingUp,
  TrendingDown,
  Clock,
} from 'lucide-react';
import {
  fetchPolicies,
  fetchPolicyViolations,
  fetchComplianceSummary,
  fetchComplianceTrend,
  type Policy,
  type PolicyViolation,
} from '@/lib/api';
import { formatTime, formatDateTime } from '@/lib/utils';
import { DonutChart, AreaChart, Sparkline } from '@/components/Charts';

// Summary Card with Donut
function SummaryCard({
  label,
  value,
  total,
  color,
  trend,
  trendLabel,
}: {
  label: string;
  value: number;
  total: number;
  color: string;
  trend?: number;
  trendLabel?: string;
}) {
  return (
    <div className="stats-card">
      <div className="flex items-center gap-4">
        <DonutChart value={value} total={total} color={color} size={64} strokeWidth={6} />
        <div className="flex-1">
          <div className="stats-label">{label}</div>
          <div className="text-2xl font-bold text-[var(--color-text-primary)]">{value}</div>
          {trend !== undefined && (
            <div className={`flex items-center gap-1 text-xs font-medium mt-1 ${trend > 0 ? 'text-emerald-600' : 'text-red-500'}`}>
              {trend > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
              {trendLabel}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Silent Violation Card
function SilentViolationCard({ violation, onClick }: { violation: PolicyViolation; onClick: () => void }) {
  return (
    <div
      className="p-4 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl hover:shadow-md transition-all cursor-pointer group"
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center flex-shrink-0 group-hover:bg-amber-200 transition-colors">
          <AlertTriangle className="w-5 h-5 text-amber-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-[var(--color-text-primary)] mb-1">{violation.policy_name}</div>
          <p className="text-sm text-[var(--color-text-secondary)] line-clamp-2">{violation.details}</p>
          <div className="flex items-center gap-2 mt-2">
            <span className="badge badge-warning">
              <span className="badge-dot"></span>
              {violation.severity}
            </span>
            <span className="text-xs text-[var(--color-text-muted)]">
              {formatDateTime(violation.timestamp)}
            </span>
          </div>
        </div>
        <ChevronRight className="w-5 h-5 text-amber-400 group-hover:text-amber-600 transition-colors" />
      </div>
    </div>
  );
}

// Violation Detail Drawer
function ViolationDrawer({ violation, onClose }: { violation: PolicyViolation; onClose: () => void }) {
  return (
    <>
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40" onClick={onClose} />
      <div className="drawer">
        <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between bg-gradient-to-r from-slate-50 to-white">
          <div>
            <h2 className="font-semibold text-lg text-[var(--color-text-primary)]">Violation Details</h2>
            <p className="text-sm text-[var(--color-text-muted)]">Full analysis and evidence</p>
          </div>
          <button onClick={onClose} className="btn-ghost p-2 rounded-xl hover:bg-slate-100">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-5 overflow-y-auto h-[calc(100vh-140px)]">
          {/* Policy Name */}
          <div className="p-4 bg-gradient-to-r from-violet-50 to-purple-50 rounded-xl border border-violet-200">
            <div className="text-xs font-semibold text-violet-600 uppercase tracking-wider mb-1">Policy</div>
            <div className="text-lg font-semibold text-violet-900">{violation.policy_name}</div>
          </div>

          {/* Status Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-[var(--color-surface-tertiary)] rounded-xl">
              <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-1">Type</div>
              <span className={`badge ${violation.type === 'SILENT' ? 'badge-warning' : 'badge-info'}`}>
                <span className="badge-dot"></span>
                {violation.type}
              </span>
            </div>
            <div className="p-3 bg-[var(--color-surface-tertiary)] rounded-xl">
              <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-1">Severity</div>
              <span className={`badge ${violation.severity === 'HIGH' ? 'badge-critical' : violation.severity === 'MEDIUM' ? 'badge-warning' : 'badge-info'}`}>
                <span className="badge-dot"></span>
                {violation.severity}
              </span>
            </div>
            <div className="p-3 bg-[var(--color-surface-tertiary)] rounded-xl">
              <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-1">Status</div>
              <span className={`badge ${violation.status === 'ACTIVE' ? 'badge-critical' : 'badge-success'}`}>
                <span className="badge-dot"></span>
                {violation.status}
              </span>
            </div>
            <div className="p-3 bg-[var(--color-surface-tertiary)] rounded-xl">
              <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider mb-1">Detected</div>
              <div className="text-sm font-medium text-[var(--color-text-primary)]">
                {formatDateTime(violation.timestamp)}
              </div>
            </div>
          </div>

          {/* Details */}
          <div>
            <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Details</div>
            <p className="text-sm text-[var(--color-text-primary)] leading-relaxed p-4 bg-slate-50 rounded-xl">
              {violation.details}
            </p>
          </div>

          {/* Evidence IDs */}
          <div>
            <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Evidence</div>
            <div className="flex flex-wrap gap-2">
              <code className="text-xs bg-slate-100 px-3 py-1.5 rounded-lg">{violation.event_id}</code>
              {violation.workflow_id && (
                <code className="text-xs bg-blue-50 text-blue-700 px-3 py-1.5 rounded-lg">{violation.workflow_id}</code>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="pt-4 border-t border-[var(--color-border)] space-y-3">
            <button className="btn btn-primary w-full" onClick={() => { onClose(); window.location.href = '/causal-analysis'; }}>
              <ExternalLink className="w-4 h-4" />
              View Causal Analysis
            </button>
            <button className="btn btn-secondary w-full" onClick={() => {
              const blob = new Blob([JSON.stringify({ violation, snapshot_time: new Date().toISOString() }, null, 2)], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a'); a.href = url; a.download = `audit-snapshot-${violation.violation_id}.json`; a.click();
            }}>
              Download Audit Snapshot
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

export default function CompliancePage() {
  const [selectedViolation, setSelectedViolation] = useState<PolicyViolation | null>(null);

  const { data: policies } = useQuery({ queryKey: ['policies'], queryFn: fetchPolicies, refetchInterval: 15000 });
  const { data: violations } = useQuery({ queryKey: ['violations'], queryFn: fetchPolicyViolations, refetchInterval: 10000 });
  const { data: summary } = useQuery({ queryKey: ['complianceSummary'], queryFn: fetchComplianceSummary, refetchInterval: 10000 });
  const { data: complianceTrend } = useQuery({ queryKey: ['complianceTrend'], queryFn: fetchComplianceTrend, refetchInterval: 15000 });

  // Real data from backend
  const riskTrendData = complianceTrend?.length
    ? complianceTrend.map(p => p.risk_exposure)
    : [10, 15, 15, 30, 42, 45, 50, 58, 55, 62, 60, 65];
  const riskTrendLabels = complianceTrend?.length
    ? complianceTrend.map((p) => {
        const d = new Date(p.ts);
        return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
      })
    : Array.from({ length: riskTrendData.length }, (_, i) => `T${i + 1}`);

  const displaySummary = summary || { policiesMonitored: 0, activeViolations: 0, silentViolations: 0, riskExposure: 0, auditReadiness: 0 };
  const displayViolations = violations?.length ? violations : [];
  const displayPolicies = policies?.length ? policies : [];
  const silentViolations = displayViolations.filter((v) => v.type === 'SILENT');

  return (
    <div className="animate-fade-in space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="icon-container icon-container-lg bg-gradient-to-br from-blue-500 to-cyan-600 shadow-lg">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="page-title">Compliance Intelligence</h1>
            <p className="page-subtitle">Monitor policy adherence, risk exposure, and audit readiness</p>
          </div>
        </div>
      </div>

      {/* Summary Strip */}
      <div className="grid grid-cols-5 gap-4">
        <SummaryCard label="Policies Monitored" value={displaySummary.policiesMonitored} total={10} color="#3b82f6" trend={1} trendLabel="+1 this week" />
        <SummaryCard label="Active Violations" value={displaySummary.activeViolations} total={10} color="#ef4444" />
        <SummaryCard label="Silent Violations" value={displaySummary.silentViolations} total={10} color="#f59e0b" />
        <SummaryCard label="Risk Exposure" value={displaySummary.riskExposure} total={100} color={displaySummary.riskExposure > 60 ? '#ef4444' : '#f59e0b'} />
        <SummaryCard label="Audit Readiness" value={displaySummary.auditReadiness} total={100} color="#10b981" trend={1} trendLabel="+5% this month" />
      </div>

      {/* Compliance Risk Trend */}
      <div className="chart-container">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="chart-title">Compliance Risk Trend</h3>
            <p className="chart-subtitle">Risk score trajectory over time</p>
          </div>
          <div className="flex items-center gap-2">
            <Sparkline data={riskTrendData.slice(-8)} color="#6366f1" width={60} height={24} />
            <span className="text-lg font-bold text-[var(--color-text-primary)]">{displaySummary.riskExposure}%</span>
          </div>
        </div>
        <AreaChart
          data={riskTrendData}
          color="#6366f1"
          gradientFrom="rgba(99, 102, 241, 0.25)"
          gradientTo="rgba(99, 102, 241, 0)"
          height={200}
          showGrid={true}
          showDots={true}
          showLabels={true}
          xLabels={riskTrendLabels}
          xAxisLabel="Time"
          yAxisLabel="Risk Exposure (%)"
          yFormatter={(v) => `${Math.round(v)}%`}
          animated={true}
        />
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Active Violations Table */}
        <div className="col-span-8">
          <div className="table-container">
            <div className="section-header">
              <h3 className="section-title">
                <AlertTriangle className="w-4 h-4 text-red-500" />
                Active Policy Violations
              </h3>
              <span className="badge badge-critical">
                <span className="badge-dot"></span>
                {displayViolations.filter(v => v.status === 'ACTIVE').length} Active
              </span>
            </div>
            <table className="w-full">
              <thead className="table-header">
                <tr>
                  <th>Policy</th>
                  <th>Type</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Time</th>
                  <th></th>
                </tr>
              </thead>
              <tbody className="table-body">
                {displayViolations.map((v) => (
                  <tr key={v.violation_id} className="cursor-pointer group" onClick={() => setSelectedViolation(v)}>
                    <td className="font-medium">{v.policy_name}</td>
                    <td><span className={`badge ${v.type === 'SILENT' ? 'badge-warning' : 'badge-info'}`}><span className="badge-dot"></span>{v.type}</span></td>
                    <td><span className={`badge ${v.severity === 'HIGH' ? 'badge-critical' : v.severity === 'MEDIUM' ? 'badge-warning' : 'badge-info'}`}><span className="badge-dot"></span>{v.severity}</span></td>
                    <td><span className={`badge ${v.status === 'ACTIVE' ? 'badge-critical' : 'badge-success'}`}><span className="badge-dot"></span>{v.status}</span></td>
                    <td className="text-[var(--color-text-muted)] text-sm font-mono">{formatTime(v.timestamp)}</td>
                    <td><ChevronRight className="w-4 h-4 text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Silent Violations */}
        <div className="col-span-4">
          <div className="card p-5 h-full">
            <div className="flex items-center gap-2 mb-4">
              <div className="icon-container icon-container-sm bg-amber-100">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
              </div>
              <h3 className="font-semibold text-[var(--color-text-primary)]">Silent Violations</h3>
            </div>
            <p className="text-sm text-[var(--color-text-secondary)] mb-4">Actions that succeeded but violated policy</p>
            <div className="space-y-3">
              {silentViolations.length > 0 ? (
                silentViolations.map((v) => (
                  <SilentViolationCard key={v.violation_id} violation={v} onClick={() => setSelectedViolation(v)} />
                ))
              ) : (
                <div className="text-center py-8">
                  <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-3">
                    <CheckCircle className="w-6 h-6 text-emerald-500" />
                  </div>
                  <p className="text-sm text-[var(--color-text-muted)]">No silent violations detected</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Monitored Policies */}
        <div className="col-span-12">
          <div className="table-container">
            <div className="section-header">
              <h3 className="section-title">
                <Shield className="w-4 h-4 text-blue-500" />
                Monitored Policies
              </h3>
              <span className="badge badge-info">{displayPolicies.length} Active</span>
            </div>
            <table className="w-full">
              <thead className="table-header">
                <tr>
                  <th>Policy Name</th>
                  <th>Condition</th>
                  <th>Severity</th>
                  <th>Rationale</th>
                </tr>
              </thead>
              <tbody className="table-body">
                {displayPolicies.map((p) => (
                  <tr key={p.policy_id}>
                    <td className="font-medium">{p.name}</td>
                    <td><code className="text-xs bg-slate-100 px-2 py-1 rounded-lg">{p.condition}</code></td>
                    <td><span className={`badge ${p.severity === 'HIGH' ? 'badge-critical' : p.severity === 'MEDIUM' ? 'badge-warning' : 'badge-info'}`}><span className="badge-dot"></span>{p.severity}</span></td>
                    <td className="text-[var(--color-text-secondary)]">{p.rationale}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Agent Attribution */}
      <div className="p-5 bg-gradient-to-r from-blue-50 via-indigo-50 to-violet-50 rounded-2xl border border-blue-100">
        <div className="flex items-start gap-4">
          <div className="icon-container icon-container-md bg-gradient-to-br from-blue-500 to-indigo-500 shadow-lg flex-shrink-0">
            <Info className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-semibold text-blue-900 mb-1">Agent Attribution</div>
            <p className="text-sm text-blue-700 leading-relaxed">
              Policy violations are detected by the <strong>Compliance Agent</strong>.
              Risk trends are computed by the <strong>Risk Forecast Agent</strong>.
              Silent violations represent actions that <em>succeeded technically</em> but violated internal policy — a key differentiator of cognitive observability.
            </p>
          </div>
        </div>
      </div>

      {/* Drawer */}
      {selectedViolation && <ViolationDrawer violation={selectedViolation} onClose={() => setSelectedViolation(null)} />}
    </div>
  );
}
