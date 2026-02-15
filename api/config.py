"""
IICWMS Production Configuration
================================
Environment-based configuration with sensible defaults.
All settings are read from environment variables at startup.

Usage:
    from api.config import settings
    print(settings.API_PORT)
"""

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

# Load .env BEFORE reading os.getenv
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Immutable application settings — loaded once at startup."""

    # ── Server ──────────────────────────────────────────────────
    APP_NAME: str = "Chronos AI — IICWMS Cognitive Observability"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = ""  # Set to "/api/v1" for versioned routing

    # ── Reasoning Loop ──────────────────────────────────────────
    CYCLE_INTERVAL_SECONDS: float = 5.0
    MAX_INSIGHTS_BUFFER: int = 100
    MAX_CYCLE_HISTORY: int = 200

    # ── CORS ────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = field(default_factory=lambda: ["*"])
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: List[str] = field(default_factory=lambda: ["*"])

    # ── Security ────────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 100  # per minute per IP
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ── LLM (Optional) ─────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    ENABLE_CREWAI: bool = False

    # ── SQLite (Operational Store) ──────────────────────────────
    SQLITE_DB_PATH: str = "data/chronos.db"

    # ── Neo4j Aura (Knowledge Graph — Optional) ────────────────
    ENABLE_NEO4J: bool = False
    NEO4J_URI: str = ""
    NEO4J_USERNAME: str = ""
    NEO4J_PASSWORD: str = ""

    # ── Logging ─────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "structured"  # "structured" or "simple"

    # ── Slack Alerts (Optional) ─────────────────────────────────
    ENABLE_SLACK_ALERTS: bool = False
    SLACK_WEBHOOK_URL: str = ""
    SLACK_ALERT_MIN_SEVERITY: str = "HIGH"      # LOW|MEDIUM|HIGH|CRITICAL
    SLACK_ALERT_MIN_RISK_STATE: str = "VIOLATION"  # AT_RISK|VIOLATION|INCIDENT
    SLACK_ALERT_COOLDOWN_SECONDS: int = 120
    FRONTEND_BASE_URL: str = "http://localhost:3000"


def load_settings() -> Settings:
    """Load settings from environment variables with defaults."""
    cors_origins_raw = os.getenv("CORS_ORIGINS", "*")
    cors_origins = [o.strip() for o in cors_origins_raw.split(",")]

    return Settings(
        APP_NAME=os.getenv("APP_NAME", Settings.APP_NAME),
        APP_VERSION=os.getenv("APP_VERSION", Settings.APP_VERSION),
        ENVIRONMENT=os.getenv("ENVIRONMENT", Settings.ENVIRONMENT),
        DEBUG=os.getenv("DEBUG", "false").lower() == "true",
        API_HOST=os.getenv("API_HOST", Settings.API_HOST),
        API_PORT=int(os.getenv("API_PORT", str(Settings.API_PORT))),
        API_PREFIX=os.getenv("API_PREFIX", Settings.API_PREFIX),
        CYCLE_INTERVAL_SECONDS=float(os.getenv("CYCLE_INTERVAL_SECONDS", str(Settings.CYCLE_INTERVAL_SECONDS))),
        MAX_INSIGHTS_BUFFER=int(os.getenv("MAX_INSIGHTS_BUFFER", str(Settings.MAX_INSIGHTS_BUFFER))),
        MAX_CYCLE_HISTORY=int(os.getenv("MAX_CYCLE_HISTORY", str(Settings.MAX_CYCLE_HISTORY))),
        CORS_ORIGINS=cors_origins,
        CORS_ALLOW_CREDENTIALS=os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
        RATE_LIMIT_REQUESTS=int(os.getenv("RATE_LIMIT_REQUESTS", str(Settings.RATE_LIMIT_REQUESTS))),
        RATE_LIMIT_WINDOW_SECONDS=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", str(Settings.RATE_LIMIT_WINDOW_SECONDS))),
        GEMINI_API_KEY=os.getenv("GEMINI_API_KEY", ""),
        ENABLE_CREWAI=os.getenv("ENABLE_CREWAI", "false").lower() == "true",
        SQLITE_DB_PATH=os.getenv("SQLITE_DB_PATH", Settings.SQLITE_DB_PATH),
        ENABLE_NEO4J=os.getenv("ENABLE_NEO4J", "false").lower() == "true",
        NEO4J_URI=os.getenv("NEO4J_URI", ""),
        NEO4J_USERNAME=os.getenv("NEO4J_USERNAME", ""),
        NEO4J_PASSWORD=os.getenv("NEO4J_PASSWORD", ""),
        LOG_LEVEL=os.getenv("LOG_LEVEL", Settings.LOG_LEVEL),
        LOG_FORMAT=os.getenv("LOG_FORMAT", Settings.LOG_FORMAT),
        ENABLE_SLACK_ALERTS=os.getenv("ENABLE_SLACK_ALERTS", "false").lower() == "true",
        SLACK_WEBHOOK_URL=os.getenv("SLACK_WEBHOOK_URL", ""),
        SLACK_ALERT_MIN_SEVERITY=os.getenv("SLACK_ALERT_MIN_SEVERITY", Settings.SLACK_ALERT_MIN_SEVERITY),
        SLACK_ALERT_MIN_RISK_STATE=os.getenv("SLACK_ALERT_MIN_RISK_STATE", Settings.SLACK_ALERT_MIN_RISK_STATE),
        SLACK_ALERT_COOLDOWN_SECONDS=int(
            os.getenv("SLACK_ALERT_COOLDOWN_SECONDS", str(Settings.SLACK_ALERT_COOLDOWN_SECONDS))
        ),
        FRONTEND_BASE_URL=os.getenv("FRONTEND_BASE_URL", Settings.FRONTEND_BASE_URL),
    )


# Singleton — loaded once
settings = load_settings()
