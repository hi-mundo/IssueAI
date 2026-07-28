"""Compatibility CLI for local/manual IssueAI runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from issueai.benchmark import load_json, run_historical_case_benchmark
from issueai.core import (
    IssueAIRequest,
    preflight_repository,
    run_issue_hunt,
    run_issue_probe,
    run_pipeline,
    run_repository_intent_review,
    run_repository_recon,
)


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


def add_review_mode_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--mode",
        default="auto",
        choices=("auto", "pending-changes", "commit-or-diff", "scoped", "repository", "deep"),
        help="Review mode. Defaults to auto-selection.",
    )
    parser.add_argument("--scope", default="", help="Optional scoped path or feature label.")
    parser.add_argument("--diff-target", default="", help="Optional commit or diff target label.")


def build_repository_recon_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "repository-recon",
        help="Run Repository Recon: snapshot, map structure, trace flow, and build the repository graph.",
    )
    parser.add_argument("--repo", type=Path, required=True, help="Local repository path.")
    parser.add_argument("--purpose", default="", help="Optional purpose hint.")
    parser.add_argument("--signal", action="append", default=[], help="Language/runtime signals to preserve in Recon.")
    add_review_mode_arguments(parser)
    parser.set_defaults(command="repository-recon")


def build_preflight_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "preflight",
        help="Compatibility alias: create or refresh the .issueai baseline for a local repository.",
    )
    parser.add_argument("--repo", type=Path, required=True, help="Local repository path.")
    parser.set_defaults(command="preflight")


def build_repository_intent_review_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "repository-intent-review",
        help="Run Repository Intent Review: validate implementation intent after Repository Recon.",
    )
    parser.add_argument("--repo", type=Path, required=True, help="Local repository path.")
    parser.add_argument("--purpose", default="", help="Optional purpose hint.")
    parser.add_argument("--signal", action="append", default=[], help="Language/runtime review hints. Repeatable.")
    add_review_mode_arguments(parser)
    parser.set_defaults(command="repository-intent-review")


def build_intent_review_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "intent-review",
        help="Compatibility alias for Repository Intent Review.",
    )
    parser.add_argument("--repo", type=Path, required=True, help="Local repository path.")
    parser.add_argument("--purpose", default="", help="Optional purpose hint.")
    parser.add_argument("--signal", action="append", default=[], help="Language/runtime review hints. Repeatable.")
    add_review_mode_arguments(parser)
    parser.set_defaults(command="intent-review")


def build_issue_hunt_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "issue-hunt",
        help="Run Issue Hunt after Recon and Repository Intent Review are clean enough.",
    )
    parser.add_argument("--repo", type=Path, required=True, help="Local repository path.")
    parser.add_argument("--purpose", default="", help="Optional purpose hint.")
    parser.add_argument("--signal", action="append", default=[], help="Extra hunt signals. Repeatable.")
    parser.add_argument("--limit", type=int, default=12, help="Maximum number of ranked hypotheses to return.")
    parser.set_defaults(command="issue-hunt")


def build_issue_probe_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "issue-probe",
        help="Run Issue Probe on the latest shortlisted findings or hypotheses.",
    )
    parser.add_argument("--repo", type=Path, required=True, help="Local repository path.")
    parser.add_argument("--limit", type=int, default=6, help="Maximum number of candidates to probe.")
    parser.set_defaults(command="issue-probe")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="issueai",
        description="Compatibility CLI for IssueAI. Primary integrations are host/plugin-based.",
    )
    subparsers = parser.add_subparsers(dest="command")
    build_pipeline_parser(subparsers)
    build_historical_case_parser(subparsers)
    build_repository_recon_parser(subparsers)
    build_preflight_parser(subparsers)
    build_repository_intent_review_parser(subparsers)
    build_intent_review_parser(subparsers)
    build_issue_hunt_parser(subparsers)
    build_issue_probe_parser(subparsers)
    return parser


def normalize_argv(argv: list[str] | None) -> list[str]:
    values = list(sys.argv[1:] if argv is None else argv)
    if not values:
        return ["pipeline"]
    if values[0] not in {
        "pipeline",
        "historical-case",
        "repository-recon",
        "preflight",
        "repository-intent-review",
        "intent-review",
        "issue-hunt",
        "issue-probe",
        "-h",
        "--help",
    }:
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
                "top20_all": result["top20_all"],
                "top100_all": result["top100_all"],
                "top10": result["topk"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def run_preflight_command(args: argparse.Namespace) -> int:
    print(json.dumps(preflight_repository(args.repo), indent=2, ensure_ascii=False))
    return 0


def run_repository_recon_command(args: argparse.Namespace) -> int:
    payload = run_repository_recon(
        args.repo,
        repository_label=args.repo.name,
        purpose_hint=args.purpose,
        local_signals=tuple(args.signal),
        explicit_mode=args.mode,
        scope=args.scope,
        diff_target=args.diff_target,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def run_repository_intent_review_command(args: argparse.Namespace) -> int:
    payload = run_repository_intent_review(
        args.repo,
        repository_label=args.repo.name,
        purpose_hint=args.purpose,
        local_signals=tuple(args.signal),
        explicit_mode=args.mode,
        scope=args.scope,
        diff_target=args.diff_target,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def run_issue_hunt_command(args: argparse.Namespace) -> int:
    payload = run_issue_hunt(
        args.repo,
        repository_label=args.repo.name,
        purpose_hint=args.purpose,
        local_signals=tuple(args.signal),
        hypothesis_limit=args.limit,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def run_issue_probe_command(args: argparse.Namespace) -> int:
    payload = run_issue_probe(
        args.repo,
        repository_label=args.repo.name,
        limit=args.limit,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(normalize_argv(argv))
    if args.command == "historical-case":
        return run_historical_case_command(args)
    if args.command == "repository-recon":
        return run_repository_recon_command(args)
    if args.command == "preflight":
        return run_preflight_command(args)
    if args.command in {"repository-intent-review", "intent-review"}:
        return run_repository_intent_review_command(args)
    if args.command == "issue-hunt":
        return run_issue_hunt_command(args)
    if args.command == "issue-probe":
        return run_issue_probe_command(args)
    return run_pipeline_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
