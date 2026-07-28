"""Core product model for AIssuer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class IssueAIModel:
    """High-level description of the AIssuer product boundary."""

    name: str = "AIssuer"
    mode: str = "hypothesis-driven issue discovery"
    strengths: tuple[str, ...] = (
        "repository understanding",
        "product understanding",
        "historical issue retrieval",
        "structured hypothesis planning",
        "high-recall issue discovery",
    )
    current_limitations: tuple[str, ...] = (
        "ranking noise between correlated mechanisms",
        "top-3 precision still behind top-20 benchmark success",
        "validation probes still need broader productization",
    )
    adapters: tuple[str, ...] = ("codex", "claude")
    benchmark_summary: dict[str, str] = field(
        default_factory=lambda: {
            "date": "2026-07-27",
            "top20_success": "20/20",
            "top100_diagnostic": "20/20",
            "note": "Expected mechanisms landed inside the top 20 for all benchmarked cases; top 100 remains diagnostic only.",
        }
    )
