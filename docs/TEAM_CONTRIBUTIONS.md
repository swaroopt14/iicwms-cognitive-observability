# Team Of 4: Code Walkthrough + Member Contributions (Judge Script)

Use this during judging when they ask:
1) "Explain the code end-to-end"
2) "What did each team member contribute?"

This is intentionally **code-referenced** so you can point to real files quickly.

---

## 1) 60-Second End-to-End Code Walkthrough (What To Say)

**Chronos runs an observe -> reason -> explain loop.**

1. **Observe (facts only)**
   - Ingest normalized envelope: `api/server.py` (`POST /ingest/envelope`)
   - Ingest GitHub pre-deploy signal: `api/server.py` (`POST /ingest/github/webhook`)
   - Store facts: `observation/layer.py` (append-only events/metrics)

2. **Detect (deterministic agents)**
   - Orchestration per cycle: `agents/master_agent.py` (Phase 1 parallel)
   - Workflow anomalies: `agents/workflow_agent.py`
   - Resource anomalies: `agents/resource_agent.py`
   - Compliance policy hits: `agents/compliance_agent.py`
   - Adaptive baseline deviations: `agents/adaptive_baseline_agent.py`
   - Pre-deploy predictive anomalies from GitHub/CI: `agents/code_agent.py`
   - All outputs append into: `blackboard/state.py` (SharedState)

3. **Forecast (risk trajectory)**
   - Entity risk states + explicit confidence: `agents/risk_forecast_agent.py`
   - System risk index (0-100) + evidence contributions: `metrics/risk_index.py`

4. **Reason (why + what next)**
   - Causal links: `agents/causal_agent.py`
   - Severity scoring (0-10 with context multipliers): `agents/severity_engine_agent.py`
   - Structured recommendations (rule-mapped): `agents/recommendation_engine_agent.py`

5. **Explain (human insight)**
   - Template/LLM/CrewAI explanation path: `explanation/engine.py`
   - Key claim: LLM is optional and used for wording only, not detection.

6. **Act (operator outputs)**
   - API surfaces signals to UI: `api/server.py` (endpoints)
   - Slack alerts with cooldown + de-dup: `api/slack_notifier.py`
   - Ask Chronos (agentic RAG over state): `rag/query_engine.py`

7. **Guards (safety)**
   - Architectural boundaries: `guards.py`

If judges want one sentence:
- "We ingest facts, agents reason deterministically into auditable artifacts, then we explain and alert with evidence IDs."

---

## 2) How To Answer "What Did Each Member Do?" (Judge-Satisfying Pattern)

For each member, answer with this structure (20-30 seconds each):
- **Ownership:** "I owned X subsystem."
- **Core changes:** "I implemented A/B/C."
- **Key files:** "Main files: <paths>."
- **One hard problem:** "Hardest bug/design decision was <X>, solved by <Y>."
- **How to verify quickly:** "You can verify by <endpoint/demo step/test>."

Do not say: "I helped everywhere."
Do say: "I owned 2-3 concrete areas with file paths."

---

## 3) Suggested Split For A Team Of 4 (Edit To Match Reality)

Pick a split that matches what you actually did and keeps coverage clean:

### Member 1: API + Ingestion + Runtime Hardening
- Scope: `api/server.py`, `api/middleware.py`, `api/config.py`, idempotency/DLQ, background loop
- Demo proof: show `/docs`, show `/ingest/envelope` quarantine reasons, show headers (`X-Request-ID`, timing)

### Member 2: Multi-Agent Reasoning (Detection + Forecast)
- Scope: `agents/master_agent.py`, `agents/workflow_agent.py`, `agents/resource_agent.py`,
  `agents/compliance_agent.py`, `agents/risk_forecast_agent.py`
- Demo proof: run cycle, show anomalies + risk signals, explain thresholds/sustained windows

### Member 3: Reasoning Quality (Causal + Severity + Recommendations)
- Scope: `agents/causal_agent.py`, `agents/severity_engine_agent.py`, `agents/recommendation_engine_agent.py`,
  plus `metrics/risk_index.py`
- Demo proof: show causal link creation, show severity score explanation vector, show structured recommendation confidence

### Member 4: UI + Ask Chronos + Slack Alerts + Docs/Demo Story
- Scope: `frontend/` pages, `rag/query_engine.py`, `api/slack_notifier.py`, judge docs in `docs/`
- Demo proof: Ask Chronos query result with evidence, Slack `/alerts/slack/status`, walkthrough pages

If you want: we can lock this split to your actual git history and files each person touched most.

---

## 4) Fill-In: Final Contribution Statements (Copy/Paste Ready)

### Member A (Name): ___________________
- Ownership:
- What I built (bullets):
- Key files:
- Judge verification:

### Member B (Name): ___________________
- Ownership:
- What I built (bullets):
- Key files:
- Judge verification:

### Member C (Name): ___________________
- Ownership:
- What I built (bullets):
- Key files:
- Judge verification:

### Member D (Name): ___________________
- Ownership:
- What I built (bullets):
- Key files:
- Judge verification:

---

## 5) Evidence For "We Really Built This" (Commands)

Run these locally if a judge challenges contributions:

```bash
git shortlog -sne HEAD
git log --stat -n 5
git log --name-only --author="NAME_OR_EMAIL" -n 20
```

---

## 6) Common Judge Follow-Ups About Contributions (With Strong Answers)

Q: "Who built the prediction engine?"
A: "We have two deterministic prediction paths: pre-deploy code risk (`agents/code_agent.py`) and runtime risk trajectory (`agents/risk_forecast_agent.py`). <Member X> owned those, and we can show the formulas and evidence IDs in the Blackboard."

Q: "Who built Slack alerts and how do you avoid spam?"
A: "`api/slack_notifier.py` posts only when severity OR risk crosses threshold, with cooldown and strict fingerprint de-dup. <Member X> implemented it."

Q: "Who built the guardrails to prevent hallucinations?"
A: "`guards.py` enforces architectural boundaries and evidence requirements. <Member X> implemented/validated those."

Q: "Who built the RAG/Ask Chronos part?"
A: "`rag/query_engine.py` decomposes the query, retrieves evidence from recent cycles, and computes confidence from evidence confidence (top-10 + capped bonus). <Member X> owned it."

