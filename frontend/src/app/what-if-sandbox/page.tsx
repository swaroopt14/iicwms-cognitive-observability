'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { FlaskConical, Play, Shield, TrendingUp, Activity, Sigma } from 'lucide-react';
import { BarChart, DonutChart } from '@/components/Charts';
import { runCompositeWhatIfSandbox, type CompositeWhatIfSandboxResponse } from '@/lib/api';

export default function WhatIfSandboxPage() {
  const router = useRouter();
  const [latencyMagnitude, setLatencyMagnitude] = useState(0.7);
  const [workloadMultiplier, setWorkloadMultiplier] = useState(2.0);
  const [policyExtension, setPolicyExtension] = useState(180);
  const [historyWindowCycles, setHistoryWindowCycles] = useState(5);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<CompositeWhatIfSandboxResponse | null>(null);

  const presets = [
    {
      id: 'paytm_hotfix',
      label: 'Paytm Hotfix Risky Deploy',
      desc: 'High regex/latency risk during deploy with moderate policy relaxation.',
      values: { latency_magnitude: 0.9, workload_multiplier: 2.4, policy_extension_minutes: 210, history_window_cycles: 5 },
    },
    {
      id: 'black_friday',
      label: 'Black Friday Surge',
      desc: 'Extreme workload spike with constrained policy flexibility.',
      values: { latency_magnitude: 1.1, workload_multiplier: 4.2, policy_extension_minutes: 120, history_window_cycles: 8 },
    },
    {
      id: 'safe_rollout',
      label: 'Safe Rollout',
      desc: 'Controlled rollout profile for low-risk deployment windows.',
      values: { latency_magnitude: 0.4, workload_multiplier: 1.4, policy_extension_minutes: 60, history_window_cycles: 6 },
    },
  ] as const;

  const applyPreset = (presetId: string) => {
    const p = presets.find((x) => x.id === presetId);
    if (!p) return;
    setLatencyMagnitude(p.values.latency_magnitude);
    setWorkloadMultiplier(p.values.workload_multiplier);
    setPolicyExtension(p.values.policy_extension_minutes);
    setHistoryWindowCycles(p.values.history_window_cycles);
  };

  const payload = useMemo(() => {
    return {
      latency_magnitude: latencyMagnitude,
      workload_multiplier: workloadMultiplier,
      policy_extension_minutes: policyExtension,
      history_window_cycles: historyWindowCycles,
    };
  }, [latencyMagnitude, workloadMultiplier, policyExtension, historyWindowCycles]);

  const run = async () => {
    setRunning(true);
    try {
      const res = await runCompositeWhatIfSandbox(payload);
      setResult(res);
    } finally {
      setRunning(false);
    }
  };

  const askChronos = (question: string) => {
    const params = new URLSearchParams({
      scenario: 'PAYTM_HOTFIX_FAIL',
      source: 'what-if-sandbox',
      q: question,
      latency: String(latencyMagnitude),
      workload: String(workloadMultiplier),
      policy: String(policyExtension),
      history: String(historyWindowCycles),
    });
    router.push(`/search?${params.toString()}`);
  };

  const chartData = result
    ? [
        Math.round(result.baseline.risk_index),
        Math.round(result.simulated.risk_index),
        Math.round(result.impact_score),
      ]
    : [0, 0, 0];

  const writtenOutcome = useMemo(() => {
    if (!result) return null;
    const riskDelta = result.simulated.risk_index - result.baseline.risk_index;
    const slaDelta = result.simulated.sla_violations - result.baseline.sla_violations;
    const compDelta = result.simulated.compliance_violations - result.baseline.compliance_violations;

    const riskDir = riskDelta > 0 ? 'increases' : riskDelta < 0 ? 'decreases' : 'stays stable';
    const severityText =
      result.simulated.projected_state === 'INCIDENT'
        ? 'critical'
        : result.simulated.projected_state === 'VIOLATION'
          ? 'high'
          : result.simulated.projected_state === 'AT_RISK'
            ? 'medium'
            : 'low';

    return {
      summary: `Simulation predicts a ${severityText} operational impact. Risk ${riskDir} by ${Math.abs(riskDelta).toFixed(1)} points, with SLA violations changing by ${slaDelta.toFixed(1)} and compliance violations by ${compDelta.toFixed(1)}.`,
      graphExplain: `Bar 1 is baseline risk (${Math.round(result.baseline.risk_index)}). Bar 2 is simulated risk after applying your hypothetical changes (${Math.round(result.simulated.risk_index)}). Bar 3 is the normalized impact score (${Math.round(result.impact_score)} / 100), computed from weighted workflow, compliance, and risk deltas.`,
    };
  }, [result]);

  const recommendations = useMemo(() => {
    if (!result) return [];
    const wf = result.logic.wf_components;
    const cv = result.logic.cv_components;
    const rk = result.logic.risk_components;

    const wfTop = Object.entries(wf).sort((a, b) => b[1] - a[1])[0]?.[0];
    const cvTop = Object.entries(cv).sort((a, b) => b[1] - a[1])[0]?.[0];
    const rkTop = Object.entries(rk).sort((a, b) => b[1] - a[1])[0]?.[0];

    const recs: string[] = [];
    if (wfTop?.includes('workload')) recs.push('Reduce concurrent workload (rate-limit jobs or lower deploy concurrency) to cut workflow breach pressure.');
    if (wfTop?.includes('latency')) recs.push('Mitigate latency first (traffic shaping, dependency timeout tuning, or route-level throttling).');
    if (cvTop?.includes('policy')) recs.push('Tighten policy window/guardrails before rollout; avoid extending policy windows during high-risk periods.');
    if (rkTop?.includes('workload')) recs.push('Scale out capacity before change rollout to absorb projected load increase safely.');
    if (rkTop?.includes('latency')) recs.push('Add circuit breaker and retry caps to prevent latency from amplifying into incident state.');

    if (result.simulated.projected_state === 'INCIDENT' || result.simulated.projected_state === 'VIOLATION') {
      recs.unshift('Do not promote this change as-is. Run a safer parameter set and target projected state <= AT_RISK before execution.');
    }

    return recs.slice(0, 5);
  }, [result]);

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center gap-4">
        <div className="icon-container icon-container-lg bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg">
          <FlaskConical className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="page-title">What-If Sandbox</h1>
          <p className="page-subtitle">Composite pre-change simulation with structured deterministic logic (dry-run only).</p>
        </div>
      </div>

      <div className="card p-5">
        <div className="mb-4">
          <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-2">Scenario Presets</div>
          <div className="grid grid-cols-3 gap-3">
            {presets.map((p) => (
              <button
                key={p.id}
                onClick={() => applyPreset(p.id)}
                className="text-left p-3 rounded-xl border border-[var(--color-border)] bg-white hover:border-indigo-300 hover:shadow-sm transition-all"
              >
                <div className="text-sm font-semibold text-[var(--color-text-primary)]">{p.label}</div>
                <div className="text-[11px] text-[var(--color-text-muted)] mt-1">{p.desc}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-4 gap-3">
          <label className="text-sm">
            <div className="mb-1 font-semibold text-[var(--color-text-secondary)]">Latency Magnitude</div>
            <input
              type="number"
              min={0.1}
              max={2}
              step={0.1}
              value={latencyMagnitude}
              onChange={(e) => setLatencyMagnitude(Number(e.target.value))}
              className="w-full px-3 py-2 rounded-lg border border-[var(--color-border)] bg-white"
            />
          </label>

          <label className="text-sm">
            <div className="mb-1 font-semibold text-[var(--color-text-secondary)]">Workload Multiplier</div>
            <input
              type="number"
              min={1}
              max={6}
              step={0.1}
              value={workloadMultiplier}
              onChange={(e) => setWorkloadMultiplier(Number(e.target.value))}
              className="w-full px-3 py-2 rounded-lg border border-[var(--color-border)] bg-white"
            />
          </label>

          <label className="text-sm">
            <div className="mb-1 font-semibold text-[var(--color-text-secondary)]">Policy Extension (min)</div>
            <input
              type="number"
              min={30}
              max={600}
              step={15}
              value={policyExtension}
              onChange={(e) => setPolicyExtension(Number(e.target.value))}
              className="w-full px-3 py-2 rounded-lg border border-[var(--color-border)] bg-white"
            />
          </label>

          <label className="text-sm">
            <div className="mb-1 font-semibold text-[var(--color-text-secondary)]">History Window (cycles)</div>
            <input
              type="number"
              min={1}
              max={50}
              step={1}
              value={historyWindowCycles}
              onChange={(e) => setHistoryWindowCycles(Number(e.target.value))}
              className="w-full px-3 py-2 rounded-lg border border-[var(--color-border)] bg-white"
            />
          </label>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <button className="btn btn-primary" onClick={run} disabled={running}>
            <Play className="w-4 h-4" />
            {running ? 'Running Sandbox...' : 'Run Dry-Run Simulation'}
          </button>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-semibold">
            <Shield className="w-3.5 h-3.5" />
            Persisted: No
          </div>
          <button
            className="btn btn-secondary"
            onClick={() =>
              askChronos(
                `Explain this sandbox result and top mitigation. latency=${latencyMagnitude}, workload=${workloadMultiplier}, policy_extension=${policyExtension}, history_window=${historyWindowCycles}`
              )
            }
          >
            Ask Chronos AI
          </button>
        </div>
      </div>

      {result && (
        <div className="grid grid-cols-3 gap-4">
          <div className="card p-4">
            <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-2">Predicted Outcome</div>
            <BarChart
              data={chartData}
              colors={['#4f46e5', '#818cf8']}
              height={170}
              xLabels={['Baseline Risk', 'Simulated Risk', 'Impact']}
              xAxisLabel="Outcome Dimension"
              yAxisLabel="Score"
              yFormatter={(v) => `${Math.round(v)}`}
            />
            <div className="text-[11px] text-[var(--color-text-muted)] mt-2">Bars: baseline risk, simulated risk, impact score.</div>
          </div>

          <div className="card p-4">
            <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-2">Confidence</div>
            <div className="flex items-center gap-3">
              <DonutChart value={Math.round(result.confidence * 100)} total={100} color="#10b981" size={60} />
              <div>
                <div className="text-lg font-bold text-[var(--color-text-primary)]">{Math.round(result.confidence * 100)}%</div>
                <div className="text-xs text-[var(--color-text-muted)]">{result.confidence_reason}</div>
              </div>
            </div>
          </div>

          <div className="card p-4">
            <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-2">Delta</div>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-[var(--color-text-muted)] inline-flex items-center gap-1"><TrendingUp className="w-3.5 h-3.5" /> Risk Score</span>
                <span className="font-semibold">{Math.round(result.baseline.risk_index)} → {Math.round(result.simulated.risk_index)} ({result.simulated.projected_state})</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[var(--color-text-muted)] inline-flex items-center gap-1"><Activity className="w-3.5 h-3.5" /> SLA Violations</span>
                <span className="font-semibold">{result.baseline.sla_violations.toFixed(1)} → {result.simulated.sla_violations.toFixed(1)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[var(--color-text-muted)]">Compliance Violations</span>
                <span className="font-semibold">{result.baseline.compliance_violations.toFixed(1)} → {result.simulated.compliance_violations.toFixed(1)}</span>
              </div>
            </div>
          </div>

          <div className="card p-4 col-span-3">
            <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-2 inline-flex items-center gap-1">
              <Sigma className="w-3.5 h-3.5" />
              Structured Logic
            </div>
            <div className="text-xs text-[var(--color-text-secondary)] mb-2">{result.logic.equation}</div>
            <div className="grid grid-cols-3 gap-3 text-xs">
              <div className="p-2 rounded-lg bg-slate-50 border border-[var(--color-border)]">
                <div className="font-semibold mb-1">Workflow Components</div>
                {Object.entries(result.logic.wf_components).map(([k, v]) => (
                  <div key={k} className="flex justify-between"><span>{k}</span><span>{v.toFixed(2)}</span></div>
                ))}
              </div>
              <div className="p-2 rounded-lg bg-slate-50 border border-[var(--color-border)]">
                <div className="font-semibold mb-1">Compliance Components</div>
                {Object.entries(result.logic.cv_components).map(([k, v]) => (
                  <div key={k} className="flex justify-between"><span>{k}</span><span>{v.toFixed(2)}</span></div>
                ))}
              </div>
              <div className="p-2 rounded-lg bg-slate-50 border border-[var(--color-border)]">
                <div className="font-semibold mb-1">Risk Components</div>
                {Object.entries(result.logic.risk_components).map(([k, v]) => (
                  <div key={k} className="flex justify-between"><span>{k}</span><span>{v.toFixed(2)}</span></div>
                ))}
              </div>
            </div>
          </div>

          <div className="card p-4 col-span-3">
            <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-2">Written Outcome</div>
            <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">
              {writtenOutcome?.summary}
            </p>
            <p className="text-xs text-[var(--color-text-secondary)] mt-2 leading-relaxed">
              {writtenOutcome?.graphExplain}
            </p>
          </div>

          <div className="card p-4 col-span-3">
            <div className="text-xs font-semibold text-[var(--color-text-muted)] uppercase mb-2">Recommended Changes</div>
            <ul className="space-y-2">
              {recommendations.map((r, i) => (
                <li key={i} className="text-sm text-[var(--color-text-primary)] leading-relaxed">
                  {i + 1}. {r}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-2 mt-3">
              <button
                className="btn btn-secondary text-xs"
                onClick={() =>
                  askChronos(
                    `Given projected_state=${result.simulated.projected_state} and impact_score=${result.impact_score}, what should DevOps do in next 15 minutes?`
                  )
                }
              >
                Ask: DevOps Action Plan
              </button>
              <button
                className="btn btn-secondary text-xs"
                onClick={() =>
                  askChronos(
                    `Create SDE-safe rollout plan for this simulation and list code/deploy guardrails.`
                  )
                }
              >
                Ask: SDE Rollout Guardrails
              </button>
              <button
                className="btn btn-secondary text-xs"
                onClick={() =>
                  askChronos(
                    `Summarize compliance risk and audit evidence expectations for this simulation output.`
                  )
                }
              >
                Ask: Compliance Summary
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
