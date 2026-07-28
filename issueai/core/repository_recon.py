"""Repository Recon: deterministic repository mapping, tracing, and graph synthesis."""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .workflows import build_workflow_envelopes


ISSUEAI_DIRNAME = ".issueai"
ISSUEAI_LAYOUT = (
    "snapshots",
    "understanding",
    "graphs",
    "metadata",
    "findings",
    "run-state",
)

IGNORED_DIRS = {
    ".git",
    ISSUEAI_DIRNAME,
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "vendor",
    "coverage",
}

SOURCE_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".swift",
    ".rb",
    ".php",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
}

SCHEMA_SUFFIXES = {".json", ".yaml", ".yml", ".toml"}

LANGUAGE_REVIEW_HINTS = {
    ".py": ("typing", "nullability", "async", "pydantic/schema"),
    ".ts": ("types", "nullability", "async", "zod/schema"),
    ".tsx": ("types", "props/contracts", "async", "zod/schema"),
    ".js": ("async", "nullability", "runtime contracts", "error paths"),
    ".jsx": ("props/contracts", "async", "runtime contracts"),
    ".go": ("error handling", "context propagation", "goroutines"),
    ".rs": ("Result handling", "ownership boundaries", "serde/contracts"),
    ".java": ("nullability", "async/executor usage", "DTO/schema"),
    ".kt": ("nullability", "coroutines", "serialization/schema"),
    ".swift": ("optionals", "async", "state boundaries"),
    ".rb": ("nil handling", "callbacks", "ActiveModel/schema"),
    ".php": ("nullable inputs", "DTO/schema", "async queues"),
    ".c": ("resource lifecycle", "boundary contracts"),
    ".cc": ("resource lifecycle", "boundary contracts"),
    ".cpp": ("resource lifecycle", "ownership", "boundary contracts"),
    ".cs": ("async/await", "nullable refs", "DTO/schema"),
}

KNOWN_ROLE_MARKERS: dict[str, set[str]] = {
    "routes": {"route", "routes", "router", "routers", "api", "endpoint", "endpoints"},
    "controllers": {"controller", "controllers", "handler", "handlers", "view", "views"},
    "middlewares": {"middleware", "middlewares", "guard", "guards", "auth", "filter", "filters"},
    "services": {"service", "services", "usecase", "usecases", "domain", "domains", "logic"},
    "schemas": {"schema", "schemas", "validator", "validators", "dto", "dtos", "type", "types", "model", "models"},
    "orm": {"orm", "db", "database", "repo", "repos", "repository", "repositories", "migration", "migrations"},
    "thirdparty": {"client", "clients", "integration", "integrations", "provider", "providers", "thirdparty", "sdk"},
    "utils": {"util", "utils", "helper", "helpers", "common", "shared"},
    "tests": {"test", "tests", "spec", "specs", "__tests__"},
}

ENTRYPOINT_FILENAMES = (
    "main.py",
    "main.ts",
    "main.js",
    "app.py",
    "app.ts",
    "app.js",
    "server.py",
    "server.ts",
    "server.js",
    "cli.py",
    "cli.ts",
    "cli.js",
    "manage.py",
    "index.ts",
    "index.js",
)

