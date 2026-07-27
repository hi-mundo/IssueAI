#!/usr/bin/env python3
"""Populate deterministic issue playbooks for structured Bug Hunt corpora."""
from __future__ import annotations

import argparse
import json
import re
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
    "state_reuse": "state-lifecycle",
    "integration": "integration",
    "compatibility": "compatibility",
    "concurrency": "concurrency",
    "observability": "observability",
    "purpose_mismatch": "intent-drift",
    "organizational_drift": "intent-drift",
    "intent-drift": "intent-drift",
}

SURFACE_HINTS = {
    "public_boundary": r"api|request|handler|parser|schema|endpoint|cli|module|argument",
    "state_resource": r"cache|session|stream|socket|file|worker|queue|resource|timer|close|retry",
    "adapter": r"adapter|backend|driver|plugin|platform|dependency|inventory|connection|transport",
    "normalization": r"encode|decode|unicode|url|path|version|normalize|canonical|release",
    "test_observability": r"test|fixture|debug|log|metric|trace|telemetry|callback|error",
}

MECHANISM_HINTS = {
    "boundary": r"empty|null|none|zero|negative|partial|invalid|malformed|limit|overflow|truncate|duplicate",
    "precedence": r"default|fallback|environment|config|override|explicit|setdefault|ignored",
    "contract": r"api|schema|type|contract|expected|interface|inconsistent|return|should",
    "lifecycle": r"close|cleanup|teardown|eof|stream|cancel|retry|redirect|flush|shutdown|timer|timeout|resource|finali[sz]|ownership|release|dispose|destroy",
    "state": r"cache|stale|reload|session|second run|restart|rollback|incremental|reuse|memo",
    "state_reuse": r"cache|stale|reload|session|second run|restart|reuse|memo",
    "representation": r"encode|unicode|utf|bytes|url|path|version|label|name|canonical|normalize|format|buffer",
    "integration": r"plugin|adapter|driver|backend|dependency|platform|subprocess|runtime|sudo|ssl",
    "compatibility": r"windows|linux|macos|python|node|java|rust|openblas|backend|driver|dependency|platform|version",
    "concurrency": r"race|thread|concurrent|async|deadlock|hang|worker|lock|parallel|intermittent",
    "observability": r"silent|missing|not reported|log|telemetry|fallback|hard to reproduce|intermittent|benchmark|slow|slower",
}

CONDITION_HINTS = {
    "common_path_passes": r"works|working|normal|common|only when|except|passes",
    "transition": r"after|before|during|until|second|restart|teardown|redirect|reload|retry|connection",
    "delayed_effect": r"later|eventually|intermittent|sporadic|only after|memory leak|hang|timeout|slow|slower",
    "environment_cell": r"windows|linux|macos|python|node|java|rust|openblas|backend|driver|dependency|platform|sudo|ssl",
    "expected_observed": r"expected|should|actual|instead|but|however|returns|raises|fails|does not|ignored|invalid",
}

WHERE_TO_LOOK = {
    "state_reuse": ["cache invalidation code", "session or memoized state", "reload and second-run branches"],
    "state": ["cache invalidation code", "session or memoized state", "reload and second-run branches"],
    "resource": ["resource owner helper", "cleanup and release path", "close or teardown branch"],
    "lifecycle": ["stream or resource lifecycle path", "retry/redirect/teardown branch", "close/cancel/error cleanup"],
    "precedence": ["config merge helper", "default/fallback branch", "explicit-vs-inherited value resolution"],
    "boundary": ["public input boundary", "validation/coercion helper", "partial or malformed input branch"],
    "contract": ["public API contract surface", "schema/type enforcement", "returned object construction"],
    "representation": ["normalize/parse helper", "identity/version/path converter", "round-trip or canonicalization code"],
    "integration": ["adapter/driver/backend shim", "alternate implementation path", "cross-boundary integration hook"],
    "compatibility": ["version/platform guard", "feature detection branch", "runtime-specific compatibility path"],
    "concurrency": ["queue/worker callback path", "shared state synchronization", "interleaving/cancellation branch"],
    "observability": ["error/reporting callback", "log/metric/telemetry path", "fallback or suppressed error branch"],
    "intent-drift": ["project convention boundary", "naming/ownership split", "redundant or misplaced implementation path"],
}

CONTROL_MAP = {
    "state_reuse": "cache invalidation or state reset control",
    "state": "state reset or reuse guard",
    "resource": "resource cleanup or ownership-transfer control",
    "lifecycle": "lifecycle cleanup, retry, or close control",
    "precedence": "precedence/default-selection control",
    "boundary": "input validation or boundary guard",
    "contract": "schema/type/return-value contract enforcement",
    "representation": "normalization or identity-conversion control",
    "integration": "adapter/backend boundary control",
    "compatibility": "version/platform compatibility guard",
    "concurrency": "interleaving or synchronization control",
    "observability": "error/reporting surfacing control",
    "intent-drift": "ownership or implementation-intent control",
}


