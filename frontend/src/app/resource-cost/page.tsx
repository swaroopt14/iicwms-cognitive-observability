'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import {
  DollarSign,
  Cpu,
  HardDrive,
  Wifi,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Info,
  ChevronRight,
  X,
  ExternalLink,
  Zap,
  Activity,
  Server,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Filter,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import { formatTime, formatDateTime } from '@/lib/utils';
import { DonutChart, AreaChart, Sparkline, BarChart, MultiLineChart } from '@/components/Charts';
import { fetchResources, fetchCostTrend, fetchResourceTrend, type ResourceData, type CostTrendPoint } from '@/lib/api';

// ============================================
// Types
// ============================================
interface ResourceMetric extends ResourceData {
  // Re-export backend type
}

interface CostAnomaly {
  id: string;
  resource: string;
  type: string;
  issue: string;
  severity: 'high' | 'medium' | 'low';
  detected_by: string;
  timestamp: string;
  evidence_ids: string[];
  cost_impact: number;
}

interface WorkflowCostImpact {
  workflow_id: string;
  workflow_name: string;
  resources_used: string[];
  cost_impact: 'high' | 'medium' | 'low';
  risk: string;
  spend_rate: number;
  trend: number[];
}

// ============================================
// Workflow check configurations
// ============================================
const WORKFLOW_CHECKS: WorkflowCostImpact[] = [
  {
    workflow_id: 'wf_onboarding_17',
    workflow_name: 'User Onboarding',
    resources_used: ['vm_2', 'vm_3', 'net_3'],
    cost_impact: 'high',
    risk: 'SLA Risk — deploy delay',
    spend_rate: 5.35,
    trend: [3.2, 3.5, 4.1, 4.8, 5.0, 5.2, 5.35],
  },
  {
    workflow_id: 'wf_deployment_03',
    workflow_name: 'Service Deployment',
    resources_used: ['vm_2', 'vm_8'],
    cost_impact: 'medium',
    risk: 'Normal',
    spend_rate: 5.65,
    trend: [5.0, 5.2, 5.3, 5.4, 5.5, 5.6, 5.65],
  },
];

// ============================================
// Stacked Cost Bar Chart (AWS Cost Explorer style) — uses real data
// ============================================
function CostBarChart({ height = 260, costData }: { height?: number; costData: CostTrendPoint[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    const w = rect.width;
    const h = rect.height;

    ctx.clearRect(0, 0, w, h);

    const padding = { top: 20, right: 20, bottom: 40, left: 50 };
    const plotW = w - padding.left - padding.right;
    const plotH = h - padding.top - padding.bottom;

    if (plotW <= 0 || plotH <= 0) return;

    const points = costData.length > 0 ? costData : [{ cost: 10, avg_utilization: 20, timestamp: '' }];
    const maxCost = Math.max(...points.map(p => p.cost)) * 1.2 || 100;
    const barCount = points.length;
    const barW = Math.max(4, (plotW / Math.max(barCount, 1)) - 6);

    // Grid
    ctx.strokeStyle = '#f1f5f9';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (plotH / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(w - padding.right, y);
      ctx.stroke();
      ctx.fillStyle = '#94a3b8';
      ctx.font = '10px Inter, system-ui';
      ctx.textAlign = 'right';
      const val = maxCost - (maxCost / 4) * i;
      ctx.fillText(`$${val.toFixed(0)}`, padding.left - 8, y + 3);
    }
    ctx.setLineDash([]);

    // Bars from real data
    points.forEach((p, idx) => {
      const x = padding.left + idx * (barW + 6) + 3;
      const barH = (p.cost / maxCost) * plotH;
      const y = padding.top + plotH - barH;

      // Gradient bar
      const grad = ctx.createLinearGradient(x, y, x, y + barH);
      const utilColor = p.avg_utilization > 80 ? '#ef4444' : p.avg_utilization > 60 ? '#f59e0b' : '#6366f1';
      grad.addColorStop(0, utilColor);
      grad.addColorStop(1, `${utilColor}aa`);

      ctx.beginPath();
      ctx.roundRect(x, y, barW, barH, [4, 4, 0, 0]);
      ctx.fillStyle = grad;
      ctx.fill();

      // X-axis label
      if (p.timestamp) {
        ctx.fillStyle = '#94a3b8';
        ctx.font = '9px Inter, system-ui';
        ctx.textAlign = 'center';
        const label = p.timestamp.slice(11, 16) || `${idx}`;
        ctx.fillText(label, x + barW / 2, h - padding.bottom + 16);
      }
    });

    // Legend
    const categories = [
      { label: 'Low Util (<60%)', color: '#6366f1' },
      { label: 'Med Util (60-80%)', color: '#f59e0b' },
      { label: 'High Util (>80%)', color: '#ef4444' },
    ];
    let legendX = padding.left;
    const legendY = h - 8;
    categories.forEach((cat) => {
      ctx.fillStyle = cat.color;
      ctx.beginPath();
      ctx.roundRect(legendX, legendY - 8, 10, 10, 2);
      ctx.fill();
      ctx.fillStyle = '#64748b';
      ctx.font = '10px Inter, system-ui';
      ctx.textAlign = 'left';
      ctx.fillText(cat.label, legendX + 14, legendY);
      legendX += ctx.measureText(cat.label).width + 28;
    });
  }, [costData]);

  return <canvas ref={canvasRef} style={{ width: '100%', height }} className="w-full" />;
}

