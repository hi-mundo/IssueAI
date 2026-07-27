"""Small standard-library helpers shared by Bug Hunt scripts."""
from __future__ import annotations
import json
from pathlib import Path

def load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def dump_json(value: object, path: str | Path) -> None:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def require(condition: bool, message: str) -> None:
    if not condition: raise ValueError(message)
