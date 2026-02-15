# IICWMS – Frontend Dashboard

Cognitive Observability Dashboard built with **Next.js 16**, **React 19**, **TypeScript**, and **TailwindCSS 4**.

---

## Overview

The frontend provides 11 specialized views for monitoring, analyzing, and understanding IT system behavior through cognitive observability:

| Page | Route | Description |
|------|-------|-------------|
| Overview | `/overview` | System health, cost trends, anomaly rates |
| Workflow Timeline | `/workflow-map` | Confidence-tracked event timeline |
| Anomaly Center | `/anomaly-center` | Anomaly detection with evidence chain drill-down |
| Causal Analysis | `/causal-analysis` | Interactive cause-effect graph with snapshot export |
| Compliance | `/compliance` | Policy monitoring and audit readiness |
| Insight Feed | `/insight-feed` | AI-generated insights with recommended actions |
| Resource & Cost | `/resource-cost` | Resource utilization and cost trend analysis |
| System Risk Graph | `/system-graph` | Risk trajectory with agent contributions |
| Scenarios | `/scenarios` | Stress testing with agent response animation |
| Chronos AI | `/search` | Natural language queries with evidence-backed answers |

---

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **UI**: React 19, TypeScript
- **Styling**: TailwindCSS 4
- **Charts**: Custom HTML5 Canvas (no chart library dependency)
- **Data Fetching**: TanStack React Query
- **Icons**: Lucide React

---

## Getting Started

### Prerequisites
- Node.js 18+
- npm

### Development

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Backend Connection (DevOps)

The frontend expects the backend at `http://localhost:8000` by default.

To override:

```bash
export NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Common checks:

```bash
curl -s http://localhost:8000/system/health | head
curl -I http://localhost:3000 | head
```

### Production Build

```bash
npm run build
npx next start -p 3000
```

---

## Architecture

```
frontend/
├── src/
│   ├── app/                   # Next.js App Router pages
│   │   ├── layout.tsx         # Root layout with sidebar + header
│   │   ├── page.tsx           # Landing redirect
│   │   ├── globals.css        # Global styles and animations
│   │   ├── overview/          # Overview dashboard
│   │   ├── workflow-map/      # Workflow timeline
│   │   ├── anomaly-center/    # Anomaly detection center
│   │   ├── causal-analysis/   # Causal graph analysis
│   │   ├── compliance/        # Compliance monitoring
│   │   ├── insight-feed/      # Insight feed
│   │   ├── resource-cost/     # Resource & cost analysis
│   │   ├── system-graph/      # System risk graph
│   │   ├── scenarios/         # Scenario injection
│   │   └── search/            # Chronos AI (RAG assistant)
│   ├── components/            # Shared components
│   │   ├── Charts.tsx         # Canvas-rendered chart library
│   │   ├── Header.tsx         # Top header bar
│   │   ├── Sidebar.tsx        # Navigation sidebar
│   │   └── Providers.tsx      # React Query + context providers
│   └── lib/                   # Utilities
│       ├── api.ts             # API client (mock-ready)
│       └── mock-data.ts       # Static mock data for demo
├── public/                    # Static assets
├── package.json
├── tsconfig.json
├── next.config.ts
├── postcss.config.mjs
└── eslint.config.mjs
```

---

## Key Features

- **Custom Canvas Charts**: All charts (Area, Bar, Multi-line, Donut, Sparkline, Risk Graph, Causal Graph) rendered directly with HTML5 Canvas for maximum performance
- **Evidence Chain Drill-down**: Navigate from any anomaly or insight to its underlying evidence
- **Cross-page Navigation**: Jump to related analysis pages from any detail view
- **Chronos AI Thinking Animation**: Multi-stage reasoning visualization (4-5 seconds)
- **Scenario Injection**: Live agent-by-agent response animation during reasoning cycles
- **Snapshot Export**: Export causal analysis and audit data as JSON
- **Mock Data Mode**: Full demo capability without backend dependency

---

## Data Modes

### Backend-Connected Mode
The API client in `src/lib/api.ts` connects to the FastAPI backend at `localhost:8000`.

### Demo/Mock Mode
For standalone demos, `src/lib/mock-data.ts` provides comprehensive static data for all 11 pages. The API layer can be configured to serve mock data with simulated network delays.
