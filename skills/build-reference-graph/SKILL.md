---
name: build-reference-graph
description: Normalize repository and reference evidence into a bounded graph so Issue Hunt can retrieve the most relevant issue patterns and surfaces before hypothesis generation.
---

# Build Reference Graph

Use this when the user explicitly wants the repository and reference graph phase
or when Issue Hunt needs that graph as part of the main review path.

## What it includes

- repository normalization
- repository map
- selected reference ingestion
- bounded graph construction
- graph-backed retrieval for later issue hypotheses

## What it is not

- not a user-facing benchmark dataset builder
- not a mutation or replay harness
- not a final review by itself
