"""Deterministic workflow contracts for the public IssueAI surfaces."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkflowPhase:
    """One deterministic phase in a public IssueAI workflow."""

    id: str
    objective: str
    static_prompt: str
    dynamic_fields: tuple[str, ...]
    expected_outputs: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowDefinition:
    """Public workflow metadata."""

    id: str
    display_name: str
    description: str
    phases: tuple[WorkflowPhase, ...]


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_dynamic_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_dynamic_payload(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize_dynamic_payload(item) for item in value]
    return value


def _phase(
    phase_id: str,
    objective: str,
    static_prompt: str,
    dynamic_fields: tuple[str, ...],
    expected_outputs: tuple[str, ...],
) -> WorkflowPhase:
    return WorkflowPhase(
        id=phase_id,
        objective=objective,
        static_prompt=static_prompt.strip(),
        dynamic_fields=dynamic_fields,
        expected_outputs=expected_outputs,
    )


WORKFLOWS: dict[str, WorkflowDefinition] = {
    "repository-recon": WorkflowDefinition(
        id="repository-recon",
        display_name="Repository Recon",
        description="Create the structural snapshot, repository map, data-flow trace, and graph.",
        phases=(
            _phase(
                "snapshot-and-entrypoints",
                "Create or refresh the repository snapshot and choose the best starting points for structural navigation.",
                """
                You are in the Repository Recon workflow.
                Work only from deterministic repository artifacts already collected by Python.
                Decide how to start navigation through the codebase without inventing missing structure.
                Prefer script or application entrypoints first. If the repository is script-shaped, start from main.
                """,
                ("repoRoot", "reviewMode", "entrypoints", "changedDomains"),
                ("navigation_start", "snapshot_notes"),
            ),
            _phase(
                "role-and-domain-map",
                "Map project roles, dominant patterns, domains, and structural outliers.",
                """
                You are in the Repository Recon workflow.
                Use the provided deterministic role map, folder census, and domain clusters.
                Explain where the project keeps each responsibility, what looks standardized, and where structure drifts.
                Do not speculate beyond the supplied repository evidence.
                """,
                ("roleLocations", "folderDepthCensus", "domainClusters", "patternSignals"),
                ("repository_map", "structural_outliers"),
            ),
            _phase(
                "flow-trace-and-graph",
                "Trace likely data flow through imports and role transitions, then synthesize the repository graph.",
                """
                You are in the Repository Recon workflow.
                Use only the deterministic import graph, role graph, and traced flow paths.
                Summarize how data likely travels through the repository and where redundancies or fractured seams appear.
                Keep the output bounded and graph-oriented.
                """,
                ("importGraphSummary", "flowTraces", "redundancies", "entrypointStrategy"),
                ("flow_summary", "repository_graph"),
            ),
        ),
    ),
    "repository-intent-review": WorkflowDefinition(
        id="repository-intent-review",
        display_name="Repository Intent Review",
        description="Compare intended repository behavior and structure against the current implementation.",
        phases=(
            _phase(
                "load-recon-and-scope",
                "Load the recon snapshot and select the most important repository seams to review.",
                """
                You are in the Repository Intent Review workflow.
                Trust the Repository Recon artifacts as the structural baseline.
                Select the seams that matter most for implementation intent: protection, schemas, contracts, async, and CRUD behavior.
                """,
                ("repoRoot", "reviewMode", "reconSummary", "criticalPaths"),
                ("review_scope", "intent_focus"),
            ),
            _phase(
                "derive-intended-behavior",
                "Infer what each important seam is supposed to guarantee before checking whether it actually does.",
                """
                You are in the Repository Intent Review workflow.
                Infer repository intent from names, roles, neighboring files, and deterministic structural evidence.
                Do not jump to deep bug hunting yet. First state the expected guarantees clearly.
                """,
                ("focusRoles", "criticalPaths", "patternSignals", "languageFocus"),
                ("intent_model", "expected_guarantees"),
            ),
            _phase(
                "compare-intent-vs-implementation",
                "Compare inferred guarantees against implementation evidence and record direct mismatches.",
                """
                You are in the Repository Intent Review workflow.
                Compare expected guarantees against deterministic evidence such as missing schemas, weak typing, middleware gaps, and async misuse.
                Favor obvious or high-confidence break paths over speculative edge cases.
                """,
                ("intentModel", "heuristicEvidence", "criticalPaths", "languageFocus"),
                ("intent_findings", "implementation_gaps"),
            ),
            _phase(
                "handoff-to-issue-hunt",
                "Prepare a clean handoff for Issue Hunt once the obvious intent mismatches are resolved or triaged.",
                """
                You are in the Repository Intent Review workflow.
                Summarize what Issue Hunt should inherit and what still blocks deeper hunting.
                Keep the handoff operational and deterministic.
                """,
                ("openFindings", "resolvedSignals", "residualRiskAreas"),
                ("handoff_summary", "issue_hunt_gate"),
            ),
        ),
    ),
    "issue-hunt": WorkflowDefinition(
        id="issue-hunt",
        display_name="Issue Hunt",
        description="Search the mature, non-obvious issue space after Recon and Intent Review are in place.",
        phases=(
            _phase(
                "load-baseline",
                "Load the latest Recon and Repository Intent Review artifacts and confirm the deep-hunt gate.",
                """
                You are in the Issue Hunt workflow.
                Do not repeat Repository Recon or Repository Intent Review.
                Consume their artifacts, confirm that the obvious issues are already handled, and define the remaining search space.
                """,
                ("repoRoot", "reviewMode", "gate", "reconSummary", "intentReviewSummary"),
                ("deep_hunt_scope", "gate_confirmation"),
            ),
            _phase(
                "retrieve-patterns",
                "Retrieve the strongest issue patterns and playbooks for this repository shape and technology mix.",
                """
                You are in the Issue Hunt workflow.
                Use the provided repository shape, language focus, graph context, and changed seams to retrieve the best matching issue families.
                Prefer structured pattern recall over generic free-form brainstorming.
                """,
                ("searchSpace", "languageFocus", "graphSummary", "changedDomains"),
                ("retrieved_patterns", "pattern_coverage"),
            ),
            _phase(
                "rank-hypotheses",
                "Generate and rank hard issue hypotheses for the remaining mature-system search space.",
                """
                You are in the Issue Hunt workflow.
                Produce bounded, falsifiable issue hypotheses tied to files, seams, and mechanisms.
                It is acceptable if the correct issue is not the top result, as long as it lands inside a testable shortlist.
                """,
                ("retrievedPatterns", "criticalPaths", "residualRiskAreas", "searchSpace"),
                ("ranked_hypotheses", "validation_candidates"),
            ),
            _phase(
                "handoff-to-probe",
                "Prepare the smallest decisive shortlist for Issue Probe.",
                """
                You are in the Issue Hunt workflow.
                Reduce the hypothesis set into a practical probe queue with explicit reasons for priority.
                """,
                ("rankedHypotheses", "coverageGaps", "residualRiskAreas"),
                ("probe_queue", "probe_priorities"),
            ),
        ),
    ),
    "issue-probe": WorkflowDefinition(
        id="issue-probe",
        display_name="Issue Probe",
        description="Turn shortlisted issues into deterministic evidence checks and verdicts.",
        phases=(
            _phase(
                "select-candidates",
                "Load the latest issue queue and select the candidates worth probing now.",
                """
                You are in the Issue Probe workflow.
                Start from the provided issue shortlist and avoid reopening the entire hunt space.
                Select candidates with the clearest potential to become evidence-backed findings.
                """,
                ("repoRoot", "probeQueue", "limit"),
                ("selected_candidates", "probe_scope"),
            ),
            _phase(
                "build-probes",
                "Build deterministic probes and checks for each selected issue.",
                """
                You are in the Issue Probe workflow.
                Define step-by-step checks that can confirm or reject each suspected issue with minimal ambiguity.
                Reuse repository artifacts and static evidence before assuming runtime execution is necessary.
                """,
                ("selectedCandidates", "repositoryArtifacts", "availableEvidence"),
                ("probe_plans", "required_evidence"),
            ),
            _phase(
                "execute-evidence-checks",
                "Run the smallest evidence checks available and preserve visible failure states.",
                """
                You are in the Issue Probe workflow.
                Use deterministic checks first. If evidence is insufficient, say so clearly instead of pretending the issue is confirmed.
                """,
                ("probePlans", "staticEvidence", "repositoryArtifacts"),
                ("probe_results", "unresolved_candidates"),
            ),
            _phase(
                "verdicts",
                "Produce verdicts and explicit next actions from the probe results.",
                """
                You are in the Issue Probe workflow.
                Separate confirmed findings, disproven branches, and unresolved candidates.
                Preserve the exact reason for each verdict.
                """,
                ("probeResults", "unresolvedCandidates"),
                ("verdicts", "follow_up_actions"),
            ),
        ),
    ),
}


def workflow_registry() -> dict[str, WorkflowDefinition]:
    """Return the public workflow registry."""

    return dict(WORKFLOWS)


def build_phase_envelope(workflow_id: str, phase_id: str, dynamic_payload: dict[str, Any]) -> dict[str, Any]:
    """Build a cacheable prompt envelope with static and dynamic parts separated."""

    workflow = WORKFLOWS[workflow_id]
    phase = next(item for item in workflow.phases if item.id == phase_id)
    normalized_payload = _normalize_dynamic_payload(
        {field: dynamic_payload.get(field) for field in phase.dynamic_fields if field in dynamic_payload}
    )
    serialized_dynamic_payload = json.dumps(normalized_payload, sort_keys=True, ensure_ascii=False)
    return {
        "workflowId": workflow.id,
        "workflowName": workflow.display_name,
        "phaseId": phase.id,
        "objective": phase.objective,
        "staticPrompt": phase.static_prompt,
        "dynamicPayload": normalized_payload,
        "expectedOutputs": list(phase.expected_outputs),
        "cache": {
            "staticHash": _hash_text(phase.static_prompt),
            "dynamicHash": _hash_text(serialized_dynamic_payload),
        },
    }


def build_workflow_envelopes(workflow_id: str, phase_payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Build the prompt envelopes for every phase in order."""

    workflow = WORKFLOWS[workflow_id]
    return [build_phase_envelope(workflow.id, phase.id, phase_payloads.get(phase.id, {})) for phase in workflow.phases]
