"""
IICWMS Explanation Engine
=========================
EXPLAIN - Human output generation.

PURPOSE:
Translate reasoning artifacts into human insight.

INPUT:
- Causal links
- Risk state
- Policy violations

OUTPUT (LLM ALLOWED):
{
  "summary": "...",
  "why_it_matters": "...",
  "what_will_happen_if_ignored": "...",
  "recommended_actions": [...],
  "confidence": 0.72,
  "uncertainty": "Simulated environment"
}

LLMs are used ONLY for explanation wording, NEVER for detection.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import os
import logging

from blackboard import (
    ReasoningCycle, Anomaly, PolicyHit, RiskSignal,
    CausalLink, Recommendation, RiskState
)

logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """
    A human-readable insight.
    
    This is the final output of the system.
    """
    insight_id: str
    summary: str
    why_it_matters: str
    what_will_happen_if_ignored: str
    recommended_actions: List[str]
    confidence: float
    uncertainty: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    timestamp: datetime
    evidence_count: int
    cycle_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


class ExplanationEngine:
    """
    Explanation Engine
    
    Translates reasoning artifacts into human insight.
    
    LLM USAGE RULES:
    - LLMs may ONLY be used for natural-language explanation
    - LLMs may ONLY be used for executive summary generation
    - LLMs do NOT detect anomalies
    - LLMs do NOT enforce policies
    - LLMs do NOT modify system state
    
    This ensures DETERMINISTIC system behavior.
    """
    
    def __init__(self, use_llm: bool = False):
        """
        Initialize engine.
        
        Args:
            use_llm: Whether to use LLM for explanation (default: False for determinism)
        """
        self._use_llm = use_llm
        self._llm_client = None
        self._crewai_crew = None
        
        if use_llm:
            self._init_llm()
        
        # Initialize CrewAI if enabled via env flag
        self._init_crewai()
    
    def _init_crewai(self):
        """Initialize CrewAI explanation crew if ENABLE_CREWAI=true."""
        enable_crewai = os.getenv("ENABLE_CREWAI", "false").lower().strip()
        if enable_crewai != "true":
            return
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("ENABLE_CREWAI=true but GEMINI_API_KEY not set; skipping CrewAI init")
            return
        
        try:
            from explanation.crew import ExplanationCrew
            self._crewai_crew = ExplanationCrew()
            logger.info("CrewAI ExplanationCrew loaded successfully")
        except ImportError as e:
            logger.warning("CrewAI not installed, falling back to templates: %s", e)
        except Exception as e:
            logger.warning("CrewAI init failed, falling back to templates: %s", e)
    
    def _init_llm(self):
        """Initialize LLM client if API key available."""
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self._llm_client = genai.GenerativeModel("gemini-1.5-flash")
            except ImportError:
                self._llm_client = None
    
    def generate_insight(self, cycle: ReasoningCycle) -> Optional[Insight]:
        """
        Generate human insight from a reasoning cycle.
        
        Only generates insight if there's something meaningful to report.
        """
        # Determine if there's anything to report
        if not (cycle.anomalies or cycle.policy_hits or cycle.risk_signals):
            return None
        
        # Calculate severity
        severity = self._calculate_severity(cycle)
        
        # Calculate confidence
        confidence = self._calculate_confidence(cycle)
        
        # Generate explanation: CrewAI > LLM > Template
        crewai_actions = None
        if self._crewai_crew:
            crewai_result = self._generate_crewai_explanation(cycle, severity)
            if crewai_result:
                explanation = {
                    "summary": crewai_result["summary"],
                    "why_it_matters": crewai_result["why_it_matters"],
                    "what_will_happen_if_ignored": crewai_result["what_will_happen_if_ignored"],
                }
                crewai_actions = crewai_result.get("recommended_actions")
            else:
                explanation = self._generate_template_explanation(cycle, severity)
        elif self._use_llm and self._llm_client:
            explanation = self._generate_llm_explanation(cycle, severity)
        else:
            explanation = self._generate_template_explanation(cycle, severity)
        
        # Gather recommended actions (CrewAI actions override if available)
        actions = crewai_actions if crewai_actions else [r.action for r in cycle.recommendations]
        
        return Insight(
            insight_id=f"insight_{cycle.cycle_id}",
            summary=explanation["summary"],
            why_it_matters=explanation["why_it_matters"],
            what_will_happen_if_ignored=explanation["what_will_happen_if_ignored"],
            recommended_actions=actions,
            confidence=confidence,
            uncertainty="Analysis based on simulated environment",
            severity=severity,
            timestamp=cycle.completed_at or datetime.utcnow(),
            evidence_count=len(cycle.anomalies) + len(cycle.policy_hits),
            cycle_id=cycle.cycle_id
        )
    
    def _calculate_severity(self, cycle: ReasoningCycle) -> str:
        """Calculate overall severity from cycle."""
        # Check for critical indicators
        has_critical_policy = any(
            "CRITICAL" in hit.policy_id or "SKIP_APPROVAL" in hit.policy_id
            for hit in cycle.policy_hits
        )
        
        has_incident_risk = any(
            signal.projected_state in (RiskState.VIOLATION, RiskState.INCIDENT)
            for signal in cycle.risk_signals
        )
        
        has_critical_resource = any(
            a.type == "SUSTAINED_RESOURCE_CRITICAL"
            for a in cycle.anomalies
        )
        
        if has_critical_policy or has_incident_risk or has_critical_resource:
            return "CRITICAL"
        
        # Check for high indicators
        has_missing_step = any(a.type == "MISSING_STEP" for a in cycle.anomalies)
        has_at_risk = any(
            signal.projected_state == RiskState.AT_RISK
            for signal in cycle.risk_signals
        )
        
        if has_missing_step or has_at_risk or len(cycle.policy_hits) > 2:
            return "HIGH"
        
        # Check for medium indicators
        if cycle.anomalies or cycle.policy_hits:
            return "MEDIUM"
        
        return "LOW"
    
    def _calculate_confidence(self, cycle: ReasoningCycle) -> float:
        """Calculate overall confidence from cycle."""
        confidences = []
        
        for a in cycle.anomalies:
            confidences.append(a.confidence)
        
        for s in cycle.risk_signals:
            confidences.append(s.confidence)
        
        for c in cycle.causal_links:
            confidences.append(c.confidence)
        
        if not confidences:
            return 0.5
        
        # Use average, weighted slightly toward higher values
        avg = sum(confidences) / len(confidences)
        max_conf = max(confidences)
        return (avg * 0.7) + (max_conf * 0.3)
    
    def _generate_crewai_explanation(
        self,
        cycle: ReasoningCycle,
        severity: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate explanation using CrewAI crew.
        
        Falls back to None on any error (caller uses template fallback).
        """
        if not self._crewai_crew:
            return None
        
        try:
            result = self._crewai_crew.generate(
                severity=severity,
                anomalies=[a.description for a in cycle.anomalies],
                policy_violations=[h.description for h in cycle.policy_hits],
                risk_signals=[s.reasoning for s in cycle.risk_signals],
                causal_links=[
                    f"{c.cause} -> {c.effect}: {c.reasoning}"
                    for c in cycle.causal_links
                ],
                recommendations=[r.action for r in cycle.recommendations],
            )
            
            if result and result.get("summary"):
                logger.info("CrewAI explanation generated successfully")
                return result
            
            logger.warning("CrewAI returned empty result, falling back to template")
            return None
            
        except Exception as e:
            logger.warning("CrewAI explanation failed: %s — falling back to template", e)
            return None
    
    def _generate_template_explanation(
        self,
        cycle: ReasoningCycle,
        severity: str
    ) -> Dict[str, str]:
        """Generate explanation using templates (deterministic)."""
        
        # Build summary
        summary_parts = []
        
        if cycle.anomalies:
            anomaly_types = set(a.type for a in cycle.anomalies)
            summary_parts.append(f"{len(cycle.anomalies)} anomalies detected ({', '.join(anomaly_types)})")
        
        if cycle.policy_hits:
            policy_ids = set(h.policy_id for h in cycle.policy_hits)
            summary_parts.append(f"{len(cycle.policy_hits)} policy violations ({', '.join(policy_ids)})")
        
        if cycle.risk_signals:
            risk_entities = [s.entity for s in cycle.risk_signals]
            summary_parts.append(f"Risk escalation detected for: {', '.join(risk_entities[:3])}")
        
        summary = ". ".join(summary_parts) if summary_parts else "System operating normally"
        
        # Build why it matters
        why_parts = []
        
        for link in cycle.causal_links:
            why_parts.append(link.reasoning)
        
        if not why_parts:
            if cycle.policy_hits:
                why_parts.append("Policy violations indicate compliance risk exposure")
            if cycle.anomalies:
                why_parts.append("Anomalies suggest operational degradation")
        
        why_it_matters = ". ".join(why_parts[:3]) if why_parts else "Monitoring continues normally"
        
        # Build consequences
        consequences = []
        
        for signal in cycle.risk_signals:
            if signal.projected_state in (RiskState.VIOLATION, RiskState.INCIDENT):
                consequences.append(
                    f"{signal.entity} projected to reach {signal.projected_state.value} within {signal.time_horizon}"
                )
        
        if not consequences:
            if severity == "CRITICAL":
                consequences.append("Immediate intervention required to prevent system degradation")
            elif severity == "HIGH":
                consequences.append("Without action, risk will escalate to critical levels")
            else:
                consequences.append("Continued monitoring recommended")
        
        what_if_ignored = ". ".join(consequences[:2])
        
        return {
            "summary": summary,
            "why_it_matters": why_it_matters,
            "what_will_happen_if_ignored": what_if_ignored
        }
    
    def _generate_llm_explanation(
        self,
        cycle: ReasoningCycle,
        severity: str
    ) -> Dict[str, str]:
        """Generate explanation using LLM (for natural language polish)."""
        
        # First get template explanation as base
        template = self._generate_template_explanation(cycle, severity)
        
        if not self._llm_client:
            return template
        
        # Prepare context for LLM
        context = {
            "anomalies": [a.description for a in cycle.anomalies],
            "policy_violations": [h.description for h in cycle.policy_hits],
            "risk_signals": [s.reasoning for s in cycle.risk_signals],
            "causal_links": [
                f"{c.cause} → {c.effect}: {c.reasoning}"
                for c in cycle.causal_links
            ],
            "recommendations": [r.action for r in cycle.recommendations],
            "severity": severity
        }
        
        prompt = f"""You are an IT operations analyst explaining system findings to an executive.

CONTEXT:
- Anomalies: {context['anomalies']}
- Policy Violations: {context['policy_violations']}
- Risk Signals: {context['risk_signals']}
- Causal Analysis: {context['causal_links']}
- Severity: {context['severity']}

Generate a professional, concise explanation with:
1. summary: One-sentence overview (max 30 words)
2. why_it_matters: Business impact explanation (max 50 words)
3. what_will_happen_if_ignored: Consequences (max 40 words)

Respond in JSON format with these three keys.
Be factual, not alarmist. Use professional IT operations language."""

        try:
            import json
            response = self._llm_client.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 300,
                    "response_mime_type": "application/json",
                }
            )
            
            result = json.loads(response.text)
            return {
                "summary": result.get("summary", template["summary"]),
                "why_it_matters": result.get("why_it_matters", template["why_it_matters"]),
                "what_will_happen_if_ignored": result.get(
                    "what_will_happen_if_ignored",
                    template["what_will_happen_if_ignored"]
                )
            }
        except Exception:
            # Fall back to template
            return template
    
    def generate_executive_summary(self, cycles: List[ReasoningCycle]) -> str:
        """
        Generate executive summary from multiple cycles.
        
        Used for dashboard overview.
        """
        if not cycles:
            return "System operating normally. No significant findings."
        
        total_anomalies = sum(len(c.anomalies) for c in cycles)
        total_violations = sum(len(c.policy_hits) for c in cycles)
        total_risks = sum(len(c.risk_signals) for c in cycles)
        
        if total_anomalies + total_violations + total_risks == 0:
            return "System operating normally. No significant findings."
        
        parts = []
        
        if total_anomalies > 0:
            parts.append(f"{total_anomalies} anomalies")
        
        if total_violations > 0:
            parts.append(f"{total_violations} policy violations")
        
        if total_risks > 0:
            parts.append(f"{total_risks} risk escalations")
        
        return f"Recent analysis: {', '.join(parts)} detected. See insights for details."
