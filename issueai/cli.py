"""Compatibility CLI for local/manual IssueAI runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from issueai.benchmark import load_json, run_historical_case_benchmark
from issueai.core import IssueAIRequest, run_pipeline


def build_pipeline_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "pipeline",
        help="Run the lightweight deterministic IssueAI pipeline.",
    )
    parser.add_argument("--repository", required=True, help="Repository identifier or local target label.")
    parser.add_argument("--purpose", default="", help="Optional purpose hint for repository understanding.")
    parser.add_argument("--surface", action="append", default=[], help="Surface hints. Repeatable.")
    parser.add_argument("--convention", action="append", default=[], help="Implementation convention hints. Repeatable.")
    parser.add_argument("--signal", action="append", default=[], help="Local signals such as async, session, timeout, log.")
    parser.add_argument(
        "--provider",
        default="host",
        choices=("host", "codex-sdk", "claude-sdk", "api-key"),
        help="Compatibility provider path. Primary usage is host/plugin import mode.",
    )
    parser.set_defaults(command="pipeline")


def build_historical_case_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "historical-case",
        help="Run one official historical-route benchmark case through the public IssueAI interface.",
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ground-truth", type=Path, required=True)
    parser.add_argument("--repos-root", type=Path, required=True)
    parser.add_argument("--artifacts-root", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, default=None)
    parser.set_defaults(command="historical-case")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="issueai",
        description="Compatibility CLI for IssueAI. Primary integrations are host/plugin-based.",
    )
    subparsers = parser.add_subparsers(dest="command")
    build_pipeline_parser(subparsers)
    build_historical_case_parser(subparsers)
    return parser


def normalize_argv(argv: list[str] | None) -> list[str]:
    values = list(sys.argv[1:] if argv is None else argv)
    if not values:
        return ["pipeline"]
    if values[0] not in {"pipeline", "historical-case", "-h", "--help"}:
        return ["pipeline", *values]
    return values


def run_pipeline_command(args: argparse.Namespace) -> int:
    request = IssueAIRequest(
        repository=args.repository,
        purpose_hint=args.purpose,
        surfaces=tuple(args.surface),
        conventions=tuple(args.convention),
        local_signals=tuple(args.signal),
        preferred_provider=args.provider,
    )
    print(json.dumps(run_pipeline(request), indent=2, ensure_ascii=False))
    return 0


def run_historical_case_command(args: argparse.Namespace) -> int:
    from evals.scripts.product_understanding import infer_product_understanding

    manifest = load_json(args.manifest.resolve())
    truth = {entry["id"]: entry for entry in load_json(args.ground_truth.resolve())["cases"]}
    case = next(item for item in manifest["cases"] if item["id"] == args.case_id)
    result = run_historical_case_benchmark(
        repo_root=Path(__file__).resolve().parents[1],
        case_id=args.case_id,
        repos_root=args.repos_root.resolve(),
        artifacts_root=args.artifacts_root.resolve(),
        graph_path=args.graph.resolve(),
        output_dir=args.output_dir.resolve(),
        repository=case["repository"],
        expected_route=truth[args.case_id]["expected_route"],
        infer_product_understanding=infer_product_understanding,
        runtime_root=args.runtime_root.resolve() if args.runtime_root else None,
    )
    if result.get("status") == "error":
        raise SystemExit(json.dumps(result))
    print(
        json.dumps(
            {
                "id": result["id"],
                "repository": result["repository"],
                "expected": result["expected"],
                "positions": result["positions"],
                "top100_all": result["top100_all"],
                "top10": result["topk"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(normalize_argv(argv))
    if args.command == "historical-case":
        return run_historical_case_command(args)
    return run_pipeline_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
