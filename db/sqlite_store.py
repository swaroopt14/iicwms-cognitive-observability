"""
IICWMS SQLite Operational Store
================================
Persistent storage for events, metrics, reasoning cycles, anomalies,
policy violations, risk history, insights, and recommendations.

Design:
- Uses Python's built-in sqlite3 (zero external dependencies)
- WAL mode for concurrent reads during reasoning loop writes
- Thread-safe via check_same_thread=False
- Tables auto-created on first connect
- All timestamps stored as ISO 8601 strings
- JSON columns for metadata/evidence/actions
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import threading

logger = logging.getLogger("chronos.db")


class SQLiteStore:
    """
    SQLite operational store for Chronos AI.

    Stores time-series operational data that needs:
    - Persistence across restarts
    - Indexed queries (by timestamp, type, resource)
    - Aggregations (COUNT, GROUP BY for trend charts)
    """

    def __init__(self, db_path: str = "data/chronos.db"):
        self._db_path = db_path
        self._lock = threading.Lock()

        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Connect and initialize
        self._conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
            timeout=10.0,
        )
        self._conn.row_factory = sqlite3.Row
        self._init_db()

        logger.info(f"SQLite store initialized at {db_path}")

    def _init_db(self):
        """Create tables and indexes if they don't exist."""
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        self._conn.executescript("""
            -- ═══════════════════════════════════════════════════════════
            -- OBSERVATION TABLES
            -- ═══════════════════════════════════════════════════════════

            CREATE TABLE IF NOT EXISTS events (
                event_id    TEXT PRIMARY KEY,
                type        TEXT NOT NULL,
                workflow_id TEXT,
                actor       TEXT NOT NULL,
                resource    TEXT,
                timestamp   TEXT NOT NULL,
                metadata    TEXT DEFAULT '{}',
                observed_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS metrics (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id TEXT NOT NULL,
                metric      TEXT NOT NULL,
                value       REAL NOT NULL,
                timestamp   TEXT NOT NULL,
                observed_at TEXT NOT NULL
            );

            -- ═══════════════════════════════════════════════════════════
            -- REASONING CYCLE TABLES
            -- ═══════════════════════════════════════════════════════════

            CREATE TABLE IF NOT EXISTS cycles (
                cycle_id            TEXT PRIMARY KEY,
                started_at          TEXT NOT NULL,
                completed_at        TEXT,
                anomaly_count       INTEGER DEFAULT 0,
                policy_hit_count    INTEGER DEFAULT 0,
                risk_signal_count   INTEGER DEFAULT 0,
                causal_link_count   INTEGER DEFAULT 0,
                recommendation_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS anomalies (
                anomaly_id  TEXT PRIMARY KEY,
                cycle_id    TEXT NOT NULL,
                type        TEXT NOT NULL,
                agent       TEXT NOT NULL,
                description TEXT,
                confidence  REAL DEFAULT 0.0,
                timestamp   TEXT NOT NULL,
                evidence    TEXT DEFAULT '[]',
                FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
            );

            CREATE TABLE IF NOT EXISTS policy_hits (
                hit_id          TEXT PRIMARY KEY,
                cycle_id        TEXT NOT NULL,
                policy_id       TEXT NOT NULL,
                event_id        TEXT,
                violation_type  TEXT NOT NULL,
                agent           TEXT NOT NULL,
                description     TEXT,
                timestamp       TEXT NOT NULL,
                FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
            );

            CREATE TABLE IF NOT EXISTS recommendations (
                rec_id      TEXT PRIMARY KEY,
                cycle_id    TEXT NOT NULL,
                cause       TEXT NOT NULL,
                action      TEXT NOT NULL,
                urgency     TEXT NOT NULL,
                rationale   TEXT,
                timestamp   TEXT NOT NULL,
                FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
            );

            -- ═══════════════════════════════════════════════════════════
            -- RISK HISTORY TABLE
            -- ═══════════════════════════════════════════════════════════

            CREATE TABLE IF NOT EXISTS risk_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id        TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                risk_score      REAL NOT NULL,
                workflow_risk   REAL NOT NULL,
                resource_risk   REAL NOT NULL,
                compliance_risk REAL NOT NULL,
                risk_state      TEXT NOT NULL,
                contributions   TEXT DEFAULT '[]'
            );

            -- ═══════════════════════════════════════════════════════════
            -- INSIGHTS TABLE
            -- ═══════════════════════════════════════════════════════════

            CREATE TABLE IF NOT EXISTS insights (
                insight_id  TEXT PRIMARY KEY,
                cycle_id    TEXT NOT NULL,
                summary     TEXT,
                severity    TEXT,
                confidence  REAL DEFAULT 0.0,
                timestamp   TEXT NOT NULL,
                why_it_matters              TEXT,
                what_will_happen_if_ignored TEXT,
                uncertainty TEXT,
                evidence_count INTEGER DEFAULT 0,
                actions     TEXT DEFAULT '[]'
            );

            -- ═══════════════════════════════════════════════════════════
            -- INDEXES
            -- ═══════════════════════════════════════════════════════════

            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
            CREATE INDEX IF NOT EXISTS idx_events_workflow ON events(workflow_id);
            CREATE INDEX IF NOT EXISTS idx_metrics_resource ON metrics(resource_id);
            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
            CREATE INDEX IF NOT EXISTS idx_metrics_resource_metric ON metrics(resource_id, metric);
            CREATE INDEX IF NOT EXISTS idx_anomalies_cycle ON anomalies(cycle_id);
            CREATE INDEX IF NOT EXISTS idx_anomalies_type ON anomalies(type);
            CREATE INDEX IF NOT EXISTS idx_policy_hits_cycle ON policy_hits(cycle_id);
            CREATE INDEX IF NOT EXISTS idx_risk_history_timestamp ON risk_history(timestamp);
            CREATE INDEX IF NOT EXISTS idx_insights_cycle ON insights(cycle_id);
        """)
        self._conn.commit()

    # ─────────────────────────────────────────────────────────────────────────
    # EVENTS
    # ─────────────────────────────────────────────────────────────────────────

    def insert_event(self, event_id: str, type: str, workflow_id: Optional[str],
                     actor: str, resource: Optional[str], timestamp: str,
                     metadata: Dict, observed_at: str):
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?,?)",
                (event_id, type, workflow_id, actor, resource, timestamp,
                 json.dumps(metadata), observed_at)
            )
            self._conn.commit()

    def get_recent_events(self, limit: int = 100) -> List[Dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_events_count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    # ─────────────────────────────────────────────────────────────────────────
    # METRICS
    # ─────────────────────────────────────────────────────────────────────────

    def insert_metric(self, resource_id: str, metric: str, value: float,
                      timestamp: str, observed_at: str):
        with self._lock:
            self._conn.execute(
                "INSERT INTO metrics (resource_id, metric, value, timestamp, observed_at) "
                "VALUES (?,?,?,?,?)",
                (resource_id, metric, value, timestamp, observed_at)
            )
            self._conn.commit()

    def get_recent_metrics(self, limit: int = 100) -> List[Dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM metrics ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_metrics_count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM metrics").fetchone()[0]

    # ─────────────────────────────────────────────────────────────────────────
    # CYCLES
    # ─────────────────────────────────────────────────────────────────────────

    def insert_cycle(self, cycle_id: str, started_at: str, completed_at: str,
                     anomaly_count: int, policy_hit_count: int,
                     risk_signal_count: int, causal_link_count: int,
                     recommendation_count: int):
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO cycles VALUES (?,?,?,?,?,?,?,?)",
                (cycle_id, started_at, completed_at, anomaly_count,
                 policy_hit_count, risk_signal_count, causal_link_count,
                 recommendation_count)
            )
            self._conn.commit()

    def get_cycles_count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM cycles").fetchone()[0]

    # ─────────────────────────────────────────────────────────────────────────
    # ANOMALIES
    # ─────────────────────────────────────────────────────────────────────────

    def insert_anomaly(self, anomaly_id: str, cycle_id: str, type: str,
                       agent: str, description: str, confidence: float,
                       timestamp: str, evidence: List[str]):
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO anomalies VALUES (?,?,?,?,?,?,?,?)",
                (anomaly_id, cycle_id, type, agent, description, confidence,
                 timestamp, json.dumps(evidence))
            )
            self._conn.commit()

    def get_anomalies_count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM anomalies").fetchone()[0]

    # ─────────────────────────────────────────────────────────────────────────
    # POLICY HITS
    # ─────────────────────────────────────────────────────────────────────────

    def insert_policy_hit(self, hit_id: str, cycle_id: str, policy_id: str,
                          event_id: str, violation_type: str, agent: str,
                          description: str, timestamp: str):
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO policy_hits VALUES (?,?,?,?,?,?,?,?)",
                (hit_id, cycle_id, policy_id, event_id, violation_type,
                 agent, description, timestamp)
            )
            self._conn.commit()

    def get_policy_hits_count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM policy_hits").fetchone()[0]

    # ─────────────────────────────────────────────────────────────────────────
    # RECOMMENDATIONS
    # ─────────────────────────────────────────────────────────────────────────

    def insert_recommendation(self, rec_id: str, cycle_id: str, cause: str,
                              action: str, urgency: str, rationale: str,
                              timestamp: str):
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO recommendations VALUES (?,?,?,?,?,?,?)",
                (rec_id, cycle_id, cause, action, urgency, rationale, timestamp)
            )
            self._conn.commit()

    # ─────────────────────────────────────────────────────────────────────────
    # RISK HISTORY
    # ─────────────────────────────────────────────────────────────────────────

    def insert_risk_point(self, cycle_id: str, timestamp: str,
                          risk_score: float, workflow_risk: float,
                          resource_risk: float, compliance_risk: float,
                          risk_state: str, contributions: List[Dict]):
        with self._lock:
            self._conn.execute(
                "INSERT INTO risk_history "
                "(cycle_id, timestamp, risk_score, workflow_risk, resource_risk, "
                "compliance_risk, risk_state, contributions) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (cycle_id, timestamp, risk_score, workflow_risk, resource_risk,
                 compliance_risk, risk_state, json.dumps(contributions))
            )
            self._conn.commit()

    def get_risk_history(self, limit: int = 100) -> List[Dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM risk_history ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["contributions"] = json.loads(d["contributions"])
                result.append(d)
            return list(reversed(result))  # oldest first for charts

    def get_risk_history_count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM risk_history").fetchone()[0]

    # ─────────────────────────────────────────────────────────────────────────
    # INSIGHTS
    # ─────────────────────────────────────────────────────────────────────────

    def insert_insight(self, insight_id: str, cycle_id: str, summary: str,
                       severity: str, confidence: float, timestamp: str,
                       why_it_matters: str, what_will_happen: str,
                       uncertainty: str, evidence_count: int,
                       actions: List[str]):
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO insights VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (insight_id, cycle_id, summary, severity, confidence, timestamp,
                 why_it_matters, what_will_happen, uncertainty, evidence_count,
                 json.dumps(actions))
            )
            self._conn.commit()

    def get_insights_count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM insights").fetchone()[0]

    # ─────────────────────────────────────────────────────────────────────────
    # STATS
    # ─────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get row counts for all tables."""
        with self._lock:
            stats = {}
            for table in ["events", "metrics", "cycles", "anomalies",
                          "policy_hits", "recommendations", "risk_history",
                          "insights"]:
                count = self._conn.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                stats[table] = count

            # DB file size
            db_file = Path(self._db_path)
            stats["db_size_bytes"] = db_file.stat().st_size if db_file.exists() else 0
            stats["db_size_mb"] = round(stats["db_size_bytes"] / (1024 * 1024), 2)

            return stats

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            logger.info("SQLite store closed")


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_instance: Optional[SQLiteStore] = None


def get_sqlite_store(db_path: Optional[str] = None) -> SQLiteStore:
    """Get the singleton SQLite store instance."""
    global _instance
    if _instance is None:
        from api.config import settings
        path = db_path or settings.SQLITE_DB_PATH
        _instance = SQLiteStore(path)
    return _instance
