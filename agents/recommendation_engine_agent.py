"""
Deterministic Recommendation Engine
===================================
Maps anomalies/policy hits + severity context to structured actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    step_templates: List[str] = field(default_factory=list)


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
            step_templates=[
                "Step 1: Freeze non-critical deploy jobs on the affected node/service for 10 minutes.",
                "Step 2: Cap deploy/workflow concurrency to a safe threshold and cap retries.",
                "Step 3: Drain or reroute hot traffic from the saturated resource.",
                "Step 4: Re-check CPU/memory/latency trend after 2 cycles before unfreezing changes.",
            ],
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
            step_templates=[
                "Step 1: Increase replica count or capacity headroom on the impacted service.",
                "Step 2: Tighten retry/backoff policy to prevent amplification while scaling stabilizes.",
                "Step 3: Validate p95 latency and queue depth are returning to baseline.",
            ],
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
            step_templates=[
                "Step 1: Pause low-priority workflow runs and prioritize critical workflows only.",
                "Step 2: Re-run delayed step with distributed tracing enabled for bottleneck evidence.",
                "Step 3: Adjust timeout/backoff values to avoid repeated step failures.",
                "Step 4: Confirm SLA burn rate declines before restoring normal concurrency.",
            ],
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
            step_templates=[
                "Step 1: Stop current promotion and mark pipeline as non-compliant.",
                "Step 2: Reinsert missing approval step and require explicit reviewer sign-off.",
                "Step 3: Re-run pipeline from the last compliant checkpoint.",
                "Step 4: Store audit evidence IDs for reviewer decision and rerun outcome.",
            ],
        ),
        RecommendationRule(
            rule_id="REC_WF_SEQ_01",
            issue_type="SEQUENCE_VIOLATION",
            action_code="FIX_STEP_ORDER",
            action_description="Restore workflow step order and replay from last valid step.",
            preconditions=["workflow_definition_available=true"],
            expected_effect="workflow consistency restored; downstream failures reduced",
            min_severity=5.5,
            base_confidence=0.8,
            step_templates=[
                "Step 1: Compare observed step order with workflow definition to locate divergence.",
                "Step 2: Roll back to last valid step and replay remaining steps in canonical order.",
                "Step 3: Add guard in orchestrator to reject future out-of-order transitions.",
            ],
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
            step_templates=[
                "Step 1: Revoke direct after-hours write permissions for affected actor/team.",
                "Step 2: Enable break-glass approval workflow with mandatory justification.",
                "Step 3: Re-audit recent after-hours writes and open follow-up tasks for exceptions.",
            ],
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
            step_templates=[
                "Step 1: Configure CI/CD gate to fail hard on missing approval token.",
                "Step 2: Lock merge/deploy rights until compliant approval is captured.",
                "Step 3: Re-run failed deployment through the approved path and preserve audit logs.",
            ],
        ),
        RecommendationRule(
            rule_id="REC_COMP_03",
            issue_type="POLICY_NO_UNUSUAL_LOCATION",
            action_code="BLOCK_UNTRUSTED_LOCATION",
            action_description="Block access from untrusted locations and force re-authentication.",
            preconditions=["policy=NO_UNUSUAL_LOCATION"],
            expected_effect="unauthorized access risk reduced",
            min_severity=6.0,
            base_confidence=0.86,
            step_templates=[
                "Step 1: Block source IP/location and invalidate active sessions.",
                "Step 2: Require MFA re-authentication for all affected users.",
                "Step 3: Review access logs for lateral movement before reopening access.",
            ],
        ),
        RecommendationRule(
            rule_id="REC_COMP_04",
            issue_type="POLICY_NO_UNCONTROLLED_SENSITIVE_ACCESS",
            action_code="ENFORCE_SENSITIVE_WORKFLOW",
            action_description="Force sensitive-resource access only through approved workflows.",
            preconditions=["policy=NO_UNCONTROLLED_SENSITIVE_ACCESS"],
            expected_effect="sensitive access becomes auditable",
            min_severity=6.5,
            base_confidence=0.9,
            step_templates=[
                "Step 1: Disable direct access path to sensitive resource.",
                "Step 2: Route all operations through tracked workflow with owner approval.",
                "Step 3: Validate audit trail contains actor, reason, and workflow ID.",
            ],
        ),
        RecommendationRule(
            rule_id="REC_COMP_05",
            issue_type="POLICY_NO_SVC_ACCOUNT_WRITE",
            action_code="DISABLE_SVC_DIRECT_WRITE",
            action_description="Disable service-account direct writes and enforce delegated workflow.",
            preconditions=["policy=NO_SVC_ACCOUNT_WRITE"],
            expected_effect="service-account misuse risk reduced",
            min_severity=6.0,
            base_confidence=0.85,
            step_templates=[
                "Step 1: Remove direct write grants from service account.",
                "Step 2: Move write operation behind approved service workflow.",
                "Step 3: Add monitoring alert for any future direct write attempt.",
            ],
        ),
        RecommendationRule(
            rule_id="REC_BASE_01",
            issue_type="BASELINE_DEVIATION",
            action_code="BASELINE_REVALIDATE",
            action_description="Validate anomaly against baseline window and isolate sustained drift.",
            preconditions=["baseline_available=true"],
            expected_effect="false positives reduced; true drift isolated",
            min_severity=5.0,
            base_confidence=0.74,
            step_templates=[
                "Step 1: Compare current metric window vs 24h baseline and weekly baseline.",
                "Step 2: Isolate whether deviation is sustained or transient burst.",
                "Step 3: If sustained, apply targeted mitigation on the deviating component.",
            ],
        ),
        RecommendationRule(
            rule_id="REC_RES_DRIFT_01",
            issue_type="RESOURCE_DRIFT",
            action_code="PIN_RESOURCE_CONFIG",
            action_description="Pin resource config/version and roll back recent drift-inducing changes.",
            preconditions=["recent_change_detected=true"],
            expected_effect="resource behavior returns to stable baseline",
            min_severity=5.0,
            base_confidence=0.76,
            step_templates=[
                "Step 1: Identify latest config/image/dependency changes on affected resource.",
                "Step 2: Roll back one change at a time and measure impact deltas.",
                "Step 3: Pin stable config and open RCA task for drift source.",
            ],
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
            step_templates=[
                "Step 1: Add tests on changed hotspots and critical error paths.",
                "Step 2: Raise minimum coverage gate for modified files/modules.",
                "Step 3: Re-run CI and block deploy until coverage threshold is met.",
            ],
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
            step_templates=[
                "Step 1: Split PR into smaller logical units with independent tests.",
                "Step 2: Require domain-owner review for risky modules.",
                "Step 3: Deploy behind feature flag and monitor rollback indicators.",
            ],
        ),
        RecommendationRule(
            rule_id="REC_CODE_03",
            issue_type="HIGH_COMPLEXITY_HINT",
            action_code="REDUCE_COMPLEXITY_BEFORE_RELEASE",
            action_description="Refactor complex code path and add guard tests before release.",
            preconditions=["complexity_above_threshold=true"],
            expected_effect="runtime error probability reduced",
            min_severity=5.0,
            base_confidence=0.75,
            step_templates=[
                "Step 1: Refactor high-complexity block into smaller deterministic functions.",
                "Step 2: Add boundary and timeout tests for worst-case paths.",
                "Step 3: Re-run static analysis and verify complexity score drops.",
            ],
        ),
        RecommendationRule(
            rule_id="REC_CODE_04",
            issue_type="HOTSPOT_FILE_CHANGE",
            action_code="ENABLE_HOTSPOT_GUARDS",
            action_description="Enable hotspot protections for frequently changed files.",
            preconditions=["hotspot_file=true"],
            expected_effect="reduces repeat regressions on unstable files",
            min_severity=5.0,
            base_confidence=0.74,
            step_templates=[
                "Step 1: Require additional reviewer for hotspot file changes.",
                "Step 2: Add focused regression suite for hotspot modules.",
                "Step 3: Enforce canary rollout for changes touching hotspot files.",
            ],
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
                outputs.extend(
                    self._emit_stepwise_recommendations(
                        state=state,
                        issue_type=anomaly.type,
                        entity=self._entity_from_anomaly(anomaly),
                        severity_score=sev.final_score,
                        confidence=conf,
                        evidence_ids=list(anomaly.evidence),
                        rule=rule,
                        rationale=anomaly.description,
                    )
                )
            if not rules:
                outputs.extend(
                    self._emit_fallback_recommendations(
                        state=state,
                        issue_type=anomaly.type,
                        entity=self._entity_from_anomaly(anomaly),
                        severity_score=sev.final_score,
                        evidence_ids=list(anomaly.evidence),
                        rationale=anomaly.description,
                    )
                )

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
                outputs.extend(
                    self._emit_stepwise_recommendations(
                        state=state,
                        issue_type=issue_type,
                        entity=hit.event_id,
                        severity_score=sev.final_score,
                        confidence=conf,
                        evidence_ids=[hit.event_id],
                        rule=rule,
                        rationale=hit.description,
                    )
                )
            if not rules:
                outputs.extend(
                    self._emit_fallback_recommendations(
                        state=state,
                        issue_type=issue_type,
                        entity=hit.event_id,
                        severity_score=sev.final_score,
                        evidence_ids=[hit.event_id],
                        rationale=hit.description,
                    )
                )
        outputs.sort(key=lambda r: (r.severity_score, r.confidence), reverse=True)
        return outputs[:40]

    def _rules_for_issue(self, issue_type: str) -> List[RecommendationRule]:
        return self._RULES_BY_ISSUE.get(issue_type, [])

    def _emit_stepwise_recommendations(
        self,
        state: SharedState,
        issue_type: str,
        entity: str,
        severity_score: float,
        confidence: float,
        evidence_ids: List[str],
        rule: RecommendationRule,
        rationale: str,
    ) -> List[RecommendationV2]:
        emitted: List[RecommendationV2] = []
        for idx, step in enumerate(rule.step_templates, start=1):
            emitted.append(
                state.add_recommendation_v2(
                    issue_type=issue_type,
                    entity=entity,
                    severity_score=severity_score,
                    action_code=f"{rule.action_code}_STEP_{idx}",
                    action_description=step,
                    confidence=round(max(0.6, confidence - 0.04), 3),
                    preconditions=rule.preconditions,
                    evidence_ids=evidence_ids,
                    expected_effect=rule.expected_effect,
                    rationale=rationale,
                    rule_id=f"{rule.rule_id}_STEP_{idx}",
                )
            )
        return emitted

    def _emit_fallback_recommendations(
        self,
        state: SharedState,
        issue_type: str,
        entity: str,
        severity_score: float,
        evidence_ids: List[str],
        rationale: str,
    ) -> List[RecommendationV2]:
        base_conf = 0.74 if severity_score >= 7 else 0.68
        templates = [
            ("INVESTIGATE_ROOT_CAUSE", "Step 1: Identify exact failing component and confirm first bad event in timeline.", "Root cause isolated with traceable evidence."),
            ("CONTAIN_IMPACT", "Step 2: Apply containment (throttle, isolate, or rollback) to stop further impact propagation.", "Blast radius reduced while investigation continues."),
            ("VERIFY_RECOVERY", "Step 3: Verify recovery with 2 consecutive healthy cycles and no new policy/risk escalations.", "Confirms mitigation actually resolved the issue."),
        ]
        emitted: List[RecommendationV2] = []
        for idx, (code, desc, effect) in enumerate(templates, start=1):
            emitted.append(
                state.add_recommendation_v2(
                    issue_type=issue_type,
                    entity=entity,
                    severity_score=severity_score,
                    action_code=f"{code}_{idx}",
                    action_description=desc,
                    confidence=round(base_conf, 3),
                    preconditions=["evidence_available=true"],
                    evidence_ids=evidence_ids,
                    expected_effect=effect,
                    rationale=rationale,
                    rule_id=f"REC_FALLBACK_{issue_type}_{idx}",
                )
            )
        return emitted

    def _entity_from_anomaly(self, anomaly: Anomaly) -> str:
        if anomaly.evidence:
            ev = anomaly.evidence[0]
            if "/" in ev:
                return ev.split("/")[0]
            return ev
        return anomaly.anomaly_id
