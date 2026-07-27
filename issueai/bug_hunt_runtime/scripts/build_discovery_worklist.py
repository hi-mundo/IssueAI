#!/usr/bin/env python3
"""Build a balanced, source-only escape-cell worklist for hypothesis discovery.

This is routing evidence, not a finding detector. It deliberately emits
several independent cells per concrete source node and rotates mechanisms so a
large repository cannot be dominated by one keyword family.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


MECHANISMS = (
    "boundary", "state_reuse", "lifecycle", "precedence", "representation",
    "integration", "concurrency", "compatibility", "observability", "typing",
)
MAX_SURFACE_SHARE = 0.4

SIGNALS = {
    "boundary": (r"null|none|empty|partial|limit|overflow|truncate|sentinel|invalid|parse|schema|request|handler", "partial or malformed input"),
    "state_reuse": (r"cache|memo|session|reload|increment|invalidate|refresh|snapshot|daemon|watch|incremental|typestate", "second run, reload, rollback, or stale state"),
    "lifecycle": (r"close|cleanup|teardown|eof|stream|cancel|flush|shutdown|retry|redirect|transaction|timer|timeout|resource|manager|owner|release|dispose|destroy|finali[sz]", "partial completion, cancellation, retry, natural timer completion, ownership release, or cleanup"),
    "precedence": (r"setdefault|fallback|environment|override|default|config|option|merge|priority", "explicit value versus default, fallback, or inherited value"),
    "representation": (r"encode|decode|unicode|bytes|version|normalize|canonical|path|url|identity|label|key", "lossy conversion, normalization, collision, or shape change"),
    "integration": (r"backend|adapter|driver|plugin|platform|dependency|subprocess|compat|remote|http2?|rpc|override|bridge|shim|f2py", "alternate backend, adapter, dependency, or protocol implementation"),
    "concurrency": (r"thread|lock|async|worker|queue|callback|parallel|atomic|pool|race|signal", "interleaving, cancellation race, duplicate work, or lost event"),
    "compatibility": (r"compat|platform|windows|linux|macos|legacy|runtime|release|version|feature", "runtime, platform, dependency, or version cell"),
    "observability": (r"retry|fallback|telemetry|metric|log|health|silent|swallow|catch|except|error|debug|trace|report|warn|diagnostic|ipc", "failure path, retry exhaustion, fallback, or missing signal"),
    "typing": (r"type|schema|optional|null|none|generic|cast|convert|container|array|object|model", "sentinel, optional value, container shape, or internal type boundary"),
}

PATH_HINTS = re.compile(r"(^|/)(src|lib|internal|pkg|app|cmd|core|runtime|api|server|client|parser|protocol|adapter|backend|driver|worker|queue|cache|session|stream|model|schema|config|exporter|receiver|processor)(/|$)", re.I)
TEST_HINT = re.compile(r"(^|/)(test|tests|spec|specs|fixture|fixtures|mock|mocks|fake|fakes)(/|$)", re.I)
LOW_SIGNAL_HINT = re.compile(r"(^|/)(bench|benchmark|benchmarks|example|examples|sample|samples|docs|doc|test-data)(/|$)", re.I)
VENDORED_HINT = re.compile(r"(^|/)(deps|vendor|vendors|third_party|third-party|external|extern)(/|$)", re.I)
FIRST_PARTY_HINT = re.compile(r"(^|/)(lib|src|pkg|app|internal|core|runtime|server|client|mypy|numpy|Lib|Python|Modules)(/|$)", re.I)
RESOURCE_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".rst"}
TEST_FILE_HINT = re.compile(r"(?:^|[._-])(test|tests|spec|specs)(?:[._-]|$)|_test\.[a-z0-9]+$", re.I)
# Preserve compound ownership/contract surfaces (AgentHost, resource-managers,
# strided_slice_op) in a bounded worklist.  These are generic risk domains.
SURFACE_HINT = re.compile(r"exporter|receiver|processor|sandbox|agent|session|compiler|kernel|slice|resource", re.I)
SURFACE_TERMS = ("exporter", "receiver", "processor", "sandbox", "agent", "session", "compiler", "kernel", "slice", "resource")


def read_source(root: Path, location: str) -> str:
    try:
        return (root / location).read_bytes()[:32768].decode("utf-8", errors="replace")
    except OSError:
        return ""


def concrete_symbol(content: str, mechanism: str) -> tuple[str, int]:
    pattern = re.compile(r"^\s*(?:async\s+)?(?:def|func|function|fn|class|struct|impl|pub\s+fn|export\s+function|(?:public|private|protected)\s+(?:static\s+)?[\w<>\[\]]+\s+)\s*([A-Za-z_][\w:<>]*)", re.I)
    signal = re.compile(SIGNALS[mechanism][0], re.I)
    fallback = ("module-scope", 1)
    for line_number, line in enumerate(content.splitlines(), 1):
        if signal.search(line):
            for match in pattern.finditer(line):
                return match.group(1), line_number
    for line_number, line in enumerate(content.splitlines(), 1):
        match = pattern.search(line)
        if match:
            return match.group(1), line_number
    return fallback


def route_for(location: str, content: str) -> list[tuple[int, str]]:
    haystack = f"{location}\n{content}"
    scores = []
    for mechanism, (pattern, _) in SIGNALS.items():
        path_score = len(re.findall(pattern, location, re.I))
        content_score = len(re.findall(pattern, content, re.I))
        boundary_bonus = 2 if PATH_HINTS.search(location) else 0
        ownership_bonus = 6 if mechanism == "lifecycle" and re.search(r"sandbox|resource.?manager|timer|timeout|owner|lifecycle", location, re.I) else 0
        contract_surface_bonus = 4 if mechanism in {"boundary", "typing", "integration"} and re.search(r"(^|/)(config|exporter|receiver|processor)(/|$)|config\.(go|ts|js|py)$", location, re.I) else 0
        surface_bonus = 3 * sum(term in location.lower() for term in SURFACE_TERMS)
        first_party_bonus = 4 if FIRST_PARTY_HINT.search(location) else 0
        vendored_penalty = 8 if VENDORED_HINT.search(location) else 0
        scores.append((path_score * 6 + content_score + boundary_bonus + ownership_bonus + contract_surface_bonus + surface_bonus + first_party_bonus - vendored_penalty, mechanism))
    routed = sorted((score, name) for score, name in scores if score > 0)[::-1]
    if not routed and re.search(r"(^|/)(config|exporter|receiver|processor)(/|$)|config\.(go|ts|js|py)$", location, re.I):
        routed = [(3, "typing"), (2, "integration"), (1, "boundary")]
    return routed


def cell_for(mechanism: str) -> tuple[str, str, str, str]:
    rare = SIGNALS[mechanism][1]
    cells = {
        "boundary": ("public input or parser boundary", rare, "shape and required-field invariant", "boundary-pass"),
        "state_reuse": ("call or prior state", rare, "equivalent input produces equivalent state/output", "transition-pass"),
        "lifecycle": ("stream, resource, or operation owner", rare, "every acquired resource is finalized exactly once", "transition-pass"),
        "precedence": ("multiple authorities for one value", rare, "explicit authority is preserved over fallback", "contract-pass"),
        "representation": ("value crossing a representation boundary", rare, "round-trip identity and uniqueness are preserved", "boundary-pass"),
        "integration": ("adapter, plugin, backend, or protocol edge", rare, "the contract holds for every supported implementation", "adapter-pass"),
        "concurrency": ("shared state or scheduled callback", rare, "no lost, duplicated, reordered, or deadlocked operation", "concurrency-pass"),
        "compatibility": ("runtime, platform, or dependency boundary", rare, "supported environment behavior remains equivalent", "compatibility-pass"),
        "observability": ("failure, retry, fallback, or telemetry edge", rare, "a failed operation cannot appear successful silently", "observability-pass"),
        "typing": ("internal type, schema, or optional-value boundary", rare, "values conform to the receiving contract on every caller path", "contract-pass"),
    }
    return cells[mechanism]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--map", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=1200)
    parser.add_argument("--cells-per-node", type=int, default=3)
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    graph = json.loads(Path(args.map).read_text(encoding="utf-8"))
    buckets: dict[str, list[dict]] = defaultdict(list)
    for node in graph.get("nodes", []):
        location = node.get("location", "")
        if not location or Path(location).suffix.lower() in RESOURCE_SUFFIXES or TEST_HINT.search(location) or TEST_FILE_HINT.search(Path(location).name) or LOW_SIGNAL_HINT.search(location):
            continue
        content = read_source(root, location)
        if not content:
            continue
        routes = route_for(location, content)[: max(1, args.cells_per_node)]
        for score, mechanism in routes:
            source, rare, oracle, pass_name = cell_for(mechanism)
            symbol, line = concrete_symbol(content, mechanism)
            digest = hashlib.sha1(f"{node.get('id')}:{mechanism}".encode()).hexdigest()[:14]
            buckets[mechanism].append({
                "id": f"cell-{digest}",
                "map_node_id": node["id"],
                "location": location,
                "symbol": symbol,
                "line": line,
                "candidate_location": f"{location}:{line} ({symbol})",
                "category": mechanism,
                "discovery_pass": pass_name,
                "source": source,
                "transformation": "Recover the concrete parse, normalize, merge, delegate, schedule, or cleanup step from the symbol and callers.",
                "control": "Locate the exact guard, branch, default, lock, validator, retry, or cleanup decision.",
                "state_or_resource": "Enumerate the cache, stream, file, worker, transaction, derived value, or shared state affected.",
                "effect": "Compare returned value, exception, persisted state, emitted event, resource state, or user-visible result.",
                "contract_anchor": "inferred: recover from public API, type, schema, documentation, caller, or focused test",
                "boundary_anchor": f"{location}:{line} ({symbol}): concrete source node and boundary signals={score}",
                "escape_cell": rare,
                "oracle": oracle,
                "missing_coverage": "No focused test was counted for this exact rare cell until the test-gap pass proves otherwise.",
                "negative_controls": ["common path", "nearest passing sibling", "single-run or sequential case"],
                "source_signal_score": score,
                "surface_priority": bool(SURFACE_HINT.search(location)),
                "status": "route-only",
            })

    for mechanism in MECHANISMS:
        buckets[mechanism].sort(key=lambda row: (-row.get("source_signal_score", 0), row.get("location", ""), row.get("line", 0)))
    rows = []
    reserved_routes = set()
    reserved_mechanism_counts: dict[str, int] = defaultdict(int)
    surface_limit = max(1, int(args.limit * MAX_SURFACE_SHARE))
    per_mechanism_surface_cap = max(2, surface_limit // max(1, len(MECHANISMS)))
    surface_rows = sorted(
        (row for bucket in buckets.values() for row in bucket if row.get("surface_priority")),
        key=lambda row: (-row.get("source_signal_score", 0), row.get("location", ""), row.get("category", "")),
    )
    for row in surface_rows:
        route_key = (row["location"], row["category"])
        if route_key not in reserved_routes:
            if len(rows) >= surface_limit:
                break
            if reserved_mechanism_counts[row["category"]] >= per_mechanism_surface_cap:
                continue
            rows.append(row)
            reserved_routes.add(route_key)
            reserved_mechanism_counts[row["category"]] += 1
    mechanism_index = 0
    while len(rows) < args.limit and any(buckets.values()):
        mechanism = MECHANISMS[mechanism_index % len(MECHANISMS)]
        if buckets[mechanism]:
            candidate = buckets[mechanism].pop(0)
            route_key = (candidate.get("location"), candidate.get("category"))
            if route_key not in reserved_routes:
                rows.append(candidate)
                reserved_routes.add(route_key)
        mechanism_index += 1
        if mechanism_index > len(MECHANISMS) * (args.limit + 1):
            break
    result = {
        "mode": "source-only-escape-cell-worklist",
        "worklist_id": "wl-" + hashlib.sha1(str(root).encode()).hexdigest()[:12],
        "repository": str(root),
        "bounded": True,
        "rows": rows,
        "coverage": {
            "total_rows": len(rows),
            "mechanisms": {name: sum(row["category"] == name for row in rows) for name in MECHANISMS},
            "uncovered_mechanisms": [name for name in MECHANISMS if not any(row["category"] == name for row in rows)],
        },
        "discovery_only": True,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "rows": len(rows), "mechanisms": result["coverage"]["mechanisms"], "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
