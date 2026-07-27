#!/usr/bin/env python3
"""Score whether an issue can be routed to Bug Hunt search locations.

This is a deterministic research aid, not a detector.  It measures whether
the issue text contains enough signals to form a falsifiable hypothesis and
maps those signals to repository locations.  It must never be reported as a
confirmed finding.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


MECHANISM_SUBTYPES = {
    "state_reuse": (r"cache|stale|reload|session|second run|again|reuse|restart", "state transitions"),
    "lifecycle": (r"close|cleanup|teardown|eof|stream|cancel|retry|redirect|keepalive|flush", "lifecycle and resource seams"),
    "precedence": (r"default|fallback|environment|config|override|explicit|null|None|precedence", "configuration precedence seams"),
    "representation": (r"encode|unicode|utf|bytes|url|path|version|label|name|canonical|normalize|format", "normalization and identity"),
    "integration": (r"plugin|adapter|driver|backend|dependency|platform|windows|linux|openblas|subprocess", "integration adapters"),
    "concurrency": (r"race|thread|concurrent|async|deadlock|hang|worker|lock|parallel|intermittent|sporadic", "concurrency and scheduling"),
    "boundary": (r"empty|null|None|zero|negative|large|partial|invalid|malformed|limit|overflow|truncat|duplicate", "public and data boundaries"),
    "observability": (r"silent|missing|not reported|log|telemetry|fallback|retry|hard to reproduce|intermittent", "history and observability"),
}

MECHANISM_FAMILY_MAP = {
    "state_reuse": "state-lifecycle",
    "lifecycle": "state-lifecycle",
    "precedence": "boundary",
    "representation": "contract",
    "integration": "integration",
    "concurrency": "concurrency",
    "boundary": "boundary",
    "observability": "observability",
}

CONJUNCTIONS = {
    "transition": r"after|before|during|when|until|second|restart|teardown|redirect|reload|retry",
    "delayed_effect": r"later|eventually|intermittent|sporadic|only after|memory leak|hang|timeout|regression",
    "environment": r"windows|linux|macos|python|node|java|rust|openblas|backend|driver|dependency|platform",
    "expected_observed": r"expected|should|actual|instead|but|however|returns|raises|fails|does not",
}


def _text(issue: dict) -> str:
    labels = " ".join(str(x) for x in issue.get("labels", []))
    return " ".join(str(issue.get(k, "")) for k in ("title", "body", "repository", "query_family", "research_signals", "escape_chain_coverage", "labels")) + " " + labels


def _matches(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text, re.IGNORECASE))


def _families(subtypes: list[str]) -> list[str]:
    families: list[str] = []
    seen: set[str] = set()
    for subtype in subtypes:
        family = MECHANISM_FAMILY_MAP.get(subtype, subtype)
        if family not in seen:
            seen.add(family)
            families.append(family)
    return families


def score(issue: dict) -> dict:
    text = _text(issue)
    subtype_matches = [
        {"id": key, "location": location}
        for key, (pattern, location) in MECHANISM_SUBTYPES.items()
        if _matches(text, pattern)
    ]
    mechanism_subtypes = [item["id"] for item in subtype_matches]
    mechanism_families = _families(mechanism_subtypes)
    signals = [key for key, pattern in CONJUNCTIONS.items() if _matches(text, pattern)]
    locations = sorted({item["location"] for item in subtype_matches})
    # Coverage is deliberately a conservative research score.  It says that
    # the method knows how to route the issue, not that the repository was
    # inspected or that the bug was found.
    coverage = min(1.0, (len(mechanism_subtypes) / 3.0) * 0.65 + (len(signals) / 4.0) * 0.35)
    eligible = len(mechanism_subtypes) >= 2 and len(signals) >= 1
    return {
        "repository": issue.get("repository"),
        "url": issue.get("url"),
        "title": issue.get("title"),
        "mechanisms": mechanism_subtypes,
        "mechanism_subtypes": mechanism_subtypes,
        "mechanism_families": mechanism_families,
        "search_locations": locations,
        "escape_chain_signals": signals,
        "coverage_score": round(coverage, 3),
        "hypothesis_covered": eligible,
        "status": "hypothesis-covered" if eligible else "insufficient-routing-evidence",
        "proof_boundary": "No repository inspection or defect detection is implied.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    issues = source.get("issues", source) if isinstance(source, dict) else source
    records = [score(issue) for issue in issues]
    counts = {
        "issues": len(records),
        "hypothesis_covered": sum(r["hypothesis_covered"] for r in records),
        "insufficient_routing_evidence": sum(not r["hypothesis_covered"] for r in records),
        "coverage_at_least_0_75": sum(r["coverage_score"] >= 0.75 for r in records),
        "coverage_at_least_0_50": sum(r["coverage_score"] >= 0.50 for r in records),
    }
    result = {"method": "escape-chain-location-routing-v1", "summary": counts, "records": records}
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": args.output, **counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
