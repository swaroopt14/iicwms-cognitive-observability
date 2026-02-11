"""
IICWMS Neo4j Knowledge Graph Client
====================================
Manages connection and operations with Neo4j Aura graph database.

Design:
- Singleton via get_neo4j_client()
- Graceful fallback: NullGraphClient if Neo4j is not configured/reachable
- System works fully without Neo4j (all graph ops become no-ops)
- Thread-safe session management
"""

import os
import logging
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger("chronos.graph")


class NullGraphClient:
    """
    No-op graph client used when Neo4j is not configured.
    Every method returns empty results silently.
    """

    def connect(self) -> None:
        pass

    def close(self) -> None:
        pass

    @contextmanager
    def session(self):
        yield None

    def init_schema(self) -> None:
        pass

    def create_workflow(self, workflow_id: str, name: str, steps: List[Dict]) -> None:
        pass

    def record_event(self, event: Dict[str, Any]) -> None:
        pass

    def write_causal_link(self, cause: str, effect: str, cause_entity: str,
                          effect_entity: str, confidence: float, reasoning: str) -> None:
        pass

    def write_anomaly(self, anomaly_id: str, type: str, agent: str,
                      confidence: float, description: str) -> None:
        pass

    def write_recommendation(self, rec_id: str, cause: str, action: str,
                             urgency: str) -> None:
        pass

    def get_workflow_state(self, workflow_id: str) -> Dict[str, Any]:
        return {}

    def find_skipped_steps(self, workflow_id: str) -> List[Dict]:
        return []

    def get_ripple_effect(self, failed_step_id: str) -> List[Dict]:
        return []

    def get_entity_relationships(self, entity_id: str) -> List[Dict]:
        return []

    def get_causal_chain(self, anomaly_id: str) -> List[Dict]:
        return []

    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        return []

    def get_stats(self) -> Dict[str, Any]:
        return {"status": "disabled", "message": "Neo4j not configured"}

    @property
    def is_connected(self) -> bool:
        return False


