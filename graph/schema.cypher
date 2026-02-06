// IICWMS Graph Schema
// Neo4j is the authoritative system state

// ============================================
// CONSTRAINTS (Unique Identifiers)
// ============================================

CREATE CONSTRAINT workflow_id IF NOT EXISTS 
FOR (w:Workflow) REQUIRE w.id IS UNIQUE;

CREATE CONSTRAINT step_id IF NOT EXISTS 
FOR (s:Step) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT event_id IF NOT EXISTS 
FOR (e:Event) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT resource_id IF NOT EXISTS 
FOR (r:Resource) REQUIRE r.id IS UNIQUE;

CREATE CONSTRAINT policy_id IF NOT EXISTS 
FOR (p:Policy) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT anomaly_id IF NOT EXISTS 
FOR (a:Anomaly) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT agent_id IF NOT EXISTS 
FOR (ag:Agent) REQUIRE ag.id IS UNIQUE;

// ============================================
// INDEXES (Query Performance)
// ============================================

CREATE INDEX event_timestamp IF NOT EXISTS 
FOR (e:Event) ON (e.timestamp);

CREATE INDEX event_type IF NOT EXISTS 
FOR (e:Event) ON (e.event_type);

CREATE INDEX step_status IF NOT EXISTS 
FOR (s:Step) ON (s.status);

CREATE INDEX anomaly_type IF NOT EXISTS 
FOR (a:Anomaly) ON (a.type);

CREATE INDEX resource_type IF NOT EXISTS 
FOR (r:Resource) ON (r.type);

// ============================================
// NODE DEFINITIONS (Reference)
// ============================================

// Workflow: Represents a business process
// Properties: id, name, description, created_at, status

// Step: Individual step within a workflow
// Properties: id, name, sequence, mandatory, status, timeout_seconds

// Event: System event that occurred
// Properties: id, timestamp, event_type, source, metadata

// Resource: System resource (CPU, Memory, Service, etc.)
// Properties: id, name, type, capacity, current_usage

// Policy: Compliance or business rule
// Properties: id, name, description, severity, condition

// Anomaly: Detected anomaly
// Properties: id, type, confidence, detected_at, description

// Agent: Reasoning agent that produced an opinion
// Properties: id, name, type, version

// ============================================
// RELATIONSHIP DEFINITIONS (Reference)
// ============================================

// Workflow Structure
// (:Workflow)-[:HAS_STEP]->(:Step)
// (:Step)-[:NEXT]->(:Step)
// (:Step)-[:USES]->(:Resource)
// (:Step)-[:REQUIRES]->(:Step)  // Dependencies

// Policy Application
// (:Policy)-[:APPLIES_TO]->(:Step)
// (:Policy)-[:APPLIES_TO]->(:Workflow)
// (:Policy)-[:MONITORS]->(:Resource)

// Event Tracking
// (:Event)-[:OCCURRED_IN_WORKFLOW]->(:Workflow)
// (:Event)-[:OCCURRED_IN_STEP]->(:Step)
// (:Event)-[:AFFECTED]->(:Resource)
// (:Event)-[:TRIGGERED_BY]->(:Event)

// Anomaly Tracking
// (:Anomaly)-[:DETECTED_IN]->(:Event)
// (:Anomaly)-[:AFFECTS]->(:Step)
// (:Anomaly)-[:AFFECTS]->(:Resource)
// (:Anomaly)-[:VIOLATES]->(:Policy)
// (:Anomaly)-[:DETECTED_BY]->(:Agent)

// Causal Chain
// (:Anomaly)-[:CAUSED_BY]->(:Anomaly)
// (:Event)-[:LED_TO]->(:Event)
