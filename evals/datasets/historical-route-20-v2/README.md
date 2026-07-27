# historical-route-20-v2

This folder reserves the structure for the next independent 20-case historical
route recovery batch.

Status on July 27, 2026:

- planned
- not populated yet
- not validated yet

## Intended contents

- `manifest.json`
  - 20 new historical cases
- `NOTES.md`
  - curation notes, exclusions, and provenance reminders

The runtime inputs for this batch should remain external and blind, just like
the first batch:

- repository snapshots
- normalized artifacts
- repository maps
- ground truth
- issue-evidence graph

## Guardrails

- Do not reuse the current official 20-case manifest as if it were a second
  batch.
- Do not mark this batch as validated until the assets exist and the benchmark
  has actually been executed.
- Do not add AI-vs-AI comparison results here yet; that belongs to a later
  benchmark phase.
