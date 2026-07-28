"""Graph and finding helpers for Repository Recon."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from .repository_recon_profile import (
    ENTRYPOINT_PLAIN_STEMS,
    NON_RUNTIME_DOMAINS,
    SOURCE_SUFFIXES,
    detect_naming_style,
    prefer_runtime_paths,
    read_text_safe,
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
        runtime_domains = sorted(
            {
                Path(path).parts[0] if len(Path(path).parts) > 1 else "__root__"
                for path in prefer_runtime_paths(paths)
                if (Path(path).parts[0] if len(Path(path).parts) > 1 else "__root__") not in NON_RUNTIME_DOMAINS
            }
        )
        if role not in {"unclassified", "tests"} and len(runtime_domains) > 1:
            redundancies.append(
                {
                    "role": role,
                    "domains": runtime_domains,
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
    starting_points = prefer_runtime_paths(role_locations.get("routes", [])[:6]) or prefer_runtime_paths(role_locations.get("entrypoint", [])[:4])
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
        for path in prefer_runtime_paths(paths)[:20]:
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
    naming_style_counts = profile.get("namingStyleCounts", {})

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
        and Path(item["path"]).stem not in ENTRYPOINT_PLAIN_STEMS
    ]
    if dominant_style != "plain" and naming_outliers:
        outlier_style = detect_naming_style(Path(naming_outliers[0]).stem)
        if outlier_style == "plain" and int(naming_style_counts.get("plain", 0)) >= 3:
            return findings
        findings.append(
            {
                "type": "naming-drift",
                "breakScore": "low",
                "path": naming_outliers[0],
                "reason": "Some high-signal files diverge from the dominant repository naming convention.",
            }
        )
    return findings
