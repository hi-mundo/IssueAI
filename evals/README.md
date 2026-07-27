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

The next benchmark expansion step is:

- add more historical real-issue batches

The following step is intentionally deferred:

- compare IssueAI against strong-prompt baseline runs from other agent hosts
  such as Codex, Claude, Cursor, or Copilot

That comparison matters, but it should happen only after IssueAI is better
optimized as a usable/installable marketplace tool.

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