IMPORT_PATTERNS = {
    ".py": (
        re.compile(r"^\s*from\s+([a-zA-Z0-9_\.]+)\s+import", re.MULTILINE),
        re.compile(r"^\s*import\s+([a-zA-Z0-9_\.]+)", re.MULTILINE),
    ),
    ".ts": (
        re.compile(r"from\s+[\"']([^\"']+)[\"']"),
        re.compile(r"require\([\"']([^\"']+)[\"']\)"),
    ),
    ".tsx": (
        re.compile(r"from\s+[\"']([^\"']+)[\"']"),
        re.compile(r"require\([\"']([^\"']+)[\"']\)"),
    ),
    ".js": (
        re.compile(r"from\s+[\"']([^\"']+)[\"']"),
        re.compile(r"require\([\"']([^\"']+)[\"']\)"),
    ),
    ".jsx": (
        re.compile(r"from\s+[\"']([^\"']+)[\"']"),
        re.compile(r"require\([\"']([^\"']+)[\"']\)"),
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(parts: list[str]) -> str:
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


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


def iter_relevant_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo_root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(repo_root).parts):
            continue
        if path.suffix.lower() in SOURCE_SUFFIXES or path.suffix.lower() in SCHEMA_SUFFIXES:
            files.append(path)
    return sorted(files)


def detect_naming_style(stem: str) -> str:
    if "-" in stem:
        return "kebab"
    if "_" in stem:
        return "snake"
    if stem[:1].isupper():
        return "pascal"
    if any(char.isupper() for char in stem[1:]):
        return "camel"
    return "plain"


def count_lines(path: Path) -> int:
    return read_text_safe(path).count("\n") + 1


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_path(repo_root: Path) -> Path:
    return repo_root / ISSUEAI_DIRNAME / "state.json"


def load_issueai_state(repo_root: Path) -> dict[str, Any]:
    path = state_path(repo_root)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def changed_domains_from_paths(paths: list[str]) -> list[str]:
    values = set()
    for item in paths:
        parts = Path(item.strip()).parts
        if not parts:
            continue
        values.add(parts[0] if len(parts) > 1 else "__root__")
    return sorted(values)


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


def classify_path_roles(relative_path: Path) -> list[str]:
    lowered_parts = [part.lower() for part in relative_path.parts]
    lowered_stem = relative_path.stem.lower()
    roles = set()
    if relative_path.name.lower() in ENTRYPOINT_FILENAMES:
        roles.add("entrypoint")
    for role, markers in KNOWN_ROLE_MARKERS.items():
        if any(part in markers for part in lowered_parts):
            roles.add(role)
            continue
        if any(marker in lowered_stem for marker in markers):
            roles.add(role)
    if not roles:
        roles.add("unclassified")
    return sorted(roles)


def collect_repository_profile(repo_root: Path) -> dict[str, Any]:
    files = iter_relevant_files(repo_root)
    domains: defaultdict[str, list[str]] = defaultdict(list)
    domain_counts: Counter[str] = Counter()
    extensions: Counter[str] = Counter()
    line_counts: list[int] = []
    file_lines: dict[str, int] = {}
    naming_styles: Counter[str] = Counter()
    structure_parts: list[str] = []
    organization_parts: set[str] = set()
    role_locations: defaultdict[str, list[str]] = defaultdict(list)

    for path in files:
        rel = path.relative_to(repo_root)
        domain = rel.parts[0] if len(rel.parts) > 1 else "__root__"
        digest = file_digest(path)
        lines = count_lines(path)
        style = detect_naming_style(path.stem)
        roles = classify_path_roles(rel)
        domains[domain].append(f"{rel.as_posix()}|{digest}|{lines}")
        domain_counts[domain] += 1
        extensions[path.suffix.lower()] += 1
        line_counts.append(lines)
        file_lines[rel.as_posix()] = lines
        naming_styles[style] += 1
        structure_parts.append(f"{rel.parent.as_posix()}|{path.suffix.lower()}|{style}|{','.join(roles)}")
        organization_parts.add(rel.parent.as_posix())
        for role in roles:
            role_locations[role].append(rel.as_posix())

    sorted_domains = {name: sha256_text(sorted(values)) for name, values in sorted(domains.items())}
    median_lines = int(statistics.median(line_counts)) if line_counts else 0
    largest_files = sorted(file_lines.items(), key=lambda item: (-item[1], item[0]))[:12]
    dominant_style = naming_styles.most_common(1)[0][0] if naming_styles else "plain"
    dominant_languages = [suffix for suffix, _ in extensions.most_common(3)]

    return {
        "capturedAt": utc_now(),
        "totalSourceFiles": len(files),
        "dominantLanguages": dominant_languages,
        "topDomains": [name for name, _ in domain_counts.most_common(6)],
        "domainFileCounts": dict(domain_counts),
        "domainChecksums": sorted_domains,
        "structureChecksum": sha256_text(sorted(structure_parts)),
        "organizationChecksum": sha256_text(sorted(organization_parts)),
        "medianSourceLines": median_lines,
        "dominantNamingStyle": dominant_style,
        "largestFiles": [{"path": path, "lines": lines} for path, lines in largest_files],
        "roleLocations": {role: sorted(paths) for role, paths in sorted(role_locations.items())},
    }


def classify_preflight(repo_root: Path, current_git: dict[str, Any], profile: dict[str, Any], state: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    previous = state.get("lastPreflight")
    if not previous:
        return "initial", ["No previous .issueai preflight snapshot exists yet."], []

    changed_domains = sorted(
        set(changed_domains_from_paths(current_git.get("relevant_changed_files", [])))
        | {
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
    if not review_state:
        snapshot["issueHuntBlockers"].append("Repository Intent Review has not run yet.")
    elif open_findings:
        snapshot["issueHuntBlockers"].append("Repository Intent Review still has open findings.")
    elif status != "fresh":
        snapshot["issueHuntBlockers"].append("Repository Intent Review snapshot must be refreshed before Issue Hunt.")
    else:
        snapshot["issueHuntReady"] = True

    write_json(issueai_root / "metadata" / "repo-profile.json", profile)
    write_json(issueai_root / "snapshots" / "latest.json", snapshot)

    merged_state = dict(state)
    merged_state["lastPreflight"] = snapshot
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


def build_language_focus(profile: dict[str, Any], local_signals: tuple[str, ...]) -> list[str]:
    hints: list[str] = []
    for suffix in profile.get("dominantLanguages", []):
        hints.extend(LANGUAGE_REVIEW_HINTS.get(suffix, ()))
    hints.extend(local_signals)
    return list(dict.fromkeys(hints))


def collect_folder_depth_census(files: list[Path], repo_root: Path) -> list[dict[str, Any]]:
    counts: defaultdict[int, dict[str, Any]] = defaultdict(lambda: {"files": 0, "directories": set()})
    for path in files:
        rel = path.relative_to(repo_root)
        depth = len(rel.parts) - 1
        counts[depth]["files"] += 1
        counts[depth]["directories"].add(rel.parent.as_posix())
    return [
        {
            "depth": depth,
            "files": values["files"],
            "distinctDirectories": len(values["directories"]),
        }
        for depth, values in sorted(counts.items())
    ]


def collect_domain_clusters(files: list[Path], repo_root: Path) -> list[dict[str, Any]]:
    clusters: defaultdict[str, dict[str, Any]] = defaultdict(lambda: {"files": 0, "children": Counter()})
    for path in files:
        rel = path.relative_to(repo_root)
        domain = rel.parts[0] if len(rel.parts) > 1 else "__root__"
        child = rel.parts[1] if len(rel.parts) > 2 else "__leaf__"
        clusters[domain]["files"] += 1
        clusters[domain]["children"][child] += 1
    return [
        {
            "domain": domain,
            "files": values["files"],
            "childBuckets": dict(values["children"].most_common(8)),
        }
        for domain, values in sorted(clusters.items())
    ]


def detect_project_patterns(role_locations: dict[str, list[str]], entrypoints: list[str]) -> list[str]:
    patterns: list[str] = []
    if any(path.endswith(("main.py", "main.ts", "main.js")) for path in entrypoints):
        patterns.append("script-main-first")
    if role_locations.get("routes") and role_locations.get("services"):
        patterns.append("layered-api")
    if role_locations.get("controllers") and role_locations.get("orm"):
        patterns.append("controller-to-database layering")
    if role_locations.get("middlewares"):
        patterns.append("middleware-protected request flow")
    if role_locations.get("schemas"):
        patterns.append("explicit-schema-contracts")
    if role_locations.get("thirdparty"):
        patterns.append("external-integrations")
    return patterns or ["unclassified-layout"]


def find_entrypoints(files: list[Path], repo_root: Path) -> list[str]:
    matches = [path.relative_to(repo_root).as_posix() for path in files if path.name.lower() in ENTRYPOINT_FILENAMES]
    ranked = sorted(matches, key=lambda item: (0 if item.endswith(("main.py", "main.ts", "main.js")) else 1, len(item)))
    return ranked[:8]


def build_entrypoint_strategy(entrypoints: list[str], role_locations: dict[str, list[str]]) -> dict[str, Any]:
    if entrypoints:
        primary = entrypoints[0]
        if primary.endswith(("main.py", "main.ts", "main.js")):
            return {
                "startingPoint": primary,
                "reason": "Repository looks script- or app-entrypoint-first, so Recon should start from main.",
                "followUps": [
                    "Trace local imports from the main entrypoint.",
                    "Map downstream services, middleware, and external integrations from there.",
                ],
            }
        return {
            "startingPoint": primary,
            "reason": "Repository exposes an obvious entrypoint, so Recon should start there before descending into helpers.",
            "followUps": [
                "Trace local imports from the entrypoint.",
                "Only branch into sibling domains after the primary flow is mapped.",
            ],
        }
    if role_locations.get("routes"):
        return {
            "startingPoint": role_locations["routes"][0],
            "reason": "Repository looks API-first, so Recon should start at routes and follow imports inward.",
            "followUps": [
                "Follow route imports into controllers, services, and persistence layers.",
                "Check whether repeated domains stay together or drift across folders.",
            ],
        }
    return {
        "startingPoint": "__tree-census__",
        "reason": "No obvious entrypoint exists, so Recon should start from folder census and dominant roles.",
        "followUps": [
            "Map the dominant domains first.",
            "Use imports and role markers to find the primary flow afterward.",
        ],
    }


def extract_import_tokens(path: Path, source: str) -> list[str]:
    patterns = IMPORT_PATTERNS.get(path.suffix.lower(), ())
    values: list[str] = []
    for pattern in patterns:
        values.extend(match for match in pattern.findall(source) if match)
    return values


def resolve_relative_import(source_rel: Path, token: str, path_index: dict[str, Path]) -> str | None:
    if not token.startswith("."):
        return None
    candidate = (source_rel.parent / token.replace(".", "/")).as_posix()
    stripped = candidate.rstrip("/")
    candidates = [stripped, f"{stripped}/__init__", f"{stripped}/index"]
    for base in candidates:
        for suffix in SOURCE_SUFFIXES:
            lookup = f"{base}{suffix}"
            if lookup in path_index:
                return lookup
    return None


def resolve_package_import(token: str, stem_index: dict[str, list[str]]) -> str | None:
    if token.startswith("@"):
        token = token.split("/")[-1]
    last = token.split("/")[-1].split(".")[-1]
    matches = stem_index.get(last.lower(), [])
    if len(matches) == 1:
        return matches[0]
    return None


def collect_import_graph(files: list[Path], repo_root: Path) -> dict[str, Any]:
    path_index = {path.relative_to(repo_root).as_posix(): path for path in files}
    stem_index: defaultdict[str, list[str]] = defaultdict(list)
    for rel in path_index:
        stem_index[Path(rel).stem.lower()].append(rel)

    edges: list[dict[str, Any]] = []
    unresolved = 0
    for rel, absolute_path in path_index.items():
        source = read_text_safe(absolute_path)
        for token in extract_import_tokens(absolute_path, source):
            resolved = resolve_relative_import(Path(rel), token, path_index) or resolve_package_import(token, stem_index)
            if resolved and resolved != rel:
                edges.append({"from": rel, "to": resolved, "kind": "import", "token": token})
            else:
                unresolved += 1

    edge_index: defaultdict[str, list[str]] = defaultdict(list)
    for edge in edges:
        edge_index[edge["from"]].append(edge["to"])

    return {
        "edges": edges[:250],
        "summary": {
            "resolvedEdges": len(edges),
            "unresolvedTokens": unresolved,
            "uniqueSources": len(edge_index),
        },
        "adjacency": {source: sorted(set(targets))[:16] for source, targets in sorted(edge_index.items())},
    }


def detect_redundancies(role_locations: dict[str, list[str]]) -> list[dict[str, Any]]:
    redundancies: list[dict[str, Any]] = []
    for role, paths in sorted(role_locations.items()):
        top_level_domains = sorted({Path(path).parts[0] if len(Path(path).parts) > 1 else "__root__" for path in paths})
        if role not in {"unclassified", "tests"} and len(top_level_domains) > 1:
            redundancies.append(
                {
                    "role": role,
                    "domains": top_level_domains,
                    "reason": "The same project responsibility appears in multiple domains and may be fragmented or redundant.",
                }
            )
    return redundancies


def build_flow_traces(role_locations: dict[str, list[str]], import_graph: dict[str, Any]) -> list[dict[str, Any]]:
    role_by_path: dict[str, list[str]] = {}
    for role, paths in role_locations.items():
        for path in paths:
            role_by_path.setdefault(path, []).append(role)

    traces: list[dict[str, Any]] = []
    adjacency = import_graph["adjacency"]
    starting_points = role_locations.get("routes", [])[:6] or role_locations.get("entrypoint", [])[:4]
    for start in starting_points:
        chain = [start]
        seen = {start}
        cursor = start
        for _ in range(4):
            next_targets = adjacency.get(cursor, [])
            if not next_targets:
                break
            preferred = None
            for target in next_targets:
                roles = set(role_by_path.get(target, []))
                if roles & {"controllers", "services", "orm", "middlewares", "thirdparty"} and target not in seen:
                    preferred = target
                    break
            if not preferred:
                preferred = next((target for target in next_targets if target not in seen), None)
            if not preferred:
                break
            chain.append(preferred)
            seen.add(preferred)
            cursor = preferred
        traces.append(
            {
                "start": start,
                "roles": [sorted(role_by_path.get(path, ["unclassified"])) for path in chain],
                "chain": chain,
            }
        )
    return traces


def build_repository_graph(
    role_locations: dict[str, list[str]],
    import_graph: dict[str, Any],
    flow_traces: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}

    for role, paths in role_locations.items():
        role_node = f"role:{role}"
        nodes[role_node] = {"id": role_node, "type": "role", "label": role}
        for path in paths[:20]:
            file_node = f"file:{path}"
            nodes[file_node] = {"id": file_node, "type": "file", "label": path}
            edges[(role_node, file_node, "contains")] = {"from": role_node, "to": file_node, "relation": "contains"}

    for edge in import_graph["edges"][:200]:
        source = f"file:{edge['from']}"
        target = f"file:{edge['to']}"
        nodes.setdefault(source, {"id": source, "type": "file", "label": edge["from"]})
        nodes.setdefault(target, {"id": target, "type": "file", "label": edge["to"]})
        edges[(source, target, "imports")] = {"from": source, "to": target, "relation": "imports"}

    for trace in flow_traces:
        chain = trace["chain"]
        for source, target in zip(chain, chain[1:]):
            edges[(f"file:{source}", f"file:{target}", "flows_to")] = {
                "from": f"file:{source}",
                "to": f"file:{target}",
                "relation": "flows_to",
            }

    return {
        "nodes": sorted(nodes.values(), key=lambda item: (item["type"], item["label"]))[:200],
        "edges": sorted(edges.values(), key=lambda item: (item["from"], item["to"], item["relation"]))[:400],
    }


def build_recon_findings(profile: dict[str, Any], redundancies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    median_lines = max(1, int(profile.get("medianSourceLines", 0)))
    total_files = int(profile.get("totalSourceFiles", 0))
    dominant_style = profile.get("dominantNamingStyle", "plain")
    domain_counts = profile.get("domainFileCounts", {})

    for item in profile.get("largestFiles", []):
        if item["lines"] >= 450 and (item["lines"] >= median_lines * 2 or total_files <= 3):
            findings.append(
                {
                    "type": "overlong-file",
                    "breakScore": "medium",
                    "path": item["path"],
                    "reason": "File is far larger than the repository median and may hide structural drift or brittle logic.",
                }
            )

    for redundancy in redundancies:
        findings.append(
            {
                "type": "role-fragmentation",
                "breakScore": "low",
                "path": redundancy["domains"][0],
                "reason": redundancy["reason"],
                "metadata": {"role": redundancy["role"], "domains": redundancy["domains"]},
            }
        )

    if profile.get("totalSourceFiles", 0) >= 12 and domain_counts.get("__root__", 0) >= 4:
        findings.append(
            {
                "type": "root-sprawl",
                "breakScore": "low",
                "path": "__root__",
                "reason": "Too many source files live at repository root, which weakens domain separation.",
            }
        )

    naming_outliers = [
        item["path"]
        for item in profile.get("largestFiles", [])
        if detect_naming_style(Path(item["path"]).stem) != dominant_style
    ]
    if dominant_style != "plain" and naming_outliers:
        findings.append(
            {
                "type": "naming-drift",
                "breakScore": "low",
                "path": naming_outliers[0],
                "reason": "Some high-signal files diverge from the dominant repository naming convention.",
            }
        )
    return findings


def load_repository_recon(repo_root: Path) -> dict[str, Any]:
    artifact = repo_root.resolve() / ISSUEAI_DIRNAME / "understanding" / "repository-recon.json"
    if not artifact.exists():
        return {}
    return json.loads(artifact.read_text())


def load_repository_intent_review_gate(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    state = load_issueai_state(repo_root)
    recon_state = state.get("repositoryRecon", {})
    blockers: list[str] = []
    if not recon_state:
        blockers.append("Repository Recon has not run yet.")
    return {
        "ready": not blockers,
        "blockers": blockers,
        "repositoryRecon": recon_state,
    }


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
    language_focus = build_language_focus(profile, local_signals)

    understanding = {
        "capturedAt": utc_now(),
        "repository": repository_label,
        "repoRoot": str(repo_root),
        "reviewMode": review_mode,
        "scope": scope or ".",
        "diffTarget": diff_target or None,
        "purpose": purpose_hint or "Repository Recon before Repository Intent Review and Issue Hunt",
        "entrypoints": entrypoints,
        "entrypointStrategy": entrypoint_strategy,
        "applicationMap": {
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
    state["repositoryRecon"] = {
        "updatedAt": utc_now(),
        "reviewMode": review_mode,
        "snapshotPath": f"{ISSUEAI_DIRNAME}/understanding/repository-recon.json",
        "graphPath": f"{ISSUEAI_DIRNAME}/graphs/repository-recon-graph.json",
        "findingsPath": f"{ISSUEAI_DIRNAME}/findings/repository-recon-findings.json",
        "roleCount": len(role_locations),
        "flowTraceCount": len(flow_traces),
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
