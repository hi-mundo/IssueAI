"""Issue Hunt: deep-hunt workflow that starts only after Recon and Repository Intent Review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import IssueAIRequest
from .pipeline import build_plan, build_understanding, retrieve_patterns
from .repository_intent_review import load_issue_hunt_gate, load_repository_intent_review
from .repository_recon import ISSUEAI_DIRNAME, load_issueai_state, load_repository_recon, state_path, write_json
from .workflows import build_workflow_envelopes


def load_issue_hunt(repo_root: Path) -> dict[str, Any]:
    artifact = repo_root.resolve() / ISSUEAI_DIRNAME / "findings" / "issue-hunt-hypotheses.json"
    if not artifact.exists():
        return {}
    return json.loads(artifact.read_text())


def load_issue_probe_gate(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    state = load_issueai_state(repo_root)
    hunt_state = state.get("issueHunt", {})
    blockers: list[str] = []
    if not hunt_state:
        blockers.append("Issue Hunt has not run yet.")
    elif int(hunt_state.get("hypothesisCount", 0)) == 0:
        blockers.append("Issue Hunt did not produce any hypotheses to probe.")
    return {
        "ready": not blockers,
        "blockers": blockers,
        "issueHunt": hunt_state,
    }


def run_issue_hunt(
    repo_root: Path,
    *,
    repository_label: str,
    purpose_hint: str = "",
    local_signals: tuple[str, ...] = (),
    hypothesis_limit: int = 12,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    gate = load_issue_hunt_gate(repo_root)
    if not gate["ready"]:
        return {"nextStepGate": gate, "searchSpace": {}, "hypotheses": [], "workflow": []}

    recon = load_repository_recon(repo_root)
    review = load_repository_intent_review(repo_root)
    search_space = {
        "focusDomains": gate["changedDomains"] or recon.get("applicationMap", {}).get("topDomains", []),
        "criticalPaths": review.get("criticalPaths", [])[:16],
        "residualRiskAreas": review.get("heuristicEvidence", {}),
        "languageFocus": review.get("languageFocus", []),
    }
    request = IssueAIRequest(
        repository=repository_label,
        purpose_hint=purpose_hint or review.get("purpose", "Issue Hunt after Repository Intent Review"),
        surfaces=tuple(search_space["focusDomains"][:3]),
        conventions=tuple(recon.get("applicationMap", {}).get("patternSignals", [])[:4]),
        local_signals=tuple(dict.fromkeys([*search_space["languageFocus"], *local_signals])),
    )
    understanding = build_understanding(request)
    retrieval = retrieve_patterns(request, understanding)
    plan = build_plan(request, retrieval)

    critical_paths = search_space["criticalPaths"] or recon.get("entrypoints", []) or [repository_label]
    hypotheses: list[dict[str, Any]] = []
    for rank, mechanism in enumerate(plan.ordered_mechanisms[:hypothesis_limit], start=1):
        hypotheses.append(
            {
                "rank": rank,
                "mechanism": mechanism,
                "path": critical_paths[(rank - 1) % len(critical_paths)] if critical_paths else None,
                "breakScore": "medium" if rank <= 3 else "low",
                "reason": "Prioritized from repository context, residual risk areas, and retrieved issue patterns.",
            }
        )

    workflow = build_workflow_envelopes(
        "issue-hunt",
        {
            "load-baseline": {
                "repoRoot": str(repo_root),
                "reviewMode": review.get("reviewMode", "repository"),
                "gate": gate,
                "reconSummary": {
                    "topDomains": recon.get("applicationMap", {}).get("topDomains", []),
                    "patternSignals": recon.get("applicationMap", {}).get("patternSignals", []),
                },
                "intentReviewSummary": {
                    "criticalPaths": review.get("criticalPaths", []),
                    "languageFocus": review.get("languageFocus", []),
                },
            },
            "retrieve-patterns": {
                "searchSpace": search_space,
                "languageFocus": review.get("languageFocus", []),
                "graphSummary": recon.get("flowTrace", {}).get("importGraphSummary", {}),
                "changedDomains": gate["changedDomains"],
            },
            "rank-hypotheses": {
                "retrievedPatterns": list(retrieval.matched_patterns),
                "criticalPaths": critical_paths,
                "residualRiskAreas": review.get("heuristicEvidence", {}),
                "searchSpace": search_space,
            },
            "handoff-to-probe": {
                "rankedHypotheses": hypotheses,
                "coverageGaps": list(retrieval.mechanism_candidates),
                "residualRiskAreas": review.get("heuristicEvidence", {}),
            },
        },
    )

    issueai_root = repo_root / ISSUEAI_DIRNAME
    hunt_payload = {
        "capturedAt": recon.get("capturedAt", review.get("capturedAt")),
        "repository": repository_label,
        "searchSpace": search_space,
        "retrievedPatterns": list(retrieval.matched_patterns),
        "orderedMechanisms": list(plan.ordered_mechanisms),
        "hypotheses": hypotheses,
    }
    write_json(issueai_root / "findings" / "issue-hunt-hypotheses.json", hunt_payload)
    write_json(issueai_root / "run-state" / "issue-hunt-workflow.json", {"phases": workflow})

    state = load_issueai_state(repo_root)
    state["issueHunt"] = {
        "updatedAt": hunt_payload["capturedAt"],
        "findingsPath": f"{ISSUEAI_DIRNAME}/findings/issue-hunt-hypotheses.json",
        "hypothesisCount": len(hypotheses),
        "issueProbeReady": bool(hypotheses),
    }
    write_json(state_path(repo_root), state)
    probe_gate = load_issue_probe_gate(repo_root)
    return {
        "gate": gate,
        "searchSpace": search_space,
        "retrieval": {
            "matchedPatterns": list(retrieval.matched_patterns),
            "mechanismCandidates": list(retrieval.mechanism_candidates),
        },
        "hypotheses": hypotheses,
        "workflow": workflow,
        "nextStepGate": probe_gate,
    }
