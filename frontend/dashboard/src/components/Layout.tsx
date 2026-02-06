import { ReactNode, useState, useEffect } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { 
  LayoutDashboard, 
  GitBranch, 
  AlertTriangle, 
  Shield, 
  Search, 
  Newspaper,
  ChevronDown,
  Circle,
  Zap,
  Info
} from 'lucide-react'
import { api } from '../api'

interface LayoutProps {
  children: ReactNode
}

// Navigation items - ORDER MATTERS: Observe → Reason → Explain → Decide
const navItems = [
  { path: '/overview', label: 'Overview', icon: LayoutDashboard },
  { path: '/workflow-map', label: 'Workflow Map', icon: GitBranch },
  { path: '/anomaly-center', label: 'Anomaly Center', icon: AlertTriangle },
  { path: '/compliance-view', label: 'Compliance View', icon: Shield },
  { path: '/causal-analysis', label: 'Causal Analysis', icon: Search },
  { path: '/insight-feed', label: 'Insight Feed', icon: Newspaper },
]

// Scenario options - reinforces "simulated IT world"
const scenarios = [
  { id: 'silent-step-skipper', name: 'Silent Step-Skipper' },
  { id: 'resource-vampire', name: 'Resource Vampire' },
  { id: 'credential-leaker', name: 'Credential Leaker' },
]

// Time windows - static options only, no custom ranges
const timeWindows = [
  { id: '5m', label: 'Last 5 min' },
  { id: '15m', label: 'Last 15 min' },
  { id: 'scenario', label: 'Scenario Run' },
]

