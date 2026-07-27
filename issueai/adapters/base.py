"""Shared adapter contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdapterDescriptor:
    """Minimal host adapter description."""

    host: str
    purpose: str
    runtime: str
