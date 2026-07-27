#!/usr/bin/env python3
"""Project validated finding artifacts into a deterministic Markdown report."""
from __future__ import annotations
import argparse,json
from pathlib import Path
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--findings",required=True); ap.add_argument("--output",required=True); a=ap.parse_args(); findings=json.loads(Path(a.findings).read_text())
    if not isinstance(findings,list): print(json.dumps({"ok":False,"error":"FINDINGS_MUST_BE_ARRAY"})); return 1
    required={"id","hypothesis_id","feature_id","disposition","evidence","confidence","impact_functional","severity","break_score"}
    for finding in findings:
        if not isinstance(finding,dict) or not required.issubset(finding) or finding["disposition"] not in {"finding","discarded","inconclusive"} or not finding["evidence"]:
            print(json.dumps({"ok":False,"error":"INVALID_VALIDATED_FINDING"})); return 1
    lines=["# Bug Hunt report","",f"Validated artifacts: {len(findings)}","", "## Dispositions", ""]
    for f in sorted(findings,key=lambda x:(x.get("disposition",""),x.get("id",""))):
        d=f.get("disposition"); lines += [f"### {f.get('title',f.get('id','untitled'))}","",f"- Disposition: `{d}`",f"- Feature: `{f.get('feature_id','')}`",f"- Hypothesis: `{f.get('hypothesis_id','')}`",f"- Confidence: `{f.get('confidence','')}`",f"- Severity: `{f.get('severity','')}`",f"- Break score: `{f.get('break_score','')}`",f"- Impact: {f.get('impact_functional','')}",f"- Evidence: {', '.join(map(str,f.get('evidence',[])))}"]
        if d=="finding": lines += [f"- Location: {f.get('location','')}",f"- Expected: {f.get('expected_behavior','')}",f"- Observed: {f.get('observed_behavior','')}",f"- Correction direction: {f.get('correction_direction','')}"]
        else: lines += [f"- Proof gap: {f.get('proof_gap','')}"]
        lines.append("")
    Path(a.output).write_text("\n".join(lines),encoding="utf-8"); print(json.dumps({"ok":True,"findings":len(findings),"output":a.output},sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
