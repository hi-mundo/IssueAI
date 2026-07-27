#!/usr/bin/env python3
"""Persist resumable review state without deleting discarded analysis branches."""
from __future__ import annotations
import argparse, hashlib, json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path

def read(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def write(path, value):
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=".run-state-",dir=str(target.parent)); os.close(fd)
    Path(tmp).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8"); os.replace(tmp,target)
def now(): return datetime.now(timezone.utc).isoformat()
def main()->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="action",required=True)
    init=sub.add_parser("init"); init.add_argument("--run",required=True); init.add_argument("--run-id",required=True); init.add_argument("--workflow-id",required=True); init.add_argument("--workflow-version",required=True); init.add_argument("--repo",required=True)
    cp=sub.add_parser("checkpoint"); cp.add_argument("--run",required=True); cp.add_argument("--workflow",required=True); cp.add_argument("--phase",required=True); cp.add_argument("--artifact",required=True,help="JSON validated artifact metadata")
    ds=sub.add_parser("discard"); ds.add_argument("--run",required=True); ds.add_argument("--branch-id",required=True); ds.add_argument("--reason",required=True)
    fail=sub.add_parser("fail"); fail.add_argument("--run",required=True); fail.add_argument("--phase",required=True); fail.add_argument("--error",required=True)
    resume=sub.add_parser("resume"); resume.add_argument("--run",required=True)
    a=ap.parse_args()
    if a.action=="init":
        repo=Path(a.repo).resolve(); digest=hashlib.sha256();
        for p in sorted(x for x in repo.rglob("*") if x.is_file() and ".git" not in x.parts): digest.update(p.relative_to(repo).as_posix().encode()); digest.update(hashlib.sha256(p.read_bytes()).digest())
        state={"run_id":a.run_id,"workflow_id":a.workflow_id,"workflow_version":a.workflow_version,"repository":str(repo),"repository_hash":digest.hexdigest(),"status":"running","current_phase":"preflight","completed_phases":[],"discarded_branches":[],"active_branches":[],"failures":[],"checkpoints":[],"created_at":now()}; write(a.run,state)
    else:
        state=read(a.run)
        if a.action=="checkpoint":
            if state["status"]!="running": print(json.dumps({"ok":False,"error":"RUN_NOT_RUNNING"})); return 1
            workflow=json.loads(Path(a.workflow).read_text(encoding="utf-8")); phases=workflow.get("phases",[]); ids=[p.get("id") for p in phases]
            if a.phase!=state.get("current_phase") or a.phase not in ids: print(json.dumps({"ok":False,"error":"CHECKPOINT_PHASE_OUT_OF_ORDER","expected":state.get("current_phase")})); return 1
            try: artifact=json.loads(a.artifact)
            except json.JSONDecodeError: print(json.dumps({"ok":False,"error":"ARTIFACT_MUST_BE_JSON"})); return 2
            coverage = artifact.get("coverage", {})
            if artifact.get("phase_id")!=a.phase or artifact.get("status")!="validated": print(json.dumps({"ok":False,"error":"CHECKPOINT_ARTIFACT_NOT_VALIDATED"})); return 1
            if coverage.get("closed") is not True or coverage.get("uncovered_ids"):
                print(json.dumps({"ok":False,"error":"CHECKPOINT_COVERAGE_NOT_CLOSED"})); return 1
            handoff = artifact.get("handoff", {})
            if handoff.get("output_artifact_id") != artifact.get("artifact_id"):
                print(json.dumps({"ok":False,"error":"CHECKPOINT_HANDOFF_INVALID"})); return 1
            state["checkpoints"].append({"phase":a.phase,"artifact":artifact,"timestamp":now()});
            if a.phase not in state["completed_phases"]: state["completed_phases"].append(a.phase)
            state["current_phase"]=phases[ids.index(a.phase)].get("next",""); write(a.run,state)
        elif a.action=="discard": state["discarded_branches"].append({"branch_id":a.branch_id,"reason":a.reason,"timestamp":now()}); write(a.run,state)
        elif a.action=="fail": state["status"]="blocked"; state["current_phase"]=a.phase; state["failures"].append({"phase":a.phase,"error":a.error,"timestamp":now()}); write(a.run,state)
        elif a.action=="resume":
            if state["status"]=="blocked": state["status"]="running"; write(a.run,state)
            print(json.dumps({"ok":True,"current_phase":state["current_phase"],"completed_phases":state["completed_phases"],"discarded_branches":state["discarded_branches"],"failures":state["failures"]},sort_keys=True)); return 0
    print(json.dumps({"ok":True,"action":a.action,"run":a.run},sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
