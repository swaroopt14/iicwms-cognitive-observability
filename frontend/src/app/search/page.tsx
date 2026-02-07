'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Search,
  Sparkles,
  Send,
  Info,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Zap,
  AlertTriangle,
  CheckCircle,
  Shield,
  Activity,
  TrendingUp,
  GitBranch,
  DollarSign,
  Network,
  User,
  Bot,
  RotateCcw,
  Copy,
  Check,
  Plus,
} from 'lucide-react';
import { DonutChart } from '@/components/Charts';

// ============================================
// Types
// ============================================
interface RAGEvidence {
  id: string;
  type: 'anomaly' | 'event' | 'metric' | 'insight' | 'forecast' | 'policy';
  summary: string;
  confidence: number;
  agent: string;
}

interface CausalStep {
  label: string;
  type: 'cause' | 'effect' | 'risk' | 'outcome';
}

interface RecommendedAction {
  action: string;
  expected_impact: string;
  priority: 'high' | 'medium' | 'low';
}

interface RAGResponse {
  answer: string;
  why_it_matters: string[];
  supporting_evidence: RAGEvidence[];
  causal_chain: CausalStep[];
  recommended_actions: RecommendedAction[];
  confidence: number;
  time_horizon: string;
  uncertainty: string;
  follow_up_queries: string[];
  agents_used: string[];
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  response?: RAGResponse;
  timestamp: string;
}

