# IssueAI official evals

This directory contains the officialized historical-route benchmark assets for IssueAI.

The benchmark posture is:

- use real historical repository snapshots;
- do not inject the issue title/URL/expected route into the review runtime;
- score whether the expected mechanisms are still recovered by the hypothesis pipeline;
- keep the benchmark usable both from Python and from `promptfoo`.

## Current official dataset

- [unmapped-repositories-20.json](./unmapped-repositories-20.json)

This is the 20-case historical route benchmark used to validate the current IssueAI recall claim.

## Runtimes

There are two benchmark entrypoints:

1. Python benchmark runner
   - [scripts/run_issueai_route_eval.py](./scripts/run_issueai_route_eval.py)
2. `promptfoo` case runner
   - [promptfoo/promptfooconfig.yaml](./promptfoo/promptfooconfig.yaml)

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
