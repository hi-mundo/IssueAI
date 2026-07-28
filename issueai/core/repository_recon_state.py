"""State, checksum, and preflight helpers for Repository Recon workflows."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .repository_recon_profile import collect_repository_profile, utc_now


ISSUEAI_DIRNAME = ".issueai"
ISSUEAI_LAYOUT = (
    "snapshots",
    "understanding",
    "graphs",
    "metadata",
    "findings",
    "run-state",
)
ARTIFACT_METADATA_PATHS = {
    "repositoryRecon": ("understanding", "repository-recon.json"),
    "repositoryIntentReview": ("understanding", "repository-intent-review.json"),
}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def ensure_issueai_gitignore(repo_root: Path) -> Path:
    gitignore = repo_root / ".gitignore"
    entry = f"{ISSUEAI_DIRNAME}/"
    if gitignore.exists():
        content = gitignore.read_text()
        lines = content.splitlines()
        if entry in lines:
            return gitignore
        suffix = "" if content.endswith("\n") or not content else "\n"
        gitignore.write_text(content + suffix + entry + "\n")
        return gitignore
    gitignore.write_text(entry + "\n")
    return gitignore


def ensure_issueai_layout(repo_root: Path) -> Path:
    issueai_root = repo_root / ISSUEAI_DIRNAME
    issueai_root.mkdir(parents=True, exist_ok=True)
    for name in ISSUEAI_LAYOUT:
        (issueai_root / name).mkdir(parents=True, exist_ok=True)
    ensure_issueai_gitignore(repo_root)
    return issueai_root


def state_path(repo_root: Path) -> Path:
    return repo_root / ISSUEAI_DIRNAME / "state.json"


def load_issueai_state(repo_root: Path) -> dict[str, Any]:
    path = state_path(repo_root)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def domain_for_path(path_text: str) -> str | None:
    parts = Path(path_text.strip()).parts
    if not parts:
        return None
    return parts[0] if len(parts) > 1 else "__root__"


def scope_domains(scope: str) -> list[str]:
    values: list[str] = []
    for raw in scope.replace(",", "\n").splitlines():
        candidate = raw.strip()
        if not candidate or candidate == ".":
            continue
        domain = domain_for_path(candidate.lstrip("./"))
        if domain:
            values.append(domain)
    return sorted(dict.fromkeys(values))


def determine_covered_domains(
    preflight: dict[str, Any],
    review_mode: str,
    scope: str = "",
    fallback_domains: list[str] | tuple[str, ...] = (),
) -> list[str]:
    available = set(preflight.get("domainChecksums", {}).keys())
    scoped = scope_domains(scope)
    if review_mode in {"pending-changes", "commit-or-diff"} and preflight.get("changedDomains"):
        candidates = preflight["changedDomains"]
    elif review_mode == "scoped" and scoped:
        candidates = scoped
    elif scoped:
        candidates = scoped
    elif fallback_domains:
        candidates = list(fallback_domains)
    else:
        candidates = sorted(available)

    filtered = [domain for domain in candidates if domain in available]
    if filtered:
        return sorted(dict.fromkeys(filtered))
    return sorted(available)


def build_checksum_metadata(
    preflight: dict[str, Any],
    *,
    review_mode: str,
    scope: str = "",
    diff_target: str = "",
    fallback_domains: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    covered_domains = determine_covered_domains(preflight, review_mode, scope, fallback_domains)
    domain_checksums = preflight.get("domainChecksums", {})
    return {
        "reviewMode": review_mode,
        "scope": scope or ".",
        "diffTarget": diff_target or None,
        "coveredDomains": covered_domains,
        "domainChecksums": {
            domain: domain_checksums[domain]
            for domain in covered_domains
            if domain in domain_checksums
        },
        "structureChecksum": preflight.get("structureChecksum"),
        "organizationChecksum": preflight.get("organizationChecksum"),
        "changedDomainsAtCapture": preflight.get("changedDomains", []),
    }


def load_artifact_checksum_metadata(repo_root: Path, state: dict[str, Any], state_key: str) -> dict[str, Any] | None:
    state_entry = state.get(state_key, {})
    compatibility = state_entry.get("compatibility")
    if isinstance(compatibility, dict):
        return compatibility
    artifact_parts = ARTIFACT_METADATA_PATHS.get(state_key)
    if not artifact_parts:
        return None
    artifact_path = repo_root / ISSUEAI_DIRNAME / artifact_parts[0] / artifact_parts[1]
    if not artifact_path.exists():
        return None
    payload = json.loads(artifact_path.read_text())
    metadata = payload.get("checksumMetadata") or payload.get("compatibility")
    return metadata if isinstance(metadata, dict) else None


def assess_artifact_freshness(preflight: dict[str, Any], metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {
            "status": "missing",
            "coveredDomains": [],
            "freshDomains": [],
            "staleDomains": [],
            "reason": "No checksum metadata recorded for this artifact yet.",
        }

    covered_domains = list(dict.fromkeys(metadata.get("coveredDomains") or list((metadata.get("domainChecksums") or {}).keys())))
    expected_domain_checksums = metadata.get("domainChecksums", {})
    current_domain_checksums = preflight.get("domainChecksums", {})
    stale_domains = [
        domain
        for domain in covered_domains
        if expected_domain_checksums.get(domain) != current_domain_checksums.get(domain)
    ]
    global_checksum_mismatch = (
        metadata.get("structureChecksum") != preflight.get("structureChecksum")
        or metadata.get("organizationChecksum") != preflight.get("organizationChecksum")
    )
    if global_checksum_mismatch and not stale_domains:
        stale_domains = list(dict.fromkeys(preflight.get("changedDomains") or covered_domains))

    fresh_domains = [domain for domain in covered_domains if domain not in stale_domains]
    if not covered_domains:
        status = "missing"
    elif not stale_domains:
        status = "fresh"
    elif fresh_domains:
        status = "partial-stale"
    else:
        status = "stale"

    if status == "fresh":
        reason = "Covered domain checksums still match the current repository state."
    elif status == "missing":
        reason = "No covered domains were recorded for this artifact."
    else:
        reason = f"Checksums changed for covered domains: {', '.join(stale_domains)}."

    return {
        "status": status,
        "coveredDomains": covered_domains,
        "freshDomains": fresh_domains,
        "staleDomains": stale_domains,
        "reason": reason,
        "globalChecksumMismatch": global_checksum_mismatch,
    }


def artifact_refresh_message(label: str, freshness: dict[str, Any]) -> str:
    if freshness.get("status") == "missing":
        return f"{label} has not run yet."
    stale_domains = freshness.get("staleDomains", [])
    if stale_domains:
        return f"{label} must be refreshed for domains: {', '.join(stale_domains)}."
    return f"{label} checksum metadata must be refreshed."


def collect_git_state(repo_root: Path) -> dict[str, Any]:
    try:
        inside = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return {"available": False, "inside_worktree": False, "head": None, "worktree_dirty": False, "changed_files": []}
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return {"available": True, "inside_worktree": False, "head": None, "worktree_dirty": False, "changed_files": []}
    head = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    status = subprocess.run(["git", "-C", str(repo_root), "status", "--porcelain"], capture_output=True, text=True, check=False)
    lines = [line for line in status.stdout.splitlines() if line.strip()]
    changed_files = [line[3:] for line in lines if len(line) > 3]
    ignored_changed_files = [path for path in changed_files if path == ".gitignore" or path.startswith(f"{ISSUEAI_DIRNAME}/")]
    relevant_changed_files = [path for path in changed_files if path not in ignored_changed_files]
    return {
        "available": True,
        "inside_worktree": True,
        "head": head.stdout.strip() if head.returncode == 0 else None,
        "worktree_dirty": bool(relevant_changed_files),
        "changed_files": changed_files,
        "relevant_changed_files": relevant_changed_files,
        "ignored_changed_files": ignored_changed_files,
    }


def git_is_ancestor(repo_root: Path, older: str | None, newer: str | None) -> bool | None:
    if not older or not newer:
        return None
    result = subprocess.run(
        ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", older, newer],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    return None


def classify_preflight(repo_root: Path, current_git: dict[str, Any], profile: dict[str, Any], state: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    previous = state.get("lastPreflight")
    if not previous:
        return "initial", ["No previous .issueai preflight snapshot exists yet."], []

    changed_domains = sorted(
        {
            name
            for name, checksum in profile["domainChecksums"].items()
            if checksum != previous.get("domainChecksums", {}).get(name)
        }
        | {name for name in previous.get("domainChecksums", {}) if name not in profile["domainChecksums"]}
    )
    reasons: list[str] = []
    previous_head = previous.get("git", {}).get("head")
    current_head = current_git.get("head")
    ancestor = git_is_ancestor(repo_root, previous_head, current_head) if current_git.get("inside_worktree") else None

    if (
        previous.get("git", {}).get("head") == current_head
        and previous.get("structureChecksum") == profile["structureChecksum"]
        and previous.get("organizationChecksum") == profile["organizationChecksum"]
        and not changed_domains
    ):
        return "fresh", ["Repository state matches the last captured preflight snapshot."], changed_domains

    if ancestor is False or previous.get("organizationChecksum") != profile["organizationChecksum"] and len(changed_domains) >= 3:
        reasons.append("Repository history or high-level organization diverged from the last analysis.")
        return "divergent", reasons, changed_domains

    if previous.get("organizationChecksum") != profile["organizationChecksum"]:
        reasons.append("Folder organization changed since the last analysis.")
        return "stale", reasons, changed_domains

    if changed_domains:
        reasons.append("Some repository domains changed since the last analysis.")
        return "partial-stale", reasons, changed_domains

    reasons.append("Repository content changed without broad structural drift.")
    return "stale", reasons, changed_domains


def preflight_repository(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    issueai_root = ensure_issueai_layout(repo_root)
    state = load_issueai_state(repo_root)
    current_git = collect_git_state(repo_root)
    profile = collect_repository_profile(repo_root)
    status, reasons, changed_domains = classify_preflight(repo_root, current_git, profile, state)
    review_state = state.get("repositoryIntentReview") or state.get("intentReview") or {}
    open_findings = int(review_state.get("openFindings", review_state.get("openObviousFindings", 0)))
    snapshot = {
        "capturedAt": utc_now(),
        "repoRoot": str(repo_root),
        "issueaiDir": str(issueai_root),
        "git": current_git,
        "status": status,
        "reasons": reasons,
        "changedDomains": changed_domains,
        "structureChecksum": profile["structureChecksum"],
        "organizationChecksum": profile["organizationChecksum"],
        "domainChecksums": profile["domainChecksums"],
        "profilePath": f"{ISSUEAI_DIRNAME}/metadata/repo-profile.json",
        "issueHuntReady": False,
        "issueHuntBlockers": [],
    }
    artifact_freshness = {
        "repositoryRecon": assess_artifact_freshness(snapshot, load_artifact_checksum_metadata(repo_root, state, "repositoryRecon")),
        "repositoryIntentReview": assess_artifact_freshness(snapshot, load_artifact_checksum_metadata(repo_root, state, "repositoryIntentReview")),
    }
    snapshot["artifactFreshness"] = artifact_freshness

    recon_freshness = artifact_freshness["repositoryRecon"]
    review_freshness = artifact_freshness["repositoryIntentReview"]
    if not review_state:
        snapshot["issueHuntBlockers"].append("Repository Intent Review has not run yet.")
    elif recon_freshness["status"] != "fresh":
        snapshot["issueHuntBlockers"].append(artifact_refresh_message("Repository Recon", recon_freshness))
    elif review_freshness["status"] != "fresh":
        snapshot["issueHuntBlockers"].append(artifact_refresh_message("Repository Intent Review", review_freshness))
    elif open_findings:
        snapshot["issueHuntBlockers"].append("Repository Intent Review still has open findings.")
    else:
        snapshot["issueHuntReady"] = True

    write_json(issueai_root / "metadata" / "repo-profile.json", profile)
    write_json(issueai_root / "snapshots" / "latest.json", snapshot)

    merged_state = dict(state)
    merged_state["lastObservedPreflight"] = snapshot
    write_json(state_path(repo_root), merged_state)
    return snapshot


def select_review_mode(explicit_mode: str, scope: str, diff_target: str, git_state: dict[str, Any]) -> str:
    if explicit_mode != "auto":
        return explicit_mode
    if diff_target:
        return "commit-or-diff"
    if scope:
        return "scoped"
    if git_state.get("worktree_dirty"):
        return "pending-changes"
    return "repository"
