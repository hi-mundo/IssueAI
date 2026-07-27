#!/usr/bin/env python3
"""Gate phase handoffs: only validated predecessor artifacts may advance."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from validate_contract import check

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--workflow",required=True); ap.add_argument("--phase",required=True); ap.add_argument("--input",required=True); ap.add_argument("--output",required=True); a=ap.parse_args()
    root=Path(a.workflow).resolve().parent
    try:
        workflow=json.loads(Path(a.workflow).read_text(encoding="utf-8")); incoming=json.loads(Path(a.input).read_text(encoding="utf-8")); outgoing=json.loads(Path(a.output).read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: print(json.dumps({"ok":False,"error":f"ARTIFACT_READ_FAILED:{exc}"})); return 2
    phases=workflow.get("phases",[]); ids=[p.get("id") for p in phases]
    if not phases or len(ids) != len(set(ids)) or any(not item for item in ids):
        print(json.dumps({"ok":False,"error":"WORKFLOW_PHASE_IDS_INVALID"})); return 1
    for index, item in enumerate(phases):
        expected = phases[index + 1].get("id") if index + 1 < len(phases) else "done"
        if item.get("next") != expected:
            print(json.dumps({"ok":False,"error":"WORKFLOW_CHAIN_INVALID","phase":item.get("id"),"expected_next":expected})); return 1
    if a.phase not in ids: print(json.dumps({"ok":False,"error":"UNKNOWN_PHASE"})); return 1
    index=ids.index(a.phase); expected_previous=ids[index-1] if index else None; phase=phases[index]
    if expected_previous is not None and (not isinstance(incoming,dict) or incoming.get("phase_id")!=expected_previous or incoming.get("status")!="validated"):
        print(json.dumps({"ok":False,"error":"PREDECESSOR_HANDOFF_INVALID","expected_previous":expected_previous})); return 1
    input_schema_path=root/"schemas"/phase["input_schema"]; output_schema_path=root/"schemas"/phase["output_schema"]
    if not input_schema_path.is_file() or not output_schema_path.is_file(): print(json.dumps({"ok":False,"error":"PHASE_SCHEMA_MISSING"})); return 1
    input_errors=check(incoming,json.loads(input_schema_path.read_text(encoding="utf-8")))
    if input_errors: print(json.dumps({"ok":False,"error":"INPUT_SCHEMA_INVALID","details":input_errors})); return 1
    errors=check(outgoing,json.loads(output_schema_path.read_text(encoding="utf-8")))
    if errors: print(json.dumps({"ok":False,"error":"OUTPUT_SCHEMA_INVALID","details":errors})); return 1
    if phase["output_schema"]=="phase-envelope.schema.json" and (outgoing.get("phase_id")!=a.phase or outgoing.get("status")!="validated"): print(json.dumps({"ok":False,"error":"OUTPUT_NOT_VALIDATED"})); return 1
    if phase["output_schema"]=="phase-envelope.schema.json" and outgoing.get("schema_id")!=phase["output_schema"]: print(json.dumps({"ok":False,"error":"OUTPUT_SCHEMA_ID_MISMATCH","expected":phase["output_schema"]})); return 1
    if not isinstance(incoming,dict) or outgoing.get("review_id")!=incoming.get("review_id"): print(json.dumps({"ok":False,"error":"REVIEW_ID_MISMATCH"})); return 1
    coverage = outgoing.get("coverage")
    if not isinstance(coverage, dict): print(json.dumps({"ok":False,"error":"COVERAGE_MISSING"})); return 1
    total = coverage.get("total_items"); examined = coverage.get("examined_items"); deferred = coverage.get("deferred_items"); uncovered = coverage.get("uncovered_ids")
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in (total, examined, deferred)) or not isinstance(uncovered, list):
        print(json.dumps({"ok":False,"error":"COVERAGE_INVALID"})); return 1
    if examined + deferred + len(uncovered) != total or coverage.get("closed") is not True or uncovered:
        print(json.dumps({"ok":False,"error":"COVERAGE_NOT_CLOSED","coverage":coverage})); return 1
    expected_next=phases[index].get("next")
    handoff = outgoing.get("handoff", {})
    if handoff.get("from_phase") != a.phase or handoff.get("to_phase") != expected_next or handoff.get("input_artifact_id") != incoming.get("artifact_id") or handoff.get("output_artifact_id") != outgoing.get("artifact_id"):
        print(json.dumps({"ok":False,"error":"HANDOFF_LINEAGE_INVALID","expected_next":expected_next})); return 1
    if coverage.get("deferred_items") != len(coverage.get("deferred_ids", [])):
        print(json.dumps({"ok":False,"error":"COVERAGE_DEFERRED_COUNT_INVALID"})); return 1
    missing_data = [key for key in phase.get("required_data_keys", []) if key not in outgoing.get("data", {})]
    if missing_data:
        print(json.dumps({"ok":False,"error":"PHASE_OUTPUT_INCOMPLETE","missing_data_keys":missing_data})); return 1
    print(json.dumps({"ok":True,"phase":a.phase,"predecessor":expected_previous,"next":expected_next,"artifact_id":outgoing.get("artifact_id")},sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
