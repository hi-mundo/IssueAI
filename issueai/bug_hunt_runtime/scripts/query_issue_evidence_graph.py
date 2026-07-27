#!/usr/bin/env python3
"""Resolve technology/product context into rank and deep-hypothesis inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

MECHANISM_FAMILY_MAP = {
    "boundary": "boundary",
    "precedence": "boundary",
    "contract": "contract",
    "representation": "contract",
    "lifecycle": "state-lifecycle",
    "state": "state-lifecycle",
    "state_reuse": "state-lifecycle",
    "data_integrity": "state-lifecycle",
    "integration": "integration",
    "compatibility": "compatibility",
    "concurrency": "concurrency",
    "observability": "observability",
}

PLAYBOOK_MECHANISM_HINTS = {
    "state-transition-regression": ["state_reuse", "lifecycle"],
    "state-reuse": ["state_reuse"],
    "suppressed-failure-signal": ["observability"],
    "intermittent-failure-with-weak-signal": ["concurrency", "observability"],
    "alternate-cell-integration-mismatch": ["integration", "compatibility"],
    "integration-failure-hidden-by-success-signal": ["integration", "observability"],
    "declared-support-vs-runtime-cell": ["compatibility", "integration"],
    "explicit-input-loses-to-fallback": ["precedence"],
    "normalized-shape-vs-consumed-shape": ["representation", "contract"],
    "validated-shape-vs-consumed-shape": ["representation", "contract"],
    "concurrent-contract-drift": ["concurrency", "contract"],
    "boundary": ["boundary"],
    "contract": ["contract"],
    "integration": ["integration"],
    "compatibility": ["compatibility"],
    "concurrency": ["concurrency"],
    "lifecycle": ["lifecycle"],
}


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


LOCAL_HINTS = {
    "boundary": r"api|request|handler|parser|schema|model|conversion|array|wrapper|exception",
    "precedence": r"config|option|setting|default|fallback|override|merge|marker|env",
    "contract": r"api|schema|type|interface|protocol|model|validation",
    "lifecycle": r"stream|response|connector|teardown|cleanup|close|retry|redirect|eof|transaction|timer|timeout|resource|manager|owner|release|dispose|destroy|finali[sz]",
    "state": r"cache|increment|reload|session|memo|build|snapshot|state|reuse|stale|invalidate|refresh",
    "state_reuse": r"cache|increment|reload|session|memo|build|snapshot|state|reuse|stale|invalidate|refresh",
    "representation": r"parser|parse|version|marker|array|string|encoding|unicode|location|url|path|json|dialect",
    "concurrency": r"thread|lock|async|worker|queue|runtime|pool|parallel|atomic|callback",
    "integration": r"adapter|backend|driver|platform|pipe|network|http|plugin|remote|subprocess|compose|kube|dns",
    "compatibility": r"compat|platform|windows|linux|macos|legacy|runtime|release|version|feature|dependency",
    "observability": r"remote|metric|log|health|report|progress|trace|retry|fallback",
    "data_integrity": r"transaction|persist|database|state|rollback|atomic|ordering|unique",
}

def family_of(mechanism: str) -> str:
    return MECHANISM_FAMILY_MAP.get(mechanism, mechanism)


def implied_mechanisms(playbook_family: str) -> list[str]:
    return PLAYBOOK_MECHANISM_HINTS.get(playbook_family, [])


def choose_contextual_mechanisms(
    raw_mechanisms: list[str],
    playbook_family: str,
    issue_text: str,
    local_mechanism_scores: dict[str, int],
) -> list[str]:
    narrowed = implied_mechanisms(playbook_family)
    if narrowed and len(raw_mechanisms) >= 6:
        return sorted(dict.fromkeys(narrowed))
    text_matches = {name for name, pattern in LOCAL_HINTS.items() if re.search(pattern, issue_text, re.I)}
    ranked: list[tuple[int, str]] = []
    for mechanism in raw_mechanisms:
        score = 0
        score += min(6, local_mechanism_scores.get(mechanism, 0))
        if mechanism in text_matches:
            score += 5
        if mechanism in narrowed:
            score += 4
        if family_of(mechanism) == "state-lifecycle" and ("timeout" in issue_text or "retry" in issue_text or "stream" in issue_text):
            score += 2
        ranked.append((score, mechanism))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    selected = [mechanism for score, mechanism in ranked if score > 0][:3]
    lifecycle_dominant = bool(
        re.search(r"close|cleanup|leak|retry|stream|timeout|teardown|dispose|release|redirect|cookie|session|resource", issue_text, re.I)
    )
    explicit_concurrency = bool(re.search(r"race|deadlock|parallel|thread|lock|worker|queue", issue_text, re.I))
    if "state" in selected and "state_reuse" in raw_mechanisms:
        selected = ["state_reuse" if mechanism == "state" else mechanism for mechanism in selected]
    if lifecycle_dominant and not explicit_concurrency and "lifecycle" in selected and "concurrency" in selected:
        selected = [mechanism for mechanism in selected if mechanism != "concurrency"]
    if selected:
        return sorted(dict.fromkeys(selected))
    return sorted(dict.fromkeys(raw_mechanisms[:2]))


def collect_context_terms(product: dict, repository_map: dict) -> tuple[set[str], set[str], set[str], set[str], set[str]]:
    stack = product.get("technology_stack", {})
    context_terms = {str(value).lower() for values in stack.values() if isinstance(values, list) for value in values}
    product_terms = set(re.findall(r"[a-z][a-z0-9+.-]+", json.dumps(product.get("product", {})).lower()))
    contract_terms = set(re.findall(r"[a-z][a-z0-9+.-]+", json.dumps(product.get("contracts", [])).lower()))
    surface_terms = set(re.findall(r"[a-z][a-z0-9+.-]+", json.dumps(product.get("surfaces", [])).lower()))
    tendency_terms = set(re.findall(r"[a-z][a-z0-9+.-]+", json.dumps(product.get("implementation_tendencies", [])).lower()))
    module_terms = set(re.findall(r"[a-z][a-z0-9+.-]+", json.dumps(product.get("architecture", {}).get("modules", [])).lower()))
    boundary_terms = set(re.findall(r"[a-z][a-z0-9+.-]+", json.dumps(product.get("architecture", {}).get("boundaries", [])).lower()))
    context_terms.update(product_terms | contract_terms | surface_terms | tendency_terms | module_terms | boundary_terms)
    return context_terms, product_terms, contract_terms, surface_terms, tendency_terms


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", required=True)
    parser.add_argument("--product-model", required=True)
    parser.add_argument("--normalized", required=True)
    parser.add_argument("--map", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()
    graph = load(args.graph)
    product = load(args.product_model)
    normalized = load(args.normalized)
    repository_map = load(args.map)
    context_terms, product_terms, contract_terms, surface_terms, tendency_terms = collect_context_terms(product, repository_map)
    path_text = " ".join(str(node.get("location", "")) for node in repository_map.get("nodes", []))
    repository_name = str(product.get("repository", "")).lower()
    local_mechanism_scores = {name: min(3, len(re.findall(pattern, path_text, re.I))) for name, pattern in LOCAL_HINTS.items()}
    issues = [node for node in graph.get("nodes", []) if node.get("type") == "issue"]
    ranked = []
    for issue in issues:
        attrs = issue.get("attributes", {})
        tech = {str(value).lower() for value in attrs.get("technology", [])}
        raw_mechanisms = list(attrs.get("mechanisms", []))
        raw_families = list(attrs.get("mechanism_families", [])) or sorted({family_of(value) for value in raw_mechanisms})
        playbook_family = str(attrs.get("playbook_family", "")).strip().lower()
        playbook_signature = str(attrs.get("playbook_signature", "")).strip()
        issue_text = f"{attrs.get('title', '')} {attrs.get('summary', '')}".lower()
        narrow = {name for name, pattern in LOCAL_HINTS.items() if re.search(pattern, issue_text, re.I)}
        mechanisms = choose_contextual_mechanisms(raw_mechanisms, playbook_family, issue_text, local_mechanism_scores)
        matched_local_mechanisms = sorted({value for value in mechanisms if local_mechanism_scores.get(value, 0) > 0} | (narrow & set(mechanisms)))
        mechanism_families = sorted({family_of(value) for value in mechanisms} | {family_of(value) for value in matched_local_mechanisms})
        local_matches = [value for value in mechanisms if local_mechanism_scores.get(value, 0) > 0]
        title_terms = set(re.findall(r"[a-z][a-z0-9+.-]+", str(attrs.get("title", "")).lower()))
        issue_terms = set(re.findall(r"[a-z][a-z0-9+.-]+", issue_text))
        specificity_penalty = max(0, len(raw_mechanisms) - 4) * 3 + max(0, len(mechanism_families) - 3) * 2
        same_repo_bonus = 24 if repository_name and str(attrs.get("repository", "")).lower() == repository_name else 0
        playbook_bonus = 0
        if playbook_family and playbook_family != "generic-contract-transition":
            playbook_bonus += 10
        if playbook_signature:
            playbook_bonus += 4
        score = (
            len(tech & context_terms) * 5
            + sum(local_mechanism_scores.get(value, 0) for value in local_matches) * 2
            + len(title_terms & product_terms) * 2
            + len(issue_terms & contract_terms) * 3
            + len(issue_terms & surface_terms) * 4
            + len(issue_terms & tendency_terms) * 2
            + same_repo_bonus
            + playbook_bonus
            - specificity_penalty
        )
        if score <= 0:
            continue
        issue_id = issue["id"]
        ranked.append((score, issue_id, attrs, mechanisms, mechanism_families, matched_local_mechanisms, issue_text, playbook_family, playbook_signature))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    rank_input = []
    deep_input = []
    for score, issue_id, attrs, mechanisms, mechanism_families, matched_local_mechanisms, issue_text, playbook_family, playbook_signature in ranked[: args.limit]:
        row_id = "context-row:" + hashlib.sha256(f"{issue_id}:{score}".encode()).hexdigest()[:16]
        keywords = sorted(set(re.findall(r"[a-z][a-z0-9_-]{3,}", issue_text, re.I)) - {"that", "this", "with", "from", "when", "after", "does", "doesn", "should"})
        row = {"row_id": row_id, "issue_example_ids": [issue_id], "score": score, "repository": attrs.get("repository"), "title": attrs.get("title"), "keywords": keywords[:40], "mechanisms": mechanisms, "mechanism_subtypes": mechanisms, "mechanism_families": mechanism_families, "conditions": attrs.get("conditions", []), "surfaces": attrs.get("surfaces", []), "technology": attrs.get("technology", []), "matched_local_mechanisms": matched_local_mechanisms, "matched_local_families": sorted({family_of(value) for value in matched_local_mechanisms}), "playbook_family": playbook_family, "playbook_signature": playbook_signature, "evidence": [issue_id]}
        rank_input.append(row)
        deep_input.append({**row, "required_closure": ["local_contract", "exact_boundary", "escape_cell", "oracle", "concrete_probe"], "status": "open"})
    result = {"document_type": "bug-hunt.contextual-discovery-input", "schema_version": "1.0", "context_id": "ctx-" + hashlib.sha256(json.dumps(sorted(context_terms)).encode()).hexdigest()[:16], "repository_context": {"technology_terms": sorted(context_terms), "product_terms": sorted(product_terms), "contract_terms": sorted(contract_terms), "surface_terms": sorted(surface_terms), "implementation_tendency_terms": sorted(tendency_terms), "local_mechanism_scores": local_mechanism_scores, "normalized_files": len(normalized.get("files", [])), "map_nodes": len(repository_map.get("nodes", [])), "product": product.get("product", {})}, "rank_input": rank_input, "deep_hypothesis_input": deep_input, "coverage": {"issue_nodes_considered": len(issues), "contextual_rows": len(deep_input), "deferred_context": []}}
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "issue_nodes_considered": len(issues), "contextual_rows": len(deep_input), "output": args.output}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
