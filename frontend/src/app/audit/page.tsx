'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  fetchAuditIncidents,
  fetchAuditIncident,
  fetchAuditTimeline,
  fetchRawAuditEvent,
  exportAuditReport,
  type AuditIncident,
  type AuditTimelineItem,
} from '@/lib/api';
import { formatDateTime } from '@/lib/utils';
import { AlertTriangle, FileText, ShieldCheck, Activity, Download, Search } from 'lucide-react';

function RiskBadge({ state }: { state: string }) {
  const normalized = (state || '').toUpperCase();
  const cls =
    normalized === 'INCIDENT' || normalized === 'CRITICAL'
      ? 'badge-critical'
      : normalized === 'VIOLATION' || normalized === 'AT_RISK'
      ? 'badge-warning'
      : 'badge-success';
  return (
    <span className={`badge ${cls}`}>
      <span className="badge-dot" />
      {normalized || 'NORMAL'}
    </span>
  );
}

function TimelineRow({ item, onOpenEvidence }: { item: AuditTimelineItem; onOpenEvidence: (id: string) => void }) {
  return (
    <div className="p-3 rounded-xl border border-[var(--color-border)] bg-white">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase">{item.kind.replace('_', ' ')}</span>
          <span className="text-xs font-mono text-[var(--color-text-muted)]">{item.id}</span>
        </div>
        <span className="text-xs text-[var(--color-text-muted)]">{formatDateTime(item.ts)}</span>
      </div>
      <p className="text-sm text-[var(--color-text-primary)] mt-1">{item.summary}</p>
      <div className="mt-2 flex items-center gap-2 flex-wrap">
        <span className="badge badge-neutral">{Math.round((item.confidence || 0) * (item.confidence <= 1 ? 100 : 1))}% conf</span>
        <span className="badge badge-info">{item.agent}</span>
        {item.evidence_ids.slice(0, 4).map((id) => (
          <button
            key={id}
            onClick={() => onOpenEvidence(id)}
            className="text-xs px-2 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-mono"
          >
            {id}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function AuditPage() {
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [exportBusy, setExportBusy] = useState<'json' | 'csv' | null>(null);

  const { data: incidents } = useQuery({
    queryKey: ['auditIncidents'],
    queryFn: () => fetchAuditIncidents(40),
    refetchInterval: 10000,
  });

  const selectedIncident = useMemo<AuditIncident | null>(() => {
    const list = incidents || [];
    if (selectedIncidentId) {
      return list.find((i) => i.incident_id === selectedIncidentId) || null;
    }
    return list[0] || null;
  }, [incidents, selectedIncidentId]);

  const { data: detail } = useQuery({
    queryKey: ['auditIncidentDetail', selectedIncident?.incident_id],
    queryFn: () => fetchAuditIncident(selectedIncident!.incident_id),
    enabled: !!selectedIncident?.incident_id,
    refetchInterval: 12000,
  });

  const { data: timeline } = useQuery({
    queryKey: ['auditIncidentTimeline', selectedIncident?.incident_id],
    queryFn: () => fetchAuditTimeline(selectedIncident!.incident_id),
    enabled: !!selectedIncident?.incident_id,
    refetchInterval: 12000,
  });

  const shouldLoadRawEvent = !!selectedEvidenceId && selectedEvidenceId.startsWith('evt_');
  const { data: rawEvent } = useQuery({
    queryKey: ['auditRawEvent', selectedEvidenceId],
    queryFn: () => fetchRawAuditEvent(selectedEvidenceId!),
    enabled: shouldLoadRawEvent,
  });

  const displayIncidents = incidents || [];
  const displayTimeline = timeline || [];

  const selectedEvidenceContext = useMemo(() => {
    if (!selectedEvidenceId) return null;
    for (const item of timeline || []) {
      if ((item.evidence_ids || []).includes(selectedEvidenceId)) {
        return item;
      }
    }
    return null;
  }, [selectedEvidenceId, timeline]);

  const handleExport = async (format: 'json' | 'csv') => {
    if (!selectedIncident?.incident_id) return;
    setExportBusy(format);
    try {
      const payload = await exportAuditReport(selectedIncident.incident_id, format);
      const content =
        format === 'csv'
          ? payload?.report?.csv || ''
          : JSON.stringify(payload?.report || payload, null, 2);
      const blob = new Blob([content], { type: format === 'csv' ? 'text/csv' : 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `chronos-audit-${selectedIncident.incident_id}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExportBusy(null);
    }
  };

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="icon-container icon-container-lg bg-gradient-to-br from-rose-500 to-orange-600 shadow-lg">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="page-title">Audit Investigation</h1>
            <p className="page-subtitle">Immutable cycle forensics, timeline replay, and raw evidence proof</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn btn-secondary" onClick={() => handleExport('json')} disabled={!selectedIncident || !!exportBusy}>
            <Download className="w-4 h-4" />
            {exportBusy === 'json' ? 'Exporting...' : 'Export JSON'}
          </button>
          <button className="btn btn-secondary" onClick={() => handleExport('csv')} disabled={!selectedIncident || !!exportBusy}>
            <Download className="w-4 h-4" />
            {exportBusy === 'csv' ? 'Exporting...' : 'Export CSV'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="stats-card">
          <div className="stats-label">Incidents</div>
          <div className="stats-value">{displayIncidents.length}</div>
        </div>
        <div className="stats-card">
          <div className="stats-label">Anomalies</div>
          <div className="stats-value text-amber-600">{detail?.counts?.anomalies || 0}</div>
        </div>
        <div className="stats-card">
          <div className="stats-label">Policy Hits</div>
          <div className="stats-value text-rose-600">{detail?.counts?.policy_hits || 0}</div>
        </div>
        <div className="stats-card">
          <div className="stats-label">Cycle SHA256</div>
          <div className="text-xs font-mono text-[var(--color-text-secondary)] truncate mt-2">{detail?.cycle_sha256 || 'n/a'}</div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-4">
          <div className="card p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Search className="w-4 h-4 text-[var(--color-text-muted)]" />
              <h3 className="font-semibold text-[var(--color-text-primary)]">Recent Incidents</h3>
            </div>
            <div className="space-y-2 max-h-[560px] overflow-auto">
              {displayIncidents.map((incident) => (
                <button
                  key={incident.incident_id}
                  onClick={() => {
                    setSelectedIncidentId(incident.incident_id);
                    setSelectedEvidenceId(null);
                  }}
                  className={`w-full text-left p-3 rounded-xl border transition-all ${
                    selectedIncident?.incident_id === incident.incident_id
                      ? 'border-indigo-300 bg-indigo-50'
                      : 'border-[var(--color-border)] hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-[var(--color-text-muted)]">{incident.incident_id}</span>
                    <RiskBadge state={incident.risk_state} />
                  </div>
                  <div className="text-sm text-[var(--color-text-primary)] mt-1">
                    Risk {incident.risk_score} · A:{incident.anomaly_count} · P:{incident.policy_hit_count}
                  </div>
                  <div className="text-xs text-[var(--color-text-muted)] mt-1">{formatDateTime(incident.timestamp)}</div>
                </button>
              ))}
              {displayIncidents.length === 0 && (
                <div className="text-sm text-[var(--color-text-muted)] py-6 text-center">No audit incidents yet</div>
              )}
            </div>
          </div>
        </div>

        <div className="col-span-8 space-y-6">
          <div className="card p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-500" />
                <h3 className="font-semibold text-[var(--color-text-primary)]">Incident Timeline</h3>
              </div>
              {selectedIncident && <RiskBadge state={selectedIncident.risk_state} />}
            </div>
            <div className="space-y-2 max-h-[360px] overflow-auto">
              {displayTimeline.map((item) => (
                <TimelineRow key={`${item.kind}-${item.id}`} item={item} onOpenEvidence={setSelectedEvidenceId} />
              ))}
              {displayTimeline.length === 0 && (
                <div className="text-sm text-[var(--color-text-muted)] py-6 text-center">Timeline will appear when an incident is selected</div>
              )}
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="w-4 h-4 text-emerald-500" />
              <h3 className="font-semibold text-[var(--color-text-primary)]">Evidence Inspector</h3>
            </div>
            {selectedEvidenceId ? (
              <div className="space-y-3">
                <div className="text-xs font-mono text-[var(--color-text-muted)]">Selected: {selectedEvidenceId}</div>
                {shouldLoadRawEvent ? (
                  <pre className="text-xs bg-slate-900 text-slate-100 p-3 rounded-xl overflow-auto">
                    {JSON.stringify(rawEvent || { loading: true }, null, 2)}
                  </pre>
                ) : (
                  selectedEvidenceContext ? (
                    <div className="p-3 rounded-xl bg-slate-50 border border-[var(--color-border)] space-y-2">
                      <div className="text-xs text-[var(--color-text-muted)] uppercase">Derived Evidence Context</div>
                      <div className="text-sm text-[var(--color-text-primary)]">
                        {selectedEvidenceContext.summary}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
                        <span className="badge badge-neutral">{selectedEvidenceContext.kind}</span>
                        <span className="badge badge-info">{selectedEvidenceContext.agent}</span>
                        <span>{Math.round((selectedEvidenceContext.confidence || 0) * (selectedEvidenceContext.confidence <= 1 ? 100 : 1))}% conf</span>
                      </div>
                    </div>
                  ) : (
                    <div className="p-3 rounded-xl bg-slate-50 border border-[var(--color-border)] text-sm text-[var(--color-text-secondary)]">
                      No matching timeline context found for this evidence ID.
                    </div>
                  )
                )}
              </div>
            ) : (
              <div className="p-3 rounded-xl bg-slate-50 border border-[var(--color-border)] text-sm text-[var(--color-text-secondary)]">
                Click any evidence chip in the timeline to inspect proof (raw event JSON for <code>evt_*</code>, derived context for other IDs).
              </div>
            )}
            <div className="mt-3 p-3 rounded-xl bg-amber-50 border border-amber-200 text-sm text-amber-800 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 mt-0.5" />
              Timeline and artifacts are immutable snapshots of completed reasoning cycles.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
