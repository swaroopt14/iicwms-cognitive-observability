# chronos-dashboard

> **Service 10** — Cognitive Observability Frontend (Next.js 16)

## Purpose

A 10-page intelligence dashboard that visualizes multi-agent reasoning with evidence-backed insights, interactive causal graphs, and a natural language query interface.

## Pages

| # | Page | Route | Question It Answers |
|---|------|-------|-------------------|
| 1 | **Overview** | `/overview` | What is the current state of the system? |
| 2 | **Workflow Timeline** | `/workflow-map` | How are workflows executing? |
| 3 | **Resource & Cost** | `/resource-cost` | Which resources are stressed? |
| 4 | **Compliance** | `/compliance` | Are we compliant? What silent violations? |
| 5 | **Anomaly Center** | `/anomaly-center` | What anomalies exist and how severe? |
| 6 | **Causal Analysis** | `/causal-analysis` | What caused what? Root cause chain? |
| 7 | **Insight Feed** | `/insight-feed` | What are the most important findings? |
| 8 | **Ask Chronos AI** | `/search` | Why did this happen? What to do? |
| 9 | **Scenario Lab** | `/scenarios` | How does the system respond to disruptions? |
| 10 | **System Risk Index** | `/system-graph` | What is the overall risk trajectory? |

## Components

| Component | Purpose |
|-----------|---------|
| `Sidebar.tsx` | Navigation grouped by Observe / Reason / Explain / Test |
| `Header.tsx` | Top bar with search, breadcrumbs, status indicators |
| `Charts.tsx` | Custom canvas-based charts (zero library dependencies) |
| `Providers.tsx` | React Query provider (staleTime: 5s, refetch: 10s) |

## Chart Library (Custom, Zero Dependencies)

| Chart | Use Case |
|-------|----------|
| `AreaChart` | Gradient-filled area charts (compliance trend, cost) |
| `BarChart` | Stacked/grouped bars (anomaly rate, resource usage) |
| `RiskGraph` | Stock-style risk index with colored zones |
| `DonutChart` | Circular progress indicators (compliance score) |
| `Sparkline` | Mini inline trend lines |
| `MultiLineChart` | Multi-series comparison (CPU/Memory/Network) |

## Running

```bash
cd frontend
npm install
npm run dev
```

## Technology

- **Framework:** Next.js 16.1.6 (App Router)
- **UI Library:** React 19.2.3
- **Language:** TypeScript 5
- **Styling:** Tailwind CSS 4
- **Data Fetching:** TanStack React Query v5 + Axios
- **Icons:** Lucide React
- **Charts:** Custom HTML Canvas (zero deps)
- **Port:** 3000
