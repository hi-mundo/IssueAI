# IssueAI official evals

This directory contains the officialized historical-route benchmark assets for IssueAI.

The benchmark posture is:

- use real historical repository snapshots;
- do not inject the issue title/URL/expected route into the review runtime;
- score whether the expected mechanisms are still recovered by the hypothesis pipeline;
- keep the benchmark usable both from Python and from `promptfoo`.

## Current official dataset

- [unmapped-repositories-20.json](./unmapped-repositories-20.json)
- [datasets/catalog.json](./datasets/catalog.json)
- [datasets/README.md](./datasets/README.md)

This is the 20-case historical route benchmark used to validate the current IssueAI recall claim.

Dataset growth is now expected to happen by adding new independent historical
batches to the dataset catalog rather than replacing this first validated set.

The next reserved batch structure already exists in:

- [datasets/historical-route-20-v2/README.md](./datasets/historical-route-20-v2/README.md)

That batch is now serialized in benchmark shape, but its route labels are still
marked as proposed-from-artifacts rather than manually gold-validated.

## Observed results on July 27, 2026

Two benchmark views are important and should not be mixed:

- primary success metric: `top20_all`
- diagnostic fallback: `top100_all` only tells us whether a miss fell just outside top 20 or disappeared entirely
- progress telemetry: position distribution such as top-10

Observed results:

- validated batch `historical-route-20-v1`: **20/20** cases passed `top20_all`
- expanded run `historical-route-20-v1` + `historical-route-20-v2`: **40/40** cases passed `top20_all`
- expanded distribution: 39/40 cases had all expected mechanisms inside the top 10
- diagnostic envelope: both benchmark views still kept **40/40** cases inside `top100_all`

Important nuance:

- `historical-route-20-v2` is useful as an additive benchmark batch
- it is still labeled `proposed-from-artifacts`
- it should not be described as manually gold-validated until that review is finished

## Observed external baseline on July 28, 2026

We also ran the same 40-case set against a Codex-only strong prompt baseline.

Observed comparison:

- IssueAI: **40/40** cases passed `top20_all`
- Codex-only baseline: **24/40** cases passed `top20_all`
- Codex-only baseline top-10 view: **20/40**

Method summary for the baseline:

- `codex exec`
- read-only mode
- plugins disabled
- remote plugin disabled
- hooks disabled
- prompt constrained to the current working tree only
- no `git log`, `git show`, `git diff`, blame, or remote/network information

Important caveat:

- this is a product-level comparison, not a byte-identical replay of the
  internal IssueAI ranking harness
- the baseline produced up to 20 ranked hypotheses which were then scored by
  the first occurrence of each expected mechanism

## Runtimes

There are two benchmark entrypoints:

1. Python benchmark runner
   - [scripts/run_issueai_route_eval.py](./scripts/run_issueai_route_eval.py)
2. `promptfoo` case runner
   - [promptfoo/promptfooconfig.yaml](./promptfoo/promptfooconfig.yaml)

Both entrypoints now share the same historical-route evaluation logic through the
IssueAI core module instead of duplicating route scoring behavior in each CLI.

## Important current constraint

At this stage, the eval runtime still uses the vendored `bug_hunt_runtime` inside the `IssueAI` package.

That is intentional during migration:

- benchmark behavior stays 1:1 with the validated predecessor;
- the standalone `IssueAI` core can evolve without losing the benchmark harness.

## Required external inputs

The historical benchmark still expects these prepared assets:

- pinned repository snapshots
- normalized repository artifacts
- repository maps
- a structured issue-evidence graph
- a separate ground-truth file

Those are intentionally external so the benchmark remains blind from the runtime point of view.

## Current sequencing decision

Completed:

- compare IssueAI against a Codex-only strong-prompt baseline on the same
  40-case set

Next benchmark expansion steps:

- add more historical real-issue batches
- extend the strong-prompt baseline comparison to other hosts such as Claude,
  Cursor, or Copilot when their local runtime/auth setup is ready

## Promptfoo usage

Example:

```bash
npx promptfoo eval -c evals/promptfoo/promptfooconfig.yaml
```

Environment variables expected by the promptfoo harness:

- `ISSUEAI_GROUND_TRUTH`
- `ISSUEAI_REPOS_ROOT`
- `ISSUEAI_ARTIFACTS_ROOT`
- `ISSUEAI_GRAPH`
- optional: `ISSUEAI_OUTPUT_DIR`
