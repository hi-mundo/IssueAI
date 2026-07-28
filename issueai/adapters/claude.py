"""Canonical Claude adapter stub."""

from __future__ import annotations

from .base import AdapterDescriptor


class ClaudeAdapter:
    """Describe how AIssuer plugs into Claude-hosted workflows."""

    descriptor = AdapterDescriptor(
        host="claude",
        purpose="Run AIssuer workflows inside Claude-facing tools as a thin host adapter.",
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
