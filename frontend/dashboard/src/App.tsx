import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Overview } from './pages/Overview'
import { WorkflowMap } from './pages/WorkflowMap'
import { AnomalyCenter } from './pages/AnomalyCenter'
import { ComplianceView } from './pages/ComplianceView'
import { CausalAnalysis } from './pages/CausalAnalysis'
import { InsightFeed } from './pages/InsightFeed'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<Overview />} />
        <Route path="/workflow-map" element={<WorkflowMap />} />
        <Route path="/anomaly-center" element={<AnomalyCenter />} />
        <Route path="/compliance-view" element={<ComplianceView />} />
        <Route path="/causal-analysis" element={<CausalAnalysis />} />
        <Route path="/causal-analysis/:id" element={<CausalAnalysis />} />
        <Route path="/insight-feed" element={<InsightFeed />} />
      </Routes>
    </Layout>
  )
}

export default App
