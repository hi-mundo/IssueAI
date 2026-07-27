# Completed Review Contract

This contract defines the canonical machine-readable documents for a completed
Bug Hunt review and the readable markdown report projection.

## Canonical Documents

A completed review bundle contains these files under `<review_dir>`:

- `review-manifest.json`: immutable completed-review receipt after finalization
- `findings.json`: semantic finding records for the completed review
- `coverage.json`: structured coverage summary with detailed receipt references

The readable `report.md` output is a deterministic projection of those three
canonical documents. The workflow must not treat a handwritten report as the
semantic source of truth.

## Coverage

`coverage.json` prevents the workflow from confusing “not found” with “not
reviewed”.

It records:

- review mode and inventory strategy
- included and excluded paths
- reviewed surfaces
- detailed receipt references
- explicit exclusions
- deferred work
- completeness

Every applicable coverage row must finish as one of:

- `reportable`
- `suppressed`
- `not_applicable`
- `deferred`

Rows exist even when they do not produce a finding.

## Candidate Identity

Every candidate finding must have a stable candidate id and a candidate ledger.
The candidate ledger must record:

- discovery receipt
- validation receipt
- probe or behavior receipt
- final disposition

Do not dedupe or finalize away a candidate before its ledger proves closure or
an explicit deferred reason.

## Finalization

Before completion, verify on disk that `review-manifest.json`, `findings.json`,
and `coverage.json` exist and satisfy their schemas.

Finalization is projection only:

- it validates canonical review artifacts
- it seals their lineage
- it writes `report.md`

It does not invent missing artifacts, rerun skipped phases, or treat the
report as input.
