"""
IICWMS Observation Layer
========================
OBSERVE - Raw facts only.

PURPOSE:
- Ingest events and metrics
- Store in append-only, time-ordered manner
- Provide windowed queries

FORBIDDEN:
- No aggregation
- No interpretation
- No reasoning

This layer is the bridge between Simulation and Reasoning.
"""

import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
import threading


@dataclass
class ObservedEvent:
    """An observed event - raw fact."""
    event_id: str
    type: str
    workflow_id: Optional[str]
    actor: str
    resource: Optional[str]
    timestamp: datetime
    metadata: Dict[str, Any]
    observed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ObservedMetric:
    """An observed metric - raw measurement."""
    resource_id: str
    metric: str
    value: float
    timestamp: datetime
    observed_at: datetime = field(default_factory=datetime.utcnow)


class ObservationLayer:
    """
    The Observation Layer.
    
    Rules:
    - Append-only
    - Time-ordered
    - No aggregation
    
    Persistence:
    - Primary: SQLite (db/sqlite_store.py)
    - In-memory buffer for fast recent queries
    - JSONL kept as optional backup
    """
    
    def __init__(self, storage_path: str = "observation/events.jsonl"):
        self._storage_path = Path(storage_path)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory buffer for fast access (bounded)
        self._events: List[ObservedEvent] = []
        self._metrics: List[ObservedMetric] = []
        self._lock = threading.Lock()
        self._max_buffer = 5000  # Keep last N in memory
        
        # SQLite store (lazy init to avoid circular import at module level)
        self._db = None
        
        # Load existing data from JSONL (backward compat)
        self._load_from_storage()
    
    def _get_db(self):
        """Lazy-init SQLite store."""
        if self._db is None:
            from db import get_sqlite_store
            self._db = get_sqlite_store()
        return self._db
    
    def _load_from_storage(self):
        """Load existing observations from storage."""
        if not self._storage_path.exists():
            return
        
        with open(self._storage_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if record.get("record_type") == "event":
                        self._events.append(ObservedEvent(
                            event_id=record["event_id"],
                            type=record["type"],
                            workflow_id=record.get("workflow_id"),
                            actor=record["actor"],
                            resource=record.get("resource"),
                            timestamp=datetime.fromisoformat(record["timestamp"]),
                            metadata=record.get("metadata", {}),
                            observed_at=datetime.fromisoformat(record["observed_at"])
                        ))
                    elif record.get("record_type") == "metric":
                        self._metrics.append(ObservedMetric(
                            resource_id=record["resource_id"],
                            metric=record["metric"],
                            value=record["value"],
                            timestamp=datetime.fromisoformat(record["timestamp"]),
                            observed_at=datetime.fromisoformat(record["observed_at"])
                        ))
                except (json.JSONDecodeError, KeyError):
                    continue
    
    # ─────────────────────────────────────────────────────────────────────────────
    # INGEST APIs
    # ─────────────────────────────────────────────────────────────────────────────
    
    def observe_event(self, event_data: Dict[str, Any]) -> ObservedEvent:
        """
        POST /observe/event
        
        Ingest a raw event. No interpretation.
        Writes to: in-memory buffer + SQLite + JSONL backup.
        """
        with self._lock:
            observed = ObservedEvent(
                event_id=event_data["event_id"],
                type=event_data["type"],
                workflow_id=event_data.get("workflow_id"),
                actor=event_data["actor"],
                resource=event_data.get("resource"),
                timestamp=datetime.fromisoformat(event_data["timestamp"]) if isinstance(event_data["timestamp"], str) else event_data["timestamp"],
                metadata=event_data.get("metadata", {}),
                observed_at=datetime.utcnow()
            )
            
            self._events.append(observed)
            # Bound in-memory buffer
            if len(self._events) > self._max_buffer:
                self._events = self._events[-self._max_buffer:]
            
            self._persist_event(observed)
            
            # Write to SQLite
            try:
                self._get_db().insert_event(
                    event_id=observed.event_id,
                    type=observed.type,
                    workflow_id=observed.workflow_id,
                    actor=observed.actor,
                    resource=observed.resource,
                    timestamp=observed.timestamp.isoformat(),
                    metadata=observed.metadata,
                    observed_at=observed.observed_at.isoformat(),
                )
            except Exception:
                pass  # SQLite write failure should not block observation
            
            return observed
    
    def observe_metric(self, metric_data: Dict[str, Any]) -> ObservedMetric:
        """
        POST /observe/metric
        
        Ingest a raw metric. No interpretation.
        Writes to: in-memory buffer + SQLite + JSONL backup.
        """
        with self._lock:
            observed = ObservedMetric(
                resource_id=metric_data["resource_id"],
                metric=metric_data["metric"],
                value=metric_data["value"],
                timestamp=datetime.fromisoformat(metric_data["timestamp"]) if isinstance(metric_data["timestamp"], str) else metric_data["timestamp"],
                observed_at=datetime.utcnow()
            )
            
            self._metrics.append(observed)
            # Bound in-memory buffer
            if len(self._metrics) > self._max_buffer:
                self._metrics = self._metrics[-self._max_buffer:]
            
            self._persist_metric(observed)
            
            # Write to SQLite
            try:
                self._get_db().insert_metric(
                    resource_id=observed.resource_id,
                    metric=observed.metric,
                    value=observed.value,
                    timestamp=observed.timestamp.isoformat(),
                    observed_at=observed.observed_at.isoformat(),
                )
            except Exception:
                pass  # SQLite write failure should not block observation
            
            return observed
    
    def _persist_event(self, event: ObservedEvent):
        """Append event to storage."""
        record = {
            "record_type": "event",
            "event_id": event.event_id,
            "type": event.type,
            "workflow_id": event.workflow_id,
            "actor": event.actor,
            "resource": event.resource,
            "timestamp": event.timestamp.isoformat(),
            "metadata": event.metadata,
            "observed_at": event.observed_at.isoformat()
        }
        with open(self._storage_path, 'a') as f:
            f.write(json.dumps(record) + '\n')
    
    def _persist_metric(self, metric: ObservedMetric):
        """Append metric to storage."""
        record = {
            "record_type": "metric",
            "resource_id": metric.resource_id,
            "metric": metric.metric,
            "value": metric.value,
            "timestamp": metric.timestamp.isoformat(),
            "observed_at": metric.observed_at.isoformat()
        }
        with open(self._storage_path, 'a') as f:
            f.write(json.dumps(record) + '\n')
    
    # ─────────────────────────────────────────────────────────────────────────────
    # QUERY APIs
    # ─────────────────────────────────────────────────────────────────────────────
    
    def get_event_window(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        event_type: Optional[str] = None,
        workflow_id: Optional[str] = None,
        limit: int = 1000
    ) -> List[ObservedEvent]:
        """
        GET /observe/window (events)
        
        Query events in a time window. No aggregation.
        """
        with self._lock:
            results = []
            for event in reversed(self._events):  # Most recent first
                if len(results) >= limit:
                    break
                
                if start and event.timestamp < start:
                    continue
                if end and event.timestamp > end:
                    continue
                if event_type and event.type != event_type:
                    continue
                if workflow_id and event.workflow_id != workflow_id:
                    continue
                
                results.append(event)
            
            return results
    
    def get_metric_window(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        resource_id: Optional[str] = None,
        metric: Optional[str] = None,
        limit: int = 1000
    ) -> List[ObservedMetric]:
        """
        GET /observe/window (metrics)
        
        Query metrics in a time window. No aggregation.
        """
        with self._lock:
            results = []
            for m in reversed(self._metrics):  # Most recent first
                if len(results) >= limit:
                    break
                
                if start and m.timestamp < start:
                    continue
                if end and m.timestamp > end:
                    continue
                if resource_id and m.resource_id != resource_id:
                    continue
                if metric and m.metric != metric:
                    continue
                
                results.append(m)
            
            return results
    
    def get_recent_events(self, count: int = 100) -> List[ObservedEvent]:
        """Get most recent N events."""
        with self._lock:
            return list(reversed(self._events[-count:]))
    
    def get_recent_metrics(self, count: int = 100) -> List[ObservedMetric]:
        """Get most recent N metrics."""
        with self._lock:
            return list(reversed(self._metrics[-count:]))
    
    def clear(self):
        """Clear all observations (for testing)."""
        with self._lock:
            self._events.clear()
            self._metrics.clear()
            if self._storage_path.exists():
                self._storage_path.unlink()


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton access
# ═══════════════════════════════════════════════════════════════════════════════

_instance: Optional[ObservationLayer] = None


def get_observation_layer() -> ObservationLayer:
    """Get the singleton observation layer instance."""
    global _instance
    if _instance is None:
        _instance = ObservationLayer()
    return _instance
