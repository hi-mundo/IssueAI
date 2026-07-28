<p align="center">
  <img src="./assets/logo.png" alt="AIssuer logo" width="160" />
</p>

<h1 align="center">AIssuer</h1>

<p align="center">
  Finds an issue before production does.
</p>

<p align="center">
  <img alt="status" src="https://img.shields.io/badge/status-viable%20prototype-ff5a3d">
  <img alt="benchmark" src="https://img.shields.io/badge/validated%20benchmark-40%2F40%20top--20-success">
  <img alt="hosts" src="https://img.shields.io/badge/hosts-Codex%20%7C%20Claude%20%7C%20Cursor-4f46e5">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-111827">
</p>

AIssuer is a host-first plugin for Codex, Claude, and Cursor. It starts by mapping the repository, then checks intended behavior, then hunts the harder mature-repo bugs, and finally probes the shortlist with deterministic evidence.

## Workflow

```mermaid
flowchart TD
  A["Repository Recon"] --> B["Repository Intent Review"]
  B --> C["Issue Hunt"]
  C --> D["Issue Probe"]
  A --- E["snapshot, entrypoints, graph"]
  B --- F["intent vs implementation"]
  C --- G["late-discovered bugs"]
  D --- H["deterministic evidence"]
```

## Levels

| Level | Skill | Focus |
| --- | --- | --- |
| Understand | `Repository Recon` | snapshot, entrypoints, graph, repository map |
| Check intent | `Repository Intent Review` | intended behavior vs implementation |
| Hunt | `Issue Hunt` | mature bugs, drift, edge cases, hidden failure paths |
| Probe | `Issue Probe` | deterministic evidence for shortlisted issues |

## Install in your IDE

Paste one of these prompts into the host you want to use.

Codex:

```text
Add https://github.com/hi-mundo/AIssuer as a plugin source or marketplace for this workspace, install the AIssuer plugin, enable it here, and confirm the plugin is active. After installed show me the capabilities and examples of how to use.
```

Claude:

```text
Add https://github.com/hi-mundo/AIssuer as a plugin source or marketplace for this project, install the AIssuer plugin, enable it here, and confirm the plugin is active. After installed show me the capabilities and examples of how to use.
```

## What you get

- plugin inside Codex, Claude, or Cursor
- BYOK-compatible local execution for testing and automation
- CLI surfaces for evals, benchmarks, and manual runs

## Current signal

- validated historical benchmark: 40/40 cases inside the top 20
- details: [benchmarks/README.md](./benchmarks/README.md)
- method: [PAPER.md](./PAPER.md)
- implementation: [IMPLEMENTATION.md](./IMPLEMENTATION.md)
- usage modes: [USAGE.md](./USAGE.md)
- eval runtime: [evals/README.md](./evals/README.md)

## Why this exists

Most AI code review is still too shallow for late-discovered bugs in mature software. AIssuer is meant to make the agent ask better questions before it guesses:

- what is the product supposed to guarantee
- where does the implementation drift from intent
- which surfaces are historically brittle
- which hypotheses are worth probing first

## License

MIT
