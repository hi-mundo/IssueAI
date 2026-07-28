"""Profile and structure helpers for Repository Recon."""

from __future__ import annotations

import hashlib
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IGNORED_DIRS = {
    ".git",
    ".issueai",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "vendor",
    "coverage",
}

NON_RUNTIME_DOMAINS = {
    "test",
    "tests",
    "evals",
    "bench",
    "benchmark",
    "benchmarks",
    "doc",
    "docs",
    "example",
    "examples",
    "fixture",
    "fixtures",
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
    "middlewares": {"middleware", "middlewares", "guard", "guards", "auth", "protect", "protection", "filter", "filters"},
    "services": {"service", "services", "usecase", "usecases", "domain", "domains", "logic"},
    "schemas": {"schema", "schemas", "validator", "validators", "dto", "dtos", "type", "types", "model", "models"},
    "orm": {"orm", "db", "database", "migration", "migrations", "store", "stores", "storage", "dao"},
    "thirdparty": {"client", "clients", "integration", "integrations", "provider", "providers", "thirdparty", "sdk"},
    "utils": {"util", "utils", "helper", "helpers", "common", "shared"},
    "tests": {"test", "tests", "spec", "specs"},
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

ENTRYPOINT_PLAIN_STEMS = {"cli", "main", "app", "server", "manage", "index"}

IDENTIFIER_TOKEN_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(parts: list[str]) -> str:
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


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


def split_identifier_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    normalized = re.sub(r"[-_.]+", " ", value)
    for chunk in normalized.split():
        for match in IDENTIFIER_TOKEN_RE.finditer(chunk):
            tokens.add(match.group(0).lower())
    return tokens


def is_non_runtime_path(relative_path: str) -> bool:
    parts = Path(relative_path).parts
    domain = parts[0].lower() if len(parts) > 1 else "__root__"
    return domain in NON_RUNTIME_DOMAINS


def prefer_runtime_paths(paths: list[str]) -> list[str]:
    runtime_paths = [path for path in paths if not is_non_runtime_path(path)]
    return runtime_paths or list(paths)


def classify_path_roles(relative_path: Path) -> list[str]:
    roles = set()
    if relative_path.name.lower() in ENTRYPOINT_FILENAMES:
        roles.add("entrypoint")

    token_pool = set()
    for part in relative_path.parts:
        token_pool.update(split_identifier_tokens(part))

    for role, markers in KNOWN_ROLE_MARKERS.items():
        if token_pool & markers:
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
        "namingStyleCounts": dict(naming_styles),
        "domainChecksums": sorted_domains,
        "structureChecksum": sha256_text(sorted(structure_parts)),
        "organizationChecksum": sha256_text(sorted(organization_parts)),
        "medianSourceLines": median_lines,
        "dominantNamingStyle": dominant_style,
        "largestFiles": [{"path": path, "lines": lines} for path, lines in largest_files],
        "roleLocations": {role: sorted(paths) for role, paths in sorted(role_locations.items())},
    }


def build_language_focus(profile: dict[str, Any], local_signals: tuple[str, ...] | list[str]) -> list[str]:
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
            "startingPoint": prefer_runtime_paths(role_locations["routes"])[0],
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
