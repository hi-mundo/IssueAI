# IssueAI vs Codex strong-prompt baseline — July 28, 2026

## Scope

- same 40 historical issue cases used by the expanded IssueAI benchmark
- same mechanism taxonomy:
  - `boundary`
  - `compatibility`
  - `concurrency`
  - `contract`
  - `integration`
  - `lifecycle`
  - `observability`
  - `precedence`
  - `representation`
  - `state_reuse`
- same success rule:
  - success means all expected mechanisms land inside the top 20
  - top 100 remains diagnostic only

## Compared systems

- IssueAI:
  - historical-route benchmark runner
  - repository artifacts and issue-evidence graph supplied through the normal benchmark harness
- Codex baseline:
  - `codex exec`
  - plugins disabled
  - remote plugin disabled
  - hooks disabled
  - user config ignored
  - rules ignored
  - read-only mode
  - prompt constrained to the current working tree only

## Baseline prompt posture

The Codex-only baseline was asked to:

- understand what the repository does
- identify the main execution flow and organization seams
- generate up to 20 ranked bug or reliability hypotheses
- tag each hypothesis with one mechanism from the benchmark taxonomy

It was explicitly forbidden from using:

- `git log`
- `git show`
- `git diff`
- blame
- network access
- remote information

Scoring for the baseline used the first ranked occurrence of each expected
mechanism in the returned hypothesis list.

## Result

- IssueAI:
  - **40/40** cases passed `top20_all`
  - **39/40** cases passed top 10
- Codex strong-prompt baseline:
  - **24/40** cases passed `top20_all`
  - **20/40** cases passed top 10

Batch breakdown:

- `historical-route-20-v1`
  - IssueAI: **20/20** top 20
  - Codex baseline: **15/20** top 20
- `historical-route-20-v2`
  - IssueAI: **20/20** top 20
  - Codex baseline: **9/20** top 20

## Misses from the Codex-only baseline

Official batch misses:

- `urllib3-2799`
- `werkzeug-3118`
- `rust-148328`
- `terraform-38466`
- `click-3065`

Expanded batch misses:

- `click-2832`
- `compose-13474`
- `cp-57281`
- `go-49075`
- `pluggy-219`
- `prometheus-15186`
- `pytest-6194`
- `redis-15389`
- `rust-76980`
- `sqlalchemy-13059`
- `urllib3-2999`

## Interpretation

This comparison is strong evidence that IssueAI is adding real retrieval value
over a good host-native prompt alone, especially on the harder second batch.

Important caveat:

- this is a product-level comparison, not a byte-for-byte identical harness
- IssueAI uses its native structured ranking path
- the Codex-only baseline uses ranked free-form hypotheses that are normalized
  back into the same mechanism taxonomy for scoring

Even with that caveat, the gap is wide enough to be meaningful:

- IssueAI kept all 40 cases inside the top 20
- the Codex-only baseline dropped 16 of 40 cases outside the top 20

## Current limitation of the comparison set

This workspace currently has a real Codex-only baseline result.

It does not yet have matching runs for:

- Claude CLI
- Cursor
- Copilot

Those remain future benchmark extensions rather than completed comparisons.
