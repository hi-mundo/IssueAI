"""Structured contracts for IssueAI pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict

try:
    from typing import NotRequired, TypeAlias
except ImportError:
    from typing_extensions import NotRequired, TypeAlias


JsonObjectContract: TypeAlias = dict[str, Any]
RepositoryMapContract: TypeAlias = dict[str, Any]
HistoricalCaseResultContract: TypeAlias = dict[str, object]


class HistoricalBenchmarkPayloadContract(TypedDict):
    """Minimal contract used by benchmark JSON payload fixtures."""

    id: str
    repository: str


class NormalizedSourceFileContract(TypedDict):
    """Normalized repository file contract used by route benchmark helpers."""

    path: str
    kind: str
    vendor: bool
    generated: bool


class NormalizedRepositoryContract(TypedDict):
    """Normalized repository contract consumed by scope-selection helpers."""

    files: list[NormalizedSourceFileContract]


class RepositoryReviewArtifactContract(TypedDict):
    """Common gate/result contract for repository review workflows."""

    ready: bool
    blockers: list[str]
    preflightStatus: NotRequired[str]
    changedDomains: NotRequired[list[str]]


@dataclass(frozen=True)
class RepositoryUnderstanding:
    """High-level reconstructed understanding of a repository."""

    repository: str
    purpose: str
    surfaces: tuple[str, ...]
    conventions: tuple[str, ...]
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalResult:
    """Structured contextual retrieval output."""

    repository: str
    matched_patterns: tuple[str, ...]
    mechanism_candidates: tuple[str, ...]
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanningResult:
    """Structured planning output for issue discovery."""

    repository: str
    ordered_mechanisms: tuple[str, ...]
    branches: tuple[str, ...]
    coverage_rows: tuple[str, ...] = ()


@dataclass(frozen=True)
class IssueAIRequest:
    """Input request for the minimal standalone pipeline."""

    repository: str
    purpose_hint: str = ""
    surfaces: tuple[str, ...] = ()
    conventions: tuple[str, ...] = ()
    local_signals: tuple[str, ...] = ()
    preferred_provider: str = "host"
    metadata: dict[str, str] = field(default_factory=dict)
