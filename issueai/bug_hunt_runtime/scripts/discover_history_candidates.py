#!/usr/bin/env python3
"""Find source locations implicated by later fix/regression history.

The script is a discovery pass only. It does not read issue metadata and does
not claim that a later change proves the snapshot was defective.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path


COMMIT_SIGNAL = re.compile(r"fix|bug|regression|hang|leak|crash|race|incorrect|compat|overflow|deadlock|retry|teardown|cleanup", re.I)
NON_SOURCE = re.compile(r"(^|/)(docs?|changelog|examples?|bench(mark)?s?|fixtures?|test(s)?)(/|$)|\.(md|rst|txt|json|yaml|yml)$", re.I)


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--map", required=True)
    parser.add_argument("--since", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    graph = json.loads(Path(args.map).read_text(encoding="utf-8"))
    source_paths = {node["location"]: node["id"] for node in graph.get("nodes", []) if node.get("location")}
    history = run("git", "-C", str(root), "log", "--all", "--since=" + args.since, "--pretty=format:%H%x09%s", "--name-only", "--no-merges", "--max-count=100")
    counts: Counter[str] = Counter()
    commit_for: dict[str, str] = {}
    commit = subject = None
    pending_files: list[str] = []

    def flush() -> None:
        if not commit or not subject or not COMMIT_SIGNAL.search(subject):
            return
        for path in pending_files:
            if path in source_paths and not NON_SOURCE.search(path):
                counts[path] += 1
                commit_for[path] = commit

    for row in history.splitlines() + [""]:
        if "\t" in row:
            flush()
            commit, subject = row.split("\t", 1)
            pending_files = []
        elif row:
            pending_files.append(row)
        else:
            flush()
            commit = subject = None
            pending_files = []
    hypotheses = []
    for priority, (location, score) in enumerate(counts.most_common(args.limit)):
        hypotheses.append({
            "id": f"h-history-{priority}-{source_paths[location].split(':')[-1]}",
            "feature_id": "repository-history",
            "map_node_ids": [source_paths[location]],
            "category": "history-seeded",
            "intent_layer": "reliability",
            "expected_behavior": "The repository contract remains true across the transition represented by this source location.",
            "suspected_behavior": "A later fix-shaped change suggests a prior edge case or regression boundary worth reconstructing.",
            "trigger": f"Reconstruct the transition around {location} and exercise the rare cell implied by its callers and tests.",
            "preconditions": [f"The location appears in {score} later fix-shaped commits.", "The commit history is evidence for discovery, not proof of a defect in this snapshot."],
            "evidence_initial": [f"repository-map:{source_paths[location]}", f"history-commit:{commit_for[location]}", f"history-hit-count:{score}"],
            "reference_ids": [],
            "candidate_locations": [location],
            "validation_method": "Inspect the changed behavior and execute a direct probe; no validation is performed by this pass.",
            "initial_confidence": min(0.7, 0.25 + score * 0.1),
            "priority": priority,
            "inferred": True,
        })
    Path(args.output).write_text(json.dumps({"mode": "history-seeded", "hypotheses": hypotheses}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "hypotheses": len(hypotheses), "output": args.output}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
