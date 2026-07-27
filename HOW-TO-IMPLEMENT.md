# How to implement IssueAI

## Product posture

IssueAI should be implemented as one product core with thin host adapters, not
as separate forked workflows per platform.

Current intended host posture:

- Codex
- Claude
- Cursor
- later: Copilot

Manual terminal usage exists for compatibility, testing, benchmarking, and
automation, but it is not the main product posture.

## What the implementation should preserve

IssueAI is not meant to be:

- a generic linter replacement
- an unbounded brute-force repo summarizer
- a prompt-only review assistant

The implementation should preserve these defining traits:

- repository understanding first
- product understanding first
- historical issue corpus and playbooks
- contextual graph retrieval
- bounded hypothesis planning
- benchmarkable outputs

## Core implementation shape

Current direction:

- standalone Python core
- thin adapters for host environments
- plugin-style manifests for host packaging
- benchmark and eval surfaces inside the repository

Current high-level layout:

```text
IssueAI/
  issueai/
    core/
    hosts/
    providers/
    adapters/
  evals/
  benchmarks/
  tests/
```

## What the core should do

The core should stay responsible for:

- repository understanding
- retrieval and pattern narrowing
- planning
- benchmark-facing orchestration

Host-specific layers should stay thin and mainly handle:

- tool wiring
- artifact locations
- provider/model invocation
- host-specific UX and installation expectations

## Multi-host packaging direction

The repository already carries parallel manifests for:

- [/.codex-plugin/plugin.json](./.codex-plugin/plugin.json)
- [/.claude-plugin/plugin.json](./.claude-plugin/plugin.json)
- [/.cursor-plugin/plugin.json](./.cursor-plugin/plugin.json)

That follows the pattern used by public multi-host agent tool projects:

- one core
- mirrored host manifests
- thin distribution-specific wrappers

## Benchmark posture

IssueAI benchmark expansion is intentionally staged.

Current phase:

- grow the historical real-issue benchmark in independent batches
- keep evaluation blind and structurally comparable

Deferred phase:

- compare IssueAI against strong-prompt baseline runs from other agent hosts

That comparison matters, but only after the tool is more optimized as a usable
and installable marketplace product.

## What to optimize next

### Product packaging

- finalize marketplace-grade packaging for Codex
- finalize marketplace-grade packaging for Claude
- finalize marketplace-grade packaging for Cursor
- add Copilot-specific packaging later
- add screenshots and richer plugin card assets

### Core method

- improve ranking purity without reducing recall
- reduce broad weak matches in contextual retrieval
- strengthen validation and probe stages

### Benchmark program

- populate `historical-route-20-v2`
- add more independent batches after v2
- preserve external ground truth and blind runtime inputs

## Supporting docs

- [README.md](./README.md): top-level product page
- [PAPER.md](./PAPER.md): method and benchmark framing
- [TODO.md](./TODO.md): roadmap
