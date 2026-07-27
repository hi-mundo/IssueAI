#!/usr/bin/env python3
"""Run the official IssueAI historical-route benchmark for a single case."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from issueai.bug_hunt_runtime import runtime_root  # noqa: E402
from evals.scripts.product_understanding import infer_product_understanding  # noqa: E402

CANONICAL = {
    "state": "state_reuse",
    "state_reuse": "state_reuse",
    "typing": "contract",
    "compatibility": "compatibility",
    "boundary": "boundary",
    "precedence": "precedence",
    "contract": "contract",
    "lifecycle": "lifecycle",
    "representation": "representation",
    "concurrency": "concurrency",
    "integration": "integration",
    "observability": "observability",
    "data_integrity": "data_integrity",
}
EXCLUDED_ROOTS = {
    ".git", ".github", "docs", "doc", "test", "tests", "testing", "fixtures",
    "examples", "example", "bench", "benchmark", "vendor", "third_party",
    "node_modules", "dist", "build",
}


def canonicalize(name: str) -> str:
    return CANONICAL.get(name, name)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def run(command: list[str], cwd: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=240)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    detail = (result.stderr or result.stdout or "").strip()[-2000:]
    return result.returncode == 0, detail


def choose_scopes(normalized: dict) -> tuple[str, list[str], int]:
    files = [
        entry
        for entry in normalized.get("files", [])
        if entry.get("kind") == "source" and not entry.get("vendor") and not entry.get("generated")
    ]
    count = len(files)
    if count <= 2200:
        return "deep", [], count
    roots = Counter()
    for entry in files:
        path = str(entry.get("path", ""))
        top = path.split("/", 1)[0]
        if not top or top in EXCLUDED_ROOTS or top.startswith("."):
            continue
        roots[top] += 1
    selected = [name for name, _ in roots.most_common(4)]
    return ("deep", [], count) if not selected else ("normal", selected, count)


def aggregate_scores(contextual: dict, plan: dict) -> dict[str, float]:
    scores: defaultdict[str, float] = defaultdict(float)
    branch_counts: Counter[str] = Counter()
    inventory_counts: Counter[str] = Counter()
    for index, row in enumerate(contextual.get("rank_input", [])[:100]):
        base = max(1.0, 120.0 - float(index))
        for mechanism in row.get("mechanisms", []):
            scores[canonicalize(mechanism)] += base
        for mechanism in row.get("matched_local_mechanisms", []):
            scores[canonicalize(mechanism)] += base * 1.5
    for index, book in enumerate(plan.get("playbooks", [])[:120]):
        base = max(1.0, 80.0 - float(index))
        for mechanism in book.get("mechanisms", []):
            scores[canonicalize(mechanism)] += base * 2.0
    for item in plan.get("inventory", []):
        for mechanism in item.get("mechanisms", []):
            inventory_counts[canonicalize(mechanism)] += 1
    for branch in plan.get("branches", []):
        for mechanism in branch.get("mechanisms", []):
            branch_counts[canonicalize(mechanism)] += 1
    for row in plan.get("coverage_rows", []):
        for mechanism in row.get("mechanisms", []):
            scores[canonicalize(mechanism)] += 4.0
    for mechanism, count in inventory_counts.items():
        scores[mechanism] += math.log1p(count) * 2.0
    for mechanism, count in branch_counts.items():
        scores[mechanism] += math.log1p(count) * 6.0
    total_files = max(1, len(plan.get("inventory", [])))
    total_branches = max(1, len(plan.get("branches", [])))
    for mechanism in list(scores):
        saturation = (inventory_counts.get(mechanism, 0) / total_files) + (branch_counts.get(mechanism, 0) / total_branches)
        scores[mechanism] = scores[mechanism] / (1.0 + saturation * 8.0)
    return dict(scores)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--manifest", type=Path, default=REPO_ROOT / "evals" / "unmapped-repositories-20.json")
    parser.add_argument("--ground-truth", type=Path, required=True)
    parser.add_argument("--repos-root", type=Path, required=True)
    parser.add_argument("--artifacts-root", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, default=runtime_root())
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    manifest = load_json(args.manifest.resolve())
    truth = {entry["id"]: entry for entry in load_json(args.ground_truth.resolve())["cases"]}
    case = next(item for item in manifest["cases"] if item["id"] == args.case_id)
    case_id = case["id"]
    repo_dir = args.repos_root.resolve() / case_id
    source_artifacts = args.artifacts_root.resolve() / case_id
    artifact_dir = args.output_dir.resolve() / case_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    normalized_path = source_artifacts / "normalized.json"
    map_path = source_artifacts / "repository-map.json"
    normalized = load_json(normalized_path)
    repository_map = load_json(map_path)
    product = infer_product_understanding(case["repository"], repo_dir, normalized, repository_map)
    product_path = artifact_dir / "product-understanding.json"
    product_path.write_text(json.dumps(product, indent=2) + "\n")

    mode, scopes, _ = choose_scopes(normalized)
    contextual_path = artifact_dir / "contextual-input.json"
    ok, detail = run(
        [
            "python3",
            str(args.runtime_root.resolve() / "scripts" / "query_issue_evidence_graph.py"),
            "--graph",
            str(args.graph.resolve()),
            "--product-model",
            str(product_path),
            "--normalized",
            str(normalized_path),
            "--map",
            str(map_path),
            "--output",
            str(contextual_path),
            "--limit",
            "100",
        ],
        REPO_ROOT,
    )
    if not ok:
        raise SystemExit(json.dumps({"id": case_id, "status": "error", "stage": "query_issue_evidence_graph.py", "detail": detail}))

    plan_path = artifact_dir / "intelligent-plan.json"
    command = [
        "python3",
        str(args.runtime_root.resolve() / "scripts" / "build_intelligent_discovery_plan.py"),
        "--repo",
        str(repo_dir),
        "--graph",
        str(args.graph.resolve()),
        "--product-model",
        str(product_path),
        "--context-input",
        str(contextual_path),
        "--mode",
        mode,
        "--shard-size",
        "120",
        "--output",
        str(plan_path),
    ]
    for scope in scopes:
        command.extend(["--scope", scope])
    ok, detail = run(command, REPO_ROOT)
    if not ok:
        raise SystemExit(json.dumps({"id": case_id, "status": "error", "stage": "build_intelligent_discovery_plan.py", "detail": detail}))

    contextual = load_json(contextual_path)
    plan = load_json(plan_path)
    ranked = sorted(aggregate_scores(contextual, plan).items(), key=lambda item: (-item[1], item[0]))
    ordered = [name for name, _ in ranked]
    expected = [canonicalize(value) for value in truth[case_id]["expected_route"]]
    positions = {name: (ordered.index(name) + 1 if name in ordered else None) for name in expected}
    top100_all = all(position is not None and position <= 100 for position in positions.values())
    result = {
        "id": case_id,
        "repository": case["repository"],
        "expected": expected,
        "positions": positions,
        "top100_all": top100_all,
        "top10": ordered[:10],
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