class Neo4jClient:
    """Client for Neo4j Aura graph database operations."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None

    def connect(self) -> None:
        """Establish connection to Neo4j."""
        from neo4j import GraphDatabase

        if not all([self.uri, self.user, self.password]):
            raise ValueError("Neo4j connection details not configured")

        self._driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password)
        )
        self._driver.verify_connectivity()
        logger.info(f"Connected to Neo4j at {self.uri}")

    def close(self) -> None:
        """Close the Neo4j connection."""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    @property
    def is_connected(self) -> bool:
        return self._driver is not None

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

    # ─────────────────────────────────────────────────────────────────────────
    # SCHEMA
    # ─────────────────────────────────────────────────────────────────────────

    def init_schema(self) -> None:
        """Initialize the graph schema with constraints and indexes."""
        schema_queries = [
            "CREATE CONSTRAINT workflow_id IF NOT EXISTS FOR (w:Workflow) REQUIRE w.id IS UNIQUE",
            "CREATE CONSTRAINT step_id IF NOT EXISTS FOR (s:Step) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT resource_id IF NOT EXISTS FOR (r:Resource) REQUIRE r.id IS UNIQUE",
            "CREATE CONSTRAINT policy_id IF NOT EXISTS FOR (p:Policy) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT anomaly_id IF NOT EXISTS FOR (a:Anomaly) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT agent_id IF NOT EXISTS FOR (ag:Agent) REQUIRE ag.id IS UNIQUE",
            "CREATE INDEX event_timestamp IF NOT EXISTS FOR (e:Event) ON (e.timestamp)",
            "CREATE INDEX step_status IF NOT EXISTS FOR (s:Step) ON (s.status)",
            "CREATE INDEX anomaly_type IF NOT EXISTS FOR (a:Anomaly) ON (a.type)",
            "CREATE INDEX resource_type IF NOT EXISTS FOR (r:Resource) ON (r.type)",
        ]

        with self.session() as session:
            for query in schema_queries:
                try:
                    session.run(query)
                except Exception as e:
                    logger.debug(f"Schema note: {e}")

        logger.info("Neo4j schema initialized")

    # ─────────────────────────────────────────────────────────────────────────
    # WORKFLOW TOPOLOGY
    # ─────────────────────────────────────────────────────────────────────────

    def create_workflow(self, workflow_id: str, name: str, steps: List[Dict]) -> None:
        """Create a workflow with its steps in the graph."""
        query = """
        MERGE (w:Workflow {id: $workflow_id})
        SET w.name = $name, w.created_at = datetime()
        WITH w
        UNWIND $steps AS step
        MERGE (s:Step {id: step.id})
        SET s.name = step.name, s.sequence = step.sequence,
            s.mandatory = step.mandatory, s.status = 'PENDING'
        MERGE (w)-[:HAS_STEP]->(s)
        WITH collect(s) AS stepNodes
        UNWIND range(0, size(stepNodes)-2) AS i
        WITH stepNodes[i] AS current, stepNodes[i+1] AS next
        MERGE (current)-[:NEXT]->(next)
        """
        try:
            with self.session() as session:
                session.run(query, workflow_id=workflow_id, name=name, steps=steps)
        except Exception as e:
            logger.warning(f"Neo4j create_workflow failed: {e}")

    def record_event(self, event: Dict[str, Any]) -> None:
        """Record an event and link it to relevant entities."""
        query = """
        MERGE (e:Event {id: $id})
        SET e.timestamp = $timestamp, e.event_type = $event_type,
            e.source = $source, e.metadata = $metadata
        WITH e
        OPTIONAL MATCH (w:Workflow {id: $workflow_id})
        FOREACH (_ IN CASE WHEN w IS NOT NULL THEN [1] ELSE [] END |
            MERGE (e)-[:OCCURRED_IN_WORKFLOW]->(w)
        )
        """
        try:
            with self.session() as session:
                session.run(
                    query,
                    id=event.get("id", event.get("event_id", "")),
                    timestamp=event.get("timestamp", ""),
                    event_type=event.get("event_type", event.get("type", "")),
                    source=event.get("source", event.get("actor", "")),
                    workflow_id=event.get("workflow_id", ""),
                    metadata=str(event.get("metadata", {}))
                )
        except Exception as e:
            logger.warning(f"Neo4j record_event failed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # CAUSAL LINKS
    # ─────────────────────────────────────────────────────────────────────────

    def write_causal_link(self, cause: str, effect: str, cause_entity: str,
                          effect_entity: str, confidence: float, reasoning: str) -> None:
        """Write a causal link as a CAUSED_BY edge."""
        query = """
        MERGE (c:Anomaly {id: $cause_entity})
        SET c.type = $cause
        MERGE (e:Anomaly {id: $effect_entity})
        SET e.type = $effect
        MERGE (e)-[r:CAUSED_BY]->(c)
        SET r.confidence = $confidence, r.reasoning = $reasoning,
            r.detected_at = datetime()
        """
        try:
            with self.session() as session:
                session.run(query, cause=cause, effect=effect,
                            cause_entity=cause_entity, effect_entity=effect_entity,
                            confidence=confidence, reasoning=reasoning)
        except Exception as e:
            logger.warning(f"Neo4j write_causal_link failed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # ANOMALIES & RECOMMENDATIONS
    # ─────────────────────────────────────────────────────────────────────────

    def write_anomaly(self, anomaly_id: str, type: str, agent: str,
                      confidence: float, description: str) -> None:
        """Write an anomaly node and link to its detecting agent."""
        query = """
        MERGE (a:Anomaly {id: $anomaly_id})
        SET a.type = $type, a.confidence = $confidence,
            a.description = $description, a.detected_at = datetime()
        MERGE (ag:Agent {id: $agent})
        SET ag.name = $agent, ag.type = 'specialized'
        MERGE (a)-[:DETECTED_BY]->(ag)
        """
        try:
            with self.session() as session:
                session.run(query, anomaly_id=anomaly_id, type=type,
                            agent=agent, confidence=confidence,
                            description=description)
        except Exception as e:
            logger.warning(f"Neo4j write_anomaly failed: {e}")

    def write_recommendation(self, rec_id: str, cause: str, action: str,
                             urgency: str) -> None:
        """Write a recommendation node."""
        query = """
        MERGE (r:Recommendation {id: $rec_id})
        SET r.cause = $cause, r.action = $action,
            r.urgency = $urgency, r.created_at = datetime()
        """
        try:
            with self.session() as session:
                session.run(query, rec_id=rec_id, cause=cause,
                            action=action, urgency=urgency)
        except Exception as e:
            logger.warning(f"Neo4j write_recommendation failed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # QUERY APIs
    # ─────────────────────────────────────────────────────────────────────────

    def get_workflow_state(self, workflow_id: str) -> Dict[str, Any]:
        """Get current state of a workflow."""
        query = """
        MATCH (w:Workflow {id: $workflow_id})
        OPTIONAL MATCH (w)-[:HAS_STEP]->(s:Step)
        OPTIONAL MATCH (e:Event)-[:OCCURRED_IN_STEP]->(s)
        RETURN w, collect(DISTINCT s) AS steps, collect(DISTINCT e) AS events
        """
        try:
            with self.session() as session:
                result = session.run(query, workflow_id=workflow_id)
                record = result.single()
                if record:
                    return {
                        "workflow": dict(record["w"]),
                        "steps": [dict(s) for s in record["steps"]],
                        "events": [dict(e) for e in record["events"]]
                    }
        except Exception as e:
            logger.warning(f"Neo4j get_workflow_state failed: {e}")
        return {}

    def find_skipped_steps(self, workflow_id: str) -> List[Dict]:
        """Find mandatory steps that were skipped."""
        query = """
        MATCH (w:Workflow {id: $workflow_id})-[:HAS_STEP]->(s:Step {mandatory: true})
        WHERE NOT EXISTS((s)<-[:OCCURRED_IN_STEP]-(:Event {event_type: 'WORKFLOW_STEP_COMPLETE'}))
        RETURN s.id AS step_id, s.name AS step_name, s.sequence AS sequence
        ORDER BY s.sequence
        """
        try:
            with self.session() as session:
                result = session.run(query, workflow_id=workflow_id)
                return [dict(record) for record in result]
        except Exception as e:
            logger.warning(f"Neo4j find_skipped_steps failed: {e}")
        return []

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
        try:
            with self.session() as session:
                result = session.run(query, step_id=failed_step_id)
                return [dict(record) for record in result]
        except Exception as e:
            logger.warning(f"Neo4j get_ripple_effect failed: {e}")
        return []

    def get_entity_relationships(self, entity_id: str) -> List[Dict]:
        """Get all relationships for an entity."""
        query = """
        MATCH (n {id: $entity_id})-[r]-(m)
        RETURN type(r) AS relationship, n.id AS from_id, labels(n) AS from_labels,
               m.id AS to_id, labels(m) AS to_labels, properties(r) AS properties
        LIMIT 50
        """
        try:
            with self.session() as session:
                result = session.run(query, entity_id=entity_id)
                return [dict(record) for record in result]
        except Exception as e:
            logger.warning(f"Neo4j get_entity_relationships failed: {e}")
        return []

    def get_causal_chain(self, anomaly_id: str) -> List[Dict]:
        """Trace the full causal chain for an anomaly."""
        query = """
        MATCH path = (a:Anomaly {id: $anomaly_id})-[:CAUSED_BY*1..5]->(root)
        UNWIND relationships(path) AS rel
        WITH startNode(rel) AS effect, endNode(rel) AS cause, rel
        RETURN effect.id AS effect_id, effect.type AS effect_type,
               cause.id AS cause_id, cause.type AS cause_type,
               rel.confidence AS confidence, rel.reasoning AS reasoning
        """
        try:
            with self.session() as session:
                result = session.run(query, anomaly_id=anomaly_id)
                return [dict(record) for record in result]
        except Exception as e:
            logger.warning(f"Neo4j get_causal_chain failed: {e}")
        return []

    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute an arbitrary Cypher query."""
        try:
            with self.session() as session:
                result = session.run(query, params or {})
                return [dict(record) for record in result]
        except Exception as e:
            logger.warning(f"Neo4j execute_query failed: {e}")
        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get graph database statistics."""
        try:
            with self.session() as session:
                node_count = session.run(
                    "MATCH (n) RETURN count(n) AS count"
                ).single()["count"]
                rel_count = session.run(
                    "MATCH ()-[r]->() RETURN count(r) AS count"
                ).single()["count"]
                labels = session.run(
                    "CALL db.labels() YIELD label RETURN collect(label) AS labels"
                ).single()["labels"]
                return {
                    "status": "connected",
                    "uri": self.uri,
                    "total_nodes": node_count,
                    "total_relationships": rel_count,
                    "labels": labels,
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton with graceful fallback
# ═══════════════════════════════════════════════════════════════════════════════

_instance = None


def get_neo4j_client():
    """
    Get the singleton Neo4j client.

    Returns NullGraphClient if Neo4j is not enabled or connection fails.
    System works fully without Neo4j.
    """
    global _instance
    if _instance is not None:
        return _instance

    from api.config import settings

    if not settings.ENABLE_NEO4J:
        logger.info("Neo4j disabled (ENABLE_NEO4J=false). Using NullGraphClient.")
        _instance = NullGraphClient()
        return _instance

    if not all([settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD]):
        logger.warning("Neo4j credentials missing. Using NullGraphClient.")
        _instance = NullGraphClient()
        return _instance

    try:
        client = Neo4jClient(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD,
        )
        client.connect()
        client.init_schema()
        _instance = client
        return _instance
    except Exception as e:
        logger.warning(f"Neo4j connection failed: {e}. Using NullGraphClient.")
        _instance = NullGraphClient()
        return _instance


def main():
    """CLI entry point for Neo4j operations."""
    import argparse
    from dotenv import load_dotenv
    load_dotenv()

    parser = argparse.ArgumentParser(description="Neo4j client operations")
    parser.add_argument("--init-schema", action="store_true")
    parser.add_argument("--test-connection", action="store_true")
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()

    client = Neo4jClient(
        uri=os.getenv("NEO4J_URI"),
        user=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
    )

    try:
        if args.test_connection:
            client.connect()
            print("Successfully connected to Neo4j")

        if args.init_schema:
            client.connect()
            client.init_schema()
            print("Schema initialized successfully")

        if args.stats:
            client.connect()
            print(client.get_stats())
    finally:
        client.close()


if __name__ == "__main__":
    main()
