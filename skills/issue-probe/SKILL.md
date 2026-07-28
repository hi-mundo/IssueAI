---
name: issue-probe
description: Run the Issue Probe workflow: take the latest findings or hypotheses, build deterministic checks, and separate supported issues from unresolved ones.
---

# Issue Probe

Use this after Issue Hunt, or on a bounded set of Repository Intent Review
findings when you want evidence.

Issue Probe is the evidence layer for IssueAI. Its job is to turn a shortlist
into deterministic checks and explicit verdicts.

## What it does

1. select the highest-value candidates
2. build deterministic probe steps
3. use static evidence first
4. preserve unresolved cases instead of pretending they are confirmed
5. emit verdicts and next actions
