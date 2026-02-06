"""
IICWMS Neo4j Client
Manages connection and operations with Neo4j graph database.

Neo4j is the authoritative system state - all agents query the graph for context.
"""

import os
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from neo4j import GraphDatabase, Driver, Session
from dotenv import load_dotenv

load_dotenv()


class Neo4jClient:
    """Client for Neo4j graph database operations."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.uri = uri or os.getenv("NEO4J_URI")
        self.user = user or os.getenv("NEO4J_USER")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self._driver: Optional[Driver] = None

    def connect(self) -> None:
        """Establish connection to Neo4j."""
        if not all([self.uri, self.user, self.password]):
            raise ValueError("Neo4j connection details not configured")
        
        self._driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password)
        )
        # Verify connectivity
        self._driver.verify_connectivity()

    def close(self) -> None:
        """Close the Neo4j connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    @contextmanager
    def session(self):
        """Context manager for Neo4j sessions."""
        if not self._driver:
            self.connect()
        session = self._driver.session()
        try:
            yield session
        finally:
            session.close()

    def init_schema(self) -> None:
        """Initialize the graph schema with constraints and indexes."""
        schema_queries = [
            # Constraints for unique identifiers
            "CREATE CONSTRAINT workflow_id IF NOT EXISTS FOR (w:Workflow) REQUIRE w.id IS UNIQUE",
            "CREATE CONSTRAINT step_id IF NOT EXISTS FOR (s:Step) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT resource_id IF NOT EXISTS FOR (r:Resource) REQUIRE r.id IS UNIQUE",
            "CREATE CONSTRAINT policy_id IF NOT EXISTS FOR (p:Policy) REQUIRE p.id IS UNIQUE",
            
            # Indexes for common queries
            "CREATE INDEX event_timestamp IF NOT EXISTS FOR (e:Event) ON (e.timestamp)",
            "CREATE INDEX step_status IF NOT EXISTS FOR (s:Step) ON (s.status)",
            "CREATE INDEX anomaly_type IF NOT EXISTS FOR (a:Anomaly) ON (a.type)",
        ]
        
        with self.session() as session:
            for query in schema_queries:
                try:
                    session.run(query)
                except Exception as e:
                    # Constraint/index may already exist
                    print(f"Schema query note: {e}")

    def create_workflow(self, workflow_id: str, name: str, steps: List[Dict]) -> None:
        """Create a workflow with its steps in the graph."""
        query = """
        CREATE (w:Workflow {id: $workflow_id, name: $name, created_at: datetime()})
        WITH w
        UNWIND $steps AS step
        CREATE (s:Step {
            id: step.id,
            name: step.name,
            sequence: step.sequence,
            mandatory: step.mandatory,
            status: 'PENDING'
        })
        CREATE (w)-[:HAS_STEP]->(s)
        WITH collect(s) AS stepNodes
        UNWIND range(0, size(stepNodes)-2) AS i
        WITH stepNodes[i] AS current, stepNodes[i+1] AS next
        CREATE (current)-[:NEXT]->(next)
        """
        
        with self.session() as session:
            session.run(query, workflow_id=workflow_id, name=name, steps=steps)

    def record_event(self, event: Dict[str, Any]) -> None:
        """Record an event and link it to relevant entities."""
        query = """
        CREATE (e:Event {
            id: $id,
            timestamp: datetime($timestamp),
            event_type: $event_type,
            source: $source,
            metadata: $metadata
        })
        WITH e
        OPTIONAL MATCH (w:Workflow {id: $workflow_id})
        FOREACH (_ IN CASE WHEN w IS NOT NULL THEN [1] ELSE [] END |
            CREATE (e)-[:OCCURRED_IN_WORKFLOW]->(w)
        )
        WITH e
        OPTIONAL MATCH (s:Step {id: $step_id})
        FOREACH (_ IN CASE WHEN s IS NOT NULL THEN [1] ELSE [] END |
            CREATE (e)-[:OCCURRED_IN_STEP]->(s)
        )
        """
        
        with self.session() as session:
            session.run(
                query,
                id=event.get("id"),
                timestamp=event.get("timestamp"),
                event_type=event.get("event_type"),
                source=event.get("source"),
                workflow_id=event.get("workflow_id"),
                step_id=event.get("step_id"),
                metadata=str(event.get("metadata", {}))
            )

    def get_workflow_state(self, workflow_id: str) -> Dict[str, Any]:
        """Get current state of a workflow including all steps and events."""
        query = """
        MATCH (w:Workflow {id: $workflow_id})
        OPTIONAL MATCH (w)-[:HAS_STEP]->(s:Step)
        OPTIONAL MATCH (e:Event)-[:OCCURRED_IN_STEP]->(s)
        RETURN w, collect(DISTINCT s) AS steps, collect(DISTINCT e) AS events
        """
        
        with self.session() as session:
            result = session.run(query, workflow_id=workflow_id)
            record = result.single()
            if record:
                return {
                    "workflow": dict(record["w"]),
                    "steps": [dict(s) for s in record["steps"]],
                    "events": [dict(e) for e in record["events"]]
                }
            return {}

    def find_skipped_steps(self, workflow_id: str) -> List[Dict]:
        """Find mandatory steps that were skipped in a workflow."""
        query = """
        MATCH (w:Workflow {id: $workflow_id})-[:HAS_STEP]->(s:Step {mandatory: true})
        WHERE NOT EXISTS((s)<-[:OCCURRED_IN_STEP]-(:Event {event_type: 'WORKFLOW_STEP_COMPLETE'}))
        RETURN s.id AS step_id, s.name AS step_name, s.sequence AS sequence
        ORDER BY s.sequence
        """
        
        with self.session() as session:
            result = session.run(query, workflow_id=workflow_id)
            return [dict(record) for record in result]

    def get_ripple_effect(self, failed_step_id: str) -> List[Dict]:
        """Find all downstream impacts when a step fails."""
        query = """
        MATCH (failed:Step {id: $step_id})-[:NEXT*]->(downstream:Step)
        OPTIONAL MATCH (downstream)-[:USES]->(resource:Resource)
        RETURN downstream.id AS step_id,
               downstream.name AS step_name,
               collect(DISTINCT resource.name) AS affected_resources,
               length((failed)-[:NEXT*]->(downstream)) AS distance
        ORDER BY distance
        """
        
        with self.session() as session:
            result = session.run(query, step_id=failed_step_id)
            return [dict(record) for record in result]

    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute an arbitrary Cypher query."""
        with self.session() as session:
            result = session.run(query, params or {})
            return [dict(record) for record in result]


def main():
    """CLI entry point for Neo4j operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Neo4j client operations")
    parser.add_argument("--init-schema", action="store_true", help="Initialize graph schema")
    parser.add_argument("--test-connection", action="store_true", help="Test Neo4j connection")
    
    args = parser.parse_args()
    
    client = Neo4jClient()
    
    try:
        if args.test_connection:
            client.connect()
            print("Successfully connected to Neo4j")
        
        if args.init_schema:
            client.connect()
            client.init_schema()
            print("Schema initialized successfully")
    
    finally:
        client.close()


if __name__ == "__main__":
    main()
