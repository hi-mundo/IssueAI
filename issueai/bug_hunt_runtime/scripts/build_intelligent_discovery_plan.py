#!/usr/bin/env python3
"""Create a complete, cacheable discovery plan from local code and issue playbooks.

This is deliberately a planner, not a detector. Every source file receives a
ledger row. Historical issues open local branches through mechanism/condition
playbooks; later phases must close each branch with evidence or an explicit
deferment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from discovery_plan_support import (
    EXT,
    MAX_MATCHED_PLAYBOOKS_PER_FILE,
    NON_RUNTIME_ROOTS,
    SKIP,
    branch_row_kinds,
    build_bounded_playbooks,
    choose_selected_families,
    digest,
    families,
    family_mechanism_map,
    family_score_map,
    file_surface_alignment,
    load_contextual_playbook_buckets,
    local_surfaces,
    mechanism_context_boosts,
    mechanism_counts,
    product_runtime_terms,
    terms,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--graph", required=True)
    parser.add_argument("--product-model", required=True)
    parser.add_argument("--context-input")
    parser.add_argument("--mode", choices=("normal", "deep"), required=True)
    parser.add_argument("--scope", action="append", default=[])
    parser.add_argument("--shard-size", type=int, default=40)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    product = json.loads(Path(args.product_model).read_text())
    graph = json.loads(Path(args.graph).read_text())
    contextual = json.loads(Path(args.context_input).read_text()) if args.context_input else None
    allowed = tuple(args.scope or ["."])

    def in_scope(path: Path) -> bool:
        rel = path.relative_to(root).as_posix()
        return args.mode == "deep" or any(rel == entry or rel.startswith(entry.rstrip("/") + "/") for entry in allowed)

    def runtime_candidate(rel: str, priority_surface: bool) -> bool:
        top = rel.split("/", 1)[0].strip().lower()
        if priority_surface:
            return True
        return top not in NON_RUNTIME_ROOTS

    raw_files = []
    family_document_frequency: Counter[str] = Counter()
    runtime_terms = product_runtime_terms(product)
    for path in sorted(root.rglob("*")):
        lower_parts = {part.lower() for part in path.parts}
        if not path.is_file() or path.suffix.lower() not in EXT or lower_parts & SKIP or not in_scope(path):
            continue
        raw = path.read_bytes()
        rel = path.relative_to(root).as_posix()
        text = raw[:65536].decode("utf-8", errors="replace")
        counts = mechanism_counts(rel + "\n" + text)
        observed_mechanisms = sorted(counts)
        surfaces = local_surfaces(rel + "\n" + text)
        aligned_surface_labels, priority_surface = file_surface_alignment(rel, product)
        runtime_term_hits = len(terms(rel) & runtime_terms)
        context_text = " ".join(
            [
                rel,
                " ".join(aligned_surface_labels),
                " ".join(surfaces),
                " ".join(sorted(terms(rel) & runtime_terms)),
            ]
        )
        context_boosts = mechanism_context_boosts(context_text)
        family_scores = family_score_map(counts, context_boosts)
        mechanisms_by_family = family_mechanism_map(counts, context_boosts)
        if not runtime_candidate(rel, priority_surface):
            continue
        if priority_surface:
            for family in list(family_scores):
                family_scores[family] += 4
        if runtime_term_hits:
            for family in list(family_scores):
                family_scores[family] += min(4, runtime_term_hits)
        for family in family_scores:
            family_document_frequency[family] += 1
        raw_files.append(
            {
                "id": "file:" + digest(rel),
                "path": rel,
                "language": EXT[path.suffix.lower()],
                "content_hash": hashlib.sha256(raw).hexdigest(),
                "observed_mechanisms": observed_mechanisms,
                "observed_mechanism_families": sorted(family_scores),
                "family_scores": family_scores,
                "mechanisms_by_family": mechanisms_by_family,
                "context_boosts": context_boosts,
                "surfaces": surfaces,
                "product_surface_labels": aligned_surface_labels,
                "priority_surface": priority_surface,
                "runtime_term_hits": runtime_term_hits,
            }
        )

    files = []
    total_files = len(raw_files)
    for item in raw_files:
        selected_families = choose_selected_families(item["family_scores"], family_document_frequency, total_files)
        selected_mechanisms = sorted(
            {
                mechanism
                for family in selected_families
                for mechanism in item["mechanisms_by_family"].get(family, [])
            }
        )
        files.append(
            {
                "id": item["id"],
                "path": item["path"],
                "language": item["language"],
                "content_hash": item["content_hash"],
                "mechanisms": selected_mechanisms,
                "mechanism_families": selected_families,
                "observed_mechanisms": item["observed_mechanisms"],
                "observed_mechanism_families": item["observed_mechanism_families"],
                "family_scores": item["family_scores"],
                "mechanisms_by_family": item["mechanisms_by_family"],
                "context_boosts": item["context_boosts"],
                "surfaces": item["surfaces"],
                "product_surface_labels": item["product_surface_labels"],
                "priority_surface": item["priority_surface"],
                "runtime_term_hits": item["runtime_term_hits"],
            }
        )
    files.sort(
        key=lambda item: (
            -int(bool(item.get("priority_surface"))),
            -int(item.get("runtime_term_hits", 0)),
            -sum(int(value) for value in item.get("family_scores", {}).values()),
            item.get("path", ""),
        )
    )

    stack = " ".join(
        str(value)
        for values in product.get("technology_stack", {}).values()
        if isinstance(values, list)
        for value in values
    )
    context = terms(stack + " " + json.dumps(product.get("product", {})))
    context.update(runtime_terms)
    playbooks = build_bounded_playbooks(load_contextual_playbook_buckets(contextual, graph, context))

    branches = []
    coverage_rows = []
    ledger = []
    for item in files:
        matched = []
        for book in playbooks:
            if not (set(item["mechanisms"]) & set(book["mechanisms"])):
                continue
            book_surfaces = set(book.get("surfaces", []))
            file_surface_union = set(item.get("surfaces", [])) | set(item.get("product_surface_labels", []))
            if book_surfaces and not (file_surface_union & book_surfaces):
                continue
            matched.append(book)
        matched.sort(key=lambda book: (-book["relevance"], book["id"]))
        matched = matched[:MAX_MATCHED_PLAYBOOKS_PER_FILE]
        file_branch_ids = []
        file_row_ids = []
        for book in matched:
            file_surface_union = set(item.get("surfaces", [])) | set(item.get("product_surface_labels", []))
            branch_mechanisms = sorted(set(item["mechanisms"]) & set(book["mechanisms"]))
            shared = families(branch_mechanisms)
            branch_id = "branch:" + digest(item["id"] + book["id"] + ",".join(shared))
            row_kinds = branch_row_kinds(item, shared, branch_mechanisms, book)
            row_ids = []
            branches.append(
                {
                    "id": branch_id,
                    "status": "open",
                    "file_id": item["id"],
                    "location": item["path"],
                    "playbook_id": book["id"],
                    "issue_example_ids": book["issue_example_ids"],
                    "mechanisms": branch_mechanisms,
                    "mechanism_families": shared,
                    "conditions": book["conditions"],
                    "oracle": book["oracle"],
                    "cache_key": digest(item["content_hash"] + book["id"]),
                    "required_receipts": ["discovery", "validation", "disposition"],
                    "row_kinds": row_kinds,
                    "priority_surface": item.get("priority_surface", False),
                    "product_surface_labels": item.get("product_surface_labels", []),
                }
            )
            for row_kind in row_kinds:
                row_id = "row:" + digest(branch_id + ":" + row_kind)
                coverage_rows.append(
                    {
                        "id": row_id,
                        "branch_id": branch_id,
                        "file_id": item["id"],
                        "location": item["path"],
                        "row_kind": row_kind,
                        "status": "open",
                        "mechanisms": branch_mechanisms,
                        "mechanism_families": shared,
                        "conditions": book["conditions"],
                        "surfaces": sorted(file_surface_union | set(book.get("surfaces", []))),
                        "priority_surface": item.get("priority_surface", False),
                        "closure_required": True,
                        "reason": "Coverage row anchored by product/runtime understanding plus local seam alignment.",
                    }
                )
                row_ids.append(row_id)
                file_row_ids.append(row_id)
            file_branch_ids.append(branch_id)
        ledger.append(
            {
                "file_id": item["id"],
                "location": item["path"],
                "content_hash": item["content_hash"],
                "status": "open",
                "branch_ids": file_branch_ids,
                "coverage_row_ids": file_row_ids,
            }
        )

    result = {
        "document_type": "bug-hunt.intelligent-discovery-plan",
        "schema_version": "1.0",
        "mode": args.mode,
        "inventory": files,
        "playbooks": playbooks,
        "branches": branches,
        "coverage_rows": coverage_rows,
        "work_ledger": ledger,
        "shards": [[item["id"] for item in files[index:index + args.shard_size]] for index in range(0, len(files), args.shard_size)],
        "coverage": {
            "total_files": len(files),
            "open_files": len(files),
            "total_rows": len(coverage_rows),
            "open_rows": len(coverage_rows),
            "closed": False,
            "uncovered_ids": [item["id"] for item in files],
        },
    }
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"ok": True, "files": len(files), "playbooks": len(playbooks), "branches": len(branches), "output": args.output}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
