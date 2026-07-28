"""Canonical Codex adapter stub."""

from __future__ import annotations

from .base import AdapterDescriptor


class CodexAdapter:
    """Describe how AIssuer plugs into Codex-hosted workflows."""

    descriptor = AdapterDescriptor(
        host="codex",
        purpose="Run AIssuer workflows inside Codex as a thin host adapter.",
        runtime="python",
    )

    @classmethod
    def describe(cls) -> dict[str, str]:
        return {
            "host": cls.descriptor.host,
            "purpose": cls.descriptor.purpose,
            "runtime": cls.descriptor.runtime,
            "shape": "thin adapter over the shared AIssuer Python core",
        }
