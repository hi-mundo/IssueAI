---
name: validate-issue-hypotheses
description: Validate selected Issue Hunt hypotheses with the smallest decisive evidence, separating observation, inference, and confirmed findings.
---

# Validate Issue Hypotheses

Use this when the user already has hypotheses and wants evidence-backed
validation.

## What it does

- inspects the strongest candidate branches
- gathers the smallest decisive evidence available
- distinguishes plausible concern from confirmed issue
- reports what was validated, disproven, or remains unresolved

## Guardrails

- do not silently upgrade a hypothesis into a finding
- do not use benchmark-only tooling as if it were a user-facing runtime
- keep failures visible and bounded
