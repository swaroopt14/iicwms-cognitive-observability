'use client';

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  TrendingUp,
  Info,
  AlertTriangle,
  CheckCircle,
  Activity,
  Zap,
  ArrowUp,
  ArrowDown,
  ExternalLink,
  GitMerge,
  Network,
} from 'lucide-react';
import { fetchRiskIndex, type RiskDataPoint, type RiskContribution } from '@/lib/api';
import { RiskGraph, MultiLineChart, DonutChart, Sparkline } from '@/components/Charts';

// Risk State Colors
const riskStateColors: Record<string, { color: string; bg: string; border: string }> = {
  NORMAL: { color: '#10b981', bg: 'bg-emerald-50', border: 'border-emerald-200' },
  DEGRADED: { color: '#f59e0b', bg: 'bg-amber-50', border: 'border-amber-200' },
  AT_RISK: { color: '#f97316', bg: 'bg-orange-50', border: 'border-orange-200' },
  VIOLATION: { color: '#ef4444', bg: 'bg-red-50', border: 'border-red-200' },
  INCIDENT: { color: '#dc2626', bg: 'bg-red-100', border: 'border-red-300' },
};

// Tooltip Component
function Tooltip({
  point,
  x,
  y,
}: {
  point: RiskDataPoint | null;
  x: number;
  y: number;
}) {
  if (!point) return null;

  const stateConfig = riskStateColors[point.risk_state] || riskStateColors.NORMAL;

  return (
    <div
      className="fixed z-50 bg-white rounded-xl shadow-xl border border-[var(--color-border)] p-4 min-w-[200px] animate-fade-in"
      style={{
        left: Math.min(x + 15, window.innerWidth - 220),
        top: y - 10,
        transform: 'translateY(-100%)',
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-2xl font-bold text-[var(--color-text-primary)]">{Math.round(point.risk_score)}</span>
        <span 
          className={`px-2.5 py-1 rounded-full text-xs font-semibold ${stateConfig.bg} ${stateConfig.border} border`}
          style={{ color: stateConfig.color }}
        >
          {point.risk_state}
        </span>
      </div>
      
      {point.contributions && point.contributions.length > 0 && (
        <div className="border-t border-[var(--color-border)] pt-3 space-y-2">
          <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">Contributors</span>
          {point.contributions.slice(0, 3).map((c, i) => (
            <div key={i} className="flex items-center justify-between text-sm">
              <span className="text-[var(--color-text-secondary)]">{c.agent}</span>
              <span className={`font-semibold ${c.contribution > 0 ? 'text-red-500' : 'text-emerald-500'}`}>
                {c.contribution > 0 ? '+' : ''}{c.contribution}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Contribution Card
function ContributionCard({ contribution }: { contribution: RiskContribution }) {
  const isPositive = contribution.contribution > 0;
  
  return (
    <div className={`p-4 rounded-xl border transition-all hover:shadow-md ${
      isPositive ? 'bg-red-50 border-red-200' : 'bg-emerald-50 border-emerald-200'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-[var(--color-text-primary)]">{contribution.agent}</span>
        <div className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-sm font-bold ${
          isPositive ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-600'
        }`}>
          {isPositive ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
          {isPositive ? '+' : ''}{contribution.contribution}
        </div>
      </div>
      <p className="text-sm text-[var(--color-text-secondary)]">{contribution.reason}</p>
    </div>
  );
}

// Risk Breakdown Card
function RiskBreakdownCard({ 
  label, 
  value, 
  color, 
  sparklineData 
}: { 
  label: string; 
  value: number; 
  color: string;
  sparklineData: number[];
}) {
  return (
    <div className="p-4 bg-white rounded-xl border border-[var(--color-border)] hover:shadow-md transition-all">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-[var(--color-text-secondary)]">{label}</span>
        <span className="text-xl font-bold" style={{ color }}>{value}</span>
      </div>
      <div className="flex items-center gap-3">
        <Sparkline data={sparklineData} color={color} width={80} height={24} />
        <div className="progress-bar flex-1">
          <div
            className="progress-bar-fill"
            style={{ width: `${value}%`, backgroundColor: color }}
          />
        </div>
      </div>
    </div>
  );
}

export default function SystemGraphPage() {
  const router = useRouter();
  const [tooltipData, setTooltipData] = useState<{
    point: RiskDataPoint | null;
    x: number;
    y: number;
  }>({ point: null, x: 0, y: 0 });

  const { data: riskData } = useQuery({
    queryKey: ['riskIndex'],
    queryFn: fetchRiskIndex,
    refetchInterval: 10000,
  });

  const displayData = riskData?.history || [];
  const currentRisk = displayData[displayData.length - 1];
  const previousRisk = displayData[displayData.length - 2];
  const trend = currentRisk && previousRisk ? currentRisk.risk_score - previousRisk.risk_score : 0;

  // Data for multi-line chart
  const multiLineData = [
    { data: displayData.map(d => d.workflow_risk), color: '#3b82f6', label: 'Workflow' },
    { data: displayData.map(d => d.resource_risk), color: '#10b981', label: 'Resource' },
    { data: displayData.map(d => d.compliance_risk), color: '#8b5cf6', label: 'Compliance' },
  ];

  // Sparkline data for breakdown cards
  const workflowSparkline = displayData.slice(-10).map(d => d.workflow_risk);
  const resourceSparkline = displayData.slice(-10).map(d => d.resource_risk);
  const complianceSparkline = displayData.slice(-10).map(d => d.compliance_risk);

  const stateConfig = riskStateColors[currentRisk?.risk_state || 'NORMAL'];

  return (
    <div className="animate-fade-in space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="icon-container icon-container-lg bg-gradient-to-br from-emerald-500 to-teal-600 shadow-lg">
            <TrendingUp className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="page-title">System Risk Index</h1>
            <p className="page-subtitle">Real-time operational risk trajectory — like a stock market for system health</p>
          </div>
        </div>

        {/* Current Status */}
        <div className={`flex items-center gap-4 px-5 py-3 rounded-2xl border ${stateConfig.bg} ${stateConfig.border}`}>
          <DonutChart
            value={currentRisk?.risk_score || 0}
            total={100}
            color={stateConfig.color}
            size={60}
            strokeWidth={6}
            animated={false}
          />
          <div>
            <div className="text-sm font-medium text-[var(--color-text-secondary)]">Current Risk</div>
            <div className="text-2xl font-bold" style={{ color: stateConfig.color }}>
              {currentRisk?.risk_state || 'NORMAL'}
            </div>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4">
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Risk Score</div>
              <div className="stats-value" style={{ color: stateConfig.color }}>
                {currentRisk?.risk_score || 0}
              </div>
            </div>
            <DonutChart value={currentRisk?.risk_score || 0} total={100} color={stateConfig.color} size={50} strokeWidth={5} />
          </div>
        </div>

        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Trend</div>
              <div className={`stats-value flex items-center gap-2 ${trend > 0 ? 'text-red-500' : trend < 0 ? 'text-emerald-500' : 'text-[var(--color-text-muted)]'}`}>
                {trend > 0 ? <ArrowUp className="w-6 h-6" /> : trend < 0 ? <ArrowDown className="w-6 h-6" /> : <Activity className="w-6 h-6" />}
                {trend > 0 ? '+' : ''}{trend}
              </div>
            </div>
            <div className="icon-container icon-container-md bg-slate-100">
              <TrendingUp className="w-5 h-5 text-slate-600" />
            </div>
          </div>
        </div>

        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Data Points</div>
              <div className="stats-value">{displayData.length}</div>
            </div>
            <div className="icon-container icon-container-md bg-blue-100">
              <Activity className="w-5 h-5 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="stats-label">Avg Risk (1h)</div>
              <div className="stats-value">
                {displayData.length > 0 ? Math.round(displayData.reduce((a, b) => a + b.risk_score, 0) / displayData.length) : 0}
              </div>
            </div>
            <div className="icon-container icon-container-md bg-violet-100">
              <Zap className="w-5 h-5 text-violet-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Main Risk Graph */}
      <div className="chart-container">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="chart-title">Risk Index Over Time</h3>
            <p className="chart-subtitle">Hover over points to see detailed breakdown and contributors</p>
          </div>
          <div className="flex items-center gap-4">
            {Object.entries(riskStateColors).slice(0, 4).map(([state, config]) => (
              <div key={state} className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: config.color }}></span>
                <span className="text-xs text-[var(--color-text-muted)]">{state}</span>
              </div>
            ))}
          </div>
        </div>
        <RiskGraph
          data={displayData}
          height={300}
          showZones={true}
          onPointHover={(point, x, y) => setTooltipData({ point, x, y })}
        />
        {tooltipData.point && <Tooltip {...tooltipData} />}
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Risk Breakdown */}
        <div className="col-span-4">
          <div className="card p-5">
            <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-4">Risk Breakdown</h3>
            <div className="space-y-4">
              <RiskBreakdownCard
                label="Workflow Risk"
                value={currentRisk?.workflow_risk || 0}
                color="#3b82f6"
                sparklineData={workflowSparkline}
              />
              <RiskBreakdownCard
                label="Resource Risk"
                value={currentRisk?.resource_risk || 0}
                color="#10b981"
                sparklineData={resourceSparkline}
              />
              <RiskBreakdownCard
                label="Compliance Risk"
                value={currentRisk?.compliance_risk || 0}
                color="#8b5cf6"
                sparklineData={complianceSparkline}
              />
            </div>
          </div>
        </div>

        {/* Multi-line Comparison */}
        <div className="col-span-8">
          <div className="chart-container h-full">
            <h3 className="chart-title mb-4">Risk Component Comparison</h3>
            <MultiLineChart
              datasets={multiLineData}
              height={280}
              showLegend={true}
            />
          </div>
        </div>

        {/* Recent Contributions */}
        <div className="col-span-12">
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">Recent Risk Contributions</h3>
              <span className="badge badge-neutral">{currentRisk?.contributions?.length || 0} agents</span>
            </div>
            <div className="grid grid-cols-3 gap-4">
              {currentRisk?.contributions?.map((c, i) => (
                <ContributionCard key={i} contribution={c} />
              )) || (
                <div className="col-span-3 text-center py-8">
                  <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
                  <p className="text-[var(--color-text-muted)]">No significant risk contributions</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Quick Navigation */}
      <div className="grid grid-cols-3 gap-4">
        <button onClick={() => router.push('/anomaly-center')} className="p-4 rounded-xl border border-[var(--color-border)] bg-white hover:shadow-md hover:border-amber-200 transition-all text-left group">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
              <Zap className="w-4 h-4 text-amber-600" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-semibold text-[var(--color-text-primary)] group-hover:text-amber-600 transition-colors">Anomaly Center</div>
              <div className="text-xs text-[var(--color-text-muted)]">View detected anomalies</div>
            </div>
            <ExternalLink className="w-4 h-4 text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </button>
        <button onClick={() => router.push('/causal-analysis')} className="p-4 rounded-xl border border-[var(--color-border)] bg-white hover:shadow-md hover:border-indigo-200 transition-all text-left group">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
              <GitMerge className="w-4 h-4 text-indigo-600" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-semibold text-[var(--color-text-primary)] group-hover:text-indigo-600 transition-colors">Causal Analysis</div>
              <div className="text-xs text-[var(--color-text-muted)]">Explore cause-effect chains</div>
            </div>
            <ExternalLink className="w-4 h-4 text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </button>
        <button onClick={() => router.push('/compliance')} className="p-4 rounded-xl border border-[var(--color-border)] bg-white hover:shadow-md hover:border-red-200 transition-all text-left group">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-red-100 flex items-center justify-center">
              <AlertTriangle className="w-4 h-4 text-red-600" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-semibold text-[var(--color-text-primary)] group-hover:text-red-600 transition-colors">Compliance</div>
              <div className="text-xs text-[var(--color-text-muted)]">Check policy violations</div>
            </div>
            <ExternalLink className="w-4 h-4 text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </button>
      </div>

      {/* Info */}
      <div className="p-5 bg-gradient-to-r from-indigo-50 via-violet-50 to-purple-50 rounded-2xl border border-indigo-100">
        <div className="flex items-start gap-4">
          <div className="icon-container icon-container-md bg-gradient-to-br from-indigo-500 to-violet-500 shadow-lg flex-shrink-0">
            <Info className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-semibold text-indigo-900 mb-1">Why This Graph Matters</div>
            <p className="text-sm text-indigo-700 leading-relaxed">
              Unlike traditional metrics, this graph shows <strong>operational risk trajectory</strong>.
              Every movement is explainable — hover over points to see which agents contributed and why.
              This answers: &quot;Are we getting safer or riskier?&quot; and &quot;What caused the change?&quot;
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
