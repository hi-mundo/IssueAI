"""Host-first integration descriptors for IssueAI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HostPluginDescriptor:
    host: str
    integration_mode: str
    primary: bool = True


def default_host_plugins() -> tuple[HostPluginDescriptor, ...]:
    return (
        HostPluginDescriptor(host="codex", integration_mode="importable plugin"),
        HostPluginDescriptor(host="claude", integration_mode="importable plugin"),
        HostPluginDescriptor(host="cursor", integration_mode="importable package/plugin"),
    )
