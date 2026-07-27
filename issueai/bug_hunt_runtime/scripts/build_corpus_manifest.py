#!/usr/bin/env python3
"""Build an auditable corpus inventory and coverage manifest."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

MECHANISM_FAMILY_MAP = {
    "contract": "contract",
    "representation": "contract",
    "type_schema": "contract",
    "boundary": "boundary",
    "precedence": "boundary",
    "lifecycle": "state-lifecycle",
    "state": "state-lifecycle",
    "resource": "state-lifecycle",
    "integration": "integration",
    "compatibility": "compatibility",
    "concurrency": "concurrency",
    "observability": "observability",
    "purpose_mismatch": "intent-drift",
    "organizational_drift": "intent-drift",
    "intent-drift": "intent-drift",
}


def values(record: dict, section: str, key: str) -> list[str]:
    value = record.get(section, {}).get(key, [])
    return [str(item).lower() for item in value] if isinstance(value, list) else []


def mechanism_families(record: dict) -> list[str]:
    families: list[str] = []
    seen: set[str] = set()
    for mechanism in values(record, "derived", "mechanisms"):
        family = MECHANISM_FAMILY_MAP.get(mechanism, mechanism)
        if family not in seen:
            seen.add(family)
            families.append(family)
    return families


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    records: list[dict] = []
    for source in args.input:
        payload = json.loads(Path(source).read_text(encoding="utf-8"))
        records.extend(payload.get("issues", payload) if isinstance(payload, dict) else payload)
    urls = [record.get("url") for record in records if record.get("url")]
    mechanism_subtypes = Counter(item for record in records for item in values(record, "derived", "mechanisms"))
    mechanism_families_counter = Counter(item for record in records for item in mechanism_families(record))
    conditions = Counter(item for record in records for item in values(record, "derived", "conditions"))
    surfaces = Counter(item for record in records for item in values(record, "derived", "surfaces"))
    tiers = Counter(record.get("complexity_tier", "legacy") for record in records)
    validation = Counter(record.get("validation", {}).get("status", "legacy") for record in records)
    missing = Counter()
    for record in records:
        evidence = record.get("evidence", {})
        derived = record.get("derived", {})
        for field in ("expected_observed", "oracle", "failure_chain"):
            if not derived.get(field):
                missing[field] += 1
        if not evidence.get("signals"):
            missing["evidence_signals"] += 1
    manifest = {
        "document_type": "bug-hunt.corpus-manifest",
        "schema_version": "1.0",
        "corpora": args.input,
        "inventory": {
            "records": len(records),
            "unique_urls": len(set(urls)),
            "duplicate_urls": len(urls) - len(set(urls)),
            "repositories": len({record.get("repository") for record in records if record.get("repository")}),
        },
        "coverage": {
            "complexity_tier": dict(sorted(tiers.items())),
            "validation_status": dict(sorted(validation.items())),
            "mechanism_families": dict(sorted(mechanism_families_counter.items())),
            "mechanism_subtypes": dict(sorted(mechanism_subtypes.items())),
            "conditions": dict(sorted(conditions.items())),
            "surfaces": dict(sorted(surfaces.items())),
        },
        "quality_gaps": dict(sorted(missing.items())),
        "policy": {
            "source_evidence_is_not_confirmation": True,
            "unvalidated_cases_must_not_be_reported": True,
            "duplicate_urls_must_be_zero": True,
        },
    }
    Path(args.output).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, **manifest["inventory"], "output": args.output}, sort_keys=True))
    return 0 if manifest["inventory"]["duplicate_urls"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
