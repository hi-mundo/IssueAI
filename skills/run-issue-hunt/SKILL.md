---
name: run-issue-hunt
description: Run the main Issue Hunt workflow on a repository or scoped feature by reconstructing intended behavior, generating contextual issue hypotheses, validating the strongest branches, and reporting evidence-backed findings without applying fixes.
---

# Run Issue Hunt

Use this as the main end-user workflow.

Issue Hunt is the install-by-default review surface for IssueAI. It should feel
like one coherent review action, not like a benchmark harness or an internal
pipeline phase list.

## What it does

1. preflight the repository and scope
2. reconstruct product and implementation intent
3. normalize and map the relevant repository surfaces
4. build and query the reference graph
5. generate contextual issue hypotheses
6. validate the strongest branches with evidence
7. report weighted findings without applying fixes

## What it is for

Use this when the user wants to:

- run Issue Hunt on a repository
- review a feature against intended behavior
- find likely real issues, hidden bugs, or reliability problems
- inspect implementation-intent drift that may increase bug probability

## What it is not

- not a benchmark runner
- not a mutation harness
- not a corpus-building workflow
- not a generic linter replacement

If the user is clearly asking for benchmark, mutation, historical replay, or
dataset work, route that to the eval surfaces in `evals/` instead of presenting
them as normal plugin capabilities.
