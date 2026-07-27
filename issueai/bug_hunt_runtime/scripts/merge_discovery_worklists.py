#!/usr/bin/env python3
"""Merge structural and history-seeded discovery rows without collapsing evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structural", required=True)
    parser.add_argument("--history", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=1200)
    args = parser.parse_args()
    structural = json.loads(Path(args.structural).read_text(encoding="utf-8"))
    history = json.loads(Path(args.history).read_text(encoding="utf-8"))
    history_locations = {}
    for item in history.get("hypotheses", []):
        for location in item.get("candidate_locations", []):
            history_locations.setdefault(location, []).append(item)

    seeded = []
    ordinary = []
    for row in structural.get("rows", []):
        matches = history_locations.get(row.get("location"), [])
        copy = dict(row)
        copy["history_seed_ids"] = [item.get("id") for item in matches]
        copy["history_evidence"] = [e for item in matches for e in item.get("evidence_initial", [])]
        copy["history_seeded"] = bool(matches)
        (seeded if matches else ordinary).append(copy)

    rows = (seeded + ordinary)[: args.limit]
    result = dict(structural)
    result["mode"] = "merged-escape-cell-worklist"
    result["rows"] = rows
    result["coverage"] = dict(result.get("coverage", {}))
    result["coverage"]["total_rows"] = len(rows)
    result["coverage"]["history_seeded_rows"] = sum(row["history_seeded"] for row in rows)
    result["discovery_only"] = True
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "rows": len(rows), "history_seeded_rows": result["coverage"]["history_seeded_rows"], "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
