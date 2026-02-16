"""
Chronos Code Agent (Demo)
========================
Turns GitHub/CI telemetry into *predictive* anomalies before deploy.

This is intentionally deterministic and explainable:
- no LLM
- no external GitHub API calls
- operates only on observed webhook payloads already ingested

INPUT:
- Observed GitHub webhook events (PR / review / workflow_run)

OUTPUT (writes to SharedState as anomalies):
- HIGH_CHURN_PR
- LOW_TEST_COVERAGE
- HIGH_COMPLEXITY_HINT
- HOTSPOT_FILE_CHANGE
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from observation import ObservedEvent
from blackboard import SharedState, Anomaly
from .langgraph_runtime import run_linear_graph, is_langgraph_enabled


class CodeAgent:
    AGENT_NAME = "CodeAgent"

    def __init__(self):
        self._use_langgraph = is_langgraph_enabled()

    def analyze(self, events: List[ObservedEvent], state: SharedState) -> List[Anomaly]:
        if self._use_langgraph:
            graph_state = run_linear_graph(
                {"events": events, "state": state, "anomalies": []},
                [("code_risk_detection", self._graph_code_risk_detection)],
            )
            return graph_state.get("anomalies", [])
        return self._analyze_core(events, state)

    def _graph_code_risk_detection(self, graph_state: Dict[str, Any]) -> Dict[str, Any]:
        graph_state["anomalies"] = self._analyze_core(graph_state["events"], graph_state["state"])
        return graph_state

    def _analyze_core(self, events: List[ObservedEvent], state: SharedState) -> List[Anomaly]:
        anomalies: List[Anomaly] = []

        gh_events = [e for e in events if self._is_github_event(e)]
        if not gh_events:
            return anomalies

        # Group by deployment_id so we can predict "this release is risky".
        by_deploy: Dict[str, List[ObservedEvent]] = {}
        for e in gh_events:
            deploy_id = self._deployment_id(e) or "deploy_unknown"
            by_deploy.setdefault(deploy_id, []).append(e)

        for deploy_id, es in by_deploy.items():
            # Pick a representative workflow id for entity attribution.
            wf_id = next((e.workflow_id for e in es if e.workflow_id), None) or "wf_unknown"

            pr_payloads = [self._github_payload(e) for e in es if self._github_event_kind(e) == "pull_request"]
            workflow_runs = [self._github_payload(e) for e in es if self._github_event_kind(e) == "workflow_run"]

            churn, hotspots, complexity_hint = self._derive_code_risk_features(pr_payloads)
            coverage = self._derive_coverage(workflow_runs)

            # 1) High churn (demo heuristic)
            if churn is not None and churn >= 40:
                conf = min(0.92, 0.65 + (churn - 40) / 100)
                anomalies.append(
                    state.add_anomaly(
                        type="HIGH_CHURN_PR",
                        agent=self.AGENT_NAME,
                        evidence=[e.event_id for e in es[:3]],
                        description=f"{wf_id} deploy {deploy_id}: high churn (+{churn} lines) increases failure probability",
                        confidence=round(conf, 2),
                    )
                )

            # 2) Low test coverage (if available)
            if coverage is not None and coverage < 0.70:
                # Stronger confidence as coverage decreases.
                conf = min(0.95, 0.70 + (0.70 - coverage) * 1.2)
                anomalies.append(
                    state.add_anomaly(
                        type="LOW_TEST_COVERAGE",
                        agent=self.AGENT_NAME,
                        evidence=[e.event_id for e in es[:3]],
                        description=f"{wf_id} deploy {deploy_id}: low test coverage ({int(coverage*100)}%) predicts higher runtime bug risk",
                        confidence=round(conf, 2),
                    )
                )

            # 3) Complexity hint (we do not parse code; we only use provided hints or filenames)
            if complexity_hint is not None and complexity_hint >= 8.0:
                conf = min(0.9, 0.6 + (complexity_hint - 8.0) * 0.08)
                anomalies.append(
                    state.add_anomaly(
                        type="HIGH_COMPLEXITY_HINT",
                        agent=self.AGENT_NAME,
                        evidence=[e.event_id for e in es[:3]],
                        description=f"{wf_id} deploy {deploy_id}: high cognitive complexity hint ({complexity_hint:.1f})",
                        confidence=round(conf, 2),
                    )
                )

            # 4) Hotspot files (demo: if payment_regex / regex / auth / policy shows up)
            if hotspots:
                conf = 0.78
                anomalies.append(
                    state.add_anomaly(
                        type="HOTSPOT_FILE_CHANGE",
                        agent=self.AGENT_NAME,
                        evidence=[e.event_id for e in es[:3]],
                        description=f"{wf_id} deploy {deploy_id}: hotspot file(s) changed: {', '.join(hotspots[:3])}",
                        confidence=conf,
                    )
                )

        return anomalies

    def _is_github_event(self, e: ObservedEvent) -> bool:
        md = e.metadata if isinstance(e.metadata, dict) else {}
        sig = md.get("source_signature", {}) if isinstance(md, dict) else {}
        if not isinstance(sig, dict):
            return False
        return str(sig.get("tool_name", "")).lower() == "github"

    def _deployment_id(self, e: ObservedEvent) -> Optional[str]:
        md = e.metadata if isinstance(e.metadata, dict) else {}
        ctx = md.get("enterprise_context", {}) if isinstance(md, dict) else {}
        if isinstance(ctx, dict) and ctx.get("deployment_id"):
            return str(ctx.get("deployment_id"))
        gh = md.get("github", {}) if isinstance(md, dict) else {}
        if isinstance(gh, dict) and gh.get("deployment_id"):
            return str(gh.get("deployment_id"))
        return None

    def _github_event_kind(self, e: ObservedEvent) -> str:
        md = e.metadata if isinstance(e.metadata, dict) else {}
        gh = md.get("github", {}) if isinstance(md, dict) else {}
        if isinstance(gh, dict) and gh.get("event"):
            return str(gh.get("event"))
        return "unknown"

    def _github_payload(self, e: ObservedEvent) -> Dict[str, Any]:
        md = e.metadata if isinstance(e.metadata, dict) else {}
        payload = md.get("event_payload", {}) if isinstance(md, dict) else {}
        return payload if isinstance(payload, dict) else {}

    def _derive_code_risk_features(self, pr_payloads: List[Dict[str, Any]]) -> Tuple[Optional[int], List[str], Optional[float]]:
        """
        Demo feature extraction:
        - churn: payload.metadata.churn_lines or files_changed*10 fallback
        - hotspots: payload.metadata.hotspot_files or infer from title
        - complexity_hint: payload.metadata.complexity or None
        """
        churn: Optional[int] = None
        hotspots: List[str] = []
        complexity: Optional[float] = None

        for p in pr_payloads:
            meta = p.get("metadata", {}) if isinstance(p, dict) else {}
            if isinstance(meta, dict):
                if churn is None and isinstance(meta.get("churn_lines"), int):
                    churn = int(meta.get("churn_lines"))
                if complexity is None and isinstance(meta.get("complexity"), (int, float)):
                    complexity = float(meta.get("complexity"))
                if isinstance(meta.get("hotspot_files"), list):
                    for f in meta.get("hotspot_files") or []:
                        if isinstance(f, str):
                            hotspots.append(f)

            pr = p.get("pull_request", {}) if isinstance(p, dict) else {}
            title = str(pr.get("title", "")).lower() if isinstance(pr, dict) else ""
            if "regex" in title and "payment_regex.py" not in hotspots:
                hotspots.append("payment_regex.py")

            # Fallback churn heuristic if none provided.
            if churn is None:
                files_changed = pr.get("changed_files") if isinstance(pr, dict) else None
                additions = pr.get("additions") if isinstance(pr, dict) else None
                deletions = pr.get("deletions") if isinstance(pr, dict) else None
                if isinstance(additions, int) and isinstance(deletions, int):
                    churn = int(additions + deletions)
                elif isinstance(files_changed, int):
                    churn = int(files_changed) * 10

        # Infer hotspots from filenames list (if present) in PR payload.
        for p in pr_payloads:
            pr = p.get("pull_request", {}) if isinstance(p, dict) else {}
            files = pr.get("files", []) if isinstance(pr, dict) else []
            if isinstance(files, list):
                for f in files:
                    if isinstance(f, str) and any(k in f.lower() for k in ("regex", "auth", "policy", "payment")):
                        hotspots.append(f)

        # De-dup while preserving order.
        dedup: List[str] = []
        seen = set()
        for f in hotspots:
            if f in seen:
                continue
            seen.add(f)
            dedup.append(f)

        return churn, dedup, complexity

    def _derive_coverage(self, workflow_runs: List[Dict[str, Any]]) -> Optional[float]:
        """
        Demo coverage extraction: accept coverage in payload.metadata.test_coverage (0-1 or 0-100).
        """
        for p in workflow_runs:
            meta = p.get("metadata", {}) if isinstance(p, dict) else {}
            cov = None
            if isinstance(meta, dict):
                cov = meta.get("test_coverage")
            if cov is None:
                cov = p.get("metadata", {}).get("test_coverage") if isinstance(p.get("metadata", {}), dict) else None
            if cov is None:
                cov = p.get("test_coverage")
            if isinstance(cov, (int, float)):
                c = float(cov)
                if c > 1.0:
                    c = c / 100.0
                return max(0.0, min(1.0, c))
        return None
