"""Minimal deterministic IssueAI pipeline."""

from __future__ import annotations

from dataclasses import asdict

from .contracts import IssueAIRequest, PlanningResult, RepositoryUnderstanding, RetrievalResult


def build_understanding(request: IssueAIRequest) -> RepositoryUnderstanding:
    """Construct a bounded repository understanding from explicit request context."""

    purpose = request.purpose_hint or "issue and bug discovery"
    surfaces = request.surfaces or ("runtime", "boundary", "integration")
    conventions = request.conventions or ("small bounded workflows", "deterministic planning")
    evidence = tuple(sorted({*surfaces, *request.local_signals}))
    return RepositoryUnderstanding(
        repository=request.repository,
        purpose=purpose,
        surfaces=tuple(surfaces),
        conventions=tuple(conventions),
        evidence=evidence,
    )


def retrieve_patterns(request: IssueAIRequest, understanding: RepositoryUnderstanding) -> RetrievalResult:
    """Create a bounded retrieval result from repository understanding."""

    surface_text = " ".join(understanding.surfaces).lower()
    signals_text = " ".join(request.local_signals).lower()
    mechanism_candidates: list[str] = ["boundary", "integration", "representation"]
    if any(token in surface_text or token in signals_text for token in ("async", "stream", "timeout", "session", "retry", "resource")):
        mechanism_candidates.extend(["lifecycle", "state_reuse"])
    if any(token in surface_text or token in signals_text for token in ("thread", "queue", "race", "worker", "parallel")):
        mechanism_candidates.append("concurrency")
    if any(token in signals_text for token in ("log", "trace", "metric", "health", "error")):
        mechanism_candidates.append("observability")
    ordered = tuple(dict.fromkeys(mechanism_candidates))
    matched_patterns = tuple(f"pattern:{name}" for name in ordered)
    evidence = tuple(sorted({*understanding.evidence, *matched_patterns}))
    return RetrievalResult(
        repository=request.repository,
        matched_patterns=matched_patterns,
        mechanism_candidates=ordered,
        evidence=evidence,
    )


def build_plan(request: IssueAIRequest, retrieval: RetrievalResult) -> PlanningResult:
    """Convert retrieval output into a minimal ordered plan."""

    branches = tuple(f"branch:{name}" for name in retrieval.mechanism_candidates)
    coverage_rows = tuple(f"coverage:{name}" for name in retrieval.mechanism_candidates)
    return PlanningResult(
        repository=request.repository,
        ordered_mechanisms=retrieval.mechanism_candidates,
        branches=branches,
        coverage_rows=coverage_rows,
    )


def run_pipeline(request: IssueAIRequest) -> dict[str, object]:
    """Run the minimal deterministic IssueAI pipeline."""

    understanding = build_understanding(request)
    retrieval = retrieve_patterns(request, understanding)
    plan = build_plan(request, retrieval)
    return {
        "request": asdict(request),
        "understanding": asdict(understanding),
        "retrieval": asdict(retrieval),
        "plan": asdict(plan),
    }
