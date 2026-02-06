# IICWMS Demo Flow

This document provides the exact steps and talking points for the demonstration video.

## Pre-Demo Checklist

- [ ] Neo4j Aura instance running (or local Neo4j)
- [ ] Backend server started (`uvicorn api.server:app`)
- [ ] Frontend dashboard running (`npm run dev`)
- [ ] Terminal visible for CLI commands

## Demo Script (5-7 minutes)

### Act 1: Introduction (30 seconds)

**Show**: README.md in IDE or GitHub

**Say**:
> "IICWMS - the Intelligent IT Compliance & Workflow Monitoring System - implements what we call Cognitive Observability. Unlike traditional monitoring that just alerts on thresholds, our system *reasons* about workflows, policies, and system behavior to produce explainable insights."

**Key phrase to include**:
> "This delivers probable causal relationships, not formal proof - but with full traceability."

---

### Act 2: Architecture Overview (45 seconds)

**Show**: Architecture diagram from `docs/architecture.md`

**Say**:
> "The architecture has four key layers:
> 1. A graph database - Neo4j - that serves as the authoritative system state
> 2. A mesh of specialized agents - workflow, policy, resource, and RCA agents
> 3. A Blackboard that records all agent opinions for full auditability
> 4. An API and dashboard for human operators"

**Emphasize**:
> "Agents are coordinated through a shared evidence substrate - the Blackboard pattern ensures every insight is traceable back to evidence."

---

### Act 3: Generate a Scenario (60 seconds)

**Show**: Terminal

**Run**:
```bash
python -m simulator.scenario_generator --scenario silent-step-skipper --output events.jsonl
```

**Say**:
> "Let me generate our first scenario - the Silent Step-Skipper. This simulates a workflow where mandatory approval steps are bypassed without authorization."

**Show**: Generated `events.jsonl` briefly

**Say**:
> "Notice every event has a UUID and structured metadata. These events flow into our graph database where they connect to workflows, steps, and policies."

---

### Act 4: Show Graph Structure (60 seconds)

**Show**: Neo4j Browser or graph visualization in dashboard

**Say**:
> "Here's the graph view. See how the workflow has defined steps with NEXT relationships? And notice the Policy nodes - these encode our compliance rules as first-class entities, not hardcoded logic."

**Highlight**: The Ripple Effect query

**Run** (in Neo4j Browser or via API):
```cypher
MATCH (failed:Step {status: 'FAILED'})-[:NEXT*]->(downstream:Step)
RETURN failed, downstream
```

**Say**:
> "This query demonstrates graph-first reasoning. When a step fails, we can instantly traverse the graph to find all downstream impacts. This isn't possible with traditional log analysis."

---

### Act 5: Agent Analysis (90 seconds)

**Show**: Dashboard insights panel

**Say**:
> "Now let's see what our agents detected."

**Walk through each insight card**:

1. **Workflow Agent finding**:
> "The Workflow Agent detected that the Approval step was skipped. It queried the graph for mandatory steps and found one without a completion event."

2. **Policy Agent finding**:
> "The Policy Agent flagged this as a compliance violation. The policy requiring approval was encoded in the graph, and the agent detected it wasn't satisfied."

3. **RCA Agent finding**:
> "The RCA Agent built a causal chain. Note the language - 'probable causal relationship, not formal proof' - we're explicit about what we can and can't claim."

**Show**: Evidence panel for one insight

**Say**:
> "Every insight traces back to specific evidence. Here's the opinion from the Workflow Agent with its confidence score, and here's the exact graph query that produced it. This is our ATRE principle - Auditable, Traceable, Retryable, Explainable."

---

### Act 6: Multi-Agent Synthesis (45 seconds)

**Show**: Master Agent insight

**Say**:
> "The Master Agent synthesizes opinions from all specialized agents. It doesn't override them - it combines them into actionable insights with recommended actions."

**Highlight**:
> "Notice the confidence scores aggregate across agents. When multiple agents agree, confidence increases. This is agent consensus, not voting - each opinion stands on its evidence."

---

### Act 7: Resource Vampire Scenario (60 seconds)

**Run**:
```bash
python -m simulator.scenario_generator --scenario resource-vampire --output resource_events.jsonl
```

**Show**: Dashboard after processing

**Say**:
> "Our second scenario - the Resource Vampire. This simulates gradual resource exhaustion."

**Highlight the trend detection**:
> "The Resource Agent detected a 150% increase over the observation window. This isn't just threshold alerting - it's trend analysis that catches slow degradation before it becomes critical."

---

### Act 8: Wrap-up (30 seconds)

**Show**: README or architecture diagram

**Say**:
> "To summarize: IICWMS delivers Cognitive Observability through:
> - Graph-based reasoning, not just pattern matching
> - Multi-agent coordination with explicit evidence
> - Full explainability via the Blackboard pattern
> 
> Round-1 focuses on architectural validation. The foundation is solid for production features like real-time streaming and advanced ML."

---

## Demo Don'ts

- **Don't** claim "AI-powered detection" - detection is rule/graph-based
- **Don't** show unfinished UI elements
- **Don't** spend time on setup/config screens
- **Don't** run queries that might fail
- **Don't** overclaim - use the approved phrases

## Backup Plans

If Neo4j connection fails:
- Show pre-recorded graph visualization
- Explain architecture without live graph

If frontend doesn't load:
- Demo via API calls in terminal
- Use `curl` to show JSON responses

If scenario generator fails:
- Have pre-generated `events.jsonl` files ready
- Load them directly via API

## Post-Demo Notes

After recording:
- Trim any pauses or errors
- Ensure audio is clear
- Add captions for key phrases
- Keep under 7 minutes total