// ============================================
// Mock Responses
// ============================================
function getMockResponse(query: string): RAGResponse {
  const q = query.toLowerCase();

  if (q.includes('cost') || q.includes('spend') || q.includes('expensive') || q.includes('budget')) {
    return {
      answer: 'Cost is trending 18% above baseline, primarily driven by sustained compute usage on vm_2 due to deployment retries in wf_onboarding_17. Network costs are also elevated from latency-induced retry loops on vm_3.',
      why_it_matters: [
        'Projected overspend of $47/day if current trend continues',
        'Deployment retries are consuming 3x normal compute cycles',
        'Network retry loops amplify both latency and cost simultaneously',
        'Budget threshold will be breached within 6 hours at this rate',
      ],
      supporting_evidence: [
        { id: 'COST_ANOMALY_04', type: 'anomaly', summary: 'Compute spend on vm_2 up 34% in last hour due to retries', confidence: 88, agent: 'ResourceAgent' },
        { id: 'METRIC_NET_09', type: 'metric', summary: 'Network egress cost 2.5x baseline from retry traffic', confidence: 82, agent: 'ResourceAgent' },
        { id: 'WF_RETRY_12', type: 'event', summary: 'wf_onboarding_17 DEPLOY step retried 4 times', confidence: 95, agent: 'WorkflowAgent' },
        { id: 'FORECAST_COST_01', type: 'forecast', summary: 'Budget threshold breach projected in 6 hours', confidence: 71, agent: 'RiskForecastAgent' },
      ],
      causal_chain: [
        { label: 'Network Latency Spike', type: 'cause' },
        { label: 'Deployment Step Retries', type: 'effect' },
        { label: 'Compute Cost Escalation', type: 'effect' },
        { label: 'Budget Threshold Risk', type: 'risk' },
        { label: 'Potential Service Throttling', type: 'outcome' },
      ],
      recommended_actions: [
        { action: 'Throttle non-critical background jobs', expected_impact: 'Reduce compute spend by ~25%', priority: 'high' },
        { action: 'Fix network latency root cause on vm_3', expected_impact: 'Eliminate retry amplification', priority: 'high' },
        { action: 'Set deployment retry limit to 2', expected_impact: 'Cap waste from failed deploys', priority: 'medium' },
      ],
      confidence: 78,
      time_horizon: '1–6 hours',
      uncertainty: 'Based on simulated environment and recent cost trends.',
      follow_up_queries: ['Which workflow is most expensive?', 'Show resource utilization breakdown', 'What if we pause non-critical deployments?'],
      agents_used: ['ResourceAgent', 'WorkflowAgent', 'RiskForecastAgent'],
    };
  }

  if (q.includes('compliance') || q.includes('policy') || q.includes('violation') || q.includes('audit')) {
    return {
      answer: 'The system is approaching a compliance violation state. Policy NO_AFTER_HOURS_WRITE has been triggered 3 times this week, with the latest occurrence at 2:15 AM. A silent violation pattern is forming around SLA-pressured manual overrides.',
      why_it_matters: [
        'Third after-hours write incident this week — pattern, not anomaly',
        'Manual overrides under SLA pressure bypass approval policies',
        'Audit review in 2 weeks may flag systematic non-compliance',
        'Combined policy risk score is 72, up from 45 last week',
      ],
      supporting_evidence: [
        { id: 'POLICY_HIT_01', type: 'policy', summary: 'NO_AFTER_HOURS_WRITE violated at 2:15 AM — repo_A write', confidence: 98, agent: 'ComplianceAgent' },
        { id: 'EVT_45', type: 'event', summary: 'Write access to repo_A by user_42 outside business hours', confidence: 95, agent: 'ComplianceAgent' },
        { id: 'RISK_COMPLIANCE_03', type: 'forecast', summary: 'Compliance risk projected to reach VIOLATION in 2 days', confidence: 68, agent: 'RiskForecastAgent' },
        { id: 'WF_OVERRIDE_07', type: 'event', summary: 'SLA override bypassed approval step in wf_deployment_03', confidence: 88, agent: 'WorkflowAgent' },
      ],
      causal_chain: [
        { label: 'SLA Pressure on Workflows', type: 'cause' },
        { label: 'Manual Override Behavior', type: 'effect' },
        { label: 'After-Hours Access Pattern', type: 'effect' },
        { label: 'Silent Policy Violation', type: 'risk' },
        { label: 'Audit Exposure', type: 'outcome' },
      ],
      recommended_actions: [
        { action: 'Enable time-based access controls', expected_impact: 'Prevent future after-hours writes', priority: 'high' },
        { action: 'Review approval bypass patterns', expected_impact: 'Close SLA override loophole', priority: 'high' },
        { action: 'Pre-audit compliance posture report', expected_impact: 'Reduce audit risk', priority: 'medium' },
      ],
      confidence: 82,
      time_horizon: '2–14 days',
      uncertainty: 'Simulated environment — real audit timelines may vary.',
      follow_up_queries: ['Show all silent violations this week', 'Which users triggered policy breaches?', 'What is the compliance risk trend?'],
      agents_used: ['ComplianceAgent', 'WorkflowAgent', 'RiskForecastAgent'],
    };
  }

  if (q.includes('workflow') || q.includes('sla') || q.includes('deploy') || q.includes('onboarding')) {
    return {
      answer: 'Workflow wf_onboarding_17 is critically degraded. The DEPLOY step has exceeded its expected duration by 108%, directly caused by sustained network latency on vm_3. The workflow confidence has dropped from 92% to 62% over the last 15 minutes.',
      why_it_matters: [
        'SLA breach imminent — DEPLOY step running 2x expected duration',
        'Downstream VERIFY step is blocked, creating cascading delay',
        'This workflow serves the user onboarding pipeline — user-facing impact',
        'Historical pattern: 3 out of 4 similar situations led to manual overrides',
      ],
      supporting_evidence: [
        { id: 'WF_DELAY_07', type: 'event', summary: 'DEPLOY step exceeded SLA by 108% (185s vs 90s expected)', confidence: 96, agent: 'WorkflowAgent' },
        { id: 'RES_LATENCY_12', type: 'metric', summary: 'Network latency on vm_3 at 420ms (3x baseline of 140ms)', confidence: 89, agent: 'ResourceAgent' },
        { id: 'CAUSAL_LINK_04', type: 'insight', summary: 'Causal link: network latency → deploy delay (confidence: 81%)', confidence: 81, agent: 'CausalAgent' },
        { id: 'FORECAST_WF_02', type: 'forecast', summary: 'Workflow projected to fail within 10 minutes without intervention', confidence: 73, agent: 'RiskForecastAgent' },
      ],
      causal_chain: [
        { label: 'Network Latency 420ms', type: 'cause' },
        { label: 'DEPLOY Step Timeout', type: 'effect' },
        { label: 'VERIFY Step Blocked', type: 'effect' },
        { label: 'SLA Breach Risk', type: 'risk' },
        { label: 'User Onboarding Impact', type: 'outcome' },
      ],
      recommended_actions: [
        { action: 'Investigate vm_3 network configuration', expected_impact: 'Resolve root latency cause', priority: 'high' },
        { action: 'Pre-notify ops team of SLA trajectory', expected_impact: 'Prevent unplanned manual override', priority: 'high' },
        { action: 'Consider temporary SLA relaxation', expected_impact: 'Buy time for resolution', priority: 'medium' },
      ],
      confidence: 81,
      time_horizon: '5–15 minutes',
      uncertainty: 'Based on simulated workflow behavior.',
      follow_up_queries: ['Show the full workflow timeline', 'What other workflows are affected?', 'What happens if we restart the deploy step?'],
      agents_used: ['WorkflowAgent', 'ResourceAgent', 'CausalAgent', 'RiskForecastAgent'],
    };
  }

  // Default: system risk
  return {
    answer: 'The system is trending toward a compliance violation due to sustained network latency impacting onboarding workflows. The primary cause is network pressure on vm_3 (420ms, 3x baseline), which cascades into DEPLOY step delays, SLA risk, and human override behavior that introduces compliance exposure.',
    why_it_matters: [
      'SLA breach risk within 10–15 minutes if latency persists',
      'Manual override likely — historical pattern shows human workaround under pressure',
      'Policy NO_AFTER_HOURS_WRITE at elevated risk due to workflow backlog',
      'Compound risk: latency + delay + compliance = incident trajectory',
    ],
    supporting_evidence: [
      { id: 'RESOURCE_ANOMALY_12', type: 'anomaly', summary: 'Network latency spike on vm_3 — 420ms (3x baseline)', confidence: 89, agent: 'ResourceAgent' },
      { id: 'WORKFLOW_DELAY_7', type: 'event', summary: 'DEPLOY step in wf_onboarding_17 exceeded SLA by 108%', confidence: 72, agent: 'WorkflowAgent' },
      { id: 'RISK_FORECAST_3', type: 'forecast', summary: 'System projected to reach AT_RISK within 15 minutes', confidence: 67, agent: 'RiskForecastAgent' },
      { id: 'METRIC_CPU_08', type: 'metric', summary: 'CPU utilization on vm_2 at 96% — sustained 5+ minutes', confidence: 95, agent: 'ResourceAgent' },
      { id: 'COMPLIANCE_PROX_01', type: 'policy', summary: 'Policy NO_AFTER_HOURS_WRITE within violation proximity', confidence: 74, agent: 'ComplianceAgent' },
    ],
    causal_chain: [
      { label: 'Network Latency ↑', type: 'cause' },
      { label: 'Workflow Step Delay', type: 'effect' },
      { label: 'SLA Pressure', type: 'risk' },
      { label: 'Human Override Risk', type: 'effect' },
      { label: 'Compliance Violation', type: 'outcome' },
    ],
    recommended_actions: [
      { action: 'Throttle non-critical background jobs', expected_impact: 'Reduce network & CPU contention', priority: 'high' },
      { action: 'Notify on-call admin of SLA trajectory', expected_impact: 'Prevent unplanned override', priority: 'high' },
      { action: 'Temporarily extend SLA threshold', expected_impact: 'Avoid automatic policy breach', priority: 'medium' },
      { action: 'Investigate vm_3 network configuration', expected_impact: 'Root cause resolution', priority: 'medium' },
    ],
    confidence: 74,
    time_horizon: '10–15 minutes',
    uncertainty: 'Based on simulated environment and recent trend extrapolation.',
    follow_up_queries: ['Which policy is most at risk?', 'Show affected workflows', 'What if we do nothing?'],
    agents_used: ['ResourceAgent', 'WorkflowAgent', 'ComplianceAgent', 'RiskForecastAgent', 'CausalAgent'],
  };
}

