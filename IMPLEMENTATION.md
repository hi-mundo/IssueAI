# AIssuer implementation

## Product posture

AIssuer should be implemented as one product core with thin host adapters, not
as separate forked workflows per platform.

Current intended host posture:

- Codex
- Claude
- Cursor
- later: Copilot

Manual terminal usage exists for compatibility, testing, benchmarking, and
automation, but it is not the main product posture.

## What the implementation should preserve

AIssuer is not meant to be:

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
- four public deterministic workflows with explicit phase objectives
- cacheable prompt envelopes that split static instructions from dynamic payloads

Current high-level layout:

```text
AIssuer/
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

Installed skill UI metadata lives under each skill in:

```text
skills/<skill-name>/agents/openai.yaml
```

That keeps installed host cards and skill lists aligned with the intended
public names, while benchmark/eval surfaces stay outside the installed plugin
surface.

Runtime review state lives in the reviewed repository under:

```text
<target>/.issueai/
  snapshots/
  understanding/
  graphs/
  metadata/
  findings/
  run-state/
```

The public workflow contract is:

- `Repository Recon`
- `Repository Intent Review`
- `Issue Hunt`
- `Issue Probe`

Each workflow is Python-driven, step-by-step, and emits a deterministic
phase envelope with:

- static prompt text
- dynamic payload
- explicit objective
- expected outputs
- persistent artifacts

## What each area is for

### Plugin manifests

- `.codex-plugin/`
- `.claude-plugin/`
- `.cursor-plugin/`

These are the host-facing plugin entry points.

They should expose the same public product contract:

- AIssuer is the plugin/product name
- Repository Recon is the first-pass structural workflow
- Repository Intent Review is the semantic implementation-vs-intent workflow
- Issue Hunt is the later deep workflow
- Issue Probe is the evidence workflow
- eval and mutation tooling stays out of the default installed surface

### Core package

- `issueai/core/`

This should hold the reusable logic for:

- workflow definitions and cacheable prompt envelopes
- repository recon and graph synthesis
- repository intent review
- issue hunt planning
- issue probe planning
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
`AIssuer` and `Issue Hunt`, even while this runtime keeps some legacy internal
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

## What we should mirror from official Codex review plugins

The official Codex review/security plugins do not treat every request as a full
repository scan.

Repository Recon, Repository Intent Review, and Issue Hunt should follow the same routing principle:

- use diff/worktree review for pending changes
- use commit or branch-diff review for Git-backed change sets
- use scoped review for one feature or path
- use whole-repository review only when explicitly requested or when no narrower mode answers the question
- reserve deep multi-pass review for explicit exhaustive requests

Repository Recon should create and refresh the baseline. Repository Intent Review
should consume that baseline. Issue Hunt should consume both.

The preflight should always:

- create a snapshot before the first broad analysis
- compare against the previous analysis when one exists
- focus later runs on changed surfaces and their neighbors instead of restarting from zero every time

## What we can reuse from the old I2B plugin

AIssuer is an evolution of the old structured-vibecoding I2B posture. The best
parts to keep are not the old branding, but the discipline:

- intent-first review instead of code-first guessing
- deterministic preflight before analysis
- explicit report contracts
- defect taxonomy and behavior modeling references
- strong separation between observation, hypothesis, and validated finding

Concretely, the I2B lineage is still valuable for Repository Intent Review:

- intended-behavior modeling
- guardrail-style preflight
- report validation
- evidence discipline

That is why the new plugin exposes Repository Recon first, Repository Intent
Review second, Issue Hunt third, and Issue Probe fourth, while
benchmark/mutation helpers stay outside the default installed surface.

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
