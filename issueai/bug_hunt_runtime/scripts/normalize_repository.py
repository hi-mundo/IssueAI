#!/usr/bin/env python3
"""Create canonical file records for the repository graph."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from _common import dump_json
SKIP={".git","node_modules",".venv","venv","dist","build","__pycache__"}
LANG={".py":"python",".js":"javascript",".ts":"typescript",".tsx":"typescript",".jsx":"javascript",".go":"go",".rs":"rust",".java":"java",".c":"c",".h":"c-header",".cc":"cpp",".cpp":"cpp",".cxx":"cpp",".hpp":"cpp-header",".php":"php",".rb":"ruby",".swift":"swift",".kt":"kotlin",".md":"markdown",".json":"json",".yaml":"yaml",".yml":"yaml"}
SOURCE_LANG={key:value for key,value in LANG.items() if value not in {"markdown","json","yaml"}}
PRIMARY={"src","lib","libs","modules","compiler","library","internal","pkg","app","cmd","include"}
SECONDARY={"deps","vendor","third_party","tools","test","tests","benchmark","bench","docs","doc","examples"}
CORE_SUBDIRS={"runtime","internal","core","net","os","syscall","reflect"}
# These are structural risk surfaces, not issue-specific terms.  Match inside
# compound names too (for example AgentHost and strided_slice_op), otherwise a
# bounded review can discard the owning implementation before discovery starts.
SURFACE_HINT=re.compile(r"config|exporter|receiver|processor|sandbox|handler|route|runtime|resource|agent|session|compiler|kernel|slice|timeout|timer",re.I)
SURFACE_TERMS=("config","exporter","receiver","processor","sandbox","handler","route","runtime","resource","agent","session","compiler","kernel","slice","timeout","timer")

def selection_key(path: Path, repository: Path) -> tuple:
    relative=path.relative_to(repository)
    surface_matches=sum(term in relative.as_posix().lower() for term in SURFACE_TERMS)
    surface_rank=-surface_matches
    parts={part.lower() for part in relative.parts}
    root=relative.parts[0].lower() if relative.parts else ""
    if root in PRIMARY: rank=0
    elif root in SECONDARY: rank=2
    else: rank=1
    if "vendor" in parts or "third_party" in parts or "node_modules" in parts: rank+=1
    if "test" in parts or "tests" in parts or "fixtures" in parts: rank+=1
    if len(relative.parts)>1 and relative.parts[1].lower() in CORE_SUBDIRS: rank-=1
    return surface_rank, rank, path.as_posix()
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",required=True); ap.add_argument("--output",required=True); ap.add_argument("--max-files",type=int,default=5000); a=ap.parse_args(); root=Path(a.repo).resolve(); records=[]
    if not root.is_dir(): print(json.dumps({"ok":False,"error":"REPO_MISSING"})); return 1
    candidates=sorted(p for p in root.rglob("*") if p.is_file() and not (set(p.parts)&SKIP))
    source_candidates=sorted((p for p in candidates if p.suffix.lower() in SOURCE_LANG),key=lambda p: selection_key(p,root))
    other_candidates=[p for p in candidates if p.suffix.lower() not in SOURCE_LANG]
    selected=(source_candidates+other_candidates)[:a.max_files]
    for path in selected:
        rel=path.relative_to(root).as_posix(); raw=path.read_bytes(); suffix=path.suffix.lower(); parse="available"
        try: text=raw.decode("utf-8")
        except UnicodeDecodeError: text=raw.decode("utf-8",errors="replace"); parse="decode_replaced"
        if not text: parse="empty"
        generated=any(part.lower() in {"generated","gen"} for part in path.parts) or path.name.endswith(".generated"+suffix)
        vendor=any(part.lower() in {"vendor","node_modules","third_party"} for part in path.parts)
        records.append({"id":"file:"+hashlib.sha256(rel.encode()).hexdigest()[:16],"path":rel,"kind":"source" if suffix in SOURCE_LANG else "resource","language":LANG.get(suffix,"unknown"),"content_hash":hashlib.sha256(raw).hexdigest(),"line_count":len(text.splitlines()),"parse_status":parse,"generated":generated,"vendor":vendor})
    dump_json({"repository":str(root),"files":records,"selection":{"max_files":a.max_files,"candidate_files":len(candidates),"truncated":len(selected)<len(candidates),"source_files_prioritized":True}},a.output); print(json.dumps({"ok":True,"files":len(records),"candidate_files":len(candidates),"truncated":len(selected)<len(candidates),"output":a.output},sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
