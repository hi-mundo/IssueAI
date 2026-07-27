# Understanding and reconnaissance

Bug Hunt must know what it is reviewing before it asks whether code is wrong.
This phase adapts the Codex Security reconnaissance boundary: resolve target,
scope, inventory, surfaces, context and coverage before deep discovery.

## Required model

```text
product purpose
→ scope
→ capability
→ feature
→ implementation surface
→ technology/architecture context
→ contract and invariant
→ observation/probe
```

## Evidence order

Use accepted product decisions and public contracts first, then schemas and
types, user documentation and examples, stable sibling behavior and tests,
implementation and history, and finally reviewer inference. Keep conflicts and
unknowns visible.

## Implementation tendencies

Record repeated local patterns such as early returns, branching depth, typing,
error propagation, file ownership, naming, duplication, lifecycle handling,
fallbacks and observability. A tendency requires multiple evidence locations or
an explicit local convention. It is not automatically a defect.

## Handoff

The understanding artifact is the contextual boundary for the issue graph and
hypothesis worklist. Every hypothesis must point back to product/capability,
feature, technology or architecture context, and a local contract. A generic
technical category is insufficient.