def issue_text(issue: dict) -> str:
    return " ".join(
        str(issue.get(key, ""))
        for key in ("title", "body", "repository", "query_family", "research_signals", "escape_chain_coverage")
    )


def list_values(issue: dict, key: str) -> list[str]:
    value = issue.get("derived", {}).get(key, [])
    return [str(item).lower() for item in value] if isinstance(value, list) else []


def raw_mechanisms(issue: dict) -> list[str]:
    explicit = ordered_unique(list_values(issue, "mechanisms"))
    if explicit:
        return explicit
    text = issue_text(issue)
    return [name for name, pattern in MECHANISM_HINTS.items() if re.search(pattern, text, re.I)]


def inferred_conditions(issue: dict) -> list[str]:
    explicit = ordered_unique(list_values(issue, "conditions"))
    if explicit:
        return explicit
    text = issue_text(issue)
    return [name for name, pattern in CONDITION_HINTS.items() if re.search(pattern, text, re.I)]


def mechanism_families(issue: dict) -> list[str]:
    seen: list[str] = []
    for mechanism in raw_mechanisms(issue):
        family = MECHANISM_FAMILY_MAP.get(mechanism, mechanism)
        if family not in seen:
            seen.append(family)
    return seen


def infer_surfaces(issue: dict) -> list[str]:
    explicit = list_values(issue, "surfaces")
    if explicit:
        return explicit
    text = issue_text(issue)
    return [name for name, pattern in SURFACE_HINTS.items() if re.search(pattern, text, re.I)] or ["public_boundary"]


def expected_invariant(issue: dict) -> str:
    expected_observed = issue.get("derived", {}).get("expected_observed")
    if isinstance(expected_observed, dict):
        expected = expected_observed.get("expected")
        observed = expected_observed.get("observed")
        if expected and observed:
            return f"Expected {expected}, not {observed}."
        if expected:
            return str(expected)
    oracle = issue.get("derived", {}).get("oracle")
    if oracle:
        return str(oracle)
    title = str(issue.get("title", "")).strip()
    return f"The documented behavior in '{title}' should remain true across the tested path." if title else "The public behavior should stay consistent across the relevant path."


def broken_transition(issue: dict, families: list[str]) -> str:
    conditions = set(inferred_conditions(issue))
    if "transition" in conditions and "state-lifecycle" in families:
        return "A lifecycle or state transition changes behavior that should stay invariant."
    if "delayed_effect" in conditions:
        return "The defect appears only after a delayed or later execution step."
    if "environment_cell" in conditions:
        return "The defect appears only in an alternate environment, backend, or platform cell."
    if "boundary" in families:
        return "A boundary transition changes the shape or meaning of the data unexpectedly."
    if "contract" in families:
        return "A contract-preserving transform fails when the value crosses into implementation logic."
    return "A non-default transition violates a behavior that appears safe on the common path."


def broken_control(issue: dict, families: list[str]) -> str:
    mechanisms = raw_mechanisms(issue)
    for mechanism in mechanisms:
        if mechanism in CONTROL_MAP:
            return CONTROL_MAP[mechanism]
    for family in families:
        if family in CONTROL_MAP:
            return CONTROL_MAP[family]
    return "A control that appears to guarantee the behavior does not cover the concrete failing path."


def false_sense_of_safety(issue: dict, families: list[str]) -> str:
    conditions = set(inferred_conditions(issue))
    if "common_path_passes" in conditions:
        return "The common path passes, which hides the rare failing cell."
    if "environment_cell" in conditions:
        return "The default environment appears healthy, masking an alternate runtime or backend cell."
    if "expected_observed" in conditions:
        return "The API shape looks correct until the observed runtime path reveals the mismatch."
    if "observability" in families:
        return "The failure is hidden by a plausible success signal or missing error surface."
    return "Nearby code and normal-path behavior make the implementation look safer than the failing path really is."


