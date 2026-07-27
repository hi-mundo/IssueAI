#!/usr/bin/env python3
"""Benchmark the IssueAI migration against the historical 20-case route corpus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from product_understanding import infer_product_understanding

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from issueai.bug_hunt_runtime import runtime_root  # noqa: E402
from issueai.core import HistoricalEvalRuntime, evaluate_historical_case  # noqa: E402


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


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
    runtime = HistoricalEvalRuntime(
        repo_root=REPO_ROOT,
        runtime_root=args.runtime_root,
        graph_path=args.graph,
    )

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
        evaluation = evaluate_historical_case(
            case_id=case_id,
            repository=case["repository"],
            expected_route=truth[case_id]["expected_route"],
            repo_dir=repo_dir,
            normalized_path=normalized_path,
            repository_map_path=map_path,
            normalized=normalized,
            repository_map=repository_map,
            artifact_dir=artifact_dir,
            runtime=runtime,
            infer_product_understanding=infer_product_understanding,
            contextual_limit=60,
            scoring_contextual_limit=60,
            scoring_contextual_base=80.0,
            scoring_playbook_limit=80,
            scoring_playbook_base=60.0,
            use_materialization=True,
            top_k=3,
        )
        if evaluation.get("status") == "error":
            results.append(evaluation)
            continue
        predicted = evaluation["topk"]
        expected = evaluation["expected"]
        classification, hit_count = classify(predicted, expected)
        results.append(
            {
                "id": evaluation["id"],
                "repository": evaluation["repository"],
                "status": classification,
                "source_count": evaluation["source_count"],
                "mode": evaluation["mode"],
                "scopes": evaluation["scopes"],
                "predicted_route": predicted,
                "expected_route": expected,
                "route_hits": hit_count,
                "top_scores": evaluation["top_scores"],
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
