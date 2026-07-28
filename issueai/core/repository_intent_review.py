"""Repository Intent Review: compare expected repository guarantees against implementation evidence."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .repository_intent_review_heuristics import (
    collect_heuristic_findings,
    critical_paths,
    derive_intent_model,
    filter_intent_model_to_domains,
    filter_paths_to_domains,
)
from .repository_recon import load_repository_recon
from .repository_recon_profile import build_language_focus
from .repository_recon_state import (
    ISSUEAI_DIRNAME,
    artifact_refresh_message,
    build_checksum_metadata,
    load_issueai_state,
    preflight_repository,
    state_path,
    write_json,
)
from .workflows import build_workflow_envelopes


def load_repository_intent_review(repo_root: Path) -> dict[str, Any]:
    artifact = repo_root.resolve() / ISSUEAI_DIRNAME / "understanding" / "repository-intent-review.json"
    if not artifact.exists():
        return {}
    return json.loads(artifact.read_text())


def load_issue_hunt_gate(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    snapshot = preflight_repository(repo_root)
    state = load_issueai_state(repo_root)
    review_state = state.get("repositoryIntentReview") or {}
    artifact_freshness = snapshot.get("artifactFreshness", {})
    recon_freshness = artifact_freshness.get("repositoryRecon", {"status": "missing"})
    review_freshness = artifact_freshness.get("repositoryIntentReview", {"status": "missing"})

    blockers: list[str] = []
    if not state.get("repositoryRecon"):
        blockers.append("Repository Recon has not run yet.")
    elif recon_freshness.get("status") != "fresh":
        blockers.append(artifact_refresh_message("Repository Recon", recon_freshness))
    if not review_state:
        blockers.append("Repository Intent Review has not run yet.")
    elif review_freshness.get("status") != "fresh":
        blockers.append(artifact_refresh_message("Repository Intent Review", review_freshness))
    elif int(review_state.get("openFindings", 0)) > 0:
        blockers.append("Repository Intent Review still has open findings.")

    return {
        "ready": not blockers,
        "blockers": blockers,
        "preflightStatus": snapshot["status"],
        "changedDomains": snapshot["changedDomains"],
        "repositoryIntentReview": review_state,
        "artifactFreshness": artifact_freshness,
    }


def load_repository_intent_review_gate(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    snapshot = preflight_repository(repo_root)
    state = load_issueai_state(repo_root)
    recon_state = state.get("repositoryRecon", {})
    recon_freshness = snapshot.get("artifactFreshness", {}).get("repositoryRecon", {"status": "missing"})

    blockers: list[str] = []
    if not recon_state:
        blockers.append("Repository Recon has not run yet.")
    elif recon_freshness.get("status") != "fresh":
        blockers.append(artifact_refresh_message("Repository Recon", recon_freshness))

    return {
        "ready": not blockers,
        "blockers": blockers,
        "repositoryRecon": recon_state,
        "preflightStatus": snapshot["status"],
        "changedDomains": snapshot["changedDomains"],
        "artifactFreshness": snapshot.get("artifactFreshness", {}),
    }


def run_repository_intent_review(
    repo_root: Path,
    *,
    repository_label: str,
    purpose_hint: str = "",
    local_signals: Sequence[str] = (),
    explicit_mode: str = "auto",
    scope: str = "",
    diff_target: str = "",
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    gate = load_repository_intent_review_gate(repo_root)
    if not gate["ready"]:
        return {"nextStepGate": gate, "understanding": {}, "findings": {"findings": []}, "workflow": []}

    preflight = preflight_repository(repo_root)
    recon = load_repository_recon(repo_root)
    profile_path = repo_root / ISSUEAI_DIRNAME / "metadata" / "repo-profile.json"
    profile = json.loads(profile_path.read_text()) if profile_path.exists() else {}
    review_mode = recon.get("reviewMode", explicit_mode if explicit_mode != "auto" else "repository")
    checksum_metadata = build_checksum_metadata(
        preflight,
        review_mode=review_mode,
        scope=scope or recon.get("scope", "."),
        diff_target=diff_target or recon.get("diffTarget") or "",
        fallback_domains=recon.get("checksumMetadata", {}).get("coveredDomains", profile.get("topDomains", [])),
    )
    covered_domains = checksum_metadata["coveredDomains"]
    scoped_critical_paths = filter_paths_to_domains(critical_paths(recon), covered_domains)
    intent_model = filter_intent_model_to_domains(derive_intent_model(recon), covered_domains)
    findings = collect_heuristic_findings(repo_root, recon, covered_domains)
    language_focus = build_language_focus(profile, local_signals)

    understanding = {
        "capturedAt": preflight["capturedAt"],
        "repository": repository_label,
        "repoRoot": str(repo_root),
        "reviewMode": review_mode,
        "scope": scope or recon.get("scope", "."),
        "diffTarget": diff_target or recon.get("diffTarget"),
        "purpose": purpose_hint or "Repository Intent Review after Repository Recon",
        "checksumMetadata": checksum_metadata,
        "criticalPaths": scoped_critical_paths,
        "focusRoles": [item["role"] for item in intent_model],
        "intentModel": intent_model,
        "patternSignals": recon.get("applicationMap", {}).get("patternSignals", []),
        "languageFocus": language_focus,
        "heuristicEvidence": {
            "schemaGapCount": sum(1 for item in findings if item["type"] == "schema-gap"),
            "typingGapCount": sum(1 for item in findings if item["type"] == "typing-gap"),
            "middlewareGapCount": sum(1 for item in findings if item["type"] == "middleware-coverage-gap"),
            "asyncGapCount": sum(1 for item in findings if item["type"].startswith("async-")),
        },
        "reconSnapshotPath": f"{ISSUEAI_DIRNAME}/understanding/repository-recon.json",
    }
    residual_risk_areas = [
        item["path"]
        for item in findings
        if item["type"] in {"async-without-await", "async-error-gap", "middleware-coverage-gap", "schema-gap"}
    ][:12]
    review = {
        "capturedAt": preflight["capturedAt"],
        "repository": repository_label,
        "reviewMode": review_mode,
        "checksumMetadata": checksum_metadata,
        "findings": findings,
        "issueHuntRecommended": len(findings) == 0,
        "recommendation": (
            "Run Issue Hunt next." if len(findings) == 0 else "Resolve or explicitly triage Repository Intent Review findings before Issue Hunt."
        ),
        "residualRiskAreas": residual_risk_areas,
    }
    workflow = build_workflow_envelopes(
        "repository-intent-review",
        {
            "load-recon-and-scope": {
                "repoRoot": str(repo_root),
                "reviewMode": review_mode,
                "reconSummary": {
                    "patternSignals": recon.get("applicationMap", {}).get("patternSignals", []),
                    "topDomains": recon.get("applicationMap", {}).get("topDomains", []),
                },
                "criticalPaths": scoped_critical_paths,
            },
            "derive-intended-behavior": {
                "focusRoles": [item["role"] for item in intent_model],
                "criticalPaths": scoped_critical_paths,
                "patternSignals": recon.get("applicationMap", {}).get("patternSignals", []),
                "languageFocus": language_focus,
            },
            "compare-intent-vs-implementation": {
                "intentModel": intent_model,
                "heuristicEvidence": understanding["heuristicEvidence"],
                "criticalPaths": scoped_critical_paths,
                "languageFocus": language_focus,
            },
            "handoff-to-issue-hunt": {
                "openFindings": len(findings),
                "resolvedSignals": [item["role"] for item in intent_model],
                "residualRiskAreas": residual_risk_areas,
            },
        },
    )

    issueai_root = repo_root / ISSUEAI_DIRNAME
    write_json(issueai_root / "understanding" / "repository-intent-review.json", understanding)
    write_json(issueai_root / "findings" / "repository-intent-review.json", review)
    write_json(issueai_root / "run-state" / "repository-intent-review-workflow.json", {"phases": workflow})

    state = load_issueai_state(repo_root)
    state["lastPreflight"] = preflight
    state["repositoryIntentReview"] = {
        "updatedAt": preflight["capturedAt"],
        "reviewMode": review_mode,
        "snapshotPath": f"{ISSUEAI_DIRNAME}/understanding/repository-intent-review.json",
        "findingsPath": f"{ISSUEAI_DIRNAME}/findings/repository-intent-review.json",
        "openFindings": len(findings),
        "compatibility": checksum_metadata,
        "issueHuntReady": len(findings) == 0,
    }
    write_json(state_path(repo_root), state)
    issue_hunt_gate = load_issue_hunt_gate(repo_root)
    return {
        "preflight": preflight_repository(repo_root),
        "understanding": understanding,
        "findings": review,
        "workflow": workflow,
        "nextStepGate": issue_hunt_gate,
    }


run_intent_review = run_repository_intent_review
