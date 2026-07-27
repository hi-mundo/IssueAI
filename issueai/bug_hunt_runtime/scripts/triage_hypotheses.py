#!/usr/bin/env python3
"""Normalize and deduplicate hypotheses without deciding whether a defect exists."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True); ap.add_argument("--output",required=True); ap.add_argument("--review-id",default="triage"); a=ap.parse_args()
    try: values=json.loads(Path(a.input).read_text(encoding="utf-8")); assert isinstance(values,list)
    except (OSError,json.JSONDecodeError,AssertionError) as exc: print(json.dumps({"ok":False,"error":f"INVALID_HYPOTHESES:{exc}"})); return 2
    entries=[]; seen={}
    for item in values:
        required=["id","feature_id","expected_behavior","suspected_behavior","validation_method"]
        if any(not item.get(k) for k in required): print(json.dumps({"ok":False,"error":"HYPOTHESIS_MISSING_VALIDATION_FIELDS","hypothesis_id":item.get("id")})); return 1
        key="|".join(str(item.get(k,"")) for k in ("feature_id","expected_behavior","suspected_behavior","validation_method")); group="root:"+hashlib.sha1(key.encode()).hexdigest()[:12]
        if group in seen: entries.append({"hypothesis_id":item["id"],"disposition":"duplicate","evidence_ids":[],"proof_gap":"Duplicate of an earlier hypothesis.","root_group":group})
        else: seen[group]=item["id"]; entries.append({"hypothesis_id":item["id"],"disposition":"selected","evidence_ids":item.get("evidence_initial",[]),"proof_gap":"","root_group":group})
    result={"review_id":a.review_id,"entries":entries}; Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(json.dumps({"ok":True,"entries":len(entries),"duplicates":sum(e["disposition"]=="duplicate" for e in entries)},sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
