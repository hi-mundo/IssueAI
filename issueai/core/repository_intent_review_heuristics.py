"""Heuristics and scope filters for Repository Intent Review."""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .repository_recon_profile import prefer_runtime_paths, read_text_safe
from .repository_recon_state import ISSUEAI_DIRNAME, domain_for_path


SCHEMA_HINTS = ("schema", "schemas", "validator", "validate", "zod", "pydantic", "dto", "type", "types", "interface")
CONTRACT_HINTS = ("from .contracts import", "from issueai.core.contracts import", "typedict", "typeddict", "typealias")
MIDDLEWARE_HINTS = ("middleware", "middlewares", "guard", "guards", "auth", "protect", "protection")
ROLE_REVIEW_ORDER = ("routes", "middlewares", "controllers", "services", "schemas", "orm", "thirdparty")


def unique_paths(recon: dict[str, Any], *roles: str) -> list[str]:
    role_locations = recon.get("applicationMap", {}).get("roleLocations", {})
    seen: set[str] = set()
    ordered: list[str] = []
    for role in roles:
        for path in prefer_runtime_paths(role_locations.get(role, [])):
            if path not in seen:
                seen.add(path)
                ordered.append(path)
    return ordered


def critical_paths(recon: dict[str, Any]) -> list[str]:
    role_paths = unique_paths(recon, "routes", "middlewares", "controllers", "services", "orm", "thirdparty")
    largest = [item["path"] for item in recon.get("applicationMap", {}).get("largestFiles", [])]
    ordered: list[str] = []
    seen: set[str] = set()
    for path in [*role_paths, *largest]:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    return ordered[:24]


def filter_paths_to_domains(paths: Sequence[str], covered_domains: Sequence[str]) -> list[str]:
    if not covered_domains:
        return list(paths)
    domain_set = set(covered_domains)
    filtered = [path for path in paths if domain_for_path(path) in domain_set]
    return filtered or list(paths)


def filter_intent_model_to_domains(intent_model: list[dict[str, Any]], covered_domains: Sequence[str]) -> list[dict[str, Any]]:
    if not covered_domains:
        return intent_model
    filtered: list[dict[str, Any]] = []
    for item in intent_model:
        scoped_paths = filter_paths_to_domains(item.get("paths", []), covered_domains)
        if not scoped_paths:
            continue
        filtered.append({**item, "paths": scoped_paths})
    return filtered or intent_model


def filter_findings_to_domains(findings: list[dict[str, Any]], covered_domains: Sequence[str]) -> list[dict[str, Any]]:
    if not covered_domains:
        return findings
    domain_set = set(covered_domains)
    return [
        item
        for item in findings
        if not item.get("path") or domain_for_path(str(item.get("path", ""))) in domain_set
    ]


def load_recon_findings(repo_root: Path) -> list[dict[str, Any]]:
    findings_path = repo_root / ISSUEAI_DIRNAME / "findings" / "repository-recon-findings.json"
    if not findings_path.exists():
        return []
    return json.loads(findings_path.read_text()).get("findings", [])


def derive_intent_model(recon: dict[str, Any]) -> list[dict[str, Any]]:
    role_locations = recon.get("applicationMap", {}).get("roleLocations", {})
    guarantees = {
        "routes": "Routes should expose the intended surface and hand off cleanly into protected, schema-respecting flows.",
        "middlewares": "Middlewares should protect or normalize cross-cutting boundaries without easy bypass paths.",
        "controllers": "Controllers should adapt external input into the right domain/service calls without leaking weak contracts.",
        "services": "Services should enforce business rules and pass structurally valid data across boundaries.",
        "schemas": "Schemas and validators should make contract drift or nullability breaks visible early.",
        "orm": "Persistence layers should receive already-normalized data and preserve repository guarantees.",
        "thirdparty": "Third-party integrations should not bypass validation, typing assumptions, or error handling.",
    }
    return [
        {"role": role, "expectedGuarantee": guarantees[role], "paths": role_locations.get(role, [])[:6]}
        for role in ROLE_REVIEW_ORDER
        if role_locations.get(role)
    ]


def path_text(repo_root: Path, relative_path: str) -> str:
    return read_text_safe(repo_root / relative_path)


def path_exists_with_hint(repo_root: Path, relative_path: str, hints: tuple[str, ...]) -> bool:
    parent = (repo_root / relative_path).parent
    if not parent.exists():
        return False
    lowered = {child.name.lower() for child in parent.iterdir() if child.is_file()}
    return any(any(hint in name for hint in hints) for name in lowered)


