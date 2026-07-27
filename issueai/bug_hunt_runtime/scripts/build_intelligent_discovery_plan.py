#!/usr/bin/env python3
"""Create a complete, cacheable discovery plan from local code and issue playbooks.

This is deliberately a planner, not a detector.  Every source file receives a
ledger row.  Historical issues open local branches through mechanism/condition
playbooks; later phases must close each branch with evidence or an explicit
deferment.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from collections import Counter, defaultdict
from pathlib import Path

EXT={".py":"python", ".js":"javascript", ".ts":"typescript", ".tsx":"typescript", ".go":"go", ".rs":"rust", ".java":"java", ".c":"c", ".cc":"cpp", ".cpp":"cpp", ".php":"php", ".rb":"ruby", ".swift":"swift", ".kt":"kotlin"}
SKIP={".git","node_modules","vendor","third_party","dist","build","__pycache__"}
NON_RUNTIME_ROOTS={"doc","docs","example","examples","test","tests","testing","fixture","fixtures","bench","benchmark","benchmarks","vendor","third_party","third-party"}
HINTS={
 "boundary":r"null|none|empty|invalid|parse|schema|limit|slice|convert",
 "precedence":r"config|default|fallback|override|merge|environment",
 "contract":r"type|schema|interface|validate|contract|optional",
 "lifecycle":r"close|cleanup|cancel|retry|timeout|timer|resource|release|dispose",
 "state":r"cache|session|reload|restart|state|snapshot|memo|reuse|stale|invalidate|refresh",
 "state_reuse":r"cache|session|reload|restart|state|snapshot|memo|reuse|stale|invalidate|refresh",
 "representation":r"encode|decode|normalize|canonical|unicode|path|url|version",
 "concurrency":r"async|thread|lock|queue|worker|race|parallel",
 "integration":r"adapter|backend|driver|plugin|http|rpc|subprocess",
 "compatibility":r"compat|platform|windows|linux|macos|legacy|runtime|release|version|feature|dependency",
 "observability":r"log|metric|telemetry|fallback|retry|health",
 "data_integrity":r"transaction|atomic|rollback|persist|ordering|duplicate",
}
MECHANISM_CONTEXT_HINTS = {
 "boundary": r"api|argument|body|boundary|field|header|input|json|message|null|parse|path|payload|query|request|response|route|schema|token|url",
 "precedence": r"config|default|env|environment|fallback|flag|merge|option|override|precedence|priority|setting",
 "contract": r"annotation|contract|dtype|interface|optional|protocol|shape|signature|type|typed|typing|validate",
 "lifecycle": r"async|asyncio|cancel|cleanup|close|dispose|drain|event|future|lease|loop|owner|process|release|resource|retry|shutdown|signal|stream|task|teardown|thread|timeout|timer|watch",
 "state": r"checkpoint|invalidate|memo|refresh|reload|restart|restore|resume|snapshot|stale|state",
 "state_reuse": r"cache|memo|pool|reuse|session|singleton|stale|store",
 "representation": r"canonical|decode|encode|format|normalize|parse|path|serialize|string|unicode|url|version",
 "concurrency": r"async|asyncio|await|concurrent|event|future|goroutine|ipc|lock|parallel|pool|process|promise|queue|race|signal|task|thread|worker",
 "integration": r"adapter|backend|bridge|client|compiler|connector|driver|gateway|http|inspector|plugin|provider|proxy|rpc|server|subprocess|tracing|transport",
 "compatibility": r"abi|api|compat|cross-version|dependency|legacy|platform|portable|version",
 "observability": r"alert|assert|debug|diagnostic|error|health|inspect|log|message|metric|monitor|notice|report|telemetry|trace|warning",
 "data_integrity": r"atomic|commit|consistency|dedup|duplicate|idempot|journal|ordering|persist|rollback|transaction",
}
MECHANISM_PRIORITY = {
 "lifecycle": 5,
 "state_reuse": 4,
 "data_integrity": 4,
 "state": 1,
}
SURFACE_HINTS = {
 "public_boundary": r"api|request|response|handler|parser|parse|schema|model|validation|validate|interface",
 "state_resource": r"cache|session|state|resource|timeout|timer|interval|queue|pool|store|snapshot|retry|manager",
 "adapter": r"adapter|backend|driver|plugin|client|server|http|rpc|subprocess|transport|connector",
 "normalization": r"normalize|canonical|encode|decode|serialize|deserialize|parse|path|url|version|format",
 "test_observability": r"test|assert|log|metric|trace|telemetry|health|report|debug|warning|error",
}
MAX_PLAYBOOKS_PER_FAMILY = 16
MAX_PLAYBOOKS_TOTAL = 120
MAX_MATCHED_PLAYBOOKS_PER_FILE = 3
MAX_COVERAGE_ROWS_PER_BRANCH = 4
FAMILY_MAP={
 "boundary":"boundary",
 "precedence":"boundary",
 "contract":"contract",
 "representation":"contract",
 "lifecycle":"state-lifecycle",
 "state":"state-lifecycle",
 "state_reuse":"state-lifecycle",
 "data_integrity":"state-lifecycle",
 "integration":"integration",
 "compatibility":"compatibility",
 "concurrency":"concurrency",
 "observability":"observability",
}

ROW_KIND_HINTS = {
    "root_control": {"families": set(), "surfaces": set()},
    "owner_transition": {"families": {"state-lifecycle"}, "surfaces": {"state_resource"}},
    "concrete_instance": {"families": {"integration", "compatibility"}, "surfaces": {"adapter"}},
    "boundary_contract": {"families": {"boundary", "contract"}, "surfaces": {"public_boundary", "normalization"}},
    "failure_signal": {"families": {"observability", "state-lifecycle", "integration"}, "surfaces": {"test_observability", "state_resource", "adapter"}},
}


def mechanism_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, pattern in HINTS.items():
        count = len(re.findall(pattern, text, re.I))
        if count > 0:
            counts[name] = count
    return counts


def mechanism_context_boosts(context_text: str) -> dict[str, int]:
    boosts: dict[str, int] = {}
    for mechanism, pattern in MECHANISM_CONTEXT_HINTS.items():
        count = len(re.findall(pattern, context_text, re.I))
        if count > 0:
            boosts[mechanism] = count
    return boosts


def family_score_map(counts: dict[str, int], boosts: dict[str, int] | None = None) -> dict[str, int]:
    scores: defaultdict[str, int] = defaultdict(int)
    for mechanism, count in counts.items():
        scores[FAMILY_MAP.get(mechanism, mechanism)] += count
    for mechanism, boost in (boosts or {}).items():
        scores[FAMILY_MAP.get(mechanism, mechanism)] += boost * 3
    return dict(scores)


def family_mechanism_map(counts: dict[str, int], boosts: dict[str, int] | None = None) -> dict[str, list[str]]:
    grouped: defaultdict[str, list[tuple[int, str]]] = defaultdict(list)
    for mechanism, count in counts.items():
        weighted = count + ((boosts or {}).get(mechanism, 0) * 3)
        grouped[FAMILY_MAP.get(mechanism, mechanism)].append((weighted, mechanism))
    result: dict[str, list[str]] = {}
    for family, entries in grouped.items():
        entries.sort(key=lambda item: (-item[0], -MECHANISM_PRIORITY.get(item[1], 2), item[1]))
        result[family] = [entries[0][1]]
    return result


def choose_selected_families(
    family_scores: dict[str, int],
    family_document_frequency: Counter[str],
    total_files: int,
) -> list[str]:
    ranked: list[tuple[float, str]] = []
    for family, score in family_scores.items():
        saturation = family_document_frequency.get(family, 0) / max(1, total_files)
        adjusted = score / (1.0 + saturation * 6.0)
        ranked.append((adjusted, family))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    selected = [family for adjusted, family in ranked if adjusted >= 1.1][:2]
    if selected:
        return selected
    return [ranked[0][1]] if ranked else []


def local_surfaces(text: str) -> list[str]:
    return sorted(name for name, pattern in SURFACE_HINTS.items() if re.search(pattern, text, re.I))


def family_of(mechanism: str) -> str:
    return FAMILY_MAP.get(mechanism, mechanism)

def digest(value: str) -> str: return hashlib.sha256(value.encode()).hexdigest()[:20]
def terms(value: str) -> set[str]: return set(re.findall(r"[a-z][a-z0-9+._-]+", value.lower()))
def families(values): return sorted({FAMILY_MAP.get(value, value) for value in values})


def product_surface_paths(product: dict) -> list[tuple[str, tuple[str, ...], str]]:
    rows = []
    for row in product.get("surfaces", []) or []:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or row.get("id") or "").strip()
        paths = tuple(
            str(value).strip("/").lower()
            for value in row.get("paths", []) or []
            if str(value).strip("/").strip()
        )
        disposition = str(row.get("disposition") or "reviewed")
        if label or paths:
            rows.append((label.lower(), paths, disposition))
    return rows


def product_runtime_terms(product: dict) -> set[str]:
    values: list[str] = []
    values.extend(str(item.get("name", "")) for item in product.get("product", {}).get("capabilities", []) if isinstance(item, dict))
    values.extend(str(item.get("name", "")) for item in product.get("product", {}).get("features", []) if isinstance(item, dict))
    values.extend(str(item.get("label", "")) for item in product.get("architecture", {}).get("modules", []) if isinstance(item, dict))
    values.extend(str(item.get("label", "")) for item in product.get("architecture", {}).get("integration_points", []) if isinstance(item, dict))
    values.extend(str(item.get("from", "")) for item in product.get("architecture", {}).get("boundaries", []) if isinstance(item, dict))
    values.extend(str(item.get("to", "")) for item in product.get("architecture", {}).get("boundaries", []) if isinstance(item, dict))
    values.extend(str(item.get("subject", "")) for item in product.get("contracts", []) if isinstance(item, dict))
    values.extend(str(item.get("promise", "")) for item in product.get("contracts", []) if isinstance(item, dict))
    return terms(" ".join(values))


def file_surface_alignment(rel: str, product: dict) -> tuple[list[str], bool]:
    lowered = rel.lower()
    aligned: list[str] = []
    priority = False
    for label, paths, disposition in product_surface_paths(product):
        if paths and any(lowered == path or lowered.startswith(path + "/") for path in paths):
            if label and label not in aligned:
                aligned.append(label)
            if disposition == "priority":
                priority = True
    return sorted(aligned), priority


def branch_row_kinds(file_entry: dict, branch_families: list[str], branch_mechanisms: list[str], book: dict) -> list[str]:
    observed_surfaces = set(file_entry.get("surfaces", []))
    observed_surfaces.update(file_entry.get("product_surface_labels", []))
    observed_surfaces.update(book.get("surfaces", []))
    families_set = set(branch_families)
    mechanisms_set = set(branch_mechanisms)
    kinds = ["root_control"]
    for row_kind, hints in ROW_KIND_HINTS.items():
        if row_kind == "root_control":
            continue
        if families_set & hints["families"] or observed_surfaces & hints["surfaces"]:
            kinds.append(row_kind)
        elif row_kind == "failure_signal" and "observability" in mechanisms_set:
            kinds.append(row_kind)
    return kinds[:MAX_COVERAGE_ROWS_PER_BRANCH]

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--graph", required=True)
    p.add_argument("--product-model", required=True)
    p.add_argument("--context-input")
    p.add_argument("--mode", choices=("normal", "deep"), required=True)
    p.add_argument("--scope", action="append", default=[])
    p.add_argument("--shard-size", type=int, default=40)
    p.add_argument("--output", required=True)
    a = p.parse_args()

    root = Path(a.repo).resolve()
    product = json.loads(Path(a.product_model).read_text())
    graph = json.loads(Path(a.graph).read_text())
    contextual = json.loads(Path(a.context_input).read_text()) if a.context_input else None
    allowed = tuple(a.scope or ["."])

    def in_scope(path: Path) -> bool:
        rel = path.relative_to(root).as_posix()
        return a.mode == "deep" or any(rel == entry or rel.startswith(entry.rstrip("/") + "/") for entry in allowed)

    def runtime_candidate(rel: str, priority_surface: bool) -> bool:
        top = rel.split("/", 1)[0].strip().lower()
        if priority_surface:
            return True
        if top in NON_RUNTIME_ROOTS:
            return False
        return True

    raw_files = []
    family_document_frequency: Counter[str] = Counter()
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
        runtime_term_hits = len(terms(rel) & product_runtime_terms(product))
        context_text = " ".join(
            [
                rel,
                " ".join(aligned_surface_labels),
                " ".join(surfaces),
                " ".join(sorted(terms(rel) & product_runtime_terms(product))),
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
        raw_files.append({
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
        })
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
        files.append({
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
        })
    files.sort(
        key=lambda item: (
            -int(bool(item.get("priority_surface"))),
            -int(item.get("runtime_term_hits", 0)),
            -sum(int(value) for value in item.get("family_scores", {}).values()),
            item.get("path", ""),
        )
    )

    stack = " ".join(str(x) for values in product.get("technology_stack", {}).values() if isinstance(values, list) for x in values)
    context = terms(stack + " " + json.dumps(product.get("product", {})))
    context.update(product_runtime_terms(product))
    grouped = {}
    if contextual:
        source_rows = contextual.get("deep_hypothesis_input", []) or contextual.get("rank_input", [])
        for row in source_rows:
            mech = set(row.get("mechanisms", []))
            if not mech:
                continue
            relevance = float(row.get("score", 0))
            if relevance <= 0:
                continue
            condition_key = tuple(sorted(row.get("conditions", []))[:2])
            surface_key = tuple(sorted(row.get("surfaces", []))[:2])
            for mechanism in mech:
                key = (mechanism, condition_key, surface_key)
                bucket = grouped.setdefault(
                    key,
                    {
                        "mechanism": mechanism,
                        "mechanism_family": family_of(mechanism),
                        "issue_example_ids": [],
                        "conditions": set(),
                        "surfaces": set(),
                        "relevance": 0,
                    },
                )
                bucket["issue_example_ids"].extend(row.get("issue_example_ids", []))
                bucket["conditions"].update(row.get("conditions", []))
                bucket["surfaces"].update(row.get("surfaces", []))
                bucket["relevance"] += relevance
    else:
        for node in graph.get("nodes", []):
            if node.get("type") != "issue":
                continue
            attrs = node.get("attributes", {})
            mech = set(attrs.get("mechanisms", []))
            tech = terms(" ".join(map(str, attrs.get("technology", []))))
            if not mech:
                continue
            relevance = len(tech & context) * 3 + len(mech)
            if not relevance:
                continue
            condition_key = tuple(sorted(attrs.get("conditions", []))[:2])
            surface_key = tuple(sorted(attrs.get("surfaces", []))[:2])
            for mechanism in mech:
                key = (mechanism, condition_key, surface_key)
                bucket = grouped.setdefault(
                    key,
                    {
                        "mechanism": mechanism,
                        "mechanism_family": family_of(mechanism),
                        "issue_example_ids": [],
                        "conditions": set(),
                        "surfaces": set(),
                        "relevance": 0,
                    },
                )
                bucket["issue_example_ids"].append(node["id"])
                bucket["conditions"].update(attrs.get("conditions", []))
                bucket["surfaces"].update(attrs.get("surfaces", []))
                bucket["relevance"] += relevance

    playbooks = []
    for _, bucket in grouped.items():
        signature = ",".join([bucket["mechanism"], *sorted(bucket["conditions"]), *sorted(bucket["surfaces"])])
        playbooks.append({
            "id": "playbook:" + bucket["mechanism"] + ":" + digest(signature),
            "issue_example_ids": sorted(bucket["issue_example_ids"])[:24],
            "mechanisms": [bucket["mechanism"]],
            "mechanism_families": [bucket["mechanism_family"]],
            "conditions": sorted(bucket["conditions"]),
            "surfaces": sorted(bucket["surfaces"]),
            "oracle": "Prove the local contract across the historical rare transition, then compare a negative control.",
            "relevance": bucket["relevance"],
        })
    playbooks.sort(key=lambda x: (-x["relevance"], x["id"]))
    bounded_playbooks = []
    family_counts: Counter[str] = Counter()
    for playbook in playbooks:
        family = playbook["mechanism_families"][0]
        if family_counts[family] >= MAX_PLAYBOOKS_PER_FAMILY:
            continue
        bounded_playbooks.append(playbook)
        family_counts[family] += 1
        if len(bounded_playbooks) >= MAX_PLAYBOOKS_TOTAL:
            break
    playbooks = bounded_playbooks

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
            branch_mechanisms = sorted(set(item["mechanisms"]) & set(book["mechanisms"]))
            shared = families(branch_mechanisms)
            branch_id = "branch:" + digest(item["id"] + book["id"] + ",".join(shared))
            row_kinds = branch_row_kinds(item, shared, branch_mechanisms, book)
            row_ids = []
            branches.append({
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
            })
            for row_kind in row_kinds:
                row_id = "row:" + digest(branch_id + ":" + row_kind)
                coverage_rows.append({
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
                })
                row_ids.append(row_id)
                file_row_ids.append(row_id)
            file_branch_ids.append(branch_id)
        ledger.append({"file_id": item["id"], "location": item["path"], "content_hash": item["content_hash"], "status": "open", "branch_ids": file_branch_ids, "coverage_row_ids": file_row_ids})

    result = {
        "document_type": "bug-hunt.intelligent-discovery-plan",
        "schema_version": "1.0",
        "mode": a.mode,
        "inventory": files,
        "playbooks": playbooks,
        "branches": branches,
        "coverage_rows": coverage_rows,
        "work_ledger": ledger,
        "shards": [[x["id"] for x in files[i:i + a.shard_size]] for i in range(0, len(files), a.shard_size)],
        "coverage": {"total_files": len(files), "open_files": len(files), "total_rows": len(coverage_rows), "open_rows": len(coverage_rows), "closed": False, "uncovered_ids": [x["id"] for x in files]},
    }
    Path(a.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"ok": True, "files": len(files), "playbooks": len(playbooks), "branches": len(branches), "output": a.output}, sort_keys=True))
    return 0
if __name__=="__main__": raise SystemExit(main())
