#!/usr/bin/env python3
"""Validate an explicit phase worklist coverage ledger."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate_contract import check


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--require-closed", action="store_true")
    args = ap.parse_args()
    try:
        value = json.loads(Path(args.input).read_text(encoding="utf-8"))
        schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": f"COVERAGE_READ_FAILED:{exc}"}))
        return 2

    errors = check(value, schema)
    if isinstance(value, dict):
        total = value.get("total_items")
        examined = value.get("examined_items")
        deferred = value.get("deferred_items")
        uncovered = value.get("uncovered_ids")
        deferred_ids = value.get("deferred_ids", [])
        if all(isinstance(x, int) and not isinstance(x, bool) for x in (total, examined, deferred)):
            if examined + deferred + len(uncovered or []) != total:
                errors.append("coverage: examined_items + deferred_items + uncovered_ids must equal total_items")
        if isinstance(deferred, int) and isinstance(deferred_ids, list) and deferred != len(deferred_ids):
            errors.append("coverage: deferred_items must equal len(deferred_ids)")
        if value.get("closed") is True and uncovered:
            errors.append("coverage: closed coverage cannot contain uncovered_ids")
        if args.require_closed and value.get("closed") is not True:
            errors.append("coverage: phase handoff requires closed coverage")

    result = {"ok": not errors, "errors": errors, "input": args.input}
    print(json.dumps(result, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