// ============================================
// Resource Usage Multi-Line Chart — uses real data
// ============================================
function ResourceUsageChart({ height = 220, resourceTrend }: { height?: number; resourceTrend: Record<string, Array<{metric: string; value: number; timestamp: string}>> }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    const w = rect.width;
    const h = rect.height;

    ctx.clearRect(0, 0, w, h);

    const padding = { top: 10, right: 20, bottom: 35, left: 40 };
    const plotW = w - padding.left - padding.right;
    const plotH = h - padding.top - padding.bottom;

    if (plotW <= 0 || plotH <= 0) return;

    // Build datasets from real resource trend data
    // Aggregate all resources: pick CPU, Memory, and Network metrics
    const cpuValues: number[] = [];
    const memValues: number[] = [];
    const netValues: number[] = [];

    Object.values(resourceTrend).forEach(metrics => {
      metrics.forEach(m => {
        if (m.metric === 'cpu_percent') cpuValues.push(m.value);
        else if (m.metric === 'memory_percent') memValues.push(m.value);
        else if (m.metric === 'network_latency_ms') netValues.push(Math.min(m.value / 5, 100)); // normalize to 0-100
      });
    });

    // If no real data, show empty chart
    const datasets = [
      { label: 'CPU %', color: '#6366f1', data: cpuValues.length > 0 ? cpuValues.slice(-20) : [0] },
      { label: 'Memory %', color: '#10b981', data: memValues.length > 0 ? memValues.slice(-20) : [0] },
      { label: 'Network (norm)', color: '#f59e0b', data: netValues.length > 0 ? netValues.slice(-20) : [0] },
    ];

    const maxVal = 100;

    // Grid
    ctx.strokeStyle = '#f1f5f9';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (plotH / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(w - padding.right, y);
      ctx.stroke();
      ctx.fillStyle = '#94a3b8';
      ctx.font = '10px Inter, system-ui';
      ctx.textAlign = 'right';
      ctx.fillText(`${100 - i * 25}%`, padding.left - 6, y + 3);
    }
    ctx.setLineDash([]);

    // Stress zone (above 80%)
    const stressY = padding.top;
    const stressH = plotH * 0.2;
    ctx.fillStyle = 'rgba(239, 68, 68, 0.05)';
    ctx.fillRect(padding.left, stressY, plotW, stressH);
    ctx.fillStyle = '#fca5a5';
    ctx.font = '9px Inter, system-ui';
    ctx.textAlign = 'left';
    ctx.fillText('Stress Zone', padding.left + 4, stressY + 12);

    // Draw lines
    datasets.forEach((ds) => {
      if (ds.data.length < 2) return;
      const dataPoints = ds.data.length;
      const points = ds.data.map((v, i) => ({
        x: padding.left + (plotW / Math.max(dataPoints - 1, 1)) * i,
        y: padding.top + plotH - (Math.min(v, maxVal) / maxVal) * plotH,
      }));

      // Area fill
      const gradient = ctx.createLinearGradient(0, padding.top, 0, h - padding.bottom);
      gradient.addColorStop(0, `${ds.color}20`);
      gradient.addColorStop(1, `${ds.color}00`);

      ctx.beginPath();
      ctx.moveTo(points[0].x, h - padding.bottom);
      points.forEach(p => ctx.lineTo(p.x, p.y));
      ctx.lineTo(points[points.length - 1].x, h - padding.bottom);
      ctx.closePath();
      ctx.fillStyle = gradient;
      ctx.fill();

      // Line
      ctx.beginPath();
      points.forEach((p, i) => { i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y); });
      ctx.strokeStyle = ds.color;
      ctx.lineWidth = 2;
      ctx.lineCap = 'round';
      ctx.stroke();

      // End dot
      const last = points[points.length - 1];
      ctx.beginPath();
      ctx.arc(last.x, last.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = ds.color;
      ctx.fill();
      ctx.strokeStyle = 'white';
      ctx.lineWidth = 2;
      ctx.stroke();
    });

    // Legend
    let lx = padding.left;
    datasets.forEach((ds) => {
      ctx.fillStyle = ds.color;
      ctx.beginPath();
      ctx.arc(lx + 4, h - 8, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#64748b';
      ctx.font = '10px Inter, system-ui';
      ctx.textAlign = 'left';
      ctx.fillText(ds.label, lx + 12, h - 5);
      lx += ctx.measureText(ds.label).width + 28;
    });
  }, [resourceTrend]);

  return <canvas ref={canvasRef} style={{ width: '100%', height }} className="w-full" />;
}

