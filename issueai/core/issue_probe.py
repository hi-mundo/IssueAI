"""Issue Probe: deterministic follow-up checks for suspected issues."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .issue_hunt import load_issue_hunt
from .repository_recon import ISSUEAI_DIRNAME, load_issueai_state, read_text_safe, state_path, write_json
from .repository_recon_profile import utc_now
from .workflows import build_workflow_envelopes


def _load_probe_candidates(repo_root: Path) -> list[dict[str, Any]]:
    hunt = load_issue_hunt(repo_root)
    if hunt.get("hypotheses"):
        return hunt["hypotheses"]
    review_path = repo_root / ISSUEAI_DIRNAME / "findings" / "repository-intent-review.json"
    if review_path.exists():
        payload = json.loads(review_path.read_text())
        return payload.get("findings", [])
    return []


def _candidate_static_evidence(repo_root: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    relative_path = candidate.get("path")
    if not relative_path:
        return {"status": "needs-manual-or-runtime-check", "reason": "Candidate does not point to a concrete file path."}
    absolute_path = repo_root / relative_path
    if not absolute_path.exists():
        return {"status": "needs-manual-or-runtime-check", "reason": "Candidate path no longer exists in the repository snapshot."}
    text = read_text_safe(absolute_path).lower()
    candidate_type = candidate.get("type") or candidate.get("mechanism")
    if candidate_type == "schema-gap" and not any(token in text for token in ("schema", "validator", "zod", "pydantic", "dto", "type")):
        return {"status": "supported-by-static-evidence", "reason": "File content still lacks an obvious schema or validator signal."}
    if candidate_type == "typing-gap" and absolute_path.suffix in {".js", ".jsx"}:
        return {"status": "supported-by-static-evidence", "reason": "High-signal JavaScript path still depends on inferred typing only."}
    if candidate_type in {"async-without-await", "async-error-gap"} and "async" in text:
        return {"status": "supported-by-static-evidence", "reason": "Async-related pattern still appears in the file content."}
    if candidate_type == "middleware-coverage-gap" and not any(token in text for token in ("middleware", "guard", "auth", "protect")):
        return {"status": "supported-by-static-evidence", "reason": "Route content still lacks an obvious protection hook."}
    return {"status": "needs-manual-or-runtime-check", "reason": "Static evidence alone is not decisive for this candidate."}


def run_issue_probe(repo_root: Path, *, repository_label: str, limit: int = 6) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    candidates = _load_probe_candidates(repo_root)[:limit]
    selected = []
    for index, candidate in enumerate(candidates, start=1):
        static_evidence = _candidate_static_evidence(repo_root, candidate)
        selected.append(
            {
                "rank": index,
                "candidate": candidate,
                "probePlan": [
                    "Load the candidate artifact and mapped repository context.",
                    "Check whether static evidence already supports or weakens the suspected issue.",
                    "Escalate to runtime or manual verification only if static evidence is insufficient.",
                ],
                "staticEvidence": static_evidence,
            }
        )

    verdicts = [
        {
            "rank": item["rank"],
            "path": item["candidate"].get("path"),
            "status": item["staticEvidence"]["status"],
            "reason": item["staticEvidence"]["reason"],
        }
        for item in selected
    ]

    workflow = build_workflow_envelopes(
        "issue-probe",
        {
            "select-candidates": {
                "repoRoot": str(repo_root),
                "probeQueue": candidates,
                "limit": limit,
            },
            "build-probes": {
                "selectedCandidates": selected,
                "repositoryArtifacts": {
                    "issueHunt": f"{ISSUEAI_DIRNAME}/findings/issue-hunt-hypotheses.json",
                    "intentReview": f"{ISSUEAI_DIRNAME}/findings/repository-intent-review.json",
                },
                "availableEvidence": verdicts,
            },
            "execute-evidence-checks": {
                "probePlans": [item["probePlan"] for item in selected],
                "staticEvidence": verdicts,
                "repositoryArtifacts": {
                    "repoRoot": str(repo_root),
                },
            },
            "verdicts": {
                "probeResults": verdicts,
                "unresolvedCandidates": [item for item in verdicts if item["status"] != "supported-by-static-evidence"],
            },
        },
    )

    issueai_root = repo_root / ISSUEAI_DIRNAME
    captured_at = utc_now()
    probe_payload = {
        "capturedAt": captured_at,
        "repository": repository_label,
        "selectedCandidates": selected,
        "verdicts": verdicts,
    }
    write_json(issueai_root / "findings" / "issue-probe-results.json", probe_payload)
    write_json(issueai_root / "run-state" / "issue-probe-workflow.json", {"phases": workflow})

    state = load_issueai_state(repo_root)
    state["issueProbe"] = {
        "updatedAt": captured_at,
        "resultsPath": f"{ISSUEAI_DIRNAME}/findings/issue-probe-results.json",
        "selectedCount": len(selected),
    }
    write_json(state_path(repo_root), state)
    return {
        "selectedCandidates": selected,
        "verdicts": verdicts,
        "workflow": workflow,
    }
