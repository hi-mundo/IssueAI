"""Public benchmark entrypoints for IssueAI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .bug_hunt_runtime import runtime_root as default_runtime_root
from .core import HistoricalEvalRuntime, evaluate_historical_case


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def run_historical_case_benchmark(
    *,
    repo_root: Path,
    case_id: str,
    repos_root: Path,
    artifacts_root: Path,
    graph_path: Path,
    output_dir: Path,
    repository: str,
    expected_route: list[str],
    infer_product_understanding: Callable[[str, Path, dict, dict], dict],
    runtime_root: Path | None = None,
    contextual_limit: int = 100,
    scoring_contextual_limit: int = 100,
    scoring_contextual_base: float = 120.0,
    scoring_playbook_limit: int = 120,
    scoring_playbook_base: float = 80.0,
    use_materialization: bool = False,
    top_k: int = 10,
) -> dict[str, object]:
    repo_root = repo_root.resolve()
    repos_root = repos_root.resolve()
    artifacts_root = artifacts_root.resolve()
    graph_path = graph_path.resolve()
    output_dir = output_dir.resolve()
    runtime_path = (runtime_root or default_runtime_root()).resolve()

    repo_dir = repos_root / case_id
    source_artifacts = artifacts_root / case_id
    artifact_dir = output_dir / case_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    normalized_path = source_artifacts / "normalized.json"
    repository_map_path = source_artifacts / "repository-map.json"
    runtime = HistoricalEvalRuntime(
        repo_root=repo_root,
        runtime_root=runtime_path,
        graph_path=graph_path,
    )
    return evaluate_historical_case(
        case_id=case_id,
        repository=repository,
        expected_route=expected_route,
        repo_dir=repo_dir,
        normalized_path=normalized_path,
        repository_map_path=repository_map_path,
        normalized=load_json(normalized_path),
        repository_map=load_json(repository_map_path),
        artifact_dir=artifact_dir,
        runtime=runtime,
        infer_product_understanding=infer_product_understanding,
        contextual_limit=contextual_limit,
        scoring_contextual_limit=scoring_contextual_limit,
        scoring_contextual_base=scoring_contextual_base,
        scoring_playbook_limit=scoring_playbook_limit,
        scoring_playbook_base=scoring_playbook_base,
        use_materialization=use_materialization,
        top_k=top_k,
    )
