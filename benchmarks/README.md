# Benchmarks

This directory stores benchmark notes and reproducible result summaries for AIssuer.

The current benchmark posture is intentionally simple:

- keep the benchmark claims close to the project;
- record the exact date of the observed result;
- distinguish validated measurements from roadmap goals.

Current validated benchmark artifact:

- [results-2026-07-27.md](./results-2026-07-27.md)

Current expanded benchmark artifact:

- [results-2026-07-27-expanded-40.md](./results-2026-07-27-expanded-40.md)

Current external baseline comparison artifact:

- [results-2026-07-28-codex-baseline-40.md](./results-2026-07-28-codex-baseline-40.md)

Current benchmark program sequencing:

- now: expand historical real-issue batches
- now: record Codex-only strong-prompt baseline comparisons on the same historical sets
- later: extend that baseline comparison to Claude, Cursor, and other host-only runs

This keeps the first benchmark phase focused on whether the method itself is
recovering real issues consistently while still allowing targeted product-level
comparisons against host-native prompting.
