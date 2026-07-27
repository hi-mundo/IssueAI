#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

EXCLUDED_ROOTS = {
    ".git", ".github", "docs", "doc", "test", "tests", "testing", "fixtures",
    "examples", "example", "bench", "benchmark", "vendor", "third_party", "deps", "test-data",
    "node_modules", "dist", "build",
}
GENERIC_ROOTS = {"src", "lib", "app", "pkg", "cmd", "core", "runtime", "server", "client", "internal", "python", "modules"}
DEPRIORITIZED_SEGMENTS = {
    "test", "tests", "testing", "fixtures", "examples", "example", "docs", "doc",
    "tools", "scripts", "bench", "benchmark", "misc", "distutils", "idlelib",
    "msilib", "tkinter", "site-packages", "__phello__",
}
DEPRIORITIZED_RUNTIME_SURFACES = {
    "encodings", "distutils", "idlelib", "lib2to3", "test", "tests", "tkinter",
    "turtledemo", "msilib", "ensurepip", "pydoc_data",
}
PUBLIC_SURFACE_HINTS = {
    "api", "asyncio", "http", "http2", "server", "client", "stream", "streams",
    "session", "state", "cache", "plugin", "plugins", "adapter", "adapters",
    "backend", "protocol", "parser", "runtime", "core", "server", "dmypy",
    "f2py", "_core", "typing", "urllib", "logging", "multiprocessing",
}


