#!/usr/bin/env python3
"""Build a structured evidence graph from Bug Hunt's issue corpora."""
from __future__ import annotations

import argparse
import collections
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
    "data_integrity": "state-lifecycle",
    "integration": "integration",
    "concurrency": "concurrency",
    "observability": "observability",
}

MECHANISMS = {
    "boundary": r"empty|null|none|zero|negative|partial|invalid|malformed|limit|overflow|truncate|duplicate",
    "precedence": r"default|fallback|environment|config|override|explicit|setdefault",
    "contract": r"api|schema|type|contract|expected|interface|inconsistent|return",
    "lifecycle": r"close|cleanup|teardown|eof|stream|cancel|retry|redirect|flush|shutdown|timer|timeout|resource|finali[sz]|ownership|release|dispose|destroy",
    "state": r"cache|stale|reload|session|second run|restart|rollback|incremental|reuse",
    "representation": r"encode|unicode|utf|bytes|url|path|version|label|name|canonical|normalize|format",
    "concurrency": r"race|thread|concurrent|async|deadlock|hang|worker|lock|parallel|intermittent",
    "integration": r"plugin|adapter|driver|backend|dependency|platform|subprocess|openblas|runtime",
    "observability": r"silent|missing|not reported|log|telemetry|fallback|hard to reproduce|intermittent",
    "data_integrity": r"data loss|corrupt|duplicate|ordering|atomic|rollback|inconsistent state",
}
CONDITIONS = {
    "common_path_passes": r"works|working|normal|common|only when|except|passes",
    "transition": r"after|before|during|until|second|restart|teardown|redirect|reload|retry",
    "delayed_effect": r"later|eventually|intermittent|sporadic|only after|memory leak|hang|timeout",
    "environment_cell": r"windows|linux|macos|python|node|java|rust|openblas|backend|driver|dependency|platform",
    "expected_observed": r"expected|should|actual|instead|but|however|returns|raises|fails|does not",
}
SURFACES = {
    "public_boundary": r"api|request|handler|cli|serializer|parser|schema|endpoint|webhook",
    "state_resource": r"cache|session|stream|socket|file|worker|queue|transaction|generator",
    "adapter": r"adapter|backend|driver|plugin|platform|subprocess|dependency",
    "normalization": r"encode|decode|unicode|url|path|version|normalize|canonical|identity",
    "test_observability": r"test|fixture|mock|metric|log|telemetry|health|retry|fallback",
}


def text(issue: dict) -> str:
    derived = issue.get("derived", {})
    evidence = issue.get("evidence", {})
    return " ".join(str(issue.get(key, "")) for key in ("title", "body", "repository", "labels", "query_family", "research_signals", "escape_chain_coverage")) + " " + " ".join(str(derived.get(key, "")) for key in ("mechanisms", "conditions", "surfaces", "technology", "expected_observed", "oracle", "failure_chain")) + " " + " ".join(str(evidence.get(key, "")) for key in ("signals", "evidence_score"))


def derived_values(issue: dict, key: str) -> list[str]:
    value = issue.get("derived", {}).get(key, [])
    return sorted({str(item).lower() for item in value if item}) if isinstance(value, list) else []


def ids(prefix: str, values: list[str]) -> list[str]:
    return [f"{prefix}:{value}" for value in values]


