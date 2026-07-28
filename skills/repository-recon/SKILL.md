---
name: repository-recon
description: Run the Repository Recon workflow: create the repository snapshot, identify entrypoints and project roles, trace likely data flow, and build the repository graph before any semantic review.
---

# Repository Recon

Use this first.

Repository Recon is the structural entrypoint for IssueAI. Its job is to map
the repository before any intent review or deep issue hunting begins.

## What it does

1. create or refresh `.issueai/`
2. classify the repository shape and likely entrypoints
3. map roles such as routes, middlewares, controllers, services, schemas, orm, integrations, and utils
4. trace likely flow through imports and role transitions
5. build the repository map and graph
6. surface structural redundancies, drift, and outliers

## References

- Navigation heuristics: see [references/navigation-strategies.md](references/navigation-strategies.md)
- Graph heuristics: see [references/repository-map-heuristics.md](references/repository-map-heuristics.md)

## Output

Repository Recon should update `.issueai/` with:

- snapshots
- understanding
- graphs
- metadata
- structural findings
- workflow run-state

Do not skip straight to semantic review without a Recon snapshot.
