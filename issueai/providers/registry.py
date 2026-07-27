"""Optional provider/runtime registry for compatibility mode."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderDescriptor:
    name: str
    mode: str
    primary: bool = False


def default_providers() -> tuple[ProviderDescriptor, ...]:
    return (
        ProviderDescriptor(name="host", mode="use host runtime when embedded", primary=True),
        ProviderDescriptor(name="codex-sdk", mode="manual compatibility runtime"),
        ProviderDescriptor(name="claude-sdk", mode="manual compatibility runtime"),
        ProviderDescriptor(name="api-key", mode="fallback direct provider path"),
    )
