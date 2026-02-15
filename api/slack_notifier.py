"""
Chronos Slack Notifier
======================
Posts high-priority incident alerts to Slack via Incoming Webhook.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from blackboard import ReasoningCycle, RiskState
from explanation import Insight


_SEVERITY_RANK = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}

_RISK_RANK = {
    RiskState.NORMAL.value: 0,
    RiskState.DEGRADED.value: 1,
    RiskState.AT_RISK.value: 2,
    RiskState.VIOLATION.value: 3,
    RiskState.INCIDENT.value: 4,
}


@dataclass
class SlackConfig:
    enabled: bool
    webhook_url: str
    min_severity: str
    min_risk_state: str
    cooldown_seconds: int
    frontend_base_url: str


class SlackNotifier:
    """
    Stateless-by-default notifier with small in-memory cooldown cache.
    """

    def __init__(self, cfg: SlackConfig):
        self._cfg = cfg
        self._last_sent_at: Optional[datetime] = None
        self._last_cycle_id: Optional[str] = None

    @property
    def enabled(self) -> bool:
        return self._cfg.enabled and bool(self._cfg.webhook_url)

    def should_alert(
        self,
        cycle: ReasoningCycle,
        insight: Optional[Insight] = None,
        risk_state: Optional[str] = None,
    ) -> bool:
        if not self.enabled:
            return False
        if self._last_cycle_id == cycle.cycle_id:
            return False

        # Cooldown guard
        if self._last_sent_at is not None:
            age = (datetime.now(timezone.utc) - self._last_sent_at).total_seconds()
            if age < max(0, self._cfg.cooldown_seconds):
                return False

        severity_ok = False
        risk_ok = False

        if insight and insight.severity:
            severity_ok = _SEVERITY_RANK.get(insight.severity.upper(), 0) >= _SEVERITY_RANK.get(
                self._cfg.min_severity.upper(), 2
            )

        if risk_state:
            risk_ok = _RISK_RANK.get(risk_state.upper(), 0) >= _RISK_RANK.get(
                self._cfg.min_risk_state.upper(), 3
            )
        else:
            # Derive risk from cycle signals if explicit state not passed
            max_risk = "NORMAL"
            for signal in cycle.risk_signals:
                if _RISK_RANK.get(signal.projected_state.value, 0) > _RISK_RANK.get(max_risk, 0):
                    max_risk = signal.projected_state.value
            risk_ok = _RISK_RANK.get(max_risk, 0) >= _RISK_RANK.get(self._cfg.min_risk_state.upper(), 3)

        # Alert if either severity or risk threshold is crossed
        return severity_ok or risk_ok

    async def send_cycle_alert(
        self,
        cycle: ReasoningCycle,
        insight: Optional[Insight] = None,
        risk_score: Optional[float] = None,
        risk_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {"sent": False, "reason": "disabled"}

        if not self.should_alert(cycle, insight=insight, risk_state=risk_state):
            return {"sent": False, "reason": "threshold_not_met_or_cooldown"}

        summary = (insight.summary if insight else "High-priority cycle detected") or "High-priority cycle detected"
        severity = (insight.severity if insight else "HIGH") or "HIGH"
        confidence = round((insight.confidence if insight else 0.8) * 100, 1)
        rec = cycle.recommendations[0].action if cycle.recommendations else "Review incident details in Chronos"
        incident_url = f"{self._cfg.frontend_base_url.rstrip('/')}/audit"

        text = (
            f"🚨 *Chronos Alert* | Cycle `{cycle.cycle_id}`\n"
            f"*Severity:* {severity} | *Risk:* {risk_state or 'N/A'}"
            + (f" ({risk_score})" if risk_score is not None else "")
            + f" | *Confidence:* {confidence}%\n"
            f"*Summary:* {summary}\n"
            f"*Recommended Action:* {rec}\n"
            f"*Evidence:* anomalies={len(cycle.anomalies)}, policy_hits={len(cycle.policy_hits)}, causal_links={len(cycle.causal_links)}\n"
            f"<{incident_url}|Open Audit Investigation>"
        )

        payload = {
            "text": text,
        }

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(self._cfg.webhook_url, json=payload)
            resp.raise_for_status()

        self._last_sent_at = datetime.now(timezone.utc)
        self._last_cycle_id = cycle.cycle_id
        return {"sent": True, "cycle_id": cycle.cycle_id}

    async def send_test(self, message: str) -> Dict[str, Any]:
        if not self.enabled:
            return {"sent": False, "reason": "disabled"}
        payload = {"text": f"🧪 Chronos Slack test: {message}"}
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(self._cfg.webhook_url, json=payload)
            resp.raise_for_status()
        return {"sent": True}
