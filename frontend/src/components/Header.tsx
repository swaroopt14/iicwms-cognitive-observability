'use client';

import { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Search, Bell, ChevronDown, Sparkles, Clock, Command } from 'lucide-react';

// Breadcrumb label from pathname
const pageTitles: Record<string, string> = {
  '/overview': 'Overview',
  '/workflow-map': 'Workflow Timeline',
  '/anomaly-center': 'Anomaly Center',
  '/compliance': 'Compliance Intel',
  '/resource-cost': 'Resource & Cost',
  '/causal-analysis': 'Causal Analysis',
  '/insight-feed': 'Insight Feed',
  '/search': 'Ask Chronos AI',
  '/system-graph': 'Risk Index',
  '/scenarios': 'Scenario Lab',
  '/audit': 'Audit Investigation',
};

export default function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const [searchQuery, setSearchQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  const currentPage = pageTitles[pathname] || 'Overview';

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/search?q=${encodeURIComponent(searchQuery)}`);
    }
  };

  return (
    <header className="h-14 bg-white/90 backdrop-blur-xl border-b border-[var(--color-border)] flex items-center px-5 sticky top-0 z-40">
      {/* Left: Breadcrumb */}
      <div className="flex items-center gap-2 mr-6 min-w-0 flex-shrink-0">
        <span className="text-sm text-[var(--color-text-muted)]">Chronos</span>
        <span className="text-[var(--color-text-muted)]">/</span>
        <span className="text-sm font-semibold text-[var(--color-text-primary)] truncate">{currentPage}</span>
      </div>

      {/* Center: Search */}
      <form onSubmit={handleSearch} className="flex-1 max-w-xl">
        <div className="relative">
          <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 transition-colors ${
            isFocused ? 'text-indigo-500' : 'text-slate-400'
          }`} />
          <input
            type="text"
            placeholder="Ask anything about your system..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            className={`w-full pl-9 pr-20 py-2 text-[13px] rounded-lg transition-all ${
              isFocused
                ? 'bg-white border-indigo-300 shadow-[0_0_0_3px_rgba(99,102,241,0.08)]'
                : 'bg-slate-50 border-transparent hover:bg-slate-100'
            } border`}
          />
          <div className="absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
            <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-white border border-slate-200 rounded text-[10px] font-medium text-slate-400">
              <Command className="w-2.5 h-2.5" />K
            </kbd>
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          </div>
        </div>
      </form>

      {/* Right: Controls */}
      <div className="flex items-center gap-2 ml-6 flex-shrink-0">
        {/* Environment */}
        <button className="flex items-center gap-1.5 px-2.5 py-1.5 text-[12px] font-medium text-[var(--color-text-secondary)] bg-slate-50 border border-[var(--color-border)] rounded-lg hover:bg-slate-100 transition-colors">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          Simulated
          <ChevronDown className="w-3 h-3 text-slate-400" />
        </button>

        {/* Time */}
        <button className="flex items-center gap-1.5 px-2.5 py-1.5 text-[12px] font-medium text-[var(--color-text-secondary)] bg-slate-50 border border-[var(--color-border)] rounded-lg hover:bg-slate-100 transition-colors">
          <Clock className="w-3 h-3 text-slate-400" />
          15m
        </button>

        <div className="w-px h-6 bg-slate-200 mx-1" />

        {/* Notifications */}
        <button className="relative p-2 rounded-lg hover:bg-slate-50 transition-colors text-slate-500 hover:text-slate-700">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-red-500 rounded-full" />
        </button>

        {/* Status */}
        <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-emerald-50 border border-emerald-200 rounded-lg">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[11px] font-semibold text-emerald-700">Healthy</span>
        </div>
      </div>
    </header>
  );
}
