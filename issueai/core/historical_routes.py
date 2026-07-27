"""Shared historical-route benchmark logic for IssueAI."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable

from .historical_eval import (
    HistoricalEvalRuntime,
    build_contextual_input,
    build_intelligent_plan,
    materialize_shard,
    write_product_understanding,
)

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


def aggregate_scores(contextual: dict, plan: dict, contextual_limit: int, playbook_limit: int, contextual_base: float, playbook_base: float) -> dict[str, float]:
    scores: defaultdict[str, float] = defaultdict(float)
    branch_counts: Counter[str] = Counter()
    inventory_counts: Counter[str] = Counter()
    for index, row in enumerate(contextual.get("rank_input", [])[:contextual_limit]):
        base = max(1.0, contextual_base - float(index))
        for mechanism in row.get("mechanisms", []):
            scores[canonicalize(mechanism)] += base
        for mechanism in row.get("matched_local_mechanisms", []):
            scores[canonicalize(mechanism)] += base * 1.5
    for index, book in enumerate(plan.get("playbooks", [])[:playbook_limit]):
        base = max(1.0, playbook_base - float(index))
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
    runtime: HistoricalEvalRuntime,
) -> dict[str, float]:
    branch_map = {entry["id"]: entry for entry in plan.get("branches", [])}
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    top_mechanisms = [name for name, _ in ranked[:4]]
    file_ids = top_branch_files(plan, top_mechanisms)
    shard_ids = shards_for_files(plan, file_ids)
    plan_path = artifact_dir / "intelligent-plan.json"
    for shard_id in shard_ids:
        output = artifact_dir / f"materialized-shard-{shard_id}.json"
        ok, detail = materialize_shard(
            runtime,
            repo_dir=repo_dir,
            plan_path=plan_path,
            shard_id=shard_id,
            output_path=output,
        )
        if not ok:
            raise RuntimeError(f"materialize shard {shard_id} failed: {detail}")
        payload = json.loads(output.read_text())
        for candidate in payload.get("candidates", []):
            branch = branch_map.get(candidate.get("id"), {})
            symbol = str(candidate.get("evidence", {}).get("symbol", ""))
            symbol_bonus = 40.0 if symbol and symbol != "module-scope" else 0.0
            for mechanism in branch.get("mechanisms", []):
                key = canonicalize(mechanism)
                scores[key] = scores.get(key, 0.0) + symbol_bonus + 8.0
    return scores


def evaluate_historical_case(
    *,
    case_id: str,
    repository: str,
    expected_route: list[str],
    repo_dir: Path,
    normalized_path: Path,
    repository_map_path: Path,
    normalized: dict,
    repository_map: dict,
    artifact_dir: Path,
    runtime: HistoricalEvalRuntime,
    infer_product_understanding: Callable[[str, Path, dict, dict], dict],
    contextual_limit: int,
    scoring_contextual_limit: int,
    scoring_contextual_base: float,
    scoring_playbook_limit: int,
    scoring_playbook_base: float,
    use_materialization: bool,
    top_k: int,
) -> dict[str, object]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    product = infer_product_understanding(repository, repo_dir, normalized, repository_map)
    product_path = artifact_dir / "product-understanding.json"
    write_product_understanding(product_path, product)

    mode, scopes, source_count = choose_scopes(normalized)

    contextual_path = artifact_dir / "contextual-input.json"
    ok, detail = build_contextual_input(
        runtime,
        product_path=product_path,
        normalized_path=normalized_path,
        repository_map_path=repository_map_path,
        output_path=contextual_path,
        limit=contextual_limit,
    )
    if not ok:
        return {"id": case_id, "repository": repository, "status": "error", "stage": "query_issue_evidence_graph.py", "detail": detail}

    plan_path = artifact_dir / "intelligent-plan.json"
    ok, detail = build_intelligent_plan(
        runtime,
        repo_dir=repo_dir,
        product_path=product_path,
        contextual_input_path=contextual_path,
        output_path=plan_path,
        mode=mode,
        scopes=scopes,
        shard_size=120,
    )
    if not ok:
        return {"id": case_id, "repository": repository, "status": "error", "stage": "build_intelligent_discovery_plan.py", "detail": detail}

    contextual = json.loads(contextual_path.read_text())
    plan = json.loads(plan_path.read_text())
    scores = aggregate_scores(
        contextual,
        plan,
        contextual_limit=scoring_contextual_limit,
        playbook_limit=scoring_playbook_limit,
        contextual_base=scoring_contextual_base,
        playbook_base=scoring_playbook_base,
    )
    if use_materialization:
        try:
            scores = enrich_with_materialization(scores, plan, artifact_dir, repo_dir, runtime)
        except Exception as exc:  # noqa: BLE001
            return {"id": case_id, "repository": repository, "status": "error", "stage": "materialize_discovery_shard.py", "detail": str(exc)}

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    ordered = [name for name, _ in ranked]
    expected = [canonicalize(value) for value in expected_route]
    result: dict[str, object] = {
        "id": case_id,
        "repository": repository,
        "expected": expected,
        "ordered": ordered,
        "positions": {name: (ordered.index(name) + 1 if name in ordered else None) for name in expected},
        "top_scores": ranked[:8],
        "source_count": source_count,
        "mode": mode,
        "scopes": scopes,
    }
    result["top100_all"] = all(position is not None and position <= 100 for position in result["positions"].values())
    result["topk"] = ordered[:top_k]
    return result
