#!/usr/bin/env python3
"""Run the official IssueAI historical-route benchmark for a single case."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from issueai.benchmark import run_historical_case_benchmark  # noqa: E402
from issueai.bug_hunt_runtime import runtime_root  # noqa: E402
from evals.scripts.product_understanding import infer_product_understanding  # noqa: E402

def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


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
    result = run_historical_case_benchmark(
        repo_root=REPO_ROOT,
        case_id=case_id,
        repos_root=args.repos_root.resolve(),
        artifacts_root=args.artifacts_root.resolve(),
        graph_path=args.graph.resolve(),
        output_dir=args.output_dir.resolve(),
        repository=case["repository"],
        expected_route=truth[case_id]["expected_route"],
        infer_product_understanding=infer_product_understanding,
        runtime_root=args.runtime_root.resolve(),
    )
    if result.get("status") == "error":
        raise SystemExit(json.dumps(result))
    result = {
        "id": result["id"],
        "repository": result["repository"],
        "expected": result["expected"],
        "positions": result["positions"],
        "top100_all": result["top100_all"],
        "top10": result["topk"],
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
