# IssueAI implementation

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
  .codex-plugin/
  .claude-plugin/
  .cursor-plugin/
  issueai/
    core/
    adapters/
    hosts/
    providers/
    bug_hunt_runtime/
  evals/
  benchmarks/
  tests/
```

## What each area is for

### Plugin manifests

- `.codex-plugin/`
- `.claude-plugin/`
- `.cursor-plugin/`

These are the host-facing plugin entry points.

### Core package

- `issueai/core/`

This should hold the reusable logic for:

- repository understanding
- retrieval and pattern narrowing
- planning
- benchmark-facing orchestration

### Host and adapter layers

- `issueai/adapters/`
- `issueai/hosts/`
- `issueai/providers/`

These should stay thin and mainly handle:

- host-specific wiring
- artifact locations
- provider/model invocation
- host-specific UX expectations

### Vendored runtime

- `issueai/bug_hunt_runtime/`

This is the current deterministic workflow/runtime layer that preserves the
validated bug-hunt method and benchmark harness.

It is intentionally still internal. The public product surface should say
`IssueAI` and `Issue Hunt`, even while this runtime keeps some legacy internal
names during migration.

### Benchmark surfaces

- `evals/`
- `benchmarks/`

These store:

- benchmark datasets
- benchmark runners
- promptfoo integration
- result summaries

## Multi-host pattern

The repository follows a public multi-host plugin pattern:

- one core product
- mirrored manifests per host
- thin host-specific wrappers
- documentation separated by presentation, usage, and implementation

## What we can reuse from the old I2B plugin

IssueAI is an evolution of the old structured-vibecoding I2B posture. The best
parts to keep are not the old branding, but the discipline:

- intent-first review instead of code-first guessing
- deterministic preflight before analysis
- explicit report contracts
- defect taxonomy and behavior modeling references
- strong separation between observation, hypothesis, and validated finding

Concretely, the I2B lineage is still valuable for:

- intended-behavior modeling
- guardrail-style preflight
- report validation
- evidence discipline

That is why the new plugin exposes user-facing skills such as intended behavior
modeling and validation, while benchmark/mutation helpers stay outside the
default installed surface.

## What to optimize next

### Product packaging

- finalize marketplace-grade packaging for Codex
- finalize marketplace-grade packaging for Claude
- finalize marketplace-grade packaging for Cursor
- add Copilot-specific packaging later
- add richer plugin card assets and screenshots

### Core method

- improve ranking purity without reducing recall
- reduce broad weak matches in contextual retrieval
- strengthen validation and probe stages

### Benchmark program

- expand historical batches
- preserve blind evaluation and external ground truth
- defer strong-prompt cross-host comparisons until the tool is more mature

## Related docs

- [README.md](./README.md): product overview
- [USAGE.md](./USAGE.md): installation and usage modes
- [PAPER.md](./PAPER.md): method and benchmark framing
- [TODO.md](./TODO.md): roadmap