def ordered_unique(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out


def where_to_look(issue: dict, families: list[str]) -> list[str]:
    locations: list[str] = []
    if "state-lifecycle" in families:
        locations.extend(["stream or resource lifecycle path", "retry/redirect/teardown branch", "close/cancel/error cleanup"])
    if "contract" in families:
        locations.extend(["public API contract surface", "schema/type enforcement", "returned object construction"])
    if "boundary" in families:
        locations.extend(["public input boundary", "validation/coercion helper", "partial or malformed input branch"])
    for mechanism in raw_mechanisms(issue):
        locations.extend(WHERE_TO_LOOK.get(mechanism, []))
    for family in families:
        locations.extend(WHERE_TO_LOOK.get(family, []))
    return ordered_unique(locations)[:4] or ["public contract surface", "closest transformation/helper boundary"]


def how_to_compare(issue: dict, families: list[str]) -> list[str]:
    conditions = set(inferred_conditions(issue))
    comparisons: list[str] = []
    if "state-lifecycle" in families:
        comparisons.append("first execution vs repeated execution or cleanup path")
    if "contract" in families:
        comparisons.append("validated/public object vs consumed/internal object")
    if "boundary" in families:
        comparisons.append("common valid input vs partial, empty, or malformed input")
    if "expected_observed" in conditions:
        comparisons.append("documented expected behavior vs observed runtime behavior")
    if "transition" in conditions:
        comparisons.append("before transition vs after transition")
    if "delayed_effect" in conditions:
        comparisons.append("immediate result vs later or repeated result")
    if "environment_cell" in conditions:
        comparisons.append("default environment/backend vs alternate environment/backend")
    return ordered_unique(comparisons)[:4] or ["common path vs rare failing path"]


def probe_shape(issue: dict, families: list[str]) -> str:
    oracle = issue.get("derived", {}).get("oracle")
    if oracle:
        return f"Construct the rare cell and falsify this oracle: {oracle}"
    comparisons = how_to_compare(issue, families)
    return "Probe the same capability across: " + "; ".join(comparisons[:3]) + "."


def pick_primary_mechanism(issue: dict) -> str:
    mechanisms = raw_mechanisms(issue)
    priority = [
        "state_reuse",
        "lifecycle",
        "precedence",
        "representation",
        "integration",
        "compatibility",
        "concurrency",
        "boundary",
        "contract",
        "resource",
        "state",
        "observability",
    ]
    for name in priority:
        if name in mechanisms:
            return name
    return mechanisms[0] if mechanisms else ""


def playbook_family(issue: dict, families: list[str]) -> str:
    conditions = set(inferred_conditions(issue))
    mechanisms = set(raw_mechanisms(issue))
    if "state-lifecycle" in families and "transition" in conditions:
        return "state-transition-regression"
    if "precedence" in mechanisms and "contract" in families:
        return "explicit-input-loses-to-fallback"
    if "representation" in mechanisms and "contract" in families:
        return "normalized-shape-vs-consumed-shape"
    if "compatibility" in families and "contract" in families:
        return "declared-support-vs-runtime-cell"
    if "integration" in families and "environment_cell" in conditions:
        return "alternate-cell-integration-mismatch"
    if "integration" in families and "observability" in families:
        return "integration-failure-hidden-by-success-signal"
    if "concurrency" in families and "contract" in families:
        return "concurrent-contract-drift"
    if "concurrency" in families and "observability" in families:
        return "intermittent-failure-with-weak-signal"
    if "contract" in families and "boundary" in families:
        return "validated-shape-vs-consumed-shape"
    if "observability" in families:
        return "suppressed-failure-signal"
    primary = pick_primary_mechanism(issue)
    if primary:
        return primary.replace("_", "-")
    if families:
        return "-".join(families[:2])
    return "generic-contract-transition"


def playbook_signature(issue: dict, families: list[str], surfaces: list[str]) -> str:
    conditions = inferred_conditions(issue)
    condition_priority = ["transition", "environment_cell", "delayed_effect", "expected_observed", "common_path_passes"]
    prioritized_conditions = [name for name in condition_priority if name in conditions]
    prioritized_conditions.extend(name for name in conditions if name not in prioritized_conditions)
    mechanisms = raw_mechanisms(issue)
    parts = [
        surfaces[0] if surfaces else "surface",
        mechanisms[0] if mechanisms else (families[0] if families else "family"),
        families[0] if families else "family",
        *(prioritized_conditions[:2] or ["condition"]),
    ]
    return " × ".join(parts)


def build_playbook(issue: dict) -> dict:
    families = mechanism_families(issue)
    surfaces = infer_surfaces(issue)
    technology = list_values(issue, "technology")
    instance = ", ".join(ordered_unique([*(surfaces[:2]), *(technology[:2])])) or str(issue.get("repository", "concrete path"))
    return {
        "surface": surfaces[0] if surfaces else "public_boundary",
        "trigger": str(issue.get("title") or issue.get("derived", {}).get("failure_chain") or "rare-path behavior mismatch"),
        "expected_invariant": expected_invariant(issue),
        "broken_transition": broken_transition(issue, families),
        "broken_control": broken_control(issue, families),
        "concrete_instance": instance,
        "false_sense_of_safety": false_sense_of_safety(issue, families),
        "where_to_look": where_to_look(issue, families),
        "how_to_compare": how_to_compare(issue, families),
        "probe_shape": probe_shape(issue, families),
        "playbook_family": playbook_family(issue, families),
        "playbook_signature": playbook_signature(issue, families, surfaces),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    issues = payload.get("issues", payload) if isinstance(payload, dict) else payload
    enriched = []
    generated = 0
    preserved = 0
    for issue in issues:
        record = dict(issue)
        if args.overwrite or not isinstance(record.get("playbook"), dict):
            record["playbook"] = build_playbook(record)
            generated += 1
        else:
            preserved += 1
        enriched.append(record)

    output_payload = payload if isinstance(payload, dict) else {"issues": enriched}
    if isinstance(output_payload, dict):
        output_payload["issues"] = enriched

    Path(args.output).write_text(json.dumps(output_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "issues": len(enriched), "generated": generated, "preserved": preserved, "output": args.output}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
