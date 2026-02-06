"""
IICWMS Evidence Store
Append-only store for agent opinions - the Blackboard pattern.

This implements the ATRE pillar:
- Auditable: All opinions are logged with timestamps and agent IDs
- Traceable: Each opinion links back to specific events and evidence
- Retryable: Given the same input, agents produce deterministic outputs
- Explainable: Full provenance chain is preserved
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import threading


class EvidenceStore:
    """
    Append-only evidence store implementing the Blackboard pattern.
    
    All agent opinions are recorded here, creating an auditable trail
    of the system's reasoning process.
    """

    def __init__(self, filepath: str = "blackboard/evidence_log.jsonl"):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        
        # In-memory index for fast lookups
        self._index_by_id: Dict[str, int] = {}
        self._index_by_agent: Dict[str, List[str]] = {}
        self._index_by_type: Dict[str, List[str]] = {}
        
        # Load existing records into index
        self._load_index()

    def _load_index(self):
        """Load existing records into the in-memory index."""
        if not self.filepath.exists():
            return
        
        with open(self.filepath, 'r') as f:
            for line_num, line in enumerate(f):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    record_id = record.get("id")
                    if record_id:
                        self._index_by_id[record_id] = line_num
                        
                        agent = record.get("agent", "unknown")
                        if agent not in self._index_by_agent:
                            self._index_by_agent[agent] = []
                        self._index_by_agent[agent].append(record_id)
                        
                        opinion_type = record.get("opinion_type", "unknown")
                        if opinion_type not in self._index_by_type:
                            self._index_by_type[opinion_type] = []
                        self._index_by_type[opinion_type].append(record_id)
                except json.JSONDecodeError:
                    continue

    def append(self, record: Dict[str, Any]) -> str:
        """
        Append a record to the evidence store.
        
        Args:
            record: The opinion/evidence to store
            
        Returns:
            The record ID
        """
        with self._lock:
            # Ensure required fields
            if "id" not in record:
                import uuid
                record["id"] = str(uuid.uuid4())
            
            if "stored_at" not in record:
                record["stored_at"] = datetime.utcnow().isoformat()
            
            # Append to file
            with open(self.filepath, 'a') as f:
                f.write(json.dumps(record) + '\n')
            
            # Update index
            record_id = record["id"]
            line_num = sum(1 for _ in open(self.filepath)) - 1
            self._index_by_id[record_id] = line_num
            
            agent = record.get("agent", "unknown")
            if agent not in self._index_by_agent:
                self._index_by_agent[agent] = []
            self._index_by_agent[agent].append(record_id)
            
            opinion_type = record.get("opinion_type", "unknown")
            if opinion_type not in self._index_by_type:
                self._index_by_type[opinion_type] = []
            self._index_by_type[opinion_type].append(record_id)
            
            return record_id

    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific record by ID."""
        if record_id not in self._index_by_id:
            return None
        
        line_num = self._index_by_id[record_id]
        
        with open(self.filepath, 'r') as f:
            for i, line in enumerate(f):
                if i == line_num:
                    return json.loads(line)
        
        return None

    def get_by_agent(self, agent: str) -> List[Dict[str, Any]]:
        """Retrieve all records from a specific agent."""
        record_ids = self._index_by_agent.get(agent, [])
        return [self.get(rid) for rid in record_ids if self.get(rid)]

    def get_by_type(self, opinion_type: str) -> List[Dict[str, Any]]:
        """Retrieve all records of a specific type."""
        record_ids = self._index_by_type.get(opinion_type, [])
        return [self.get(rid) for rid in record_ids if self.get(rid)]

    def get_by_insight(self, insight_id: str) -> Dict[str, Any]:
        """
        Retrieve all evidence related to an insight.
        
        This traverses the evidence chain to collect all contributing opinions.
        """
        # For now, return all records as context
        # In production, this would filter by insight linkage
        records = self.get_all()
        return {
            "insight_id": insight_id,
            "evidence_count": len(records),
            "records": records[-20:]  # Return last 20 for context
        }

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve all records with pagination."""
        records = []
        
        if not self.filepath.exists():
            return records
        
        with open(self.filepath, 'r') as f:
            for i, line in enumerate(f):
                if i < offset:
                    continue
                if len(records) >= limit:
                    break
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        return records

    def get_recent(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent records."""
        records = []
        
        if not self.filepath.exists():
            return records
        
        # Read all lines and get last N
        with open(self.filepath, 'r') as f:
            lines = f.readlines()
        
        for line in lines[-count:]:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        
        return records

    def search(
        self,
        agent: Optional[str] = None,
        opinion_type: Optional[str] = None,
        since: Optional[datetime] = None,
        confidence_min: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search records with filters.
        
        Args:
            agent: Filter by agent name
            opinion_type: Filter by opinion type
            since: Filter by timestamp (records after this time)
            confidence_min: Filter by minimum confidence score
            
        Returns:
            List of matching records
        """
        results = []
        
        for record in self.get_all(limit=1000):
            # Apply filters
            if agent and record.get("agent") != agent:
                continue
            
            if opinion_type and record.get("opinion_type") != opinion_type:
                continue
            
            if since:
                record_time = record.get("timestamp") or record.get("stored_at")
                if record_time:
                    try:
                        rt = datetime.fromisoformat(record_time.replace('Z', '+00:00'))
                        if rt < since:
                            continue
                    except Exception:
                        pass
            
            if confidence_min is not None:
                if record.get("confidence", 0) < confidence_min:
                    continue
            
            results.append(record)
        
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the evidence store."""
        return {
            "total_records": len(self._index_by_id),
            "records_by_agent": {
                agent: len(ids) 
                for agent, ids in self._index_by_agent.items()
            },
            "records_by_type": {
                otype: len(ids) 
                for otype, ids in self._index_by_type.items()
            },
            "filepath": str(self.filepath)
        }

    def clear(self):
        """Clear all records (use with caution - for testing only)."""
        with self._lock:
            if self.filepath.exists():
                self.filepath.unlink()
            self._index_by_id.clear()
            self._index_by_agent.clear()
            self._index_by_type.clear()


# Singleton instance for easy access
_default_store: Optional[EvidenceStore] = None


def get_evidence_store(filepath: str = "blackboard/evidence_log.jsonl") -> EvidenceStore:
    """Get the default evidence store instance."""
    global _default_store
    if _default_store is None:
        _default_store = EvidenceStore(filepath)
    return _default_store
