#!/usr/bin/env python3
"""Run one explicitly approved local probe and preserve its observed result."""
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--command",required=True,help="JSON array of argv"); ap.add_argument("--repo",required=True); ap.add_argument("--output",required=True); ap.add_argument("--allow-execution",action="store_true"); a=ap.parse_args()
    if not a.allow_execution: print(json.dumps({"ok":False,"error":"EXECUTION_NOT_APPROVED"})); return 2
    try: command=json.loads(a.command); assert isinstance(command,list) and command and all(isinstance(x,str) for x in command)
    except (json.JSONDecodeError,AssertionError): print(json.dumps({"ok":False,"error":"COMMAND_MUST_BE_JSON_ARGV"})); return 2
    blocked={"curl","wget","ssh","scp","nc","aws","gcloud","az","docker","kubectl"}
    if Path(command[0]).name in blocked: print(json.dumps({"ok":False,"error":"EXTERNAL_COMMAND_BLOCKED"})); return 2
    try: proc=subprocess.run(command,cwd=str(Path(a.repo).resolve()),capture_output=True,text=True,timeout=30,check=False)
    except (OSError,subprocess.TimeoutExpired) as exc: result={"ok":False,"error":str(exc)}
    else: result={"ok":proc.returncode==0,"command":command,"returncode":proc.returncode,"stdout":proc.stdout,"stderr":proc.stderr,"conclusion":"completed" if proc.returncode==0 else "failed"}
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); print(json.dumps({"ok":result["ok"],"output":a.output},sort_keys=True)); return 0 if result["ok"] else 1
if __name__ == "__main__": raise SystemExit(main())
