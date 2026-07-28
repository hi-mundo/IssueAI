<p align="center">
  <span style="display:inline-block; padding:16px; background:#ffffff; border-radius:20px;">
    <img src="./assets/logo.png" alt="IssueAI logo" width="160" />
  </span>
</p>

<h1 align="center">IssueAI</h1>

<p align="center">
  Hypothesis-driven bug and issue discovery for real codebases.
</p>

<p align="center">
  <img alt="status" src="https://img.shields.io/badge/status-viable%20prototype-ff5a3d">
  <img alt="benchmark" src="https://img.shields.io/badge/validated%20benchmark-20%2F20%20top--100-success">
  <img alt="hosts" src="https://img.shields.io/badge/hosts-Codex%20%7C%20Claude%20%7C%20Cursor-4f46e5">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-111827">
</p>

<p align="center">
  <code>bugs</code>
  <code>reliability</code>
  <code>historical-issues</code>
  <code>benchmark-driven</code>
</p>

IssueAI helps AI coding agents find real bugs that usually survive normal code
review, generic static analysis, and shallow “review this repo” prompts.

## Default installed capabilities

The installed plugin surface is intentionally small:

- `Repository Recon`: snapshot, structural map, role map, flow trace, and graph
- `Repository Intent Review`: implementation-vs-intent review using the Recon artifacts
- `Issue Hunt`: deeper late-stage hunt once the obvious findings are handled
- `Issue Probe`: deterministic evidence checks for shortlisted issues

Benchmark, replay, mutation, and dataset tooling stay outside the default
installed surface.

## What is this?

IssueAI is a plugin for AI coding agents that uses Repository Recon first,
Repository Intent Review second, Issue Hunt third, and Issue Probe last to help
them find real bugs in a repository instead of stopping at superficial code
review comments.

It is built for the class of defects that usually escape obvious checks:

- subtle bugs in mature repositories
- reliability failures that appear only under specific paths
- implementation-intent drift that increases bug probability over time
- issues that survive many releases before maintainers finally notice them

In plain terms: IssueAI tries to make Codex or Claude review code more like an
investigator and less like a linter.

It first maps the repository structurally, then reviews what the repository is
supposed to guarantee, then hunts the harder mature-system issues that remain,
and finally probes the shortlisted candidates with deterministic checks.

It is not a generic static analyzer and not a plain “review this repo” prompt.

## Why would someone use this?

Because normal AI code review often misses the bugs that matter most:

- bugs hidden behind valid-looking code
- failures that only appear in edge paths or weird state combinations
- logic that is locally reasonable but globally wrong for the product
- implementation drift that makes a codebase fragile even before an obvious bug appears

IssueAI is for people who want the agent to ask:

- “what is this supposed to do?”
- “what would break in a real product path?”
- “where is the implementation weaker than the intent?”
- “which bug patterns are historically common for this kind of repository?”

## What does it actually output?

IssueAI does not try to pretend it already proved the bug.

Its job is to produce strong, contextual bug hypotheses such as:

- likely failure points
- suspicious contracts and state transitions
- implementation-intent mismatches
- reliability risks worth validating next

So the value is not just “review text”. The value is a better search space for
real bug discovery.

## Quick install

Use the host's plugin or marketplace flow first. These prompts are meant to be
pasted directly into the agent so it can perform the correct install steps and
confirm activation.

Codex:

```text
Add https://github.com/hi-mundo/IssueAI as a plugin source or marketplace for this workspace, install the IssueAI plugin, enable it here, and confirm the plugin is active. After installed show me the capabilities and examples of how to use.
```

Claude:

```text
Add https://github.com/hi-mundo/IssueAI as a plugin source or marketplace for this project, install the IssueAI plugin, enable it here, and confirm the plugin is active. After installed show me the capabilities and examples of how to use.
```

## Compatibility

IssueAI is designed as a host-first plugin for AI coding agents, especially:

- Codex
- Claude

The intended order is:

1. easiest path: install it into your coding agent
2. fallback path: run it locally with your own keys or local runtime
3. benchmark path: use the CLI surfaces for historical-case and eval workflows

For exact usage modes and examples, see [USAGE.md](./USAGE.md).

## Other ways to use it

IssueAI can also be used outside plugin installation when needed:

- BYOK usage for local experimentation and testing
- CLI usage for evals, benchmarks, and manual runs

That makes the product usable in three layers:

1. plugin inside Codex or Claude
2. BYOK-compatible local execution
3. CLI-driven benchmark and eval workflows

## What problem does it solve?

Large coding models are good at code, but they are not automatically good at
finding late-discovered, context-dependent bugs in mature software.

IssueAI tries to reduce that gap by:

- reconstructing repository and product intent before guessing
- retrieving structured historical issue patterns
- generating bounded contextual bug hypotheses
- preserving benchmarkable outputs for iteration

## Current validated signal

As of **July 27, 2026**:

- official validated benchmark set: 20 real issue cases from mature public repositories
- primary metric: all expected real mechanisms inside the top 20 ranked hypotheses
- validated result: **20/20 cases passed**

Expanded internal benchmark snapshot on the same date:

- combined benchmark set: **40/40** cases passed `top20_all`
- composition: 20 validated cases + 20 `proposed-from-artifacts` cases
- progress telemetry: 39/40 cases had all expected mechanisms inside the top 10
- diagnostic envelope: 40/40 cases still landed inside the top 100

External comparison snapshot on **Tuesday, July 28, 2026**:

- same 40-case set, compared against a Codex-only strong prompt with no plugin
- IssueAI: **40/40** cases inside the top 20
- Codex-only baseline: **24/40** cases inside the top 20
- that gap is strongest on the harder second 20-case batch

That is a strong viability signal, not a claim that the product is already
finished.

## Repository map

- [README.md](./README.md): product overview and quick install
- [USAGE.md](./USAGE.md): Codex, Claude, BYOK, and CLI usage modes
- [IMPLEMENTATION.md](./IMPLEMENTATION.md): plugin pattern, architecture, runtime, and repo structure
- [PAPER.md](./PAPER.md): method and benchmark framing
- [TODO.md](./TODO.md): roadmap and open work
- [evals/README.md](./evals/README.md): benchmark runtime details
- [benchmarks/README.md](./benchmarks/README.md): dated benchmark result summaries

## Installed vs internal surfaces

Installed by default:

- Repository Recon
- Repository Intent Review
- Issue Hunt
- Issue Probe

Internal or eval-only:

- historical replay and benchmark runners
- dataset derivation and route evaluation
- mutation and public-repo test harnesses

Those internal surfaces stay in `evals/` and are not part of the default plugin
skill list.

## License

MIT