// ============================================
// Resource Detail Drawer
// ============================================
function ResourceDetailDrawer({ resource, onClose }: { resource: ResourceData; onClose: () => void }) {
  const statusColor = resource.status === 'critical' ? '#ef4444' : resource.status === 'warning' ? '#f59e0b' : '#10b981';
  const typeIcon = resource.type === 'compute' ? Cpu : resource.type === 'network' ? Wifi : HardDrive;
  const TypeIcon = typeIcon;

  return (
    <>
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40" onClick={onClose} />
      <div className="drawer">
        <div className="p-5 border-b border-[var(--color-border)] flex items-center justify-between bg-gradient-to-r from-slate-50 to-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shadow-md" style={{ backgroundColor: statusColor }}>
              <TypeIcon className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-lg text-[var(--color-text-primary)]">{resource.name}</h2>
              <code className="text-xs text-[var(--color-text-muted)]">{resource.resource_id}</code>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-slate-100 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-5 overflow-y-auto h-[calc(100vh-140px)]">
          {/* Status & Type */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-xl border border-[var(--color-border)]">
              <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider mb-1">Type</div>
              <span className="text-sm font-semibold text-[var(--color-text-primary)] capitalize">{resource.type}</span>
            </div>
            <div className="p-3 rounded-xl border border-[var(--color-border)]">
              <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider mb-1">Status</div>
              <span className="px-2.5 py-1 rounded-full text-xs font-semibold" style={{ backgroundColor: `${statusColor}15`, color: statusColor }}>
                {resource.status.toUpperCase()}
              </span>
            </div>
          </div>

          {/* Metrics */}
          <div className="p-4 rounded-xl border border-[var(--color-border)]">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider mb-3">Current Metrics</div>
            <div className="space-y-3">
              {[
                { key: 'cpu', label: 'CPU', value: resource.metrics.cpu, unit: '%' },
                { key: 'memory', label: 'Memory', value: resource.metrics.memory, unit: '%' },
                { key: 'network_latency', label: 'Network Latency', value: resource.metrics.network_latency, unit: 'ms' },
              ].map(({ key, label, value, unit }) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-sm text-[var(--color-text-secondary)]">{label}</span>
                  <div className="flex items-center gap-3">
                    <div className="w-24 h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full rounded-full transition-all" style={{
                        width: `${Math.min(unit === 'ms' ? value / 5 : value, 100)}%`,
                        backgroundColor: (unit === '%' ? value : value / 5) > 85 ? '#ef4444' : (unit === '%' ? value : value / 5) > 60 ? '#f59e0b' : '#10b981',
                      }} />
                    </div>
                    <span className="text-sm font-mono font-semibold w-16 text-right">{value}{unit}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Historical Trend */}
          <div className="p-4 rounded-xl border border-[var(--color-border)]">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider mb-3">Historical Trend</div>
            <Sparkline data={resource.trend} color={statusColor} width={320} height={48} />
          </div>

          {/* Cost */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200">
            <div className="text-[10px] text-emerald-700 uppercase tracking-wider mb-1">Cost Rate</div>
            <div className="text-2xl font-bold text-emerald-800">${resource.cost_per_hour.toFixed(2)}/hr</div>
            <div className="text-xs text-emerald-600 mt-1">${(resource.cost_per_hour * 24).toFixed(2)}/day estimated</div>
          </div>

          {/* Associated Workflows */}
          {resource.associated_workflows.length > 0 && (
            <div>
              <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Associated Workflows</div>
              <div className="flex flex-wrap gap-2">
                {resource.associated_workflows.map((wf) => (
                  <code key={wf} className="text-xs bg-indigo-50 text-indigo-700 px-3 py-1.5 rounded-lg border border-indigo-200">{wf}</code>
                ))}
              </div>
            </div>
          )}

          {/* Anomalies */}
          {resource.anomalies.length > 0 && (
            <div>
              <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Detected Anomalies</div>
              {resource.anomalies.map((a, i) => (
                <div key={i} className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-sm text-amber-700">
                  <AlertTriangle className="w-3.5 h-3.5 inline mr-2 text-amber-500" />
                  {a}
                </div>
              ))}
            </div>
          )}

          {/* Agent Source */}
          <div className="p-3 bg-slate-50 rounded-xl">
            <div className="text-[10px] text-[var(--color-text-muted)]">Detected By</div>
            <div className="text-sm font-semibold text-[var(--color-text-primary)] mt-0.5">{resource.agent_source}</div>
          </div>

          {/* Actions */}
          <div className="pt-4 border-t border-[var(--color-border)] space-y-3">
            <button className="btn btn-primary w-full" onClick={() => { onClose(); window.location.href = '/anomaly-center'; }}>
              <ExternalLink className="w-4 h-4" /> View Evidence
            </button>
            <button className="btn btn-secondary w-full" onClick={() => { onClose(); window.location.href = '/system-graph'; }}>
              Jump to System Graph
            </button>
            <button className="btn btn-secondary w-full" onClick={() => {
              const blob = new Blob([JSON.stringify({ resource, snapshot_time: new Date().toISOString() }, null, 2)], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a'); a.href = url; a.download = `resource-snapshot-${resource.resource_id}.json`; a.click();
            }}>
              Export Snapshot
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

// ============================================
// Predictive Cost Panel
// ============================================
function PredictiveCostPanel() {
  return (
    <div className="p-5 bg-gradient-to-br from-violet-50 via-purple-50 to-indigo-50 rounded-2xl border border-violet-200">
      <div className="flex items-start gap-4">
        <div className="icon-container icon-container-md bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg flex-shrink-0">
          <TrendingUp className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="font-semibold text-violet-900">Predictive Cost & Resource Risk</h3>
              <p className="text-xs text-violet-600">Risk Forecast Agent — next 60 minutes</p>
            </div>
            <span className="badge badge-warning">
              <span className="badge-dot"></span>
              Active Forecast
            </span>
          </div>

          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="p-3 bg-white/80 rounded-xl border border-violet-200">
              <div className="text-[10px] text-violet-600 uppercase tracking-wider">Projected Spend</div>
              <div className="text-xl font-bold text-violet-900 mt-1">+18%</div>
              <div className="text-xs text-violet-500">next hour</div>
            </div>
            <div className="p-3 bg-white/80 rounded-xl border border-violet-200">
              <div className="text-[10px] text-violet-600 uppercase tracking-wider">Saturation Risk</div>
              <div className="text-xl font-bold text-red-600 mt-1">HIGH</div>
              <div className="text-xs text-violet-500">vm_2 compute</div>
            </div>
            <div className="p-3 bg-white/80 rounded-xl border border-violet-200">
              <div className="text-[10px] text-violet-600 uppercase tracking-wider">If No Action</div>
              <div className="text-xl font-bold text-amber-600 mt-1">SLA Breach</div>
              <div className="text-xs text-violet-500">~15 min</div>
            </div>
          </div>

          <div className="p-4 bg-white/60 rounded-xl border border-violet-200">
            <div className="flex items-start gap-2">
              <Zap className="w-4 h-4 text-violet-500 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-violet-800 leading-relaxed">
                <strong>Forecast:</strong> At current trend, compute spend will increase by 18% in the next hour 
                due to sustained deployment retries on vm_2. Network costs are also trending up from latency-induced 
                retry loops. Recommend throttling non-critical jobs and pre-notifying ops team.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================
// Main Page
// ============================================
export default function ResourceCostPage() {
  const [selectedResource, setSelectedResource] = useState<ResourceData | null>(null);
  const [resourceScope, setResourceScope] = useState('all');
  const [resources, setResources] = useState<ResourceMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string>('');

  const [costTrendData, setCostTrendData] = useState<CostTrendPoint[]>([]);
  const [resourceTrendData, setResourceTrendData] = useState<Record<string, Array<{metric: string; value: number; timestamp: string}>>>({});

  // Fetch resources and trend data from backend
  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        setLoading(true);
        const [data, costTrend, resTrend] = await Promise.all([
          fetchResources(),
          fetchCostTrend(),
          fetchResourceTrend(),
        ]);
        if (mounted) {
          setResources(data.map((r) => ({ ...r })));
          setCostTrendData(costTrend || []);
          setResourceTrendData(resTrend || {});
          setLastRefresh(new Date().toLocaleTimeString());
          setError(null);
        }
      } catch {
        if (mounted) {
          setError('Backend not running — waiting for connection');
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    // Poll every 10s
    const interval = setInterval(load, 10000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  // Generate anomalies from resource data
  const costAnomalies: CostAnomaly[] = useMemo(() => {
    return resources
      .filter((r) => r.anomalies.length > 0)
      .map((r, i) => ({
        id: `ca_${i}`,
        resource: r.resource_id,
        type: r.type.charAt(0).toUpperCase() + r.type.slice(1),
        issue: r.anomalies[0],
        severity: (r.status === 'critical' ? 'high' : r.status === 'warning' ? 'medium' : 'low') as 'high' | 'medium' | 'low',
        detected_by: r.agent_source,
        timestamp: new Date().toISOString(),
        evidence_ids: [`metric_${r.resource_id}`],
        cost_impact: r.status === 'critical' ? 12.50 : r.status === 'warning' ? 4.20 : 1.80,
      }));
  }, [resources]);

  // Update workflow impact with real resource cost data
  const workflowImpact: WorkflowCostImpact[] = useMemo(() => {
    return WORKFLOW_CHECKS.map((wf) => {
      const usedResources = resources.filter((r) => wf.resources_used.includes(r.resource_id));
      const spend = usedResources.reduce((a, r) => a + r.cost_per_hour, 0);
      const hasRisk = usedResources.some((r) => r.status !== 'normal');
      return {
        ...wf,
        spend_rate: spend > 0 ? spend : wf.spend_rate,
        risk: hasRisk ? 'SLA Risk — resource stress detected' : 'Normal',
        cost_impact: (spend > 5 ? 'high' : spend > 3 ? 'medium' : 'low') as 'high' | 'medium' | 'low',
      };
    });
  }, [resources]);

  // Summary KPIs
  const totalResources = resources.length;
  const spendRate = resources.reduce((a, r) => a + r.cost_per_hour, 0);
  const costAnomalyCount = costAnomalies.length;
  const inefficiencyScore = Math.round(resources.filter((r) => r.status !== 'normal').length / Math.max(resources.length, 1) * 100);
  const costRisk = Math.round(resources.reduce((a, r) => a + (r.status === 'critical' ? 30 : r.status === 'warning' ? 15 : 5), 0));

  // Filter resources
  const filteredResources = resourceScope === 'all'
    ? resources
    : resources.filter(r => r.type === resourceScope);

  return (
    <div className="animate-fade-in space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="icon-container icon-container-lg bg-gradient-to-br from-emerald-500 to-teal-600 shadow-lg">
            <DollarSign className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="page-title">Resource & Cost Intelligence</h1>
            <p className="page-subtitle">Understand infrastructure usage, inefficiencies, and cost risk</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {lastRefresh && (
            <span className="text-xs text-[var(--color-text-muted)] flex items-center gap-1.5">
              {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
              {error ? <span className="text-amber-500">{error}</span> : `Live · ${lastRefresh}`}
            </span>
          )}
          <select
            value={resourceScope}
            onChange={(e) => setResourceScope(e.target.value)}
            className="input w-40"
          >
            <option value="all">All Resources</option>
            <option value="compute">Compute</option>
            <option value="network">Network</option>
            <option value="storage">Storage</option>
          </select>
        </div>
      </div>

      {/* KPI Summary Strip */}
      <div className="grid grid-cols-5 gap-4">
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Active Resources</div>
              <div className="stats-value">{totalResources}</div>
            </div>
            <div className="icon-container icon-container-md bg-blue-100">
              <Server className="w-5 h-5 text-blue-600" />
            </div>
          </div>
        </div>
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Spend Rate</div>
              <div className="stats-value text-emerald-600">${spendRate.toFixed(2)}<span className="text-base font-medium text-[var(--color-text-muted)]">/hr</span></div>
            </div>
            <div className="icon-container icon-container-md bg-emerald-100">
              <DollarSign className="w-5 h-5 text-emerald-600" />
            </div>
          </div>
          <div className="stats-trend stats-trend-up mt-2">
            <TrendingUp className="w-3 h-3" /> Simulated
          </div>
        </div>
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Cost Anomalies</div>
              <div className="stats-value text-amber-500">{costAnomalyCount}</div>
            </div>
            <DonutChart value={costAnomalyCount} total={10} color="#f59e0b" size={40} strokeWidth={4} />
          </div>
        </div>
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Inefficiency Score</div>
              <div className="stats-value text-orange-500">{inefficiencyScore}%</div>
            </div>
            <DonutChart value={inefficiencyScore} total={100} color="#f97316" size={40} strokeWidth={4} />
          </div>
        </div>
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Cost Risk</div>
              <div className="stats-value text-red-500">{costRisk}</div>
            </div>
            <DonutChart value={costRisk} total={100} color="#ef4444" size={40} strokeWidth={4} />
          </div>
        </div>
      </div>

      {/* Section A: Resource Usage Trend */}
      <div className="chart-container">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="chart-title">
              <Activity className="w-4 h-4 text-indigo-500" />
              Resource Usage Trend
            </h3>
            <p className="chart-subtitle">CPU, Memory, and Network latency with stress zones</p>
          </div>
          <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
            <span className="px-2 py-1 bg-red-50 text-red-500 rounded-md border border-red-200">Stress Zone &gt; 80%</span>
          </div>
        </div>
        <ResourceUsageChart height={220} resourceTrend={resourceTrendData} />
      </div>

      {/* Section B: Cost Trend (AWS Cost Explorer style) */}
      <div className="chart-container">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="chart-title">
              <BarChart3 className="w-4 h-4 text-emerald-500" />
              Cost & Usage Report
            </h3>
            <p className="chart-subtitle">Daily spend breakdown by resource category (simulated)</p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-[var(--color-text-primary)]">
              ${costTrendData.length > 0 ? costTrendData.reduce((s, p) => s + p.cost, 0).toFixed(2) : '—'}
            </div>
            <div className="flex items-center gap-1 text-sm text-amber-600 font-medium">
              <ArrowUpRight className="w-4 h-4" />
              {costTrendData.length} data points
            </div>
          </div>
        </div>
        <CostBarChart height={260} costData={costTrendData} />
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Section C: Cost & Resource Anomaly Table */}
        <div className="col-span-8">
          <div className="table-container">
            <div className="section-header">
              <h3 className="section-title">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                Cost & Resource Anomalies
              </h3>
              <span className="badge badge-warning">
                <span className="badge-dot"></span>
                {costAnomalies.length} detected
              </span>
            </div>
            <table className="w-full">
              <thead className="table-header">
                <tr>
                  <th>Resource</th>
                  <th>Type</th>
                  <th>Issue</th>
                  <th>Severity</th>
                  <th>Cost Impact</th>
                  <th></th>
                </tr>
              </thead>
              <tbody className="table-body">
                {costAnomalies.map((a) => {
                  const res = resources.find(r => r.resource_id === a.resource);
                  return (
                    <tr key={a.id} className="cursor-pointer group" onClick={() => res && setSelectedResource(res)}>
                      <td>
                        <div className="flex items-center gap-2">
                          <code className="text-xs">{a.resource}</code>
                        </div>
                      </td>
                      <td><span className="badge badge-neutral text-xs">{a.type}</span></td>
                      <td className="text-sm text-[var(--color-text-secondary)] max-w-[200px] truncate">{a.issue}</td>
                      <td>
                        <span className={`badge ${a.severity === 'high' ? 'badge-critical' : a.severity === 'medium' ? 'badge-warning' : 'badge-info'}`}>
                          <span className="badge-dot"></span>
                          {a.severity.toUpperCase()}
                        </span>
                      </td>
                      <td className="font-mono font-semibold text-red-500 text-sm">${a.cost_impact.toFixed(2)}</td>
                      <td><ChevronRight className="w-4 h-4 text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity" /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Resource Cards */}
        <div className="col-span-4">
          <div className="card p-5">
            <h3 className="font-semibold text-[var(--color-text-primary)] mb-4 flex items-center gap-2">
              <Server className="w-4 h-4 text-[var(--color-text-muted)]" />
              Resource Status
            </h3>
            <div className="space-y-3">
              {filteredResources.map((r) => {
                const statusColor = r.status === 'critical' ? '#ef4444' : r.status === 'warning' ? '#f59e0b' : '#10b981';
                const TypeIcon = r.type === 'compute' ? Cpu : r.type === 'network' ? Wifi : HardDrive;
                return (
                  <div
                    key={r.resource_id}
                    className="p-3 rounded-xl border border-[var(--color-border)] hover:shadow-md hover:border-indigo-200 transition-all cursor-pointer group"
                    onClick={() => setSelectedResource(r)}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${statusColor}15` }}>
                        <TypeIcon className="w-4 h-4" style={{ color: statusColor }} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-semibold text-[var(--color-text-primary)] truncate">{r.name}</div>
                        <div className="text-xs text-[var(--color-text-muted)]">{r.resource_id} · ${r.cost_per_hour.toFixed(2)}/hr</div>
                      </div>
                      <Sparkline data={r.trend} color={statusColor} width={50} height={20} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Section D: Workflow → Resource Impact Map */}
        <div className="col-span-12">
          <div className="table-container">
            <div className="section-header">
              <h3 className="section-title">
                <Zap className="w-4 h-4 text-indigo-500" />
                Workflow → Resource Impact Map
              </h3>
              <span className="badge badge-info">Which workflows cost the most</span>
            </div>
            <table className="w-full">
              <thead className="table-header">
                <tr>
                  <th>Workflow</th>
                  <th>Resources Used</th>
                  <th>Spend Rate</th>
                  <th>Cost Impact</th>
                  <th>Risk</th>
                  <th>Trend</th>
                </tr>
              </thead>
              <tbody className="table-body">
                {workflowImpact.map((wf) => (
                  <tr key={wf.workflow_id}>
                    <td>
                      <div>
                        <div className="font-semibold text-sm">{wf.workflow_name}</div>
                        <code className="text-[10px] text-[var(--color-text-muted)]">{wf.workflow_id}</code>
                      </div>
                    </td>
                    <td>
                      <div className="flex flex-wrap gap-1">
                        {wf.resources_used.map((r) => (
                          <code key={r} className="text-[10px] bg-slate-100 px-2 py-0.5 rounded">{r}</code>
                        ))}
                      </div>
                    </td>
                    <td className="font-mono font-semibold text-sm">${wf.spend_rate.toFixed(2)}/hr</td>
                    <td>
                      <span className={`badge ${wf.cost_impact === 'high' ? 'badge-critical' : wf.cost_impact === 'medium' ? 'badge-warning' : 'badge-info'}`}>
                        <span className="badge-dot"></span>
                        {wf.cost_impact.toUpperCase()}
                      </span>
                    </td>
                    <td className="text-sm text-[var(--color-text-secondary)]">{wf.risk}</td>
                    <td><Sparkline data={wf.trend} color={wf.cost_impact === 'high' ? '#ef4444' : '#f59e0b'} width={60} height={20} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Section E: Predictive Cost & Risk */}
      <PredictiveCostPanel />

      {/* Agent Attribution */}
      <div className="p-5 bg-gradient-to-r from-emerald-50 via-teal-50 to-cyan-50 rounded-2xl border border-emerald-100">
        <div className="flex items-start gap-4">
          <div className="icon-container icon-container-md bg-gradient-to-br from-emerald-500 to-teal-500 shadow-lg flex-shrink-0">
            <Info className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-semibold text-emerald-900 mb-1">This is Not Just Metrics</div>
            <p className="text-sm text-emerald-700 leading-relaxed">
              Traditional tools show CPU %, memory %, and cost numbers. This page explains <strong>why usage spiked</strong>,
              <strong> which workflow caused it</strong>, whether it&apos;s waste or necessary, and <strong>what risk it introduces</strong> to SLA and compliance.
              Resource trends are detected by the <strong>Resource Agent</strong>, cost analysis by the <strong>Cost Agent</strong>,
              and predictions by the <strong>Risk Forecast Agent</strong>.
            </p>
          </div>
        </div>
      </div>

      {/* Resource Detail Drawer */}
      {selectedResource && (
        <ResourceDetailDrawer resource={selectedResource} onClose={() => setSelectedResource(null)} />
      )}
    </div>
  );
}