def _read_text(path: Path, limit: int = 4000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _first_sentence(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)
    return parts[0][:240]


def _find_readme(root: Path) -> tuple[str, list[str]]:
    for name in ("README.md", "README.rst", "README.txt", "readme.md"):
        path = root / name
        if path.exists():
            text = _read_text(path)
            lines = [line.strip("# ").strip() for line in text.splitlines() if line.strip()]
            heading = lines[0] if lines else root.name
            body = "\n".join(lines[1:12])
            purpose = _first_sentence(body) or f"{heading} runtime or library behavior."
            return purpose, [name]
    return "Repository behavior reconstructed from manifests and source layout.", []


def _detect_stack(root: Path, normalized: dict) -> dict:
    languages = Counter(
        entry.get("language")
        for entry in normalized.get("files", [])
        if entry.get("kind") == "source" and not entry.get("vendor") and not entry.get("generated")
    )
    runtimes, frameworks, libraries, integrations = set(), set(), set(), set()
    manifest_files = {
        "package.json": ("node.js", None),
        "pyproject.toml": ("python", None),
        "setup.py": ("python", None),
        "requirements.txt": ("python", None),
        "go.mod": ("go", None),
        "Cargo.toml": ("rust", None),
        "Gemfile": ("ruby", None),
        "composer.json": ("php", None),
    }
    for filename, (runtime, _) in manifest_files.items():
        if (root / filename).exists():
            if runtime:
                runtimes.add(runtime)
    for path in ("package.json", "pyproject.toml", "setup.py", "go.mod", "Cargo.toml", "Gemfile", "composer.json"):
        text = _read_text(root / path)
        low = text.lower()
        for token in ("django", "flask", "fastapi", "aiohttp", "pytest", "sqlalchemy", "click", "requests", "urllib3", "react", "express", "kubernetes", "terraform", "rails", "laravel"):
            if token in low:
                if token in {"react", "express", "django", "flask", "fastapi", "aiohttp", "rails", "laravel"}:
                    frameworks.add(token)
                else:
                    libraries.add(token)
        for token in ("postgres", "mysql", "redis", "docker", "kubernetes", "grpc", "http", "aws", "gcp", "azure"):
            if token in low:
                integrations.add(token)
    return {
        "languages": [name for name, _ in languages.most_common(8) if name],
        "runtimes": sorted(runtimes),
        "frameworks": sorted(frameworks),
        "libraries": sorted(libraries),
        "integrations": sorted(integrations),
    }


def _top_roots(normalized: dict, limit: int = 6) -> list[str]:
    roots = Counter()
    for entry in normalized.get("files", []):
        if entry.get("kind") != "source" or entry.get("vendor") or entry.get("generated"):
            continue
        path = str(entry.get("path", ""))
        top = path.split("/", 1)[0]
        if not top or top in EXCLUDED_ROOTS or top.startswith("."):
            continue
        roots[top] += 1
    return [name for name, _ in roots.most_common(limit)]


def _source_files(normalized: dict) -> list[str]:
    files: list[str] = []
    for entry in normalized.get("files", []):
        if entry.get("kind") != "source" or entry.get("vendor") or entry.get("generated"):
            continue
        path = str(entry.get("path", "")).strip()
        if not path:
            continue
        if "/" not in path:
            continue
        top = path.split("/", 1)[0]
        if not top or top in EXCLUDED_ROOTS or top.startswith("."):
            continue
        files.append(path)
    return files


def _candidate_surface_prefixes(source_files: list[str]) -> list[tuple[str, int]]:
    counts = Counter()
    package_roots: set[str] = set()
    for path in source_files:
        parts = path.split("/")
        if len(parts) >= 2 and parts[-1] == "__init__.py":
            package_roots.add("/".join(parts[:-1]))
    for path in source_files:
        parts = path.split("/")
        top = parts[0].lower()
        if top in DEPRIORITIZED_SEGMENTS:
            continue
        prefixes = set()
        prefixes.add(parts[0])
        if len(parts) >= 2 and "." not in parts[1]:
            prefixes.add("/".join(parts[:2]))
        if len(parts) >= 3 and parts[0].lower() in GENERIC_ROOTS and "." not in parts[2]:
            prefixes.add("/".join(parts[:3]))
        for prefix in prefixes:
            counts[prefix] += 1
    scored: list[tuple[float, str, int]] = []
    for prefix, count in counts.items():
        parts = prefix.split("/")
        last = parts[-1].lower()
        first = parts[0].lower()
        score = math.log1p(count) * 10.0
        if prefix in package_roots:
            score += 6.0
        if last in PUBLIC_SURFACE_HINTS:
            score += 16.0
        if any(segment.lower() in PUBLIC_SURFACE_HINTS for segment in parts):
            score += 8.0
        if any(segment.lower() in DEPRIORITIZED_SEGMENTS for segment in parts):
            score -= 8.0
        if last in DEPRIORITIZED_RUNTIME_SURFACES:
            score -= 20.0
        if first in GENERIC_ROOTS and len(parts) >= 2:
            score += 2.0
        if len(parts) == 1 and first in GENERIC_ROOTS:
            score -= 3.0
        scored.append((score, prefix, count))
    scored.sort(key=lambda item: (-item[0], -item[2], item[1]))
    deeper_children: dict[str, list[tuple[str, float, int]]] = {}
    for score, prefix, count in scored:
        parts = prefix.split("/")
        if len(parts) >= 2:
            deeper_children.setdefault(parts[0], []).append((prefix, score, count))
    selected: list[tuple[str, int]] = []
    chosen: list[str] = []
    for score, prefix, count in scored:
        parts = prefix.split("/")
        if len(parts) == 1 and parts[0].lower() in GENERIC_ROOTS:
            children = deeper_children.get(parts[0], [])
            if any(child_count >= 8 for _, _, child_count in children):
                continue
        if any(prefix == existing or prefix.startswith(existing + "/") or existing.startswith(prefix + "/") for existing in chosen):
            continue
        chosen.append(prefix)
        selected.append((prefix, count))
        if len(selected) >= 8:
            break
    return selected


def _surface_rows(roots: list[str], source_files: list[str]) -> list[dict]:
    candidate_surfaces = _candidate_surface_prefixes(source_files)
    rows = []
    selected = [prefix for prefix, _ in candidate_surfaces] or roots[:6]
    for index, root in enumerate(selected[:8], start=1):
        rows.append({
            "id": f"surface-{index}",
            "label": root,
            "paths": [root],
            "disposition": "priority" if index <= 5 else "reviewed",
        })
    return rows


def _contracts_from_repo(root: Path, readme_purpose: str, evidence_ids: list[str]) -> list[dict]:
    contracts = []
    if readme_purpose:
        contracts.append({
            "id": "contract-product-purpose",
            "subject": "repository-purpose",
            "promise": readme_purpose,
            "source_ids": evidence_ids or ["repository-map"],
        })
    if (root / "package.json").exists():
        contracts.append({
            "id": "contract-package-entrypoints",
            "subject": "package-manifest",
            "promise": "Published package entrypoints and scripts must match exported behavior and runtime assumptions.",
            "source_ids": ["package.json"],
        })
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        contracts.append({
            "id": "contract-python-public-api",
            "subject": "python-package",
            "promise": "Documented Python API surfaces and runtime package behavior must stay aligned with implementation and edge-case handling.",
            "source_ids": [name for name in ("pyproject.toml", "setup.py") if (root / name).exists()],
        })
    if (root / "go.mod").exists():
        contracts.append({
            "id": "contract-go-module-api",
            "subject": "go-module",
            "promise": "Exported module behavior, versioned packages, and platform/runtime contracts should remain stable across supported environments.",
            "source_ids": ["go.mod"],
        })
    return contracts


def infer_product_understanding(repository: str, repo_root: Path, normalized: dict, repository_map: dict) -> dict:
    purpose, readme_ids = _find_readme(repo_root)
    stack = _detect_stack(repo_root, normalized)
    roots = _top_roots(normalized)
    source_files = _source_files(normalized)
    evidence_ids = readme_ids or ["repository-map"]
    capabilities = []
    features = []
    surface_prefixes = [row["paths"][0] for row in _surface_rows(roots, source_files)]
    for index, root in enumerate(surface_prefixes[:5], start=1):
        cap_id = f"capability-{index}"
        feature_id = f"feature-{index}"
        capabilities.append({"id": cap_id, "name": root, "purpose": f"Primary repository surface rooted in {root}.", "feature_ids": [feature_id]})
        features.append({"id": feature_id, "name": root, "capability_ids": [cap_id], "surfaces": [root]})
    folder_rows = [{"path": root, "role": "primary-source-root"} for root in surface_prefixes[:8]]
    boundaries = [{"from": "public-surface", "to": root, "kind": "implementation-root"} for root in surface_prefixes[:5]]
    modules = [{"id": f"module-{i+1}", "label": root, "paths": [root]} for i, root in enumerate(surface_prefixes[:8])]
    surfaces = _surface_rows(roots, source_files)
    contracts = _contracts_from_repo(repo_root, purpose, evidence_ids)
    open_questions = [] if readme_ids else ["Repository purpose inferred without README; treat product intent confidence as medium."]
    return {
        "repository": repository,
        "product": {
            "name": repository,
            "purpose": purpose,
            "scope": surface_prefixes[:8],
            "capabilities": capabilities,
            "features": features,
        },
        "technology_stack": stack,
        "architecture": {
            "modules": modules,
            "boundaries": boundaries,
            "data_flows": [],
            "integration_points": [{"label": value, "kind": "integration"} for value in stack["integrations"][:8]],
        },
        "organization_patterns": {
            "folders": folder_rows,
            "files": [],
            "naming": [],
            "ownership": [],
        },
        "implementation_tendencies": [],
        "contracts": contracts,
        "surfaces": surfaces,
        "open_questions": open_questions,
        "evidence_ids": evidence_ids,
    }
