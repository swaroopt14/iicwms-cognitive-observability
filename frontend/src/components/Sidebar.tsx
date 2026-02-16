'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  GitBranch,
  AlertTriangle,
  Shield,
  Network,
  Lightbulb,
  DollarSign,
  Database,
  Cloud,
  Activity,
  Zap,
  FlaskConical,
  Beaker,
  Bot,
  ChevronDown,
  ScrollText,
} from 'lucide-react';
import { useState } from 'react';

// ── Navigation groups ──────────────────────────────────────────────
const navGroups = [
  {
    label: 'Observe',
    items: [
      { href: '/overview', label: 'Overview', icon: LayoutDashboard },
      { href: '/workflow-map', label: 'Workflow Timeline', icon: GitBranch },
      { href: '/resource-cost', label: 'Resource & Cost', icon: DollarSign },
    ],
  },
  {
    label: 'Reason',
    items: [
      { href: '/anomaly-center', label: 'Anomaly Center', icon: AlertTriangle },
      { href: '/compliance', label: 'Compliance Intel', icon: Shield },
      { href: '/causal-analysis', label: 'Causal Analysis', icon: Network },
    ],
  },
  {
    label: 'Explain',
    items: [
      { href: '/search', label: 'Ask Chronos AI', icon: Bot },
      { href: '/insight-feed', label: 'Insight Feed', icon: Lightbulb },
      { href: '/audit', label: 'Audit Investigation', icon: ScrollText },
    ],
  },
  {
    label: 'Test',
    items: [
      { href: '/scenarios', label: 'Scenario Lab', icon: FlaskConical },
      { href: '/what-if-sandbox', label: 'What-If Sandbox', icon: Beaker },
    ],
  },
];

const dataSources = [
  { name: 'CloudWatch', icon: Cloud, status: 'live', color: '#f59e0b' },
  { name: 'Grafana', icon: Activity, status: 'live', color: '#f97316' },
  { name: 'Datadog', icon: Database, status: 'live', color: '#8b5cf6' },
];

// ── Agent count badge ──────────────────────────────────────────────
const agents = [
  { name: 'Workflow', color: '#6366f1' },
  { name: 'Resource', color: '#10b981' },
  { name: 'Compliance', color: '#ef4444' },
  { name: 'Causal', color: '#8b5cf6' },
  { name: 'Query', color: '#3b82f6' },
  { name: 'Baseline', color: '#06b6d4' },
  { name: 'Scenario', color: '#f97316' },
  { name: 'Master', color: '#64748b' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [sourcesOpen, setSourcesOpen] = useState(true);

  return (
    <aside className="w-[260px] bg-white border-r border-[var(--color-border)] flex flex-col h-full select-none">
      {/* ── Logo ────────────────────────────────────── */}
      <div className="h-14 flex items-center px-4 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2.5 w-full">
          <div className="relative flex-shrink-0">
            <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-lg flex items-center justify-center shadow-sm">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <div className="absolute -bottom-px -right-px w-2.5 h-2.5 bg-emerald-400 rounded-full border-[1.5px] border-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-bold text-[var(--color-text-primary)] leading-tight tracking-tight">Chronos AI</div>
            <div className="text-[10px] text-[var(--color-text-muted)] leading-tight">IICWMS · PS-08</div>
          </div>
          <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-emerald-50 border border-emerald-200">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[9px] font-semibold text-emerald-700 uppercase">Live</span>
          </div>
        </div>
      </div>

      {/* ── Navigation ──────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto py-2 px-2 space-y-4 sidebar-scroll">
        {navGroups.map((group) => (
          <div key={group.label}>
            <div className="px-2.5 mb-1">
              <span className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-[0.08em]">
                {group.label}
              </span>
            </div>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const isActive = pathname === item.href || (item.href === '/overview' && pathname === '/');
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`
                      flex items-center gap-2.5 px-2.5 py-[7px] rounded-lg text-[13px] font-medium
                      transition-all duration-100 relative group
                      ${isActive
                        ? 'bg-indigo-50 text-indigo-700'
                        : 'text-[var(--color-text-secondary)] hover:bg-slate-50 hover:text-[var(--color-text-primary)]'
                      }
                    `}
                  >
                    {isActive && (
                      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 bg-indigo-500 rounded-r-full" />
                    )}
                    <item.icon className={`w-[16px] h-[16px] flex-shrink-0 ${
                      isActive
                        ? 'text-indigo-600'
                        : 'text-slate-400 group-hover:text-slate-500'
                    } transition-colors`} />
                    <span className="truncate">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* ── Connected Sources ───────────────────────── */}
      <div className="border-t border-[var(--color-border)]">
        <button
          onClick={() => setSourcesOpen(!sourcesOpen)}
          className="flex items-center justify-between w-full px-4 py-2.5 hover:bg-slate-50 transition-colors"
        >
          <span className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-[0.08em]">
            Data Sources
          </span>
          <ChevronDown className={`w-3.5 h-3.5 text-[var(--color-text-muted)] transition-transform ${sourcesOpen ? '' : '-rotate-90'}`} />
        </button>

        {sourcesOpen && (
          <div className="px-2 pb-2.5 space-y-0.5">
            {dataSources.map((source) => (
              <div
                key={source.name}
                className="flex items-center gap-2.5 px-2.5 py-[6px] rounded-lg hover:bg-slate-50 transition-colors cursor-default"
              >
                <div
                  className="w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0"
                  style={{ backgroundColor: `${source.color}12` }}
                >
                  <source.icon className="w-3 h-3" style={{ color: source.color }} />
                </div>
                <span className="text-[12px] text-[var(--color-text-secondary)] font-medium">{source.name}</span>
                <div className="ml-auto flex items-center gap-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <span className="text-[9px] font-semibold text-[var(--color-text-muted)] uppercase">sim</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Agent Strip ─────────────────────────────── */}
      <div className="border-t border-[var(--color-border)] px-3 py-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-[0.08em]">
            Active Agents
          </span>
          <span className="text-[10px] font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">
            {agents.length}
          </span>
        </div>
        <div className="flex flex-wrap gap-1">
          {agents.map((agent) => (
            <div
              key={agent.name}
              className="flex items-center gap-1 px-1.5 py-[3px] rounded-md border border-[var(--color-border)] bg-white hover:shadow-sm transition-shadow cursor-default"
              title={`${agent.name}Agent`}
            >
              <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: agent.color }} />
              <span className="text-[9px] font-semibold text-[var(--color-text-muted)]">{agent.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Footer ──────────────────────────────────── */}
      <div className="border-t border-[var(--color-border)] px-4 py-2.5 bg-gradient-to-b from-white to-slate-50/80">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] font-medium text-[var(--color-text-muted)]">Observe → Reason → Explain</span>
          </div>
          <span className="text-[9px] font-bold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">R1+R2</span>
        </div>
      </div>
    </aside>
  );
}
