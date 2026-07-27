"""Compatibility CLI for local/manual IssueAI runs."""

from __future__ import annotations

import argparse
import json

from issueai.core import IssueAIRequest, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="issueai",
        description="Compatibility CLI for IssueAI. Primary integrations are host/plugin-based.",
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
    return parser


def main() -> int:
    args = build_parser().parse_args()
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


if __name__ == "__main__":
    raise SystemExit(main())