// ============================================
// Causal Chain (inline horizontal)
// ============================================
function CausalChainInline({ chain }: { chain: CausalStep[] }) {
  const typeColors: Record<string, { bg: string; text: string; border: string; dot: string }> = {
    cause: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', dot: 'bg-blue-500' },
    effect: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', dot: 'bg-amber-500' },
    risk: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', dot: 'bg-orange-500' },
    outcome: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', dot: 'bg-red-500' },
  };

  return (
    <div className="flex items-center gap-0 overflow-x-auto py-1">
      {chain.map((step, i) => {
        const c = typeColors[step.type] || typeColors.effect;
        return (
          <div key={i} className="flex items-center flex-shrink-0">
            <div className={`px-3 py-1.5 rounded-lg border text-xs font-medium whitespace-nowrap ${c.bg} ${c.border} ${c.text} flex items-center gap-1.5`}>
              <div className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
              {step.label}
            </div>
            {i < chain.length - 1 && (
              <ChevronRight className="w-4 h-4 text-slate-300 mx-0.5 flex-shrink-0" />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ============================================
// Agent Badges
// ============================================
function AgentBadges({ agents }: { agents: string[] }) {
  const agentConfig: Record<string, { icon: typeof Activity; color: string }> = {
    ResourceAgent: { icon: Activity, color: '#10b981' },
    WorkflowAgent: { icon: GitBranch, color: '#6366f1' },
    ComplianceAgent: { icon: Shield, color: '#ef4444' },
    RiskForecastAgent: { icon: TrendingUp, color: '#f59e0b' },
    CausalAgent: { icon: Network, color: '#8b5cf6' },
  };

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {agents.map((a) => {
        const cfg = agentConfig[a] || { icon: Zap, color: '#64748b' };
        const Icon = cfg.icon;
        return (
          <span key={a} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white border border-[var(--color-border)] text-[10px] font-medium text-[var(--color-text-muted)]">
            <Icon className="w-3 h-3" style={{ color: cfg.color }} />
            {a.replace('Agent', '')}
          </span>
        );
      })}
    </div>
  );
}

// ============================================
// Collapsible Section
// ============================================
function CollapsibleSection({ title, icon: Icon, iconColor, defaultOpen = false, count, children }: {
  title: string;
  icon: typeof Zap;
  iconColor: string;
  defaultOpen?: boolean;
  count?: number;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-[var(--color-border)] rounded-xl overflow-hidden bg-white">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4" style={{ color: iconColor }} />
          <span className="text-sm font-semibold text-[var(--color-text-primary)]">{title}</span>
          {count !== undefined && (
            <span className="text-[10px] font-bold bg-slate-100 text-[var(--color-text-muted)] px-2 py-0.5 rounded-full">{count}</span>
          )}
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-[var(--color-text-muted)]" /> : <ChevronDown className="w-4 h-4 text-[var(--color-text-muted)]" />}
      </button>
      {open && <div className="px-4 pb-4 border-t border-[var(--color-border)]">{children}</div>}
    </div>
  );
}

// ============================================
// Assistant Message (structured output)
// ============================================
function AssistantMessage({ message, onFollowUp }: { message: ChatMessage; onFollowUp: (q: string) => void }) {
  const [copied, setCopied] = useState(false);
  const r = message.response!;
  const confidenceColor = r.confidence > 70 ? '#10b981' : r.confidence > 40 ? '#f59e0b' : '#ef4444';

  const handleCopy = () => {
    navigator.clipboard.writeText(r.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const evidenceTypeConfig: Record<string, { color: string; label: string }> = {
    anomaly: { color: '#f59e0b', label: 'Anomaly' },
    event: { color: '#3b82f6', label: 'Event' },
    metric: { color: '#10b981', label: 'Metric' },
    insight: { color: '#8b5cf6', label: 'Insight' },
    forecast: { color: '#6366f1', label: 'Forecast' },
    policy: { color: '#ef4444', label: 'Policy' },
  };

  return (
    <div className="flex gap-3 group">
      {/* Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-md">
        <Sparkles className="w-4 h-4 text-white" />
      </div>

      <div className="flex-1 min-w-0 space-y-3">
        {/* Agent attribution */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[var(--color-text-primary)]">Chronos AI</span>
          <span className="text-[10px] text-[var(--color-text-muted)]">{message.timestamp}</span>
          <AgentBadges agents={r.agents_used} />
        </div>

        {/* Main answer */}
        <div className="p-4 bg-[var(--color-surface-tertiary)] rounded-2xl rounded-tl-sm">
          <p className="text-[var(--color-text-primary)] leading-relaxed">{r.answer}</p>

          {/* Confidence strip */}
          <div className="flex items-center gap-4 mt-3 pt-3 border-t border-[var(--color-border)]">
            <div className="flex items-center gap-2">
              <DonutChart value={r.confidence} total={100} color={confidenceColor} size={28} strokeWidth={3} showLabel={false} />
              <span className="text-xs font-bold" style={{ color: confidenceColor }}>{r.confidence}% confidence</span>
            </div>
            <span className="text-[10px] text-[var(--color-text-muted)]">·</span>
            <span className="text-xs text-[var(--color-text-muted)]">{r.time_horizon}</span>
            <span className="text-[10px] text-[var(--color-text-muted)]">·</span>
            <span className="text-[10px] text-amber-600 italic">{r.uncertainty}</span>
          </div>
        </div>

        {/* Why it matters */}
        <CollapsibleSection title="Why This Matters" icon={AlertTriangle} iconColor="#f59e0b" defaultOpen={true}>
          <ul className="space-y-2 mt-3">
            {r.why_it_matters.map((point, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <span className="w-5 h-5 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0 mt-0.5 text-[10px] font-bold text-amber-700">{i + 1}</span>
                <span className="text-sm text-[var(--color-text-secondary)] leading-relaxed">{point}</span>
              </li>
            ))}
          </ul>
        </CollapsibleSection>

        {/* Evidence */}
        <CollapsibleSection title="Supporting Evidence" icon={Zap} iconColor="#6366f1" count={r.supporting_evidence.length} defaultOpen={true}>
          <div className="space-y-2 mt-3">
            {r.supporting_evidence.map((e) => {
              const cfg = evidenceTypeConfig[e.type] || { color: '#64748b', label: e.type };
              return (
                <div key={e.id} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer group/ev">
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-md border" style={{ color: cfg.color, borderColor: cfg.color, backgroundColor: `${cfg.color}08` }}>
                    {cfg.label}
                  </span>
                  <code className="text-xs font-bold text-[var(--color-primary)]">{e.id}</code>
                  <span className="text-sm text-[var(--color-text-secondary)] flex-1 truncate">{e.summary}</span>
                  <span className="text-[10px] text-[var(--color-text-muted)]">{e.agent}</span>
                  <div className="flex items-center gap-1">
                    <div className="w-12 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${e.confidence}%`, backgroundColor: e.confidence > 80 ? '#10b981' : '#f59e0b' }} />
                    </div>
                    <span className="text-[10px] font-mono font-bold text-[var(--color-text-muted)]">{e.confidence}%</span>
                  </div>
                  <ExternalLink className="w-3.5 h-3.5 text-[var(--color-text-muted)] opacity-0 group-hover/ev:opacity-100 transition-opacity" />
                </div>
              );
            })}
          </div>
        </CollapsibleSection>

        {/* Causal chain */}
        <CollapsibleSection title="Causal Chain" icon={Network} iconColor="#8b5cf6">
          <div className="mt-3">
            <CausalChainInline chain={r.causal_chain} />
            <div className="flex items-center gap-3 mt-2 text-[10px] text-[var(--color-text-muted)]">
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-blue-500" /> Cause</span>
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-amber-500" /> Effect</span>
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-orange-500" /> Risk</span>
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-red-500" /> Outcome</span>
            </div>
          </div>
        </CollapsibleSection>

        {/* Recommended actions */}
        <CollapsibleSection title="Recommended Actions" icon={CheckCircle} iconColor="#10b981" count={r.recommended_actions.length}>
          <div className="space-y-2 mt-3">
            {r.recommended_actions.map((a, i) => (
              <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-slate-50">
                <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-md ${a.priority === 'high' ? 'bg-red-100 text-red-700' : a.priority === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'}`}>
                  {a.priority}
                </span>
                <span className="text-sm font-medium text-[var(--color-text-primary)] flex-1">{a.action}</span>
                <span className="text-xs text-[var(--color-text-muted)]">{a.expected_impact}</span>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-[var(--color-text-muted)] mt-2 italic">Actions are suggestive — the system does not auto-remediate.</p>
        </CollapsibleSection>

        {/* Follow-up suggestions */}
        <div className="flex flex-wrap gap-2 pt-1">
          {r.follow_up_queries.map((fq, i) => (
            <button
              key={i}
              onClick={() => onFollowUp(fq)}
              className="px-3 py-1.5 text-xs bg-white border border-[var(--color-border)] rounded-lg hover:border-[var(--color-primary)] hover:bg-indigo-50 transition-all text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] flex items-center gap-1.5"
            >
              {fq}
              <ChevronRight className="w-3 h-3" />
            </button>
          ))}
        </div>

        {/* Actions bar */}
        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onClick={handleCopy} className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors text-[var(--color-text-muted)]" title="Copy answer">
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <button className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors text-[var(--color-text-muted)]" title="Regenerate">
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================
// User Message
// ============================================
function UserMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="flex gap-3 justify-end">
      <div className="max-w-[75%]">
        <div className="flex items-center gap-2 justify-end mb-1">
          <span className="text-[10px] text-[var(--color-text-muted)]">{message.timestamp}</span>
          <span className="text-xs font-semibold text-[var(--color-text-primary)]">You</span>
        </div>
        <div className="p-4 bg-[var(--color-primary)] text-white rounded-2xl rounded-tr-sm">
          <p className="leading-relaxed">{message.content}</p>
        </div>
      </div>
      <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-slate-200 flex items-center justify-center">
        <User className="w-4 h-4 text-slate-600" />
      </div>
    </div>
  );
}

// ============================================
// Thinking Indicator (multi-stage)
// ============================================
function ThinkingIndicator({ elapsed }: { elapsed: number }) {
  const stages = [
    { label: 'Decomposing query across agents...', icon: Search, color: '#6366f1', minTime: 0 },
    { label: 'Querying ResourceAgent, WorkflowAgent...', icon: Activity, color: '#10b981', minTime: 800 },
    { label: 'Correlating evidence from blackboard...', icon: Zap, color: '#f59e0b', minTime: 1800 },
    { label: 'Running causal inference chain...', icon: Network, color: '#8b5cf6', minTime: 2800 },
    { label: 'Synthesizing answer with confidence scores...', icon: Sparkles, color: '#6366f1', minTime: 3800 },
  ];

  const activeStageIdx = stages.reduce((idx, s, i) => elapsed >= s.minTime ? i : idx, 0);

  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-md">
        <Sparkles className="w-4 h-4 text-white animate-pulse" />
      </div>
      <div className="flex-1 space-y-2">
        <div className="p-4 bg-[var(--color-surface-tertiary)] rounded-2xl rounded-tl-sm">
          {/* Progress bar */}
          <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden mb-3">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${Math.min(95, (elapsed / 4500) * 100)}%` }}
            />
          </div>

          {/* Stages */}
          <div className="space-y-2">
            {stages.map((stage, i) => {
              const StageIcon = stage.icon;
              const isActive = i === activeStageIdx;
              const isDone = i < activeStageIdx;
              const isVisible = elapsed >= stage.minTime;

              if (!isVisible) return null;

              return (
                <div key={i} className={`flex items-center gap-2 transition-all duration-300 ${isActive ? 'opacity-100' : isDone ? 'opacity-40' : 'opacity-0'}`}>
                  {isDone ? (
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                  ) : (
                    <StageIcon className="w-3.5 h-3.5 flex-shrink-0 animate-pulse" style={{ color: stage.color }} />
                  )}
                  <span className={`text-xs ${isActive ? 'text-[var(--color-text-primary)] font-medium' : 'text-[var(--color-text-muted)]'}`}>
                    {stage.label}
                  </span>
                  {isActive && (
                    <div className="flex gap-1 ml-1">
                      <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================
// Welcome Screen
// ============================================
function WelcomeScreen({ onSelectQuery }: { onSelectQuery: (q: string) => void }) {
  const suggestions = [
    { icon: Activity, label: 'System Health', query: 'Why is the system at risk right now?', color: '#ef4444', desc: 'Get a full risk assessment' },
    { icon: GitBranch, label: 'Workflow Intel', query: 'Which workflow is most likely to breach SLA?', color: '#6366f1', desc: 'Detect degrading workflows' },
    { icon: DollarSign, label: 'Cost Analysis', query: 'What caused the cost spike?', color: '#10b981', desc: 'Trace cost to root causes' },
    { icon: Shield, label: 'Compliance', query: 'Are we close to any compliance violation?', color: '#f59e0b', desc: 'Check policy risk proximity' },
  ];

  return (
    <div className="flex-1 flex flex-col items-center justify-center py-16">
      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-xl mb-5">
        <Sparkles className="w-8 h-8 text-white" />
      </div>
      <h2 className="text-xl font-bold text-[var(--color-text-primary)] mb-1">Chronos AI — System Intelligence</h2>
      <p className="text-sm text-[var(--color-text-muted)] mb-8 max-w-md text-center">
        Ask questions about your IT system. Answers are synthesized from agent reasoning, not generated from prompts.
      </p>
      <div className="grid grid-cols-2 gap-3 w-full max-w-2xl">
        {suggestions.map((s) => {
          const Icon = s.icon;
          return (
            <button
              key={s.label}
              onClick={() => onSelectQuery(s.query)}
              className="p-4 rounded-xl border border-[var(--color-border)] bg-white hover:shadow-md hover:border-indigo-200 transition-all text-left group"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${s.color}10` }}>
                  <Icon className="w-4 h-4" style={{ color: s.color }} />
                </div>
                <span className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">{s.label}</span>
              </div>
              <p className="text-sm text-[var(--color-text-secondary)] group-hover:text-[var(--color-primary)] transition-colors">{s.query}</p>
              <p className="text-[10px] text-[var(--color-text-muted)] mt-1">{s.desc}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ============================================
// Main Page
// ============================================
export default function SearchPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingElapsed, setThinkingElapsed] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const thinkingTimerRef = useRef<NodeJS.Timeout | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, thinkingElapsed, scrollToBottom]);

  // Clean up timer on unmount
  useEffect(() => {
    return () => { if (thinkingTimerRef.current) clearInterval(thinkingTimerRef.current); };
  }, []);

  const handleSend = async (text?: string) => {
    const q = text || input;
    if (!q.trim() || isLoading) return;

    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    const userMsg: ChatMessage = {
      id: `msg_${messages.length}`,
      role: 'user',
      content: q,
      timestamp: timeStr,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);
    setThinkingElapsed(0);

    // Start a timer to update elapsed time for the thinking animation
    const startTime = Date.now();
    thinkingTimerRef.current = setInterval(() => {
      setThinkingElapsed(Date.now() - startTime);
    }, 200);

    // Simulate 4-5 second thinking time
    const thinkingDuration = 4000 + Math.random() * 1000;
    await new Promise(r => setTimeout(r, thinkingDuration));

    // Stop timer
    if (thinkingTimerRef.current) clearInterval(thinkingTimerRef.current);

    const response: RAGResponse = getMockResponse(q);

    const assistantMsg: ChatMessage = {
      id: `msg_${messages.length + 1}`,
      role: 'assistant',
      content: response.answer,
      response,
      timestamp: timeStr,
    };

    setMessages((prev) => [...prev, assistantMsg]);
    setIsLoading(false);
    setThinkingElapsed(0);
  };

  const handleNewChat = () => {
    setMessages([]);
    setInput('');
    inputRef.current?.focus();
  };

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)] -mt-2">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-1 py-3 border-b border-[var(--color-border)] bg-white flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-md">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-[var(--color-text-primary)]">System Intelligence Search</h1>
            <p className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Agentic RAG · Evidence-first · Not a chatbot</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button onClick={handleNewChat} className="btn btn-secondary text-xs">
              <Plus className="w-3.5 h-3.5" />
              New Chat
            </button>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-1 py-6">
        {messages.length === 0 && !isLoading ? (
          <WelcomeScreen onSelectQuery={(q) => handleSend(q)} />
        ) : (
          <div className="space-y-8 max-w-4xl mx-auto">
            {messages.map((msg) =>
              msg.role === 'user' ? (
                <UserMessage key={msg.id} message={msg} />
              ) : (
                <AssistantMessage key={msg.id} message={msg} onFollowUp={(q) => handleSend(q)} />
              )
            )}
            {isLoading && <ThinkingIndicator elapsed={thinkingElapsed} />}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Bar (pinned to bottom) */}
      <div className="flex-shrink-0 border-t border-[var(--color-border)] bg-white px-1 py-3">
        <div className="max-w-4xl mx-auto">
          <div className={`flex items-center gap-3 rounded-2xl border bg-white transition-all ${input ? 'border-[var(--color-primary)] shadow-lg ring-2 ring-indigo-100' : 'border-[var(--color-border)] shadow-sm hover:shadow-md'}`}>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about workflows, resources, cost, compliance..."
              className="flex-1 py-4 pl-5 text-sm bg-transparent focus:outline-none"
              disabled={isLoading}
            />
            <button
              onClick={() => handleSend()}
              disabled={isLoading || !input.trim()}
              className="mr-2 w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white hover:shadow-lg transition-all disabled:opacity-40 disabled:hover:shadow-none flex-shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center justify-between mt-2 px-1">
            <p className="text-[10px] text-[var(--color-text-muted)]">
              Powered by coordinated agents · LLM explains, agents reason · Evidence-backed answers
            </p>
            <p className="text-[10px] text-[var(--color-text-muted)]">
              Press Enter to send
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
