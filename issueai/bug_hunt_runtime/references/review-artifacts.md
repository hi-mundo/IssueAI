# Review Artifact Paths

Use these shared path conventions for Bug Hunt reviews unless the user
explicitly provides different input or output paths.

## Base Paths

- `plugin_dir=<bug-hunt plugin root>`
- `repo_name=<basename of repo_root>`
- `reviews_dir=<system_temp_dir>/bug-hunt-reviews/<repo_name>`
- `review_id=<timestamp or host-provided review id>`
- `review_dir=<reviews_dir>/<review_id>`
- `artifacts_dir=<review_dir>/artifacts`
- `context_dir=<artifacts_dir>/01_context`
- `discovery_dir=<artifacts_dir>/02_discovery`
- `coverage_dir=<artifacts_dir>/03_coverage`
- `reconciliation_dir=<artifacts_dir>/04_reconciliation`
- `findings_dir=<artifacts_dir>/05_findings`

## Context Paths

- Review contract: `<context_dir>/review-context.json`
- Normalized repository: `<context_dir>/normalized-repository.json`
- Repository map: `<context_dir>/repository-map.json`
- Product understanding: `<context_dir>/product-understanding.json`
- Intent model: `<context_dir>/intent-model.json`
- Reference graph: `<context_dir>/reference-graph.json`
- Issue evidence graph: `<context_dir>/issue-evidence-graph.json`
- Contextual discovery input: `<context_dir>/contextual-discovery-input.json`

## Discovery Paths

- Rank input: `<discovery_dir>/rank_input.jsonl`
- Rank shards: `<discovery_dir>/rank_shards/rank-shard-NNNN.input.jsonl`
- Rank worker assignments: `<discovery_dir>/rank_worker_assignments.json`
- Rank output: `<discovery_dir>/rank_output.jsonl`
- Deep review input: `<discovery_dir>/deep_review_input.jsonl`
- Discovery work ledger: `<discovery_dir>/work_ledger.jsonl`
- Raw candidates: `<discovery_dir>/raw_candidates.jsonl`
- Discovery report: `<discovery_dir>/discovery_report.md`

## Coverage Paths

- Repository coverage ledger: `<coverage_dir>/repository_coverage_ledger.md`
- Coverage summary: `<coverage_dir>/coverage.json`

## Reconciliation Paths

- Dedupe report: `<reconciliation_dir>/dedupe_report.md`
- Deduped candidates: `<reconciliation_dir>/deduped_candidates.jsonl`

## Findings Paths

- Per-candidate directory: `<findings_dir>/<candidate_id>/`
- Candidate ledger: `<findings_dir>/<candidate_id>/candidate_ledger.jsonl`
- Validation report: `<findings_dir>/<candidate_id>/validation_report.md`
- Probe artifacts: `<findings_dir>/<candidate_id>/probe/`
- Finding writeup: `<findings_dir>/<slug>/<slug>.md`

## Final Paths

- Review manifest: `<review_dir>/review-manifest.json`
- Canonical findings: `<review_dir>/findings.json`
- Canonical coverage: `<review_dir>/coverage.json`
- Final report projection: `<review_dir>/report.md`

## Placement Rules

- Context artifacts define the review universe and must be written before
  discovery.
- Discovery artifacts define the bounded worklists and candidate inventory.
- Coverage artifacts define which rows remain open, closed, suppressed, not
  applicable, or deferred.
- Reconciliation artifacts operate on candidate instances, not on generic
  mechanism families.
- Final report files are projections of canonical review artifacts; they are
  not the semantic source of truth.
