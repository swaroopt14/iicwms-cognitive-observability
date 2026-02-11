# chronos-explainer

> **Service 5** — Explanation Engine (Insight Generation)

## Purpose

Translates reasoning cycle artifacts into **human-readable, evidence-backed insights**. The Explanation Engine is the system's voice — it answers "What happened?", "Why does it matter?", and "What should we do?"

## 3-Tier Pipeline

| Tier | Method | Latency | Requirement |
|------|--------|---------|-------------|
| **Tier 1** | CrewAI (Analyst → Explainer → Recommender) | 3-8s | `ENABLE_CREWAI=true` + Gemini API |
| **Tier 2** | Google Gemini (LLM narrative polish) | 1-3s | Gemini API key |
| **Tier 3** | Deterministic templates | <100ms | None (always available) |

## Insight Output

```json
{
  "summary": "What happened",
  "why_it_matters": "Business impact",
  "what_will_happen_if_ignored": "Projected consequences",
  "recommended_actions": ["Specific next steps"],
  "confidence": 0.82,
  "severity": "HIGH",
  "evidence_ids": ["evt_042", "metric_087"],
  "uncertainty": "Based on simulated environment"
}
```

## LLM Restrictions (Enforced by guards.py)

| LLMs CAN | LLMs CANNOT |
|-----------|-------------|
| Generate natural language explanations | Detect anomalies |
| Polish template outputs | Enforce policies |
| Compose executive summaries | Modify shared state |
| Answer query synthesis | Make decisions |

## Technology

- **Language:** Python 3.10+
- **LLM:** Google Gemini (`google-generativeai`)
- **Multi-Agent:** CrewAI (optional)
- **Default:** Template-based (zero external deps)
