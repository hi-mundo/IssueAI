---
name: issue-hunt
description: Run the Issue Hunt workflow: consume Repository Recon and Repository Intent Review artifacts, search the mature non-obvious issue space, and produce a ranked shortlist for probing.
---

# Issue Hunt

Use this only after Repository Recon and Repository Intent Review are strong
enough.

Issue Hunt is the late-stage search layer for IssueAI. It should focus on
harder issues that survive the obvious review passes.

## What it does

1. confirm the deep-hunt gate
2. inherit Recon and Repository Intent Review artifacts
3. retrieve the most relevant issue families for this repository shape
4. generate and rank bounded issue hypotheses
5. hand the best shortlist to Issue Probe

## Guardrail

If the repository still has open Repository Intent Review findings, go back and
resolve or triage them first.
