'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Search, Bell, Sparkles, Command, AlertCircle, AlertTriangle, Info, CheckCircle } from 'lucide-react';

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
  '/scenarios': 'Scenario Lab',
  '/audit': 'Audit Investigation',
};

// Severity colors and configurations
const severityConfig: Record<string, { borderColor: string; bgColor: string; textColor: string; icon: React.ReactNode }> = {
  'alert': { 
    borderColor: 'border-l-4 border-l-red-500', 
    bgColor: 'hover:bg-red-50', 
    textColor: 'text-red-700',
    icon: <AlertCircle className="w-4 h-4 text-red-500" />
  },
  'warning': { 
    borderColor: 'border-l-4 border-l-yellow-500', 
    bgColor: 'hover:bg-yellow-50', 
    textColor: 'text-yellow-700',
    icon: <AlertTriangle className="w-4 h-4 text-yellow-500" />
  },
  'info': { 
    borderColor: 'border-l-4 border-l-blue-500', 
    bgColor: 'hover:bg-blue-50', 
    textColor: 'text-blue-700',
    icon: <Info className="w-4 h-4 text-blue-500" />
  },
  'success': {
    borderColor: 'border-l-4 border-l-emerald-500',
    bgColor: 'hover:bg-emerald-50',
    textColor: 'text-emerald-700',
    icon: <CheckCircle className="w-4 h-4 text-emerald-500" />
  }
};

// Utility function to group notifications by type
const groupNotificationsByType = (notifications: any[]) => {
  const grouped: Record<string, any[]> = {
    alert: [],
    warning: [],
    info: [],
    success: [],
  };

  notifications.forEach(notification => {
    const type = notification.type || 'info';
    if (!grouped[type]) grouped[type] = [];
    grouped[type].push(notification);
  });

  return Object.entries(grouped)
    .filter(([_, items]) => items.length > 0)
    .flatMap(([type, items]) => items);
};

export default function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const [searchQuery, setSearchQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const unreadNotifications = 3;

  // Example notifications (replace with dynamic data / API)
  const [notifications, setNotifications] = useState(() => [
    { id: 1, title: 'Critical Alert', message: 'High CPU usage detected', timestamp: '2 minutes ago', type: 'alert', route: '/anomaly-center', read: false },
    { id: 2, title: 'Resource Warning', message: 'Database disk space low', timestamp: '15 minutes ago', type: 'warning', route: '/resource-cost', read: false },
    { id: 3, title: 'Compliance Issue', message: 'New security policy update', timestamp: '1 hour ago', type: 'info', route: '/compliance', read: false },
    { id: 4, title: 'Deployment Success', message: 'New version deployed successfully', timestamp: '2 hours ago', type: 'success', route: '/audit', read: true },
  ]);

  const currentPage = pageTitles[pathname] || 'Overview';
  const groupedNotifications = groupNotificationsByType(notifications);

  const markAsRead = useCallback((id: number) => {
    setNotifications((prev) => prev.map(n => n.id === id ? { ...n, read: true } : n));
    // optional: call API to mark as read
  }, []);

  const handleNotificationClick = useCallback((route?: string, id?: number) => {
    return (e: React.MouseEvent) => {
      e.stopPropagation();
      if (typeof id === 'number') markAsRead(id);
      setShowNotifications(false);
      if (route) router.push(route);
    };
  }, [router, markAsRead]);

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
          {/* Notifications Bell with dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setShowNotifications(s => !s); }}
              className="relative p-2.5 rounded-lg hover:bg-slate-100 transition-all duration-200 text-slate-600 hover:text-slate-900 hover:scale-105 active:scale-95"
              aria-label="Notifications"
              title="Notifications"
            >
              <Bell className="w-5 h-5" />
              {notifications.some(n => !n.read) && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-semibold rounded-full flex items-center justify-center animate-pulse shadow-lg">
                  {notifications.filter(n => !n.read).length > 9 ? '9+' : notifications.filter(n => !n.read).length}
                </span>
              )}
            </button>

            {showNotifications && (
              <div
                onClick={(e) => e.stopPropagation()}
                className="absolute right-0 mt-2 w-96 bg-white rounded-lg shadow-xl border border-slate-200 z-50 overflow-hidden"
              >
                <div className="bg-gradient-to-r from-slate-50 to-slate-100 px-4 py-3 border-b border-slate-200">
                  <h3 className="text-sm font-semibold text-slate-900">Notifications</h3>
                </div>
                <div className="max-h-96 overflow-y-auto">
                  {groupedNotifications.map((notification, idx) => {
                    const config = severityConfig[notification.type] || severityConfig.info;
                    const typeCount = groupedNotifications.filter(n => n.type === notification.type).length;
                    const isFirstOfType = groupedNotifications.findIndex(n => n.type === notification.type) === idx;
                    
                    return (
                      <div key={notification.id}>
                        {/* Type header/separator */}
                        {isFirstOfType && (
                          <div className={`px-4 py-2 bg-slate-50 border-b border-slate-100 flex items-center gap-2`}>
                            {config.icon}
                            <span className="text-xs font-semibold text-slate-600 capitalize">{notification.type}s</span>
                            <span className="ml-auto text-xs font-bold text-slate-500 bg-slate-200 px-2 py-0.5 rounded-full">{typeCount}</span>
                          </div>
                        )}
                        {/* Notification item */}
                        <button
                          type="button"
                          onClick={handleNotificationClick(notification.route, notification.id)}
                          className={`w-full px-4 py-3 border-b border-slate-100 transition-colors duration-150 text-left cursor-pointer active:bg-slate-100 ${config.borderColor} ${config.bgColor}`}
                        >
                          <div className="flex items-start gap-3">
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-semibold text-slate-900">{notification.title}</p>
                              <p className="text-xs text-slate-600 mt-0.5 line-clamp-2">{notification.message}</p>
                              <p className={`text-xs mt-1 ${notification.read ? 'text-slate-400' : 'font-medium text-slate-500'}`}>
                                {notification.timestamp}
                              </p>
                            </div>
                            {!notification.read && (
                              <div className="w-2.5 h-2.5 rounded-full bg-indigo-600 flex-shrink-0 mt-1.5" />
                            )}
                          </div>
                        </button>
                      </div>
                    );
                  })}
                </div>
                <div className="px-4 py-2.5 bg-slate-50 border-t border-slate-200">
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setShowNotifications(false); router.push('/audit'); }}
                    className="w-full text-xs font-medium text-indigo-600 hover:text-indigo-700 py-1 cursor-pointer transition-colors"
                  >
                    View all notifications
                  </button>
                </div>
              </div>
            )}
          </div>

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
