---
name: model-intended-behavior
description: Reconstruct what a feature or repository surface is supposed to do before judging whether the implementation is correct.
---

# Model Intended Behavior

This is the clearest reusable skill inherited from the old I2B posture.

Use it when the user wants to understand:

- what the feature is supposed to do
- what invariants or contracts should hold
- where product intent and implementation intent might diverge

## Why this exists

IssueAI should not start by guessing random bugs from code alone.

It should first model:

- actor
- trigger
- inputs
- preconditions
- state transition
- output
- side effects
- forbidden outcomes

That intent model becomes the basis for later hypothesis generation and
validation.
