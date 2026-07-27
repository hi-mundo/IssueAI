"""Shared orchestration helpers for historical IssueAI benchmark runs."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HistoricalEvalRuntime:
    """Runtime locations needed by the historical benchmark harness."""

    repo_root: Path
    runtime_root: Path
    graph_path: Path


def run_command(command: list[str], cwd: Path, timeout: int = 240) -> tuple[bool, str]:
    """Run a bounded subprocess and return a compact success/detail pair."""

    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    detail = (result.stderr or result.stdout or "").strip()[-2000:]
    return result.returncode == 0, detail


def write_product_understanding(output_path: Path, payload: dict) -> None:
    output_path.write_text(json.dumps(payload, indent=2) + "\n")


def build_contextual_input(
    runtime: HistoricalEvalRuntime,
    product_path: Path,
    normalized_path: Path,
    repository_map_path: Path,
    output_path: Path,
    limit: int = 100,
) -> tuple[bool, str]:
    return run_command(
        [
            "python3",
            str(runtime.runtime_root / "scripts" / "query_issue_evidence_graph.py"),
            "--graph",
            str(runtime.graph_path),
            "--product-model",
            str(product_path),
            "--normalized",
            str(normalized_path),
            "--map",
            str(repository_map_path),
            "--output",
            str(output_path),
            "--limit",
            str(limit),
        ],
        runtime.repo_root,
    )


def build_intelligent_plan(
    runtime: HistoricalEvalRuntime,
    repo_dir: Path,
    product_path: Path,
    contextual_input_path: Path,
    output_path: Path,
    mode: str,
    scopes: list[str],
    shard_size: int = 120,
) -> tuple[bool, str]:
    command = [
        "python3",
        str(runtime.runtime_root / "scripts" / "build_intelligent_discovery_plan.py"),
        "--repo",
        str(repo_dir),
        "--graph",
        str(runtime.graph_path),
        "--product-model",
        str(product_path),
        "--context-input",
        str(contextual_input_path),
        "--mode",
        mode,
        "--shard-size",
        str(shard_size),
        "--output",
        str(output_path),
    ]
    for scope in scopes:
        command.extend(["--scope", scope])
    return run_command(command, runtime.repo_root)


def materialize_shard(
    runtime: HistoricalEvalRuntime,
    repo_dir: Path,
    plan_path: Path,
    shard_id: int,
    output_path: Path,
) -> tuple[bool, str]:
    return run_command(
        [
            "python3",
            str(runtime.runtime_root / "scripts" / "materialize_discovery_shard.py"),
            "--repo",
            str(repo_dir),
            "--plan",
            str(plan_path),
            "--shard",
            str(shard_id),
            "--output",
            str(output_path),
        ],
        runtime.repo_root,
    )
