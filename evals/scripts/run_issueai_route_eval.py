#!/usr/bin/env python3
"""Benchmark the IssueAI migration against the historical 20-case route corpus."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from product_understanding import infer_product_understanding

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from issueai.bug_hunt_runtime import runtime_root  # noqa: E402

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
    ".git",
    ".github",
    "docs",
    "doc",
    "test",
    "tests",
    "testing",
    "fixtures",
    "examples",
    "example",
    "bench",
    "benchmark",
    "vendor",
    "third_party",
    "node_modules",
    "dist",
    "build",
}


def canonicalize(name: str) -> str:
    return CANONICAL.get(name, name)


def run(command: list[str], cwd: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    detail = (result.stderr or result.stdout or "").strip()[-2000:]
    return result.returncode == 0, detail


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


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
    if not selected:
        return "deep", [], count
    return "normal", selected, count


def aggregate_scores(contextual: dict, plan: dict) -> dict[str, float]:
    scores: defaultdict[str, float] = defaultdict(float)
    branch_counts: Counter[str] = Counter()
    inventory_counts: Counter[str] = Counter()
    for index, row in enumerate(contextual.get("rank_input", [])[:60]):
        base = max(2.0, 80.0 - float(index))
        for mechanism in row.get("mechanisms", []):
            scores[canonicalize(mechanism)] += base
        for mechanism in row.get("matched_local_mechanisms", []):
            scores[canonicalize(mechanism)] += base * 1.5
    for index, book in enumerate(plan.get("playbooks", [])[:80]):
        base = max(1.0, 60.0 - float(index))
        for mechanism in book.get("mechanisms", []):
            scores[canonicalize(mechanism)] += base * 2.0
    for item in plan.get("inventory", []):
        for mechanism in item.get("mechanisms", []):
            inventory_counts[canonicalize(mechanism)] += 1
    for branch in plan.get("branches", []):
        for mechanism in branch.get("mechanisms", []):
            branch_counts[canonicalize(mechanism)] += 1
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


def top_branch_files(plan: dict, top_mechanisms: list[str], limit: int = 6) -> list[str]:
    file_counts: Counter[str] = Counter()
    for branch in plan.get("branches", []):
        mechanisms = [canonicalize(value) for value in branch.get("mechanisms", [])]
        if any(value in top_mechanisms for value in mechanisms):
            file_counts[str(branch.get("file_id"))] += 1
    return [file_id for file_id, _ in file_counts.most_common(limit)]


def shards_for_files(plan: dict, file_ids: list[str], limit: int = 3) -> list[int]:
    wanted = set(file_ids)
    hits = []
    for index, shard in enumerate(plan.get("shards", [])):
        overlap = len(wanted & set(shard))
        if overlap:
            hits.append((overlap, index))
    hits.sort(reverse=True)
    return [index for _, index in hits[:limit]]


def enrich_with_materialization(
    scores: dict[str, float],
    plan: dict,
    artifact_dir: Path,
    repo_dir: Path,
    plugin_root: Path,
) -> dict[str, float]:
    branch_map = {entry["id"]: entry for entry in plan.get("branches", [])}
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    top_mechanisms = [name for name, _ in ranked[:4]]
    file_ids = top_branch_files(plan, top_mechanisms)
    shard_ids = shards_for_files(plan, file_ids)
    plan_path = artifact_dir / "intelligent-plan.json"
    for shard_id in shard_ids:
        output = artifact_dir / f"materialized-shard-{shard_id}.json"
        ok, detail = run(
            [
                "python3",
                str(plugin_root / "scripts" / "materialize_discovery_shard.py"),
                "--repo",
                str(repo_dir),
                "--plan",
                str(plan_path),
                "--shard",
                str(shard_id),
                "--output",
                str(output),
            ],
            plugin_root.parent,
        )
        if not ok:
            raise RuntimeError(f"materialize shard {shard_id} failed: {detail}")
        payload = load_json(output)
        for candidate in payload.get("candidates", []):
            branch = branch_map.get(candidate.get("id"), {})
            symbol = str(candidate.get("evidence", {}).get("symbol", ""))
            symbol_bonus = 40.0 if symbol and symbol != "module-scope" else 0.0
            for mechanism in branch.get("mechanisms", []):
                key = canonicalize(mechanism)
                scores[key] = scores.get(key, 0.0) + symbol_bonus + 8.0
    return scores


def classify(predicted: list[str], expected: list[str]) -> tuple[str, int]:
    hit_count = len(set(predicted) & set(expected))
    if hit_count == len(expected):
        return "pass", hit_count
    if hit_count >= max(2, len(expected) - 1):
        return "partial", hit_count
    return "fail", hit_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=REPO_ROOT / "evals" / "unmapped-repositories-20.json")
    parser.add_argument("--ground-truth", type=Path, required=True)
    parser.add_argument("--repos-root", type=Path, required=True)
    parser.add_argument("--artifacts-root", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, default=runtime_root())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.runtime_root = args.runtime_root.resolve()
    args.graph = args.graph.resolve()
    args.repos_root = args.repos_root.resolve()
    args.artifacts_root = args.artifacts_root.resolve()
    args.ground_truth = args.ground_truth.resolve()
    args.output = args.output.resolve()

    manifest = load_json(args.manifest)
    truth = {entry["id"]: entry for entry in load_json(args.ground_truth)["cases"]}
    work_root = args.output.with_suffix("")
    work_root.mkdir(parents=True, exist_ok=True)
    results = []

    for case in manifest["cases"]:
        case_id = case["id"]
        repo_dir = args.repos_root / case_id
        source_artifacts = args.artifacts_root / case_id
        artifact_dir = work_root / case_id
        artifact_dir.mkdir(parents=True, exist_ok=True)

        normalized_path = source_artifacts / "normalized.json"
        map_path = source_artifacts / "repository-map.json"
        if not normalized_path.exists() or not map_path.exists():
            raise FileNotFoundError(f"missing baseline artifacts for {case_id}")
        normalized = load_json(normalized_path)
        repository_map = load_json(map_path)
        product = infer_product_understanding(case["repository"], repo_dir, normalized, repository_map)
        product_path = artifact_dir / "product-understanding.json"
        product_path.write_text(json.dumps(product, indent=2) + "\n")

        mode, scopes, source_count = choose_scopes(normalized)
        contextual_path = artifact_dir / "contextual-input.json"
        ok, detail = run(
            [
                "python3",
                str(args.runtime_root / "scripts" / "query_issue_evidence_graph.py"),
                "--graph",
                str(args.graph),
                "--product-model",
                str(product_path),
                "--normalized",
                str(normalized_path),
                "--map",
                str(map_path),
                "--output",
                str(contextual_path),
                "--limit",
                "60",
            ],
            REPO_ROOT,
        )
        if not ok:
            results.append({"id": case_id, "repository": case["repository"], "status": "error", "stage": "query_issue_evidence_graph.py", "detail": detail})
            continue

        plan_path = artifact_dir / "intelligent-plan.json"
        command = [
            "python3",
            str(args.runtime_root / "scripts" / "build_intelligent_discovery_plan.py"),
            "--repo",
            str(repo_dir),
            "--graph",
            str(args.graph),
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
            results.append({"id": case_id, "repository": case["repository"], "status": "error", "stage": "build_intelligent_discovery_plan.py", "detail": detail})
            continue

        contextual = load_json(contextual_path)
        plan = load_json(plan_path)
        scores = aggregate_scores(contextual, plan)
        try:
            scores = enrich_with_materialization(scores, plan, artifact_dir, repo_dir, args.runtime_root)
        except Exception as exc:  # noqa: BLE001
            results.append({"id": case_id, "repository": case["repository"], "status": "error", "stage": "materialize_discovery_shard.py", "detail": str(exc)})
            continue
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        predicted = [name for name, _ in ranked[:3]]
        expected = [canonicalize(value) for value in truth[case_id]["expected_route"]]
        classification, hit_count = classify(predicted, expected)
        results.append(
            {
                "id": case_id,
                "repository": case["repository"],
                "status": classification,
                "source_count": source_count,
                "mode": mode,
                "scopes": scopes,
                "predicted_route": predicted,
                "expected_route": expected,
                "route_hits": hit_count,
                "top_scores": ranked[:8],
            }
        )
        print(json.dumps(results[-1], sort_keys=True), flush=True)

    summary = {
        "results": results,
        "pass": sum(item["status"] == "pass" for item in results),
        "partial": sum(item["status"] == "partial" for item in results),
        "fail": sum(item["status"] == "fail" for item in results),
        "error": sum(item["status"] == "error" for item in results),
        "pass_rate": round(sum(item["status"] == "pass" for item in results) / len(results), 4) if results else 0.0,
        "good_rate": round(sum(item["status"] in {"pass", "partial"} for item in results) / len(results), 4) if results else 0.0,
    }
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
