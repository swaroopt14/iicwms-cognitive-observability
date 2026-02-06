import { ReactNode, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, 
  GitBranch, 
  AlertTriangle, 
  Shield, 
  Search, 
  Newspaper,
  ChevronDown,
  Clock,
  Zap
} from 'lucide-react'

interface LayoutProps {
  children: ReactNode
}

const navItems = [
  { path: '/overview', label: 'Overview', icon: LayoutDashboard },
  { path: '/workflow-map', label: 'Workflow Map', icon: GitBranch },
  { path: '/anomaly-center', label: 'Anomaly Center', icon: AlertTriangle },
  { path: '/compliance-view', label: 'Compliance View', icon: Shield },
  { path: '/causal-analysis', label: 'Causal Analysis', icon: Search },
  { path: '/insight-feed', label: 'Insight Feed', icon: Newspaper },
]

const timeWindows = ['Last 5m', 'Last 15m', 'Last 1h', 'Scenario Run']
const environments = ['Simulated Environment', 'Silent Step-Skipper', 'Resource Vampire', 'Credential Leaker']

export function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const [timeWindow, setTimeWindow] = useState('Last 15m')
  const [environment, setEnvironment] = useState('Simulated Environment')
  const [showTimeDropdown, setShowTimeDropdown] = useState(false)
  const [showEnvDropdown, setShowEnvDropdown] = useState(false)

  return (
    <div className="min-h-screen bg-surface-primary flex">
      {/* Left Sidebar */}
      <aside className="w-64 bg-surface-secondary border-r border-gray-700/50 flex flex-col">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-gray-700/50">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-accent-purple to-accent-blue rounded-lg flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">IICWMS</h1>
              <p className="text-[10px] text-gray-400 -mt-0.5">Cognitive Observability</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname.startsWith(item.path)
            
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                  isActive
                    ? 'bg-accent-purple/20 text-accent-purple border-l-2 border-accent-purple'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-surface-elevated'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium text-sm">{item.label}</span>
              </NavLink>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700/50">
          <div className="text-xs text-gray-500 text-center">
            PS-08 • Round 1
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <header className="h-16 bg-surface-secondary border-b border-gray-700/50 flex items-center justify-between px-6">
          <div className="flex items-center gap-4">
            {/* Environment Selector */}
            <div className="relative">
              <button
                onClick={() => setShowEnvDropdown(!showEnvDropdown)}
                className="flex items-center gap-2 px-3 py-1.5 bg-surface-elevated rounded-lg text-sm text-gray-300 hover:text-white transition-colors"
              >
                <div className="w-2 h-2 rounded-full bg-status-healthy" />
                <span>{environment}</span>
                <ChevronDown className="w-4 h-4" />
              </button>
              
              {showEnvDropdown && (
                <div className="absolute top-full left-0 mt-1 w-48 bg-surface-elevated rounded-lg border border-gray-600 shadow-xl z-50">
                  {environments.map((env) => (
                    <button
                      key={env}
                      onClick={() => { setEnvironment(env); setShowEnvDropdown(false) }}
                      className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-600 first:rounded-t-lg last:rounded-b-lg ${
                        env === environment ? 'text-accent-purple' : 'text-gray-300'
                      }`}
                    >
                      {env}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Time Window Selector */}
            <div className="relative">
              <button
                onClick={() => setShowTimeDropdown(!showTimeDropdown)}
                className="flex items-center gap-2 px-3 py-1.5 bg-surface-elevated rounded-lg text-sm text-gray-300 hover:text-white transition-colors"
              >
                <Clock className="w-4 h-4" />
                <span>{timeWindow}</span>
                <ChevronDown className="w-4 h-4" />
              </button>
              
              {showTimeDropdown && (
                <div className="absolute top-full right-0 mt-1 w-36 bg-surface-elevated rounded-lg border border-gray-600 shadow-xl z-50">
                  {timeWindows.map((tw) => (
                    <button
                      key={tw}
                      onClick={() => { setTimeWindow(tw); setShowTimeDropdown(false) }}
                      className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-600 first:rounded-t-lg last:rounded-b-lg ${
                        tw === timeWindow ? 'text-accent-purple' : 'text-gray-300'
                      }`}
                    >
                      {tw}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Live indicator */}
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <div className="w-2 h-2 rounded-full bg-status-healthy animate-pulse" />
              <span>Live</span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
