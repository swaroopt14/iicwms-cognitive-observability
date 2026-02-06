import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Shield, Activity, GitBranch, RefreshCw } from 'lucide-react'
import { api } from './api'
import { InsightCard } from './components/InsightCard'
import { EvidencePanel } from './components/EvidencePanel'
import { GraphView } from './components/GraphView'

type TabType = 'insights' | 'evidence' | 'graph'

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('insights')
  const [selectedInsightId, setSelectedInsightId] = useState<string | null>(null)

  const { data: insights, isLoading, refetch } = useQuery({
    queryKey: ['insights'],
    queryFn: api.getInsights,
  })

  const { data: hypotheses } = useQuery({
    queryKey: ['hypotheses'],
    queryFn: api.getHypotheses,
  })

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-brand-600 rounded-lg flex items-center justify-center">
                <Shield className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">IICWMS</h1>
                <p className="text-sm text-gray-500">Cognitive Observability Dashboard</p>
              </div>
            </div>
            <button
              onClick={() => refetch()}
              className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-8">
            <TabButton
              active={activeTab === 'insights'}
              onClick={() => setActiveTab('insights')}
              icon={<AlertTriangle className="w-4 h-4" />}
              label="Insights"
              count={insights?.insights?.length}
            />
            <TabButton
              active={activeTab === 'evidence'}
              onClick={() => setActiveTab('evidence')}
              icon={<Activity className="w-4 h-4" />}
              label="Evidence"
              count={hypotheses?.hypotheses?.length}
            />
            <TabButton
              active={activeTab === 'graph'}
              onClick={() => setActiveTab('graph')}
              icon={<GitBranch className="w-4 h-4" />}
              label="Graph View"
            />
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600"></div>
          </div>
        ) : (
          <>
            {activeTab === 'insights' && (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold text-gray-900">Active Insights</h2>
                {insights?.insights?.length === 0 ? (
                  <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
                    <Shield className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-500">No active insights</p>
                    <p className="text-sm text-gray-400 mt-1">System is operating normally</p>
                  </div>
                ) : (
                  <div className="grid gap-4">
                    {insights?.insights?.map((insight: any) => (
                      <InsightCard
                        key={insight.id}
                        insight={insight}
                        onViewEvidence={() => {
                          setSelectedInsightId(insight.id)
                          setActiveTab('evidence')
                        }}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'evidence' && (
              <EvidencePanel
                hypotheses={hypotheses?.hypotheses || []}
                selectedInsightId={selectedInsightId}
              />
            )}

            {activeTab === 'graph' && <GraphView />}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <p className="text-sm text-gray-500 text-center">
            IICWMS — Cognitive Observability: Understanding "why" is as important as knowing "what"
          </p>
        </div>
      </footer>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  icon,
  label,
  count,
}: {
  active: boolean
  onClick: () => void
  icon: React.ReactNode
  label: string
  count?: number
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-1 py-4 border-b-2 transition ${
        active
          ? 'border-brand-600 text-brand-600'
          : 'border-transparent text-gray-500 hover:text-gray-700'
      }`}
    >
      {icon}
      <span className="font-medium">{label}</span>
      {count !== undefined && count > 0 && (
        <span className={`px-2 py-0.5 text-xs rounded-full ${
          active ? 'bg-brand-100 text-brand-700' : 'bg-gray-100 text-gray-600'
        }`}>
          {count}
        </span>
      )}
    </button>
  )
}

export default App
