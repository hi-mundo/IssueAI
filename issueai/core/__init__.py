"""Core AIssuer concepts."""

from .contracts import (
    HistoricalBenchmarkPayloadContract,
    HistoricalCaseResultContract,
    IssueAIRequest,
    JsonObjectContract,
    NormalizedRepositoryContract,
    NormalizedSourceFileContract,
    PlanningResult,
    RepositoryMapContract,
    RepositoryReviewArtifactContract,
    RepositoryUnderstanding,
    RetrievalResult,
)
from .historical_eval import (
    HistoricalEvalRuntime,
    build_contextual_input,
    build_intelligent_plan,
    materialize_shard,
    run_command,
    write_product_understanding,
)
from .historical_routes import (
    aggregate_scores,
    canonicalize,
    choose_scopes,
    enrich_with_materialization,
    evaluate_historical_case,
)
from .issue_hunt import load_issue_hunt, load_issue_probe_gate, run_issue_hunt
from .issue_probe import run_issue_probe
from .repository_intent_review import (
    load_issue_hunt_gate,
    load_repository_intent_review,
    load_repository_intent_review_gate,
    run_intent_review,
    run_repository_intent_review,
)
from .repository_recon import (
    load_repository_recon,
    preflight_repository,
    run_repository_recon,
)
from .model import IssueAIModel
from .pipeline import build_plan, build_understanding, retrieve_patterns, run_pipeline
from .workflows import build_phase_envelope, build_workflow_envelopes, workflow_registry

__all__ = [
    "IssueAIModel",
    "IssueAIRequest",
    "JsonObjectContract",
    "HistoricalBenchmarkPayloadContract",
    "HistoricalCaseResultContract",
    "NormalizedRepositoryContract",
    "NormalizedSourceFileContract",
    "RepositoryMapContract",
    "RepositoryReviewArtifactContract",
    "RepositoryUnderstanding",
    "RetrievalResult",
    "PlanningResult",
    "build_understanding",
    "retrieve_patterns",
    "build_plan",
    "run_pipeline",
    "HistoricalEvalRuntime",
    "run_command",
    "write_product_understanding",
    "build_contextual_input",
    "build_intelligent_plan",
    "materialize_shard",
    "canonicalize",
    "choose_scopes",
    "aggregate_scores",
    "enrich_with_materialization",
    "evaluate_historical_case",
    "load_repository_recon",
    "run_repository_recon",
    "load_repository_intent_review",
    "load_repository_intent_review_gate",
    "run_repository_intent_review",
    "load_issue_hunt_gate",
    "load_issue_hunt",
    "run_issue_hunt",
    "load_issue_probe_gate",
    "run_issue_probe",
    "workflow_registry",
    "build_phase_envelope",
    "build_workflow_envelopes",
    "preflight_repository",
    "run_intent_review",
]
