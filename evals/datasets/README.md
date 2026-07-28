# IssueAI historical benchmark datasets

This folder is the canonical registry surface for IssueAI historical benchmark
datasets.

The benchmark strategy is intentionally staged:

1. first, optimize IssueAI as a usable and installable tool;
2. then, grow the historical real-issue benchmark in independent batches;
3. only after the tool is stable enough, run external AI-vs-IssueAI comparisons
   with strong prompts.

## Current posture

Right now the benchmark program is centered on historical issue recovery:

- real repository snapshots
- blind runtime inputs
- structured ground truth outside the runtime
- mechanism/route recovery as the primary score

This means benchmark expansion should happen by adding more historical issue
batches, not by changing the benchmark philosophy.

## Registry rules

- Each dataset batch should be independently named and versionable.
- The benchmark runtime must remain blind to titles, URLs, and expected routes.
- Ground truth must stay outside the review runtime.
- New batches should be additive; do not rewrite prior validated batches.
- Cross-model comparisons belong to a later benchmark phase, after IssueAI is
  more optimized as a marketplace-installable tool.

## Current batch

- `historical-route-20-v1`
  - manifest: `../unmapped-repositories-20.json`
  - purpose: first official historical route recovery set
  - status: validated on July 27, 2026

## Reserved next batch

- `historical-route-20-v2`
  - manifest: `historical-route-20-v2/manifest.json`
  - proposed ground truth: `historical-route-20-v2/ground-truth.proposed.json`
  - purpose: next independent 20-case historical route recovery set
  - status: proposed from artifacts, not manually gold-validated yet

## Current measured expansion snapshot

As of July 27, 2026:

- `historical-route-20-v1` remains the official validated batch with 20/20 top-20 success
- `historical-route-20-v1` + `historical-route-20-v2` together reached 40/40 top-20 success in the current internal run
- top-100 remained a diagnostic envelope in both runs
- the second statement is useful benchmark evidence, but not a replacement for manual gold validation of `historical-route-20-v2`
