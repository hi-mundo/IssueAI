#!/usr/bin/env python3
"""Turn one intelligent-plan shard into concrete, probe-ready candidate tuples."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

DECLARATION = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:(?:default\s+)?function|class|def|func|fn|struct|interface|type)\s+([A-Za-z_][\w:$]*)",
    re.I,
)
METHOD = re.compile(
    r"^\s*(?:public\s+|private\s+|protected\s+|static\s+|async\s+)*(?:get\s+|set\s+)?([A-Za-z_][\w$]*)\s*\(",
    re.I,
)
CONST_FUNCTION = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_][\w$]*)\s*=>",
    re.I,
)
CONTROL = re.compile(r"\b(if|else|switch|case|guard|try|catch|finally|throw|return)\b")
STATE = re.compile(r"\b(cache|session|state|resource|resources|timeout|interval|queue|map|set|store|snapshot|memo)\b", re.I)
EFFECT = re.compile(r"\b(return|throw|emit|dispatch|persist|write|send|clear\w*|close\w*|cleanup|destroy\w*|remove\w*|push|apply)\b", re.I)
CALL = re.compile(r"\b([A-Za-z_][\w$]*)\s*\(")
HINT = {
    "lifecycle": r"close|cleanup|cancel|retry|timeout|timer|resource|release|dispose|destroy|remove|clear",
    "state": r"cache|session|reload|restart|snapshot|state|memo|store|reuse|stale|invalidate|refresh",
    "state_reuse": r"cache|session|reload|restart|snapshot|state|memo|store|reuse|stale|invalidate|refresh",
    "boundary": r"null|none|empty|invalid|parse|limit|undefined|optional",
    "contract": r"type|schema|validate|optional|interface|assert",
    "precedence": r"default|fallback|override|config|merge|priority",
    "representation": r"encode|decode|normalize|path|url|canonical|serialize|parse",
    "concurrency": r"async|thread|lock|queue|worker|await|race|parallel",
    "integration": r"adapter|backend|driver|plugin|http|rpc|request|response",
    "compatibility": r"compat|platform|windows|linux|macos|legacy|runtime|release|version|feature|dependency",
    "observability": r"log|metric|telemetry|fallback|health|trace",
    "data_integrity": r"transaction|atomic|rollback|persist|duplicate|ordering|commit",
}
SOURCE_HINT = {
    "lifecycle": r"setInterval|setTimeout|create|add|open|start|schedule|register",
    "state": r"set|store|cache|memo|snapshot|session|reuse|refresh|invalidate",
    "state_reuse": r"set|store|cache|memo|snapshot|session|reuse|refresh|invalidate",
    "boundary": r"parse|decode|validate|guard|coerce|assert",
    "contract": r"validate|assert|schema|type|interface",
    "precedence": r"default|fallback|override|merge|priority|config",
    "representation": r"encode|decode|normalize|serialize|parse",
    "concurrency": r"await|enqueue|queue|spawn|dispatch|lock",
    "integration": r"request|response|connect|send|adapter|client|server",
    "compatibility": r"platform|runtime|version|feature|legacy|compat",
    "observability": r"log|metric|trace|telemetry|record",
    "data_integrity": r"persist|commit|rollback|write|dedupe",
}
EFFECT_HINT = {
    "lifecycle": r"clear\w*|close\w*|cleanup|destroy\w*|dispose|remove\w*|release|cancel",
    "state": r"store|cache|reload|reset|clear|invalidate|refresh|return",
    "state_reuse": r"store|cache|reload|reset|clear|invalidate|refresh|return",
    "boundary": r"throw|return|assert|reject",
    "contract": r"throw|return|assert|validate",
    "precedence": r"return|override|fallback|default",
    "representation": r"return|encode|decode|normalize",
    "concurrency": r"await|dispatch|resolve|reject|unlock",
    "integration": r"send|request|response|connect|close",
    "compatibility": r"return|fallback|version|feature|platform|runtime",
    "observability": r"log|record|emit|trace|report",
    "data_integrity": r"commit|rollback|persist|write",
}
SYMBOL_BONUS = {
    "lifecycle": ("manager", "timeout", "interval", "resource", "destroy", "remove", "clear", "dispose"),
    "state": ("cache", "session", "state", "store", "snapshot", "memo", "refresh", "invalidate"),
    "state_reuse": ("cache", "session", "state", "store", "snapshot", "memo", "refresh", "invalidate"),
    "boundary": ("parse", "decode", "validate", "guard", "assert"),
    "contract": ("schema", "type", "validate", "assert", "interface"),
    "precedence": ("config", "merge", "override", "default", "fallback"),
    "representation": ("normalize", "encode", "decode", "path", "url", "serialize"),
    "concurrency": ("queue", "worker", "async", "parallel", "lock"),
    "integration": ("adapter", "client", "server", "request", "response", "plugin"),
    "compatibility": ("platform", "runtime", "version", "legacy", "compat"),
    "observability": ("log", "metric", "trace", "telemetry"),
    "data_integrity": ("transaction", "persist", "commit", "rollback"),
}
GENERIC_NESTED_SYMBOLS = ("wrapped", "callback", "handler", "inner", "helper")
ROW_KIND_MECHANISM = {
    "root_control": None,
    "owner_transition": "state_reuse",
    "concrete_instance": "integration",
    "boundary_contract": "contract",
    "failure_signal": "observability",
}


def declarations(lines: list[str]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    pending_class: dict[str, object] | None = None
    depth = 0
    for index, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped:
            depth += raw.count("{") - raw.count("}")
            continue
        symbol = None
        kind = None
        match = DECLARATION.match(raw) or CONST_FUNCTION.match(raw)
        if match:
            symbol = match.group(1)
            kind = "declaration"
            pending_class = results[-1] if results and results[-1].get("kind") == "class" and results[-1]["end"] >= index else None
        else:
            class_match = re.match(r"^\s*(?:export\s+)?class\s+([A-Za-z_][\w$]*)", raw)
            if class_match:
                symbol = class_match.group(1)
                kind = "class"
                pending_class = None
            elif pending_class:
                method_match = METHOD.match(raw)
                if method_match and not stripped.startswith(("if ", "for ", "while ", "switch ", "catch ")):
                    symbol = f"{pending_class['symbol']}.{method_match.group(1)}"
                    kind = "method"
        if symbol:
            results.append({"symbol": symbol, "start": index, "end": len(lines) - 1, "kind": kind or "declaration", "depth": max(depth, 0)})
            if kind == "class":
                pending_class = results[-1]
        depth += raw.count("{") - raw.count("}")
        if stripped.startswith("}"):
            pending_class = None
    for idx, block in enumerate(results):
        next_start = results[idx + 1]["start"] if idx + 1 < len(results) else len(lines)
        block["end"] = max(int(block["start"]), int(next_start) - 1)
    return results


def line_hits(lines: list[str], pattern: re.Pattern[str]) -> list[int]:
    return [index for index, value in enumerate(lines) if pattern.search(value)]


def block_score(
    block: dict[str, object],
    lines: list[str],
    rel_path: str,
    mechanism: str,
) -> tuple[int, dict[str, list[int]]]:
    start = int(block["start"])
    end = int(block["end"])
    block_lines = lines[start : end + 1]
    text = "\n".join(block_lines)
    signal = re.compile(HINT[mechanism], re.I)
    signal_hits = line_hits(block_lines, signal)
    control_hits = line_hits(block_lines, CONTROL)
    state_hits = line_hits(block_lines, STATE)
    effect_hits = line_hits(block_lines, EFFECT)
    score = len(signal_hits) * 5 + len(control_hits) * 2 + len(state_hits) * 2 + len(effect_hits) * 2
    symbol_name = str(block["symbol"]).lower()
    for token in SYMBOL_BONUS.get(mechanism, ()):
        if token in symbol_name:
            score += 6
    if mechanism in rel_path.lower():
        score += 2
    if symbol_name in rel_path.lower():
        score += 3
    if str(block["kind"]) == "method":
        score += 1
    if any(token in symbol_name for token in GENERIC_NESTED_SYMBOLS):
        score -= 12
    score -= int(block.get("depth", 0)) * 6
    return score, {
        "signal": [start + value for value in signal_hits],
        "control": [start + value for value in control_hits],
        "state": [start + value for value in state_hits],
        "effect": [start + value for value in effect_hits],
    }


def choose_block(lines: list[str], rel_path: str, mechanism: str) -> tuple[dict[str, object], dict[str, list[int]]]:
    blocks = declarations(lines)
    if not blocks:
        return {"symbol": "module-scope", "start": 0, "end": max(len(lines) - 1, 0), "kind": "module"}, {"signal": [], "control": [], "state": [], "effect": []}
    ranked: list[tuple[int, int, dict[str, object], dict[str, list[int]]]] = []
    for block in blocks:
        score, evidence = block_score(block, lines, rel_path, mechanism)
        ranked.append((score, len(evidence["signal"]), block, evidence))
    ranked.sort(
        key=lambda item: (
            item[0],
            item[1],
            -int(item[2]["start"]),
            -len(str(item[2]["symbol"])),
        ),
        reverse=True,
    )
    best = ranked[0]
    return best[2], best[3]


def choose_block_for_row_kind(
    lines: list[str],
    rel_path: str,
    mechanism: str,
    row_kind: str,
) -> tuple[dict[str, object], dict[str, list[int]], str]:
    preferred_mechanism = ROW_KIND_MECHANISM.get(row_kind) or mechanism
    block, evidence = choose_block(lines, rel_path, preferred_mechanism)
    if row_kind == "concrete_instance" and str(block.get("symbol", "")) == "module-scope":
        block, evidence = choose_block(lines, rel_path, mechanism)
        preferred_mechanism = mechanism
    return block, evidence, preferred_mechanism


def anchor(lines: list[str], candidates: list[int], fallback: int) -> int:
    return candidates[0] if candidates else fallback


def snippet(lines: list[str], index: int) -> str:
    if not lines:
        return ""
    value = lines[max(0, min(index, len(lines) - 1))].strip()
    return re.sub(r"\s+", " ", value)[:180]


def caller_names(lines: list[str], start: int, end: int) -> list[str]:
    names: list[str] = []
    for raw in lines[start : end + 1]:
        for match in CALL.findall(raw):
            if match not in names and match not in {"if", "for", "while", "switch", "return"}:
                names.append(match)
    return names[:4]


def local_hits(lines: list[str], start: int, end: int, pattern: str) -> list[int]:
    compiled = re.compile(pattern, re.I)
    if not lines:
        return []
    upper = min(end, len(lines) - 1)
    lower = max(0, min(start, upper))
    return [index for index in range(lower, upper + 1) if compiled.search(lines[index])]


def source_line_score(line: str, mechanism: str) -> int:
    score = 0
    lower = line.strip().lower()
    if not lower:
        return -100
    if lower.startswith("//") or lower.startswith("*"):
        score -= 4
    if "import " in lower:
        score -= 10
    if re.search(SOURCE_HINT.get(mechanism, HINT[mechanism]), line, re.I):
        score += 5
    if CONTROL.search(line):
        score += 1
    if STATE.search(line):
        score += 2
    if EFFECT.search(line):
        score += 2
    if CALL.search(line):
        score += 3
    if "=>" in line or line.rstrip().endswith("{"):
        score -= 1
    return score


def choose_source_line(lines: list[str], start: int, end: int, mechanism: str, fallback: int) -> int:
    if not lines:
        return fallback
    upper = min(end, len(lines) - 1)
    lower = max(0, min(start, upper))
    ranked = sorted(
        ((source_line_score(lines[index], mechanism), index) for index in range(lower, upper + 1)),
        key=lambda item: (item[0], -item[1]),
        reverse=True,
    )
    return ranked[0][1] if ranked and ranked[0][0] > -100 else fallback


def choose_effect_line(lines: list[str], start: int, end: int, mechanism: str, fallback: int) -> int:
    if not lines:
        return fallback
    upper = min(end, len(lines) - 1)
    lower = max(0, min(start, upper))
    ranked: list[tuple[int, int]] = []
    preferred_pattern = re.compile(EFFECT_HINT.get(mechanism, EFFECT.pattern), re.I)
    for index in range(lower, upper + 1):
        line = lines[index]
        score = -100
        if preferred_pattern.search(line) or EFFECT.search(line):
            score = 0
            lower = line.strip().lower()
            if lower.startswith("//") or lower.startswith("*"):
                score -= 4
            if "import " in lower:
                score -= 10
            if preferred_pattern.search(line):
                score += 5
            if EFFECT.search(line):
                score += 3
            if CALL.search(line):
                score += 4
            if line.rstrip().endswith("{"):
                score -= 2
            if "return " in lower and mechanism == "lifecycle":
                score -= 1
        ranked.append((score, index))
    ranked.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    return ranked[0][1] if ranked and ranked[0][0] > -100 else fallback


def make_candidate(branch: dict[str, object], item: dict[str, object], root: Path, row: dict[str, object]) -> dict[str, object]:
    text = (root / str(item["path"])).read_text(errors="replace")
    lines = text.splitlines()
    mechanism = str(branch["mechanisms"][0])
    row_kind = str(row.get("row_kind", "root_control"))
    block, evidence, block_mechanism = choose_block_for_row_kind(lines, str(item["path"]), mechanism, row_kind)
    start = int(block["start"])
    end = int(block["end"])
    local_signal_hits = local_hits(lines, start, end, HINT[block_mechanism])
    evidence["signal"] = local_signal_hits or evidence["signal"]
    source_line = choose_source_line(lines, start, end, block_mechanism, anchor(lines, evidence["signal"], start))
    control_line = anchor(lines, evidence["control"], source_line)
    state_line = anchor(lines, evidence["state"], source_line)
    effect_line = choose_effect_line(lines, start, end, block_mechanism, control_line)
    callers = caller_names(lines, start, end)
    return {
        "id": f"{branch['id']}:{row_kind}",
        "branch_id": branch["id"],
        "coverage_row_id": row["id"],
        "status": "open",
        "row_kind": row_kind,
        "location": f"{item['path']}:{start + 1}-{end + 1} ({block['symbol']})",
        "source": f"{item['path']}:{source_line + 1} {snippet(lines, source_line)}",
        "transformation": f"Trace local flow inside {block['symbol']} from trigger through state/resource mutation; callers={', '.join(callers) or 'none-observed'}.",
        "control": f"{item['path']}:{control_line + 1} {snippet(lines, control_line)}",
        "state_resource": f"{item['path']}:{state_line + 1} {snippet(lines, state_line)}",
        "effect": f"{item['path']}:{effect_line + 1} {snippet(lines, effect_line)}",
        "rare_cell": branch["conditions"],
        "oracle": branch["oracle"],
        "issue_example_ids": branch["issue_example_ids"],
        "required_receipts": branch["required_receipts"],
        "evidence": {
            "symbol": block["symbol"],
            "kind": block["kind"],
            "block_mechanism": block_mechanism,
            "start_line": start + 1,
            "end_line": end + 1,
            "signal_lines": [value + 1 for value in evidence["signal"][:8]],
            "control_lines": [value + 1 for value in evidence["control"][:8]],
            "state_lines": [value + 1 for value in evidence["state"][:8]],
            "effect_lines": [value + 1 for value in evidence["effect"][:8]],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.repo)
    plan = json.loads(Path(args.plan).read_text())
    ids = set(plan["shards"][args.shard])
    files = {entry["id"]: entry for entry in plan["inventory"]}
    coverage_rows = defaultdict(list)
    for row in plan.get("coverage_rows", []):
        coverage_rows[str(row.get("branch_id"))].append(row)
    candidates = []
    for branch in plan["branches"]:
        if branch["file_id"] not in ids:
            continue
        rows = coverage_rows.get(str(branch["id"])) or [{"id": f"row:{branch['id']}:root", "row_kind": "root_control"}]
        for row in rows:
            candidates.append(make_candidate(branch, files[branch["file_id"]], root, row))
    out = {
        "document_type": "bug-hunt.materialized-discovery-shard",
        "shard": args.shard,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "coverage": {"branch_ids": [entry["id"] for entry in candidates], "closed": False},
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"ok": True, "shard": args.shard, "candidates": len(candidates), "output": args.output}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
