#!/usr/bin/env python3
"""Build a bounded, line-oriented repository index without loading source into a model."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from _common import dump_json

SKIP={".git","node_modules",".venv","venv","dist","build","__pycache__"}
EXT={".py":"python",".js":"javascript",".ts":"typescript",".tsx":"typescript",".jsx":"javascript",".go":"go",".rs":"rust",".java":"java",".c":"c",".h":"c-header",".cc":"cpp",".cpp":"cpp",".cxx":"cpp",".hpp":"cpp-header",".php":"php",".rb":"ruby",".swift":"swift",".kt":"kotlin"}
def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",required=True); ap.add_argument("--normalized",required=True); ap.add_argument("--output",required=True); ap.add_argument("--max-nodes",type=int,default=5000); ap.add_argument("--max-edges",type=int,default=20000); a=ap.parse_args(); root=Path(a.repo).resolve(); nodes=[]; edges=[]
    normalized=json.loads(Path(a.normalized).read_text(encoding="utf-8")); all_files=[root/item["path"] for item in normalized.get("files",[]) if item.get("kind")=="source" and not item.get("generated") and not item.get("vendor")]
    # normalize_repository already made the deterministic, risk-aware bounded
    # selection.  Reordering here would lose compound surfaces that it retained
    # (for example AgentHost or strided_slice_op) when this smaller index is cut.
    files=all_files[:a.max_nodes]
    by_stem={}
    for other in files:
        by_stem.setdefault(other.stem, []).append(other)
    for p in files:
        rel=p.relative_to(root).as_posix(); text=p.read_text(encoding="utf-8",errors="replace"); node_id="file:"+hashlib.sha1(rel.encode()).hexdigest()[:12]
        language=EXT.get(p.suffix, normalized.get("files",[])[next((i for i,item in enumerate(normalized.get("files",[])) if item.get("path")==rel),0)].get("language","unknown"))
        nodes.append({"id":node_id,"type":"file","location":rel,"responsibility_observed":text.splitlines()[0][:160] if text.splitlines() else "empty file","dependencies":[],"structural_deviations":[],"tags":[language]})
        if a.max_edges > 0:
            for stem, candidates in by_stem.items():
                if stem == "__init__" or stem not in text:
                    continue
                for other in candidates:
                    if len(edges) >= a.max_edges:
                        break
                    if other != p:
                        edges.append({"from":node_id,"to":"file:"+hashlib.sha1(other.relative_to(root).as_posix().encode()).hexdigest()[:12],"relation":"depends_on"})
    dump_json({"nodes":nodes,"edges":edges,"bounded":{"max_nodes":a.max_nodes,"max_edges":a.max_edges,"source_files":len(all_files),"truncated":len(files)<len(all_files)}},a.output); print(json.dumps({"ok":True,"nodes":len(nodes),"edges":len(edges),"source_files":len(all_files),"truncated":len(files)<len(all_files),"output":a.output},sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