def schema_gaps(repo_root: Path, recon: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for relative_path in unique_paths(recon, "routes", "controllers", "services")[:18]:
        text = path_text(repo_root, relative_path).lower()
        if any(hint in text for hint in SCHEMA_HINTS):
            continue
        if any(hint in text for hint in CONTRACT_HINTS):
            continue
        if path_exists_with_hint(repo_root, relative_path, SCHEMA_HINTS):
            continue
        findings.append(
            {
                "type": "schema-gap",
                "breakScore": "medium",
                "path": relative_path,
                "reason": "This high-signal implementation path does not show a nearby schema, validator, or explicit contract artifact.",
            }
        )
    return findings[:8]


def split_top_level_params(raw_params: str) -> list[str]:
    params: list[str] = []
    current: list[str] = []
    closers: list[str] = []
    quote: str | None = None
    escaped = False
    opener_to_closer = {"(": ")", "[": "]", "{": "}"}

    for char in raw_params:
        if quote is not None:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue

        if char in {"'", '"'}:
            quote = char
            current.append(char)
            continue
        if char in opener_to_closer:
            closers.append(opener_to_closer[char])
            current.append(char)
            continue
        if closers and char == closers[-1]:
            closers.pop()
            current.append(char)
            continue
        if char == "," and not closers:
            value = "".join(current).strip()
            if value and value not in {"self", "cls", "*", "/"}:
                params.append(value)
            current = []
            continue
        current.append(char)

    value = "".join(current).strip()
    if value and value not in {"self", "cls", "*", "/"}:
        params.append(value)
    return params


def regex_python_annotation_findings(relative_path: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    pattern = re.compile(r"^\s*(async\s+def|def)\s+([a-zA-Z_][a-zA-Z0-9_]*)\((.*?)\)(\s*->\s*[^:]+)?\s*:", re.MULTILINE | re.DOTALL)
    for _, function_name, raw_params, return_annotation in pattern.findall(text):
        if function_name.startswith("_"):
            continue
        params = split_top_level_params(raw_params)
        if any(":" not in item for item in params) or not return_annotation:
            findings.append(
                {
                    "type": "typing-gap",
                    "breakScore": "low",
                    "path": relative_path,
                    "reason": f"Function `{function_name}` relies on implicit typing in a high-signal file, which weakens contract tracking.",
                }
            )
            break
    return findings


def python_annotation_findings(repo_root: Path, recon: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for relative_path in unique_paths(recon, "middlewares", "controllers", "services")[:18]:
        if not relative_path.endswith(".py"):
            continue
        text = path_text(repo_root, relative_path)
        try:
            tree = ast.parse(text, filename=relative_path)
        except SyntaxError:
            findings.extend(regex_python_annotation_findings(relative_path, text))
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name.startswith("_"):
                continue
            params = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            if node.args.vararg is not None:
                params.append(node.args.vararg)
            if node.args.kwarg is not None:
                params.append(node.args.kwarg)
            relevant_params = [param for param in params if param.arg not in {"self", "cls"}]
            if any(param.annotation is None for param in relevant_params) or node.returns is None:
                findings.append(
                    {
                        "type": "typing-gap",
                        "breakScore": "low",
                        "path": relative_path,
                        "reason": f"Function `{node.name}` relies on implicit typing in a high-signal file, which weakens contract tracking.",
                    }
                )
                break
    return findings[:8]


def javascript_typing_findings(recon: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for relative_path in unique_paths(recon, "routes", "middlewares", "controllers", "services")[:18]:
        if relative_path.endswith((".js", ".jsx")):
            findings.append(
                {
                    "type": "typing-gap",
                    "breakScore": "low",
                    "path": relative_path,
                    "reason": "JavaScript path in a high-signal role depends on inferred contracts, so Intent Review should treat typing assumptions as fragile.",
                }
            )
    return findings[:6]


def async_findings(repo_root: Path, recon: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for relative_path in unique_paths(recon, "routes", "middlewares", "controllers", "services", "thirdparty")[:24]:
        lowered = path_text(repo_root, relative_path).lower()
        if "async def " not in lowered and "async function" not in lowered and "async (" not in lowered:
            continue
        if "await " not in lowered:
            findings.append(
                {
                    "type": "async-without-await",
                    "breakScore": "medium",
                    "path": relative_path,
                    "reason": "Async code appears to exist without visible await usage, which often signals a broken or misleading async boundary.",
                }
            )
        elif not any(token in lowered for token in ("try:", "except ", "try {", ".catch(", "catch (")):
            findings.append(
                {
                    "type": "async-error-gap",
                    "breakScore": "low",
                    "path": relative_path,
                    "reason": "Async code exists without obvious local failure handling, which can make break paths easier to miss.",
                }
            )
    return findings[:8]


def middleware_findings(repo_root: Path, recon: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not recon.get("applicationMap", {}).get("roleLocations", {}).get("middlewares"):
        return findings
    for relative_path in unique_paths(recon, "routes")[:12]:
        text = path_text(repo_root, relative_path).lower()
        if any(hint in text for hint in MIDDLEWARE_HINTS):
            continue
        findings.append(
            {
                "type": "middleware-coverage-gap",
                "breakScore": "medium",
                "path": relative_path,
                "reason": "Repository has middleware/guard-like structure, but this route path does not show an obvious protection hook.",
            }
        )
    return findings[:6]


def dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in findings:
        key = (item["type"], item["path"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def collect_heuristic_findings(repo_root: Path, recon: dict[str, Any], covered_domains: Sequence[str]) -> list[dict[str, Any]]:
    heuristic_findings = [
        *load_recon_findings(repo_root),
        *schema_gaps(repo_root, recon),
        *python_annotation_findings(repo_root, recon),
        *javascript_typing_findings(recon),
        *async_findings(repo_root, recon),
        *middleware_findings(repo_root, recon),
    ]
    return dedupe_findings(filter_findings_to_domains(heuristic_findings, covered_domains))
