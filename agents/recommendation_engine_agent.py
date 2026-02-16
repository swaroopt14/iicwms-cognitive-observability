"""
Deterministic Recommendation Engine
===================================
Maps anomalies/policy hits + severity context to structured actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from blackboard import (
    SharedState,
    Anomaly,
    PolicyHit,
    CausalLink,
    SeverityScore,
    RecommendationV2,
)


@dataclass(frozen=True)
class RecommendationRule:
    rule_id: str
    issue_type: str
    action_code: str
    action_description: str
    preconditions: List[str]
    expected_effect: str
    min_severity: float = 0.0
    max_severity: float = 10.0
    base_confidence: float = 0.7


class RecommendationEngineAgent:
    AGENT_NAME = "RecommendationEngineAgent"

    _RULES: List[RecommendationRule] = [
        RecommendationRule(
            rule_id="REC_RES_CPU_01",
            issue_type="SUSTAINED_RESOURCE_CRITICAL",
            action_code="THROTTLE_DEPLOYS",
            action_description="Throttle concurrent deploy jobs on the affected resource.",
            preconditions=["env=prod_or_staging", "asset_type=worker_or_api"],
            expected_effect="risk_score -15 to -25 in next 2 cycles",
            min_severity=7.0,
            base_confidence=0.82,
        ),
        RecommendationRule(
            rule_id="REC_RES_WARN_01",
            issue_type="SUSTAINED_RESOURCE_WARNING",
            action_code="SCALE_OUT",
            action_description="Scale out replicas or increase resource limits before saturation.",
            preconditions=["autoscaling_or_capacity_available"],
            expected_effect="risk_score -8 to -15",
            min_severity=5.0,
            base_confidence=0.72,
        ),
        RecommendationRule(
            rule_id="REC_WF_DELAY_01",
            issue_type="WORKFLOW_DELAY",
            action_code="DECREASE_CONCURRENCY",
            action_description="Reduce workflow concurrency and re-run delayed steps with tracing.",
            preconditions=["workflow_in_progress=true"],
            expected_effect="SLA breach probability -20%",
            min_severity=6.0,
            base_confidence=0.78,
        ),
        RecommendationRule(
            rule_id="REC_WF_MISS_01",
            issue_type="MISSING_STEP",
            action_code="BLOCK_AND_REVIEW",
            action_description="Block promotion and enforce mandatory approval/review step.",
            preconditions=["approval_step_required=true"],
            expected_effect="compliance breach probability -40%",
            min_severity=7.0,
            base_confidence=0.9,
        ),
        RecommendationRule(
            rule_id="REC_COMP_01",
            issue_type="POLICY_NO_AFTER_HOURS_WRITE",
            action_code="RESTRICT_AFTER_HOURS_ACCESS",
            action_description="Restrict write access after policy cutoff and require break-glass approval.",
            preconditions=["policy=NO_AFTER_HOURS_WRITE"],
            expected_effect="after-hours violations near zero",
            min_severity=6.0,
            base_confidence=0.88,
        ),
        RecommendationRule(
            rule_id="REC_COMP_02",
            issue_type="POLICY_NO_SKIP_APPROVAL",
            action_code="ENFORCE_APPROVAL_GATE",
            action_description="Enforce approval gate in CI/CD and reject skipped approvals.",
            preconditions=["pipeline_has_approval_stage=true"],
            expected_effect="silent approval bypass reduced",
            min_severity=7.0,
            base_confidence=0.92,
        ),
        RecommendationRule(
            rule_id="REC_CODE_01",
            issue_type="LOW_TEST_COVERAGE",
            action_code="ADD_TESTS_BEFORE_DEPLOY",
            action_description="Add targeted unit/integration tests before merge/deploy.",
            preconditions=["coverage_below_threshold=true"],
            expected_effect="deploy failure probability -15 to -25%",
            min_severity=5.0,
            base_confidence=0.8,
        ),
        RecommendationRule(
            rule_id="REC_CODE_02",
            issue_type="HIGH_CHURN_PR",
            action_code="SPLIT_PR_AND_REVIEW",
            action_description="Split high-churn PR and require staged review.",
            preconditions=["changed_lines_high=true"],
            expected_effect="review quality improvement; rollback probability reduced",
            min_severity=5.0,
            base_confidence=0.76,
        ),
    ]
    _RULES_BY_ISSUE: Dict[str, List[RecommendationRule]] = {}

    def __init__(self):
        # Cache issue-type -> rules mapping once for faster lookups on each cycle.
        if not self._RULES_BY_ISSUE:
            by_issue: Dict[str, List[RecommendationRule]] = {}
            for rule in self._RULES:
                by_issue.setdefault(rule.issue_type, []).append(rule)
            self.__class__._RULES_BY_ISSUE = by_issue

    def generate(
        self,
        anomalies: List[Anomaly],
        policy_hits: List[PolicyHit],
        causal_links: List[CausalLink],
        severity_scores: List[SeverityScore],
        state: SharedState,
    ) -> List[RecommendationV2]:
        by_source: Dict[str, SeverityScore] = {
            s.source_id: s for s in severity_scores
        }
        outputs: List[RecommendationV2] = []
        seen = set()

        # Build a weak causal map for rationale boost.
        causal_by_cause = {c.cause: c for c in causal_links}

        for anomaly in anomalies:
            sev = by_source.get(anomaly.anomaly_id)
            if not sev:
                continue
            rules = self._rules_for_issue(anomaly.type)
            for rule in rules:
                if not (rule.min_severity <= sev.final_score <= rule.max_severity):
                    continue
                key = (rule.rule_id, anomaly.type, anomaly.evidence[0] if anomaly.evidence else anomaly.anomaly_id)
                if key in seen:
                    continue
                seen.add(key)

                c_sev = max(0.0, min(1.0, sev.final_score / 10.0))
                c_ctx = 1.0 if sev.context_factors else 0.7
                conf = round(0.5 * rule.base_confidence + 0.2 * c_sev + 0.3 * c_ctx, 3)

                causal_hint = ""
                if anomaly.type in causal_by_cause:
                    link = causal_by_cause[anomaly.type]
                    causal_hint = f" Linked effect: {link.effect} (conf {link.confidence:.2f})."

                rec = state.add_recommendation_v2(
                    issue_type=anomaly.type,
                    entity=self._entity_from_anomaly(anomaly),
                    severity_score=sev.final_score,
                    action_code=rule.action_code,
                    action_description=rule.action_description,
                    confidence=conf,
                    preconditions=rule.preconditions,
                    evidence_ids=list(anomaly.evidence),
                    expected_effect=rule.expected_effect,
                    rationale=f"{anomaly.description}.{causal_hint}".strip(),
                    rule_id=rule.rule_id,
                )
                outputs.append(rec)

        for hit in policy_hits:
            issue_type = f"POLICY_{hit.policy_id}"
            sev = by_source.get(hit.hit_id)
            if not sev:
                continue
            rules = self._rules_for_issue(issue_type)
            for rule in rules:
                if not (rule.min_severity <= sev.final_score <= rule.max_severity):
                    continue
                key = (rule.rule_id, issue_type, hit.event_id)
                if key in seen:
                    continue
                seen.add(key)

                c_sev = max(0.0, min(1.0, sev.final_score / 10.0))
                conf = round(0.5 * rule.base_confidence + 0.2 * c_sev + 0.3 * 1.0, 3)
                rec = state.add_recommendation_v2(
                    issue_type=issue_type,
                    entity=hit.event_id,
                    severity_score=sev.final_score,
                    action_code=rule.action_code,
                    action_description=rule.action_description,
                    confidence=conf,
                    preconditions=rule.preconditions,
                    evidence_ids=[hit.event_id],
                    expected_effect=rule.expected_effect,
                    rationale=hit.description,
                    rule_id=rule.rule_id,
                )
                outputs.append(rec)

        outputs.sort(key=lambda r: (r.severity_score, r.confidence), reverse=True)
        return outputs

    def _rules_for_issue(self, issue_type: str) -> List[RecommendationRule]:
        return self._RULES_BY_ISSUE.get(issue_type, [])

    def _entity_from_anomaly(self, anomaly: Anomaly) -> str:
        if anomaly.evidence:
            ev = anomaly.evidence[0]
            if "/" in ev:
                return ev.split("/")[0]
            return ev
        return anomaly.anomaly_id