export function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
  
  const [selectedScenario, setSelectedScenario] = useState(scenarios[1]) // Default: Resource Vampire
  const [selectedTime, setSelectedTime] = useState(timeWindows[1]) // Default: Last 15 min
  const [showScenarioDropdown, setShowScenarioDropdown] = useState(false)
  const [showTimeDropdown, setShowTimeDropdown] = useState(false)

  // Poll system health every 10 seconds
  const { data: systemHealth } = useQuery({
    queryKey: ['system-health'],
    queryFn: api.getSystemHealth,
    refetchInterval: 10000,
  })

  // Poll insights summary every 10 seconds
  const { data: insightsSummary } = useQuery({
    queryKey: ['insights-summary'],
    queryFn: () => api.getInsights({ limit: 100 }),
    refetchInterval: 10000,
  })

  const activeInsightsCount = insightsSummary?.insights?.length || 0
  const systemStatus = systemHealth?.status || 'healthy'
  
  // Derive confidence from system health
  const confidence = systemHealth?.status === 'critical' ? 'High' : 
                     systemHealth?.status === 'degraded' ? 'Medium' : 'High'

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      setShowScenarioDropdown(false)
      setShowTimeDropdown(false)
    }
    document.addEventListener('click', handleClickOutside)
    return () => document.removeEventListener('click', handleClickOutside)
  }, [])

  return (
    <div className="min-h-screen bg-surface-primary flex flex-col">
      {/* ═══════════════════════════════════════════════════════════════
          TOP BAR — GLOBAL COMMAND STRIP (Datadog/Splunk style)
          Purpose: Global situational awareness, context switching, trust signals
          ═══════════════════════════════════════════════════════════════ */}
      <header className="h-12 bg-surface-secondary border-b border-gray-700/50 flex items-center px-4 flex-shrink-0">
        {/* ─── LEFT SECTION: Product Identity ─── */}
        <div className="flex items-center gap-3">
          <button 
            onClick={() => navigate('/overview')}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity"
          >
            <div className="w-7 h-7 bg-gradient-to-br from-accent-purple to-accent-blue rounded flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-white text-sm">IICWMS</span>
          </button>
          
          <div className="w-px h-6 bg-gray-700 mx-2" />
        </div>

        {/* ─── CENTER SECTION: Context Selectors (MOST IMPORTANT) ─── */}
        <div className="flex items-center gap-4 flex-1 justify-center">
          {/* Scenario Selector */}
          <div className="relative">
            <button
              onClick={(e) => { e.stopPropagation(); setShowScenarioDropdown(!showScenarioDropdown); setShowTimeDropdown(false) }}
              className="flex items-center gap-2 px-3 py-1.5 bg-surface-elevated hover:bg-gray-600 rounded text-sm text-gray-300 transition-colors min-w-[180px] justify-between"
            >
              <span className="text-gray-500 text-xs">Scenario:</span>
              <span className="text-white font-medium">{selectedScenario.name}</span>
              <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
            </button>
            
            {showScenarioDropdown && (
              <div className="absolute top-full left-0 mt-1 w-full bg-surface-elevated rounded border border-gray-600 shadow-xl z-50">
                {scenarios.map((scenario) => (
                  <button
                    key={scenario.id}
                    onClick={(e) => { e.stopPropagation(); setSelectedScenario(scenario); setShowScenarioDropdown(false) }}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-600 first:rounded-t last:rounded-b transition-colors ${
                      scenario.id === selectedScenario.id ? 'text-accent-purple bg-accent-purple/10' : 'text-gray-300'
                    }`}
                  >
                    {scenario.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Time Window Selector */}
          <div className="relative">
            <button
              onClick={(e) => { e.stopPropagation(); setShowTimeDropdown(!showTimeDropdown); setShowScenarioDropdown(false) }}
              className="flex items-center gap-2 px-3 py-1.5 bg-surface-elevated hover:bg-gray-600 rounded text-sm text-gray-300 transition-colors min-w-[140px] justify-between"
            >
              <span className="text-gray-500 text-xs">Time:</span>
              <span className="text-white font-medium">{selectedTime.label}</span>
              <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
            </button>
            
            {showTimeDropdown && (
              <div className="absolute top-full left-0 mt-1 w-full bg-surface-elevated rounded border border-gray-600 shadow-xl z-50">
                {timeWindows.map((tw) => (
                  <button
                    key={tw.id}
                    onClick={(e) => { e.stopPropagation(); setSelectedTime(tw); setShowTimeDropdown(false) }}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-600 first:rounded-t last:rounded-b transition-colors ${
                      tw.id === selectedTime.id ? 'text-accent-purple bg-accent-purple/10' : 'text-gray-300'
                    }`}
                  >
                    {tw.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ─── RIGHT SECTION: Trust Indicators ─── */}
        <div className="flex items-center gap-4">
          {/* System Status Badge */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">System Status:</span>
            <StatusBadge status={systemStatus} />
          </div>

          <div className="w-px h-6 bg-gray-700" />

          {/* Active Insights Count (clickable) */}
          <button
            onClick={() => navigate('/insight-feed')}
            className="flex items-center gap-2 hover:bg-surface-elevated px-2 py-1 rounded transition-colors"
          >
            <span className="text-xs text-gray-500">Active Insights:</span>
            <span className={`text-sm font-bold ${activeInsightsCount > 0 ? 'text-severity-high' : 'text-gray-400'}`}>
              {activeInsightsCount}
            </span>
          </button>

          <div className="w-px h-6 bg-gray-700" />

          {/* Confidence Indicator */}
          <div className="flex items-center gap-2 group relative">
            <span className="text-xs text-gray-500">Confidence:</span>
            <span className={`text-sm font-medium ${
              confidence === 'High' ? 'text-status-healthy' : 
              confidence === 'Medium' ? 'text-status-degraded' : 'text-gray-400'
            }`}>
              {confidence}
            </span>
            <Info className="w-3 h-3 text-gray-500" />
            
            {/* Tooltip */}
            <div className="absolute top-full right-0 mt-2 w-48 p-2 bg-surface-elevated rounded border border-gray-600 shadow-xl text-xs text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
              Based on agent consensus & evidence strength
            </div>
          </div>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        {/* ═══════════════════════════════════════════════════════════════
            SIDEBAR — PRIMARY NAVIGATION
            Purpose: Stable mental map, progressive investigation
            Order: Observe → Reason → Explain → Decide
            ═══════════════════════════════════════════════════════════════ */}
        <aside className="w-56 bg-surface-secondary border-r border-gray-700/50 flex flex-col flex-shrink-0">
          <nav className="flex-1 py-4">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname.startsWith(item.path)
              
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-2.5 mx-2 rounded-md transition-all relative ${
                    isActive
                      ? 'bg-accent-purple/15 text-white'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-surface-elevated'
                  }`}
                >
                  {/* Left accent bar for active state */}
                  {isActive && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-accent-purple rounded-r" />
                  )}
                  
                  <Icon className={`w-4 h-4 ${isActive ? 'text-accent-purple' : ''}`} strokeWidth={1.5} />
                  <span className="text-sm font-medium">{item.label}</span>
                </NavLink>
              )
            })}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-gray-700/50">
            <div className="text-[10px] text-gray-600 text-center uppercase tracking-wider">
              PS-08 • Round 1 • Hackathon
            </div>
          </div>
        </aside>

        {/* ═══════════════════════════════════════════════════════════════
            MAIN CONTENT AREA
            ═══════════════════════════════════════════════════════════════ */}
        <main className="flex-1 overflow-auto p-6 bg-surface-primary">
          {children}
        </main>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Status Badge Component
// ─────────────────────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { color: string; label: string; pulse: boolean }> = {
    healthy: { color: 'bg-status-healthy', label: 'Normal', pulse: false },
    degraded: { color: 'bg-status-degraded', label: 'Degraded', pulse: true },
    critical: { color: 'bg-status-critical', label: 'Critical', pulse: true },
  }

  const { color, label, pulse } = config[status] || config.healthy

  return (
    <div className="flex items-center gap-1.5">
      <div className="relative">
        <Circle className={`w-2.5 h-2.5 ${color} fill-current`} />
        {pulse && (
          <Circle className={`w-2.5 h-2.5 ${color} fill-current absolute inset-0 animate-ping opacity-75`} />
        )}
      </div>
      <span className={`text-sm font-medium ${
        status === 'critical' ? 'text-status-critical' : 
        status === 'degraded' ? 'text-status-degraded' : 'text-status-healthy'
      }`}>
        {label}
      </span>
    </div>
  )
}
