<p align="center">
  <img src="./assets/logo.png" alt="IssueAI logo" width="160" />
</p>

<h1 align="center">IssueAI</h1>

<p align="center">
  Hypothesis-driven bug and issue discovery for real codebases.
</p>

<p align="center">
  <img alt="status" src="https://img.shields.io/badge/status-viable%20prototype-ff5a3d">
  <img alt="benchmark" src="https://img.shields.io/badge/historical%20benchmark-20%2F20%20top--100-success">
  <img alt="packaging" src="https://img.shields.io/badge/hosts-Codex%20%7C%20Claude%20%7C%20Cursor-4f46e5">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-111827">
</p>

<p align="center">
  <code>bugs</code>
  <code>reliability</code>
  <code>hypothesis-planning</code>
  <code>historical-issues</code>
  <code>benchmark-driven</code>
</p>

IssueAI is a bug-hunting engine built for the class of defects that usually
escape obvious checks:

- subtle bugs in mature repositories
- reliability failures that appear only under specific paths
- implementation-intent drift that increases bug probability over time
- issues that survive many releases before maintainers finally notice them

It is not a generic static analyzer and not a prompt that says “review this
repo.”

Its goal is to recover the real issue hypotheses that matter before the system
is told the answer.

## At a glance

- reconstructs repository and product intent before guessing
- retrieves structured historical issue patterns instead of relying only on LLM intuition
- generates bounded, contextual bug hypotheses
- preserves benchmarkable outputs for iteration and comparison
- is being packaged as a multi-host plugin-style product

## Why it exists

Large coding models are good at code, but they are not automatically good at
finding late-discovered, context-dependent bugs in mature software.

Common failure mode:

- too much code enters the context window
- product intent is not reconstructed first
- the model falls back to broad, generic guesses
- the exact real failure path gets missed

IssueAI exists to reduce that gap with a more structured workflow.

## What IssueAI does

IssueAI tries to answer:

- what this repository is supposed to do
- what important surfaces and contracts are supposed to guarantee
- which historical issue patterns are plausible here
- where the bug is most likely hiding
- which hypotheses should be tested first

The system combines:

- repository understanding
- product understanding
- implementation-intent reconstruction
- structured historical issue corpora
- issue playbooks
- graph-based contextual retrieval
- deterministic hypothesis planning

## Current validated signal

As of **July 27, 2026**, IssueAI has already crossed the “real enough to treat
as a product” line.

- benchmark set: 20 historical real issue cases from mature public repositories
- primary metric: expected real mechanisms present inside the top 100 ranked hypotheses
- measured result: **20/20 cases passed**

That does not mean the ranking is finished or that the marketplace packaging is
fully complete. It does mean the underlying method is already viable.

For the deeper method and benchmark framing, see [PAPER.md](./PAPER.md).

## Product shape

IssueAI is moving toward a host-first architecture:

- standalone Python core
- thin adapters for agent hosts
- plugin-style packaging for major coding agents

The current repository already carries parallel host manifests for:

- Codex: [/.codex-plugin/plugin.json](./.codex-plugin/plugin.json)
- Claude: [/.claude-plugin/plugin.json](./.claude-plugin/plugin.json)
- Cursor: [/.cursor-plugin/plugin.json](./.cursor-plugin/plugin.json)

Current branding asset:

- [assets/logo.png](./assets/logo.png)

Copilot-specific packaging is intentionally deferred until the bundle is more
stable.

## Documentation map

- [PAPER.md](./PAPER.md): method, thesis, benchmark framing, and technical rationale
- [TODO.md](./TODO.md): roadmap, open work, and packaging priorities
- [evals/README.md](./evals/README.md): benchmark runtime details
- [benchmarks/results-2026-07-27.md](./benchmarks/results-2026-07-27.md): current validated result note

## Benchmark and research

IssueAI benchmark expansion is intentionally staged.

Current phase:

- expand the historical real-issue benchmark in independent batches
- keep the benchmark blind and structurally comparable

Deferred phase:

- compare IssueAI against strong-prompt baseline runs from other agent hosts

For the benchmark rationale, research framing, and methodology, see:

- [PAPER.md](./PAPER.md)
- [evals/README.md](./evals/README.md)
- [evals/datasets/catalog.json](./evals/datasets/catalog.json)
- [benchmarks/results-2026-07-27.md](./benchmarks/results-2026-07-27.md)

## Local surfaces in this repository

- `issueai/`: Python package and core public interfaces
- `evals/`: official historical benchmark assets and runners
- `benchmarks/`: benchmark summaries and result notes
- `tests/`: lightweight validation for package, benchmark, and manifest layout

## Current usage posture

Today, the most honest description is:

- usable as an internal bug-hunting engine
- benchmarked against real historical cases
- partially packaged for multi-host plugin distribution
- not yet fully polished as a final marketplace product

## Host posture

IssueAI is meant to be consumed primarily through agent hosts such as:

- Codex
- Claude
- Cursor

Manual execution still matters for compatibility, testing, benchmarking, and
automation, but it is not the main product posture.

## License

MIT
