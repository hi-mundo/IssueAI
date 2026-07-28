---
name: repository-intent-review
description: Run the Repository Intent Review workflow: consume the Repository Recon snapshot, infer what the repository is supposed to guarantee, and compare that intent against the current implementation.
---

# Repository Intent Review

Use this after Repository Recon.

Repository Intent Review is the semantic review layer for IssueAI. Its job is
to compare expected repository guarantees against implementation evidence before
deep issue hunting begins.

## What it does

1. load the Repository Recon snapshot and graph
2. pick the most important seams to review
3. infer expected repository guarantees
4. inspect likely break paths such as middleware gaps, schema gaps, implicit typing, async misuse, and weak contracts
5. record findings that are obvious enough to act on before Issue Hunt

## References

- Fragility patterns: see [references/fragility-patterns.md](references/fragility-patterns.md)
- Inferred contracts: see [references/inferred-contracts.md](references/inferred-contracts.md)

## Output

Repository Intent Review should update `.issueai/` with:

- semantic understanding
- intent findings
- issue-hunt gate state
- workflow run-state

If Repository Intent Review still has open findings, do not jump straight into
Issue Hunt.
