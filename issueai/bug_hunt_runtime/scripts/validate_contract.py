#!/usr/bin/env python3
"""Validate a JSON artifact against the plugin's intentionally small schema subset."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def check(value, schema, path="$", errors=None):
    errors = errors if errors is not None else []
    typ = schema.get("type")
    ok = {"object": isinstance(value, dict), "array": isinstance(value, list), "string": isinstance(value, str), "integer": isinstance(value, int) and not isinstance(value, bool), "number": isinstance(value, (int, float)) and not isinstance(value, bool), "boolean": isinstance(value, bool)}
    if typ in ok and not ok[typ]: errors.append(f"{path}: expected {typ}"); return errors
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value: errors.append(f"{path}.{key}: required")
        for key, child in schema.get("properties", {}).items():
            if key in value: check(value[key], child, f"{path}.{key}", errors)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0): errors.append(f"{path}: too few items")
        for i, item in enumerate(value): check(item, schema.get("items", {}), f"{path}[{i}]", errors)
    if isinstance(value, str) and len(value) < schema.get("minLength", 0): errors.append(f"{path}: too short")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]: errors.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]: errors.append(f"{path}: above maximum")
    if "enum" in schema and value not in schema["enum"]: errors.append(f"{path}: invalid enum value")
    return errors

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--schema", required=True); ap.add_argument("--input", required=True)
    args = ap.parse_args()
    try:
        value = json.loads(Path(args.input).read_text(encoding="utf-8")); schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
        errors = check(value, schema)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)})); return 2
    result = {"ok": not errors, "errors": errors, "schema": args.schema, "input": args.input}
    print(json.dumps(result, sort_keys=True)); return 0 if not errors else 1
if __name__ == "__main__": raise SystemExit(main())
