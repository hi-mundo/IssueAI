#!/usr/bin/env python3
"""Build a provenance-preserving graph of validated local references."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from _common import dump_json
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); ap.add_argument("--registry",required=True); ap.add_argument("--output",required=True); a=ap.parse_args(); root=Path(a.root).resolve()
    try: registry=json.loads(Path(a.registry).read_text(encoding="utf-8")); assert isinstance(registry,list)
    except (OSError,json.JSONDecodeError,AssertionError) as exc: print(json.dumps({"ok":False,"error":f"INVALID_REFERENCE_REGISTRY:{exc}"})); return 2
    nodes=[]; edges=[]; seen=set()
    for ref in registry:
        required={"id","source","type","authority","domain","technologies","applies_to","validation_status"}
        if not required.issubset(ref) or ref["validation_status"]!="validated": print(json.dumps({"ok":False,"error":"REFERENCE_NOT_VALIDATED","reference_id":ref.get("id")})); return 1
        source=Path(ref["source"]); source=source if source.is_absolute() else root/source
        if not source.is_file(): print(json.dumps({"ok":False,"error":"REFERENCE_SOURCE_MISSING","reference_id":ref["id"]})); return 1
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        if ref.get("content_hash") and ref["content_hash"]!=digest: print(json.dumps({"ok":False,"error":"REFERENCE_HASH_MISMATCH","reference_id":ref["id"]})); return 1
        seen.add(ref["id"]); node={k:ref[k] for k in ("id","type","source","validation_status","domain","technologies","applies_to")}; node["content_hash"]=digest; nodes.append(node)
    for left in sorted(nodes,key=lambda n:n["id"]):
        for right in sorted(nodes,key=lambda n:n["id"]):
            if left["id"] < right["id"] and set(left.get("applies_to",[])) & set(right.get("applies_to",[])): edges.append({"from":left["id"],"to":right["id"],"relation":"shares_domain"})
    dump_json({"nodes":nodes,"edges":edges},a.output); print(json.dumps({"ok":True,"nodes":len(nodes),"edges":len(edges),"output":a.output},sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
