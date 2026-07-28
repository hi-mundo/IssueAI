"""Repository Recon: deterministic repository mapping, tracing, and graph synthesis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .repository_recon_graph import (
    build_flow_traces,
    build_recon_findings,
    build_repository_graph,
    collect_import_graph,
    detect_redundancies,
)
from .repository_recon_profile import (
    build_entrypoint_strategy,
    build_language_focus,
    collect_domain_clusters,
    collect_folder_depth_census,
    detect_project_patterns,
    find_entrypoints,
    iter_relevant_files,
    read_text_safe,
    utc_now,
)
from .repository_recon_state import (
    ISSUEAI_DIRNAME,
    build_checksum_metadata,
    ensure_issueai_layout,
    load_issueai_state,
    preflight_repository,
    select_review_mode,
    state_path,
    write_json,
)
from .workflows import build_workflow_envelopes


def load_repository_recon(repo_root: Path) -> dict[str, Any]:
    artifact = repo_root.resolve() / ISSUEAI_DIRNAME / "understanding" / "repository-recon.json"
    if not artifact.exists():
        return {}
    return json.loads(artifact.read_text())


def run_repository_recon(
    repo_root: Path,
    *,
    repository_label: str,
    purpose_hint: str = "",
    local_signals: tuple[str, ...] = (),
    explicit_mode: str = "auto",
    scope: str = "",
    diff_target: str = "",
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    issueai_root = ensure_issueai_layout(repo_root)
    preflight = preflight_repository(repo_root)
    profile = json.loads((issueai_root / "metadata" / "repo-profile.json").read_text())
    files = iter_relevant_files(repo_root)
    role_locations = profile.get("roleLocations", {})
    entrypoints = find_entrypoints(files, repo_root)
    entrypoint_strategy = build_entrypoint_strategy(entrypoints, role_locations)
    folder_depth_census = collect_folder_depth_census(files, repo_root)
    domain_clusters = collect_domain_clusters(files, repo_root)
    import_graph = collect_import_graph(files, repo_root)
    redundancies = detect_redundancies(role_locations)
    flow_traces = build_flow_traces(role_locations, import_graph)
    pattern_signals = detect_project_patterns(role_locations, entrypoints)
    recon_findings = build_recon_findings(profile, redundancies)

    review_mode = select_review_mode(explicit_mode, scope, diff_target, preflight["git"])
    checksum_metadata = build_checksum_metadata(
        preflight,
        review_mode=review_mode,
        scope=scope,
        diff_target=diff_target,
        fallback_domains=profile.get("topDomains", []),
    )
    language_focus = build_language_focus(profile, local_signals)

    understanding = {
        "capturedAt": utc_now(),
        "repository": repository_label,
        "repoRoot": str(repo_root),
        "reviewMode": review_mode,
        "scope": scope or ".",
        "diffTarget": diff_target or None,
        "purpose": purpose_hint or "Repository Recon before Repository Intent Review and Issue Hunt",
        "checksumMetadata": checksum_metadata,
        "entrypoints": entrypoints,
        "entrypointStrategy": entrypoint_strategy,
        "applicationMap": {
            "focusDomains": checksum_metadata["coveredDomains"],
            "topDomains": profile.get("topDomains", []),
            "dominantLanguages": profile.get("dominantLanguages", []),
            "dominantNamingStyle": profile.get("dominantNamingStyle", "plain"),
            "largestFiles": profile.get("largestFiles", []),
            "roleLocations": role_locations,
            "folderDepthCensus": folder_depth_census,
            "domainClusters": domain_clusters,
            "patternSignals": pattern_signals,
            "redundancies": redundancies,
        },
        "flowTrace": {
            "importGraphSummary": import_graph["summary"],
            "flowTraces": flow_traces,
        },
        "languageFocus": language_focus,
        "reusedBaseline": {
            "status": preflight["status"],
            "changedDomains": preflight["changedDomains"],
        },
    }
    graph = build_repository_graph(role_locations, import_graph, flow_traces)
    workflow = build_workflow_envelopes(
        "repository-recon",
        {
            "snapshot-and-entrypoints": {
                "repoRoot": str(repo_root),
                "reviewMode": review_mode,
                "entrypoints": entrypoints,
                "changedDomains": preflight["changedDomains"],
            },
            "role-and-domain-map": {
                "roleLocations": role_locations,
                "folderDepthCensus": folder_depth_census,
                "domainClusters": domain_clusters,
                "patternSignals": pattern_signals,
            },
            "flow-trace-and-graph": {
                "importGraphSummary": import_graph["summary"],
                "flowTraces": flow_traces,
                "redundancies": redundancies,
                "entrypointStrategy": entrypoint_strategy,
            },
        },
    )

    write_json(issueai_root / "understanding" / "repository-recon.json", understanding)
    write_json(issueai_root / "graphs" / "repository-recon-graph.json", graph)
    write_json(issueai_root / "metadata" / "repository-map.json", understanding["applicationMap"])
    write_json(issueai_root / "findings" / "repository-recon-findings.json", {"findings": recon_findings})
    write_json(issueai_root / "run-state" / "repository-recon-workflow.json", {"phases": workflow})

    state = load_issueai_state(repo_root)
    state["lastPreflight"] = preflight
    state["repositoryRecon"] = {
        "updatedAt": utc_now(),
        "reviewMode": review_mode,
        "snapshotPath": f"{ISSUEAI_DIRNAME}/understanding/repository-recon.json",
        "graphPath": f"{ISSUEAI_DIRNAME}/graphs/repository-recon-graph.json",
        "findingsPath": f"{ISSUEAI_DIRNAME}/findings/repository-recon-findings.json",
        "roleCount": len(role_locations),
        "flowTraceCount": len(flow_traces),
        "compatibility": checksum_metadata,
        "repositoryIntentReviewReady": True,
    }
    write_json(state_path(repo_root), state)
    return {
        "preflight": preflight_repository(repo_root),
        "understanding": understanding,
        "graph": graph,
        "findings": {"findings": recon_findings},
        "workflow": workflow,
        "nextStepGate": {
            "ready": True,
            "blockers": [],
            "recommendedNext": "repository-intent-review",
        },
    }
