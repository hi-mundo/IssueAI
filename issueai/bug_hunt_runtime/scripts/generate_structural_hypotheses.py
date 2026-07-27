#!/usr/bin/env python3
"""Generate bounded source-only hypotheses for an unfamiliar repository.

This is a deterministic prefilter for the model hypothesis phase. It never
reads issue metadata and never claims that a candidate is a finding.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


RULES = {
    "state_reuse": r"\b(cache|incremental|reload|memo|session|invalidate)\b",
    "lifecycle": r"\b(close|cleanup|teardown|eof|stream|redirect|cancel|flush|shutdown|timer|timeout|resource|manager|owner|release|dispose|destroy|finali[sz])\b",
    "precedence": r"\b(setdefault|fallback|environment|override)\b",
    "representation": r"\b(encode|decode|unicode|bytes|version|normalize|canonical)\b",
    "integration": r"\b(backend|adapter|driver|plugin|platform|dependency|subprocess|compat)\b",
    "concurrency": r"\b(thread|lock|async|worker|queue|callback|parallel|atomic)\b",
    "boundary": r"\b(null|none|empty|partial|limit|overflow|truncate|sentinel|invalid)\b",
    "observability": r"\b(retry|fallback|telemetry|silent|health)\b",
    "compatibility": r"\b(compat|platform|windows|linux|macos|legacy|runtime|release|version)\b",
    "performance": r"\b(perf|performance|benchmark|latency|slow|throughput)\b",
}
CANONICAL = {
    "typing": "contract",
    "state": "state_reuse",
    "data_integrity": "state_reuse",
}
GENERIC_PRIMARY = {"boundary", "contract", "precedence", "representation"}

PATH_RULES = {
    "state_reuse": r"cache|increment|reload|session|memo|build",
    "lifecycle": r"stream|response|connector|fixture|teardown|cleanup|close|retry|redirect|timer|timeout|resource|manager|owner|release|dispose|destroy|finali[sz]",
    "precedence": r"config|option|middleware|setting|merge|default|marker",
    "representation": r"parser|parse|version|marker|array|string|encoding|unicode|location|url|path|json|dialect",
    "integration": r"adapter|backend|driver|platform|pipe|network|http|plugin|remote|subprocess|compose|kube|dns",
    "concurrency": r"thread|lock|async|worker|queue|runtime|pool|parallel|atomic",
    "boundary": r"parser|array|bitop|slice|model|marker|exception|core|wrapper|conversion",
    "observability": r"remote|metric|log|health|report|progress|trace",
    "compatibility": r"compat|platform|windows|linux|legacy|runtime|release|version",
    "performance": r"perf|performance|benchmark|latency|slow|throughput",
}

TEMPLATES = {
    "boundary": ("logic", "The boundary preserves required shape and value invariants.", "A partial or malformed input path may violate the boundary invariant.", "Exercise partial, empty, malformed, or oversized input at the concrete boundary."),
    "contract": ("logic", "Values crossing this boundary continue to satisfy the receiving contract.", "A type, schema, or contract-preserving path may accept or emit a shape the downstream consumer does not truly support.", "Cross a type, schema, or internal contract boundary and compare the public promise with consumed behavior."),
    "state_reuse": ("reliability", "Repeated or resumed execution preserves equivalent state and output.", "A cached, resumed, or stale-state path may diverge from the first successful run.", "Repeat the operation after prior state has been created, reused, or invalidated."),
    "lifecycle": ("reliability", "Resources and lifecycle transitions close, flush, cancel, or retry exactly as documented.", "A cleanup, close, retry, or timeout path may leak, duplicate, or stall work.", "Exercise close, cleanup, retry, redirect, timeout, or cancellation after partial progress."),
    "precedence": ("logic", "Explicit authority wins over default, fallback, or inherited configuration.", "A fallback or merge rule may override the explicit value on a rare path.", "Compare explicit input against default, fallback, inherited, or merged state."),
    "representation": ("logic", "Representations round-trip without lossy normalization or identity drift.", "A normalization or conversion path may change meaning, identity, or uniqueness.", "Cross a parse, encode/decode, normalize, path, URL, or version boundary and compare round-trip behavior."),
    "integration": ("reliability", "The contract holds across adapters, backends, plugins, and protocol implementations.", "An alternate backend, adapter, or integration cell may diverge from the default implementation.", "Run the same capability through a non-default adapter, backend, protocol, or dependency cell."),
    "concurrency": ("reliability", "Concurrent or scheduled execution preserves ordering, uniqueness, and liveness.", "An interleaving, callback, queue, or cancellation race may lose, duplicate, or deadlock work.", "Exercise concurrent calls, callbacks, worker scheduling, or cancellation interleavings."),
    "compatibility": ("reliability", "Supported runtimes, platforms, and versions behave equivalently at the boundary.", "A runtime, platform, or dependency-version cell may violate the same contract.", "Compare default environment behavior with an alternate runtime, platform, or version cell."),
    "observability": ("reliability", "Failures cannot look like success and must remain visible through retries and fallbacks.", "A retry, fallback, or error path may swallow or misreport the failure.", "Force an error, fallback, or retry-exhaustion path and verify the failure remains visible."),
}


def canonicalize(name: str) -> str:
    return CANONICAL.get(name, name)


def mechanism_template(name: str) -> tuple[str, str, str, str]:
    return TEMPLATES[canonicalize(name)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--map", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--worklist-limit", type=int, default=300)
    parser.add_argument("--worklist")
    parser.add_argument("--context-input")
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    graph = json.loads(Path(args.map).read_text(encoding="utf-8"))
    candidates = []
    worklist = {}
    contextual_input = {}
    if args.context_input:
        contextual_input = json.loads(Path(args.context_input).read_text(encoding="utf-8"))
    if args.worklist:
        worklist = json.loads(Path(args.worklist).read_text(encoding="utf-8"))
        for priority, row in enumerate(worklist.get("rows", [])[: args.worklist_limit]):
            candidates.append((row.get("source_signal_score", 0), 1, row.get("location", ""), row.get("map_node_id", ""), [row.get("category", "boundary")], row))
    else:
        for node in graph.get("nodes", []):
            location = node.get("location", "")
            path = root / location
            if not path.is_file():
                continue
            try:
                content = path.read_bytes()[:16384].decode("utf-8", errors="replace")
            except OSError:
                continue
            if Path(location).suffix.lower() in {".md", ".json", ".yaml", ".yml"}:
                continue
            path_counts = {name: len(re.findall(pattern, location, re.IGNORECASE)) for name, pattern in PATH_RULES.items()}
            content_counts = {name: len(re.findall(pattern, content, re.IGNORECASE)) for name, pattern in RULES.items()}
            counts = {name: path_counts.get(name, 0) * 5 + content_counts.get(name, 0) for name in RULES}
            mechanisms = [name for name, count in counts.items() if count]
            if not mechanisms:
                continue
            score = max(counts.values())
            ranked = sorted(mechanisms, key=lambda name: (-counts[name], name))
            candidates.append((score, len(mechanisms), location, node["id"], ranked, None))
    if not args.worklist:
        candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
    if args.context_input:
        contextual_rows = contextual_input.get("deep_hypothesis_input", [])
        category_aliases = {"state_reuse": "state", "typing": "contract"}
        enriched = []
        for candidate in candidates:
            route = candidate[5]
            mechanism = candidate[4][0]
            contextual_mechanism = category_aliases.get(mechanism, mechanism)
            matches = [row for row in contextual_rows if contextual_mechanism in row.get("mechanisms", []) or contextual_mechanism in row.get("matched_local_mechanisms", [])]
            context_score = max((row.get("score", 0) for row in matches), default=0)
            location_text = f"{candidate[2]} {route.get('symbol','') if route else ''}".lower()
            keyword_score = max((sum(1 for keyword in row.get("keywords", []) if keyword in location_text) for row in matches), default=0)
            route = dict(route or {})
            route["context_score"] = context_score
            route["keyword_score"] = keyword_score
            route["context_matches"] = matches[:3]
            enriched.append((*candidate[:5], route))
        # Historical examples enrich an already-local candidate set; they must
        # not push a concrete high-risk ownership or contract surface out of a
        # bounded result solely because an unrelated path has better corpus
        # keyword overlap.
        candidates = sorted(enriched, key=lambda item: (-bool(item[5].get("surface_priority")), -item[0], -item[5].get("keyword_score", 0), -item[5].get("context_score", 0), -bool(item[5].get("history_seeded")), item[2]))
        selected = []
        category_counts = {}
        for candidate in candidates:
            category = candidate[4][0]
            surface_priority = bool(candidate[5].get("surface_priority"))
            if not surface_priority and category_counts.get(category, 0) >= 50:
                continue
            selected.append(candidate)
            category_counts[category] = category_counts.get(category, 0) + 1
            if len(selected) >= args.limit:
                break
        candidates = selected
    hypotheses = []
    for priority, (_, _, location, node_id, mechanisms, route) in enumerate(candidates[: args.limit]):
        primary = canonicalize(mechanisms[0])
        all_contextual_rows = contextual_input.get("deep_hypothesis_input", [])
        contextual_rows = [item for item in all_contextual_rows if primary in [canonicalize(value) for value in item.get("mechanisms", [])] or any(primary in value for value in item.get("surfaces", []))][:3]
        if primary in GENERIC_PRIMARY and not contextual_rows:
            contextual_rows = all_contextual_rows[:3]
        contextual_rows += [item for item in (route.get("context_matches", []) if route else []) if item not in contextual_rows]
        contextual_examples = [item.get("issue_example_ids", []) for item in contextual_rows]
        contextual_evidence = [evidence for item in contextual_rows for evidence in item.get("evidence", [])]
        is_config_surface = bool(re.search(r"(^|/)config(?:/|\.)|/(exporter|receiver|processor)/.+config\.", location, re.I))
        category = primary
        intent_layer, expected_behavior, suspected_behavior, trigger = mechanism_template(category)
        hypotheses.append({
            "id": "h-struct-" + hashlib.sha1(f"{location}:{category}".encode()).hexdigest()[:12],
            "feature_id": "repository-structure",
            "map_node_ids": [node_id],
            "category": category,
            "intent_layer": "reliability" if category in {"state_reuse", "lifecycle", "concurrency", "observability", "integration", "compatibility"} else intent_layer,
            "expected_behavior": "Configuration rejects semantically invalid values before runtime construction." if is_config_surface else (route.get("oracle") if route else expected_behavior),
            "suspected_behavior": "A missing range, enum, or cross-field check may permit an invalid configuration that fails later." if is_config_surface else suspected_behavior,
            "trigger": "negative, zero, malformed, or incompatible configuration value" if is_config_surface else (route.get("escape_cell", "") if route else trigger),
            "preconditions": ["The node is a source file in the normalized repository map.", f"Observed mechanism signals: {', '.join(sorted({canonicalize(value) for value in mechanisms}))}.", "The contract anchor remains inferred until closed by the model/reference pass."],
            "evidence_initial": [f"repository-map:{node_id}", f"location:{location}", "source-only-structural-signal"] + (route.get("history_evidence", []) if route else []) + contextual_evidence,
            "reference_ids": [],
            "candidate_locations": [route.get("candidate_location", location)] if route else [location],
            "validation_method": "Generate and execute a smallest direct probe after human/model review; not executed in hypothesis phase.",
            "initial_confidence": 0.35,
            "priority": priority,
            "inferred": True,
            "route_anchors": ({key: route.get(key) for key in ("contract_anchor", "boundary_anchor", "escape_cell", "oracle", "missing_coverage", "negative_controls", "history_seeded", "history_seed_ids", "history_evidence", "context_score", "surface_priority")} if route else {}),
            "worklist_id": worklist.get("worklist_id") if args.worklist else None,
            "symbol": route.get("symbol") if route else None,
            "line": route.get("line") if route else None,
            "context_id": contextual_input.get("context_id") if args.context_input else None,
            "contextual_examples": contextual_examples,
        })
    Path(args.output).write_text(json.dumps({"mode": "source-only-escape-cell" if args.worklist else "source-only", "hypotheses": hypotheses, "worklist_id": worklist.get("worklist_id") if args.worklist else None}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "hypotheses": len(hypotheses), "output": args.output}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
