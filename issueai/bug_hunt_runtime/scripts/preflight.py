#!/usr/bin/env python3
"""Validate a review contract and safe local review workspace."""
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path
from validate_contract import check

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--contract", required=True); ap.add_argument("--repo", required=True); ap.add_argument("--artifacts", required=True)
    a = ap.parse_args(); failures=[]; repo=Path(a.repo).resolve()
    try: contract=json.loads(Path(a.contract).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: print(json.dumps({"ok":False,"failures":[f"CONTRACT_READ:{exc}"]})); return 2
    schema=Path(__file__).parent.parent/"schemas/review-context.schema.json"; failures.extend(check(contract,json.loads(schema.read_text()),"$"))
    if not repo.is_dir(): failures.append("REPO_MISSING")
    if not (repo/".git").exists(): failures.append("GIT_METADATA_MISSING")
    try: subprocess.run(["git","-C",str(repo),"rev-parse","--show-toplevel"],check=True,capture_output=True,text=True)
    except (OSError, subprocess.CalledProcessError): failures.append("GIT_UNAVAILABLE")
    if Path(a.artifacts).resolve() == repo: failures.append("ARTIFACTS_MUST_BE_SEPARATE")
    result={"ok":not failures,"failures":failures,"review_id":contract.get("review_id"),"repository":str(repo),"artifacts":str(Path(a.artifacts).resolve())}
    print(json.dumps(result,sort_keys=True)); return 0 if not failures else 1
if __name__ == "__main__": raise SystemExit(main())
