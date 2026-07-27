"""Canonical adapter entrypoints for host integrations."""

from .claude import ClaudeAdapter
from .codex import CodexAdapter

__all__ = ["ClaudeAdapter", "CodexAdapter"]
