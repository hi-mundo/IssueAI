#!/usr/bin/env python3
"""Derive a proposed historical-route dataset from prepared benchmark artifacts.

This is intentionally marked as proposed ground truth, not manually validated
gold truth. It exists so a partially curated batch can still be serialized into
the same benchmark shape used by the official runners.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path

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

HYPOTHESIS_SOURCES = (
    ("source-only-hypotheses.json", 12.0),
    ("source-only-hypotheses-rerun.json", 9.0),
    ("escape-cell-hypotheses-final.json", 8.0),
    ("escape-cell-hypotheses-rerun.json", 6.0),
)

ROW_SOURCES = (
    ("merged-worklist-final.json", 1.0),
    ("discovery-worklist-final.json", 0.75),
)


def canonicalize(name: str) -> str:
    return CANONICAL.get(name, name)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def github_repo_from_remote(repo_dir: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_dir), "config", "--get", "remote.origin.url"],
        capture_output=True,
        text=True,
        check=False,
    )
    remote = proc.stdout.strip()
    if remote.endswith(".git"):
        remote = remote[:-4]
    remote = remote.replace("https://github.com/", "").replace("git@github.com:", "")
    return remote


def score_case(artifact_dir: Path) -> list[str]:
    scores: defaultdict[str, float] = defaultdict(float)

    for filename, base in HYPOTHESIS_SOURCES:
        path = artifact_dir / filename
        if not path.exists():
            continue
        payload = load_json(path)
        for index, hypothesis in enumerate(payload.get("hypotheses", [])):
            category = canonicalize(str(hypothesis.get("category", "")))
            if not category or category == "history-seeded":
                continue
            scores[category] += max(1.0, base - float(index))

    for filename, scale in ROW_SOURCES:
        path = artifact_dir / filename
        if not path.exists():
            continue
        payload = load_json(path)
        for index, row in enumerate(payload.get("rows", [])[:24]):
            category = canonicalize(str(row.get("category", "")))
            if not category or category == "history-seeded":
                continue
            signal = float(row.get("source_signal_score", 1.0))
            scores[category] += signal * scale
            scores[category] += max(1.0, 18.0 - float(index))

    ordered = [name for name, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))]
    return ordered[:3]


def build_case(repo_id: str, repo_dir: Path, artifact_dir: Path) -> tuple[dict, dict]:
    repository = github_repo_from_remote(repo_dir)
    tracker, issue = repo_id.rsplit("-", 1)
    issue_number = int(issue)
    manifest_case = {
        "id": repo_id,
        "repository": repository,
    }
    truth_case = {
        "id": repo_id,
        "repository": repository,
        "issue": issue_number,
        "url": f"https://github.com/{repository}/issues/{issue_number}",
        "created_at": None,
        "expected_route": score_case(artifact_dir),
        "status": "proposed-from-artifacts",
    }
    return manifest_case, truth_case


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos-root", type=Path, required=True)
    parser.add_argument("--artifacts-root", type=Path, required=True)
    parser.add_argument("--manifest-out", type=Path, required=True)
    parser.add_argument("--ground-truth-out", type=Path, required=True)
    args = parser.parse_args()

    case_ids = sorted([p.name for p in args.repos_root.iterdir() if p.is_dir()])
    manifest_cases: list[dict] = []
    truth_cases: list[dict] = []
    for case_id in case_ids:
        manifest_case, truth_case = build_case(
            case_id,
            repo_dir=args.repos_root / case_id,
            artifact_dir=args.artifacts_root / case_id,
        )
        manifest_cases.append(manifest_case)
        truth_cases.append(truth_case)

    manifest = {
        "warning": "This dataset was reconstructed from prepared artifacts and is not yet manually gold-validated.",
        "cases": manifest_cases,
    }
    truth = {
        "warning": "expected_route values in this file are proposed from local benchmark artifacts, not yet manually validated against issue texts.",
        "cases": truth_cases,
    }
    args.manifest_out.write_text(json.dumps(manifest, indent=2) + "\n")
    args.ground_truth_out.write_text(json.dumps(truth, indent=2) + "\n")
    print(json.dumps({"cases": len(case_ids), "manifest": str(args.manifest_out), "ground_truth": str(args.ground_truth_out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
