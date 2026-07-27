#!/usr/bin/env python3
"""Return a depth- and node-bounded subgraph from a JSON repository map."""
from __future__ import annotations
import argparse, json
from pathlib import Path
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--map",required=True); ap.add_argument("--root",required=True); ap.add_argument("--depth",type=int,default=2); ap.add_argument("--max-nodes",type=int,default=50); ap.add_argument("--output",required=True); a=ap.parse_args()
    data=json.loads(Path(a.map).read_text()); nodes={n["id"]:n for n in data.get("nodes",[])}; adj={k:[] for k in nodes}
    for e in data.get("edges",[]):
        if e.get("from") in adj and e.get("to") in nodes: adj[e["from"]].append(e["to"])
    if a.root not in nodes: print(json.dumps({"ok":False,"error":"ROOT_NOT_FOUND"})); return 1
    seen=[a.root]; frontier=[a.root]
    for _ in range(max(0,a.depth)):
        nxt=[]
        for cur in frontier:
            for target in adj[cur]:
                if target not in seen and len(seen)<a.max_nodes: seen.append(target); nxt.append(target)
        frontier=nxt
    result={"nodes":[nodes[k] for k in seen],"edges":[e for e in data.get("edges",[]) if e.get("from") in seen and e.get("to") in seen]}; Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"ok":True,"nodes":len(result["nodes"]),"edges":len(result["edges"])},sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
