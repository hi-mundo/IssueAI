"""Repository Intent Review: compare expected repository guarantees against implementation evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .repository_recon import (
    ISSUEAI_DIRNAME,
    build_language_focus,
    load_issueai_state,
    load_repository_recon,
    preflight_repository,
    read_text_safe,
    state_path,
    write_json,
)
from .workflows import build_workflow_envelopes


SCHEMA_HINTS = ("schema", "schemas", "validator", "validate", "zod", "pydantic", "dto", "type", "types", "interface")
MIDDLEWARE_HINTS = ("middleware", "middlewares", "guard", "guards", "auth", "protect", "protection")
ROLE_REVIEW_ORDER = ("routes", "middlewares", "controllers", "services", "schemas", "orm", "thirdparty")


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
    blockers: list[str] = []
    if not state.get("repositoryRecon"):
        blockers.append("Repository Recon has not run yet.")
    if not review_state:
        blockers.append("Repository Intent Review has not run yet.")
    elif int(review_state.get("openFindings", 0)) > 0:
        blockers.append("Repository Intent Review still has open findings.")
    if snapshot["status"] != "fresh":
        blockers.append("Repository snapshot changed since the last Repository Intent Review.")
    return {
        "ready": not blockers,
        "blockers": blockers,
        "preflightStatus": snapshot["status"],
        "changedDomains": snapshot["changedDomains"],
        "repositoryIntentReview": review_state,
    }


def load_repository_intent_review_gate(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    state = load_issueai_state(repo_root)
    blockers: list[str] = []
    if not state.get("repositoryRecon"):
        blockers.append("Repository Recon has not run yet.")
    return {
        "ready": not blockers,
        "blockers": blockers,
        "repositoryRecon": state.get("repositoryRecon", {}),
    }


def _unique_paths(recon: dict[str, Any], *roles: str) -> list[str]:
    role_locations = recon.get("applicationMap", {}).get("roleLocations", {})
    seen: set[str] = set()
    ordered: list[str] = []
    for role in roles:
        for path in role_locations.get(role, []):
            if path not in seen:
                seen.add(path)
                ordered.append(path)
    return ordered


def _critical_paths(recon: dict[str, Any]) -> list[str]:
    role_paths = _unique_paths(recon, "routes", "middlewares", "controllers", "services", "orm", "thirdparty")
    largest = [item["path"] for item in recon.get("applicationMap", {}).get("largestFiles", [])]
    ordered: list[str] = []
    seen: set[str] = set()
    for path in [*role_paths, *largest]:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered[:24]


def _load_recon_findings(repo_root: Path) -> list[dict[str, Any]]:
    findings_path = repo_root / ISSUEAI_DIRNAME / "findings" / "repository-recon-findings.json"
    if not findings_path.exists():
        return []
    return json.loads(findings_path.read_text()).get("findings", [])


def _derive_intent_model(recon: dict[str, Any]) -> list[dict[str, Any]]:
    role_locations = recon.get("applicationMap", {}).get("roleLocations", {})
    guarantees = {
        "routes": "Routes should expose the intended surface and hand off cleanly into protected, schema-respecting flows.",
        "middlewares": "Middlewares should protect or normalize cross-cutting boundaries without easy bypass paths.",
        "controllers": "Controllers should adapt external input into the right domain/service calls without leaking weak contracts.",
        "services": "Services should enforce business rules and pass structurally valid data across boundaries.",
        "schemas": "Schemas and validators should make contract drift or nullability breaks visible early.",
        "orm": "Persistence layers should receive already-normalized data and preserve repository guarantees.",
        "thirdparty": "Third-party integrations should not bypass validation, typing assumptions, or error handling.",
    }
    return [
        {"role": role, "expectedGuarantee": guarantees[role], "paths": role_locations.get(role, [])[:6]}
        for role in ROLE_REVIEW_ORDER
        if role_locations.get(role)
    ]


def _path_text(repo_root: Path, relative_path: str) -> str:
    return read_text_safe(repo_root / relative_path)


def _path_exists_with_hint(repo_root: Path, relative_path: str, hints: tuple[str, ...]) -> bool:
    parent = (repo_root / relative_path).parent
    if not parent.exists():
        return False
    lowered = {child.name.lower() for child in parent.iterdir() if child.is_file()}
    return any(any(hint in name for hint in hints) for name in lowered)


def _schema_gaps(repo_root: Path, recon: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for relative_path in _unique_paths(recon, "routes", "controllers", "services")[:18]:
        text = _path_text(repo_root, relative_path).lower()
        if any(hint in text for hint in SCHEMA_HINTS):
            continue
        if _path_exists_with_hint(repo_root, relative_path, SCHEMA_HINTS):
            continue
        findings.append(
            {
                "type": "schema-gap",
                "breakScore": "medium",
                "path": relative_path,
                "reason": "This high-signal implementation path does not show a nearby schema, validator, or explicit contract artifact.",
            }
        )
    return findings[:8]


def _python_annotation_findings(repo_root: Path, recon: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    pattern = re.compile(r"^\s*(async\s+def|def)\s+([a-zA-Z_][a-zA-Z0-9_]*)\((.*?)\)(\s*->\s*[^:]+)?\s*:", re.MULTILINE | re.DOTALL)
    for relative_path in _unique_paths(recon, "middlewares", "controllers", "services")[:18]:
        if not relative_path.endswith(".py"):
            continue
        text = _path_text(repo_root, relative_path)
        for _, function_name, raw_params, return_annotation in pattern.findall(text):
            if function_name.startswith("_"):
                continue
            params = [item.strip() for item in raw_params.split(",") if item.strip() and item.strip() not in {"self", "cls", "*", "/"}]
            missing_param_annotation = any(":" not in item for item in params)
            missing_return_annotation = not return_annotation
            if missing_param_annotation or missing_return_annotation:
                findings.append(
                    {
                        "type": "typing-gap",
                        "breakScore": "low",
                        "path": relative_path,
                        "reason": f"Function `{function_name}` relies on implicit typing in a high-signal file, which weakens contract tracking.",
                    }
                )
                break
    return findings[:8]


def _javascript_typing_findings(recon: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for relative_path in _unique_paths(recon, "routes", "middlewares", "controllers", "services")[:18]:
        if relative_path.endswith((".js", ".jsx")):
            findings.append(
                {
                    "type": "typing-gap",
                    "breakScore": "low",
                    "path": relative_path,
                    "reason": "JavaScript path in a high-signal role depends on inferred contracts, so Intent Review should treat typing assumptions as fragile.",
                }
            )
    return findings[:6]


def _async_findings(repo_root: Path, recon: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for relative_path in _unique_paths(recon, "routes", "middlewares", "controllers", "services", "thirdparty")[:24]:
        text = _path_text(repo_root, relative_path)
        lowered = text.lower()
        if "async def " in lowered or "async function" in lowered or "async (" in lowered:
            if "await " not in lowered:
                findings.append(
                    {
                        "type": "async-without-await",
                        "breakScore": "medium",
                        "path": relative_path,
                        "reason": "Async code appears to exist without visible await usage, which often signals a broken or misleading async boundary.",
                    }
                )
            elif not any(token in lowered for token in ("try:", "except ", "try {", ".catch(", "catch (")):
                findings.append(
                    {
                        "type": "async-error-gap",
                        "breakScore": "low",
                        "path": relative_path,
                        "reason": "Async code exists without obvious local failure handling, which can make break paths easier to miss.",
                    }
                )
    return findings[:8]


def _middleware_findings(repo_root: Path, recon: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not recon.get("applicationMap", {}).get("roleLocations", {}).get("middlewares"):
        return findings
    for relative_path in _unique_paths(recon, "routes")[:12]:
        text = _path_text(repo_root, relative_path).lower()
        if any(hint in text for hint in MIDDLEWARE_HINTS):
            continue
        findings.append(
            {
                "type": "middleware-coverage-gap",
                "breakScore": "medium",
                "path": relative_path,
                "reason": "Repository has middleware/guard-like structure, but this route path does not show an obvious protection hook.",
            }
        )
    return findings[:6]


def _dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in findings:
        key = (item["type"], item["path"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def run_repository_intent_review(
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
    gate = load_repository_intent_review_gate(repo_root)
    if not gate["ready"]:
        return {"nextStepGate": gate, "understanding": {}, "findings": {"findings": []}, "workflow": []}

    preflight = preflight_repository(repo_root)
    recon = load_repository_recon(repo_root)
    profile_path = repo_root / ISSUEAI_DIRNAME / "metadata" / "repo-profile.json"
    profile = json.loads(profile_path.read_text()) if profile_path.exists() else {}
    critical_paths = _critical_paths(recon)
    intent_model = _derive_intent_model(recon)
    heuristic_findings = [
        *_load_recon_findings(repo_root),
        *_schema_gaps(repo_root, recon),
        *_python_annotation_findings(repo_root, recon),
        *_javascript_typing_findings(recon),
        *_async_findings(repo_root, recon),
        *_middleware_findings(repo_root, recon),
    ]
    findings = _dedupe_findings(heuristic_findings)
    review_mode = recon.get("reviewMode", explicit_mode if explicit_mode != "auto" else "repository")
    language_focus = build_language_focus(profile, local_signals)
    understanding = {
        "capturedAt": preflight["capturedAt"],
        "repository": repository_label,
        "repoRoot": str(repo_root),
        "reviewMode": review_mode,
        "scope": scope or recon.get("scope", "."),
        "diffTarget": diff_target or recon.get("diffTarget"),
        "purpose": purpose_hint or "Repository Intent Review after Repository Recon",
        "criticalPaths": critical_paths,
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
                "criticalPaths": critical_paths,
            },
            "derive-intended-behavior": {
                "focusRoles": [item["role"] for item in intent_model],
                "criticalPaths": critical_paths,
                "patternSignals": recon.get("applicationMap", {}).get("patternSignals", []),
                "languageFocus": language_focus,
            },
            "compare-intent-vs-implementation": {
                "intentModel": intent_model,
                "heuristicEvidence": understanding["heuristicEvidence"],
                "criticalPaths": critical_paths,
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
    state["repositoryIntentReview"] = {
        "updatedAt": preflight["capturedAt"],
        "reviewMode": review_mode,
        "snapshotPath": f"{ISSUEAI_DIRNAME}/understanding/repository-intent-review.json",
        "findingsPath": f"{ISSUEAI_DIRNAME}/findings/repository-intent-review.json",
        "openFindings": len(findings),
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


# Compatibility alias during migration.
run_intent_review = run_repository_intent_review
