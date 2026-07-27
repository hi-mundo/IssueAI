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

## What is this?

IssueAI is a bug-hunting engine for the class of defects that usually escape
obvious checks:

- subtle bugs in mature repositories
- reliability failures that appear only under specific paths
- implementation-intent drift that increases bug probability over time
- issues that survive many releases before maintainers finally notice them

It is not a generic static analyzer and not a plain “review this repo” prompt.

Its goal is to recover the real issue hypotheses that matter before the system
is told the answer.

## How to use

Current usage posture:

- primary: run through an agent host such as Codex, Claude, or Cursor
- secondary: run locally for compatibility, evals, and experimentation

Current local CLI surfaces:

```bash
python3 -m issueai.cli --repository example/repo --signal async --signal timeout
python3 -m issueai.cli historical-case --case-id <case-id> ...
```

## How to install

IssueAI is moving toward host-first packaging.

Current repository manifests:

- Codex: [/.codex-plugin/plugin.json](./.codex-plugin/plugin.json)
- Claude: [/.claude-plugin/plugin.json](./.claude-plugin/plugin.json)
- Cursor: [/.cursor-plugin/plugin.json](./.cursor-plugin/plugin.json)

This means the repository is already shaped for multi-host plugin packaging, but
the marketplace/distribution flow is still being polished.

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
- primary metric: all expected real mechanisms inside the top 100 ranked hypotheses
- validated result: **20/20 cases passed**

Expanded internal benchmark snapshot on the same date:

- combined benchmark set: **40/40** cases passed `top100_all`
- composition: 20 validated cases + 20 `proposed-from-artifacts` cases
- progress telemetry: 38/40 cases had all expected mechanisms inside the top 10, and 40/40 inside the top 20

That is a strong viability signal, not a claim that the product is already
finished.

## Documentation

- [HOW-TO-IMPLEMENT.md](./HOW-TO-IMPLEMENT.md): architecture, host posture, implementation direction, and packaging notes
- [PAPER.md](./PAPER.md): method, thesis, and benchmark framing
- [TODO.md](./TODO.md): roadmap and open work
- [evals/README.md](./evals/README.md): benchmark runtime details
- [benchmarks/README.md](./benchmarks/README.md): dated benchmark result summaries

## License

MIT
