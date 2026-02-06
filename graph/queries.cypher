// IICWMS Reasoning Queries
// These queries demonstrate graph-first reasoning capabilities

// ============================================
// 1. WORKFLOW INTEGRITY QUERIES
// ============================================

// Find skipped mandatory steps in a workflow
// Detects the "Silent Step-Skipper" scenario
MATCH (w:Workflow {id: $workflow_id})-[:HAS_STEP]->(s:Step {mandatory: true})
WHERE NOT EXISTS {
    MATCH (e:Event {event_type: 'WORKFLOW_STEP_COMPLETE'})-[:OCCURRED_IN_STEP]->(s)
}
RETURN s.id AS skipped_step_id, 
       s.name AS skipped_step_name, 
       s.sequence AS expected_sequence
ORDER BY s.sequence;

// Detect out-of-order step execution
MATCH (w:Workflow {id: $workflow_id})-[:HAS_STEP]->(s1:Step)-[:NEXT]->(s2:Step)
MATCH (e1:Event {event_type: 'WORKFLOW_STEP_COMPLETE'})-[:OCCURRED_IN_STEP]->(s1)
MATCH (e2:Event {event_type: 'WORKFLOW_STEP_COMPLETE'})-[:OCCURRED_IN_STEP]->(s2)
WHERE e2.timestamp < e1.timestamp
RETURN s1.name AS expected_first, 
       s2.name AS executed_first,
       e1.timestamp AS first_completed,
       e2.timestamp AS second_completed;

// ============================================
// 2. RIPPLE EFFECT QUERY (KEY DIFFERENTIATOR)
// ============================================

// Find all downstream impacts when a step fails
// This demonstrates graph-traversal reasoning
MATCH (failed:Step {id: $failed_step_id})-[:NEXT*1..10]->(downstream:Step)
OPTIONAL MATCH (downstream)-[:USES]->(resource:Resource)
OPTIONAL MATCH (policy:Policy)-[:APPLIES_TO]->(downstream)
RETURN downstream.id AS affected_step_id,
       downstream.name AS affected_step_name,
       collect(DISTINCT resource.name) AS affected_resources,
       collect(DISTINCT policy.name) AS applicable_policies,
       length((failed)-[:NEXT*]->(downstream)) AS impact_distance
ORDER BY impact_distance;

// ============================================
// 3. RESOURCE CORRELATION QUERIES
// ============================================

// Find resources under stress with connected workflows
// Supports the "Resource Vampire" scenario
MATCH (r:Resource)
WHERE r.current_usage > r.capacity * 0.8
OPTIONAL MATCH (s:Step)-[:USES]->(r)
OPTIONAL MATCH (w:Workflow)-[:HAS_STEP]->(s)
RETURN r.id AS resource_id,
       r.name AS resource_name,
       r.type AS resource_type,
       r.current_usage AS current_usage,
       r.capacity AS capacity,
       round(r.current_usage * 100.0 / r.capacity, 2) AS usage_percent,
       collect(DISTINCT w.name) AS affected_workflows,
       collect(DISTINCT s.name) AS consuming_steps;

// Trace resource consumption over time
MATCH (e:Event {event_type: 'RESOURCE_METRIC'})-[:AFFECTED]->(r:Resource {id: $resource_id})
RETURN e.timestamp AS timestamp,
       e.metadata.value AS metric_value,
       e.metadata.threshold AS threshold,
       e.metadata.threshold_breached AS breached
ORDER BY e.timestamp;

// ============================================
// 4. POLICY VIOLATION QUERIES
// ============================================

// Find all policy violations for a workflow
MATCH (w:Workflow {id: $workflow_id})
MATCH (a:Anomaly)-[:VIOLATES]->(p:Policy)
MATCH (a)-[:AFFECTS]->(s:Step)<-[:HAS_STEP]-(w)
RETURN p.id AS policy_id,
       p.name AS policy_name,
       p.severity AS severity,
       a.id AS anomaly_id,
       a.description AS violation_description,
       s.name AS affected_step;

// List policies applicable to a step with their status
MATCH (s:Step {id: $step_id})
MATCH (p:Policy)-[:APPLIES_TO]->(s)
OPTIONAL MATCH (a:Anomaly)-[:VIOLATES]->(p)
WHERE (a)-[:AFFECTS]->(s)
RETURN p.id AS policy_id,
       p.name AS policy_name,
       p.description AS policy_description,
       CASE WHEN a IS NOT NULL THEN 'VIOLATED' ELSE 'COMPLIANT' END AS status,
       a.description AS violation_details;

// ============================================
// 5. CAUSAL CHAIN QUERIES
// ============================================

// Build causal chain for an anomaly (root cause tracing)
MATCH path = (root:Anomaly)-[:CAUSED_BY*0..5]->(a:Anomaly {id: $anomaly_id})
WITH nodes(path) AS chain
UNWIND range(0, size(chain)-1) AS idx
WITH chain[idx] AS anomaly, idx AS depth
RETURN anomaly.id AS anomaly_id,
       anomaly.type AS anomaly_type,
       anomaly.description AS description,
       anomaly.confidence AS confidence,
       depth AS causal_depth
ORDER BY depth DESC;

// Find events leading to an anomaly
MATCH (a:Anomaly {id: $anomaly_id})-[:DETECTED_IN]->(trigger:Event)
MATCH path = (earlier:Event)-[:LED_TO*0..5]->(trigger)
RETURN nodes(path) AS event_chain,
       [n IN nodes(path) | n.event_type] AS event_types,
       [n IN nodes(path) | n.timestamp] AS timestamps;

// ============================================
// 6. CREDENTIAL ACCESS PATTERN QUERY
// ============================================

// Detect abnormal credential access patterns
// Supports the "Credential Leaker" scenario
MATCH (e:Event {event_type: 'CREDENTIAL_ACCESS'})
WHERE e.metadata.matches_normal_pattern = false
OPTIONAL MATCH (e)-[:TRIGGERED_BY]->(prev:Event)
RETURN e.id AS event_id,
       e.timestamp AS access_time,
       e.metadata.access_location AS location,
       e.metadata.requesting_service AS service,
       e.metadata.risk_score AS risk_score,
       prev.id AS triggered_by_event
ORDER BY e.timestamp;

// ============================================
// 7. AGENT OPINION CORRELATION
// ============================================

// Find anomalies detected by multiple agents (high confidence)
MATCH (a:Anomaly)
MATCH (ag:Agent)-[:DETECTED]->(a)
WITH a, collect(ag) AS detecting_agents
WHERE size(detecting_agents) > 1
RETURN a.id AS anomaly_id,
       a.type AS anomaly_type,
       a.description AS description,
       [ag IN detecting_agents | ag.name] AS detecting_agents,
       size(detecting_agents) AS agent_consensus;
