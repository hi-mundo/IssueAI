# Review artifacts

Store each execution locally with this layout:

```text
artifacts/
  01_context/
    review-context.json
    normalized-repository.json
    repository-map.json
    product-understanding.json
    intent-model.json
    reference-graph.json
    issue-evidence-graph.json
    contextual-discovery-input.json
  02_discovery/
    rank_input.jsonl
    rank_shards/
    rank_worker_assignments.json
    rank_output.jsonl
    deep_review_input.jsonl
    work_ledger.jsonl
    raw_candidates.jsonl
    discovery_report.md
  03_coverage/
    repository_coverage_ledger.md
    coverage.json
  04_reconciliation/
    dedupe_report.md
    deduped_candidates.jsonl
  05_findings/
    <candidate-id>/candidate_ledger.jsonl
    <candidate-id>/validation_report.md
    <candidate-id>/probe/

review-manifest.json
findings.json
coverage.json
report.md
```

Artifact writes must be atomic at the workflow level: validate before handing
an artifact to the next phase and preserve failed validation output visibly.

Every phase envelope also carries:

```json
{
  "coverage": {
    "worklist_id": "map-1",
    "total_items": 12,
    "examined_items": 10,
    "deferred_items": 2,
    "deferred_ids": ["node-11", "node-12"],
    "uncovered_ids": [],
    "closed": true,
    "surfaces": [
      {
        "id": "surface-1",
        "family": "state-lifecycle",
        "disposition": "reportable"
      }
    ]
  },
  "handoff": {
    "from_phase": "repository-map",
    "to_phase": "understanding",
    "input_artifact_id": "map-input-1",
    "output_artifact_id": "map-output-1"
  }
}
```

`examined_items + deferred_items + len(uncovered_ids)` must equal
`total_items`. A handoff requires `closed: true` and an empty
`uncovered_ids`. Deferred items are explicit scope decisions, not missing
work. Coverage rows remain required even when they do not produce findings.
