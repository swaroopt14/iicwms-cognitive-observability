'use client';

import { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Search, Bell, Sparkles, Command } from 'lucide-react';

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
  const unreadNotifications = 3;

  const currentPage = pageTitles[pathname] || 'Overview';

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/search?q=${encodeURIComponent(searchQuery)}`);
    }
  };

  return (
    <header className="h-16 bg-white/95 backdrop-blur-md border-b border-slate-200/60 shadow-sm sticky top-0 z-40">
      <div className="flex items-center justify-between h-full px-6 gap-4">
        {/* Left: Breadcrumb */}
        <div className="flex items-center min-w-0 flex-shrink-0">
          <div className="hidden sm:flex items-center gap-2">
            <span className="text-sm font-semibold text-slate-900">Chronos</span>
            <span className="text-slate-300">/</span>
            <span className="text-sm text-slate-600 truncate">{currentPage}</span>
          </div>
        </div>

        {/* Center: Search */}
        <form onSubmit={handleSearch} className="flex-1 max-w-2xl">
          <div className="relative">
            <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 transition-colors ${
              isFocused ? 'text-indigo-600' : 'text-slate-400'
            }`} />
            <input
              type="text"
              placeholder="Search or ask about your system..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              className={`w-full pl-10 pr-14 py-2.5 text-sm rounded-lg transition-all border ${
                isFocused
                  ? 'border-indigo-400 bg-white shadow-[0_0_0_3px_rgba(99,102,241,0.08)]'
                  : 'border-slate-200 bg-slate-50/50 hover:bg-slate-100/50'
              }`}
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
              <kbd className="hidden md:inline-flex items-center gap-0.5 px-2 py-1 bg-slate-100 border border-slate-300 rounded text-xs font-medium text-slate-500">
                <Command className="w-3 h-3" />K
              </kbd>
              <Sparkles className="w-4 h-4 text-indigo-400" />
            </div>
          </div>
        </form>

        {/* Right: Controls */}
        <div className="flex items-center gap-3 flex-shrink-0">
          {/* Notifications Bell */}
          <button
            className="relative p-2.5 rounded-lg hover:bg-slate-100 transition-all duration-200 text-slate-600 hover:text-slate-900 hover:scale-105 active:scale-95"
            aria-label="Notifications"
            title="Notifications"
          >
            <Bell className="w-5 h-5" />
            {unreadNotifications > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-semibold rounded-full flex items-center justify-center animate-pulse shadow-lg">
                {unreadNotifications > 9 ? '9+' : unreadNotifications}
              </span>
            )}
          </button>

          {/* Profile Avatar */}
          <div className="h-8 w-8 rounded-lg overflow-hidden ring-2 ring-slate-200 hover:ring-indigo-300 transition-all duration-200 flex-shrink-0 cursor-pointer">
            <img
              src="https://api.dicebear.com/7.x/avataaars/svg?seed=admin"
              alt="User avatar"
              className="w-full h-full"
            />
          </div>

          {/* Status Indicator */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200/60 rounded-lg shadow-sm">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-lg shadow-emerald-500/50" />
            <span className="text-xs font-semibold text-emerald-700 whitespace-nowrap">Healthy</span>
          </div>
        </div>
      </div>
    </header>
  );
}
