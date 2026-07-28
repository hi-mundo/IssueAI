# AIssuer TODO

## Product packaging

- finalize marketplace-grade packaging for Codex
- finalize marketplace-grade packaging for Claude
- finalize marketplace-grade packaging for Cursor
- add Copilot-specific packaging once the host-facing bundle is stable
- add screenshots and richer plugin card assets
- polish installation instructions for each host

## Core method

- improve ranking purity without reducing recall
- make contextual graph retrieval less permissive on weak broad matches
- distinguish better between:
  - lifecycle vs concurrency
  - boundary vs representation noise
  - state reuse vs generic state handling
- expand validation/probe stages for cheaper hypothesis testing

## Benchmark program

- populate `historical-route-20-v2`
- add more independent historical batches after v2
- preserve blind runtime inputs and external ground truth
- add cross-host strong-prompt comparisons later, not now

## Documentation

- add per-host installation guides
- add a more explicit architecture diagram
- document how AIssuer is expected to run inside host agents vs manual mode
- document benchmark asset preparation workflow for future batches

## Engineering

- keep one canonical core and thin host adapters
- continue reducing duplicated benchmark/orchestration glue
- add lightweight validation for any new marketplace/distribution surface