def families(values: list[str]) -> list[str]:
    return sorted({MECHANISM_FAMILY_MAP.get(value, value) for value in values})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    taxonomy = {
        "mechanisms": sorted(MECHANISMS),
        "mechanism_families": sorted(set(MECHANISM_FAMILY_MAP.values())),
        "playbook_families": {},
        "conditions": sorted(CONDITIONS),
        "surfaces": sorted(SURFACES),
    }
    playbook_family_index: dict[str, dict[str, set[str] | int]] = collections.defaultdict(
        lambda: {"count": 0, "signatures": set(), "issue_ids": set()}
    )
    total = 0
    for source_name in args.input:
        source = json.loads(Path(source_name).read_text(encoding="utf-8"))
        issues = source.get("issues", source) if isinstance(source, dict) else source
        for index, issue in enumerate(issues):
            total += 1
            issue_key = issue.get("url") or issue.get("case_id") or f"{issue.get('repository')}#{issue.get('issue_number')}"
            issue_id = "issue:" + hashlib.sha256(issue_key.encode()).hexdigest()[:20]
            body = str(issue.get("body", ""))
            all_text = text(issue)
            mechanisms = sorted(set(derived_values(issue, "mechanisms")) | {key for key, pattern in MECHANISMS.items() if re.search(pattern, all_text, re.I)})
            mechanism_families = families(mechanisms)
            conditions = sorted(set(derived_values(issue, "conditions")) | {key for key, pattern in CONDITIONS.items() if re.search(pattern, all_text, re.I)})
            surfaces = sorted(set(derived_values(issue, "surfaces")) | {key for key, pattern in SURFACES.items() if re.search(pattern, all_text, re.I)})
            technology = sorted(set(re.findall(r"\b(?:python|node|java|rust|go|ruby|php|c\+\+|windows|linux|macos|openblas|asyncio|http|grpc|sql|postgres|mysql|redis|kubernetes|docker)\b", all_text, re.I)))
            technology = sorted(set(technology) | set(derived_values(issue, "technology")))
            playbook = issue.get("playbook", {}) if isinstance(issue.get("playbook"), dict) else {}
            playbook_family = str(playbook.get("playbook_family", "")).lower().strip()
            playbook_signature = str(playbook.get("playbook_signature", "")).strip()
            if playbook_family:
                entry = playbook_family_index[playbook_family]
                entry["count"] += 1
                entry["issue_ids"].add(issue_id)
                if playbook_signature:
                    entry["signatures"].add(playbook_signature)
            attributes = {"repository": issue.get("repository"), "issue_number": issue.get("issue_number"), "case_id": issue.get("case_id"), "title": issue.get("title"), "summary": body[:800], "mechanisms": mechanisms, "mechanism_families": mechanism_families, "conditions": conditions, "surfaces": surfaces, "technology": technology, "complexity_tier": issue.get("complexity_tier"), "validation_status": issue.get("validation", {}).get("status"), "evidence_score": issue.get("evidence", {}).get("evidence_score"), "playbook_family": playbook_family, "playbook_signature": playbook_signature}
            nodes[issue_id] = {"id": issue_id, "type": "issue", "attributes": attributes, "evidence": {"source": source_name, "record_index": index, "url": issue.get("url")}}
            related = [("mechanism", mechanisms), ("condition", conditions), ("surface", surfaces), ("technology", technology)]
            if issue.get("complexity_tier"):
                related.append(("complexity", [str(issue["complexity_tier"]).lower()]))
            if issue.get("validation", {}).get("status"):
                related.append(("validation", [str(issue["validation"]["status"]).lower()]))
            if playbook_family or playbook_signature:
                playbook_id = "playbook:" + hashlib.sha256((playbook_signature or issue_key).encode()).hexdigest()[:20]
                nodes.setdefault(playbook_id, {"id": playbook_id, "type": "playbook", "attributes": {"family": playbook_family or "unknown", "signature": playbook_signature or issue_key}, "evidence": {"source": source_name, "record_index": index}})
                edges.append({"from": issue_id, "to": playbook_id, "relation": "exhibits_playbook", "evidence_ids": [issue_id]})
            for node_type, values in related:
                for value in values:
                    node_id = f"{node_type}:{value.lower()}"
                    nodes.setdefault(node_id, {"id": node_id, "type": node_type, "attributes": {"name": value.lower()}, "evidence": {"source": source_name, "record_index": index}})
                    edges.append({"from": issue_id, "to": node_id, "relation": f"exhibits_{node_type}", "evidence_ids": [issue_id]})
            for left in mechanisms:
                for right in conditions:
                    edges.append({"from": f"mechanism:{left}", "to": f"condition:{right}", "relation": "co_occurs_with", "evidence_ids": [issue_id]})
    taxonomy["playbook_families"] = {
        family: {
            "count": data["count"],
            "signatures": sorted(data["signatures"]),
            "issue_ids": sorted(data["issue_ids"]),
        }
        for family, data in sorted(playbook_family_index.items())
    }
    unique_edges = {(edge["from"], edge["to"], edge["relation"]): edge for edge in edges}
    result = {"document_type": "bug-hunt.issue-evidence-graph", "schema_version": "1.0", "corpora": args.input, "nodes": sorted(nodes.values(), key=lambda item: item["id"]), "edges": sorted(unique_edges.values(), key=lambda item: (item["from"], item["to"], item["relation"])), "taxonomy": taxonomy, "summary": {"issues": total, "nodes": len(nodes), "edges": len(unique_edges)}}
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, **result["summary"], "output": args.output}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
