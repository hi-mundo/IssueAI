# IssueAI

IssueAI is a hypothesis-driven issue and bug discovery system for real codebases.

It is designed to reduce false negatives in mature repositories where the real problem often survives many releases before somebody finally notices it.

The core idea is simple:

1. understand the repository and product before guessing;
2. use a structured corpus of historical issues and playbooks instead of relying only on generic LLM intuition;
3. generate many valid hypotheses, but do it intelligently;
4. keep the workflow deterministic enough that the same repository context produces comparable results;
5. optimize for catching the real issue even when the exact ranking is still imperfect.

The current implementation was born as a Codex plugin, but the architecture already points to a standalone core that can be imported by agent hosts such as Codex, Claude, Cursor, and similar environments.

## What IssueAI does

IssueAI tries to answer:

- what this repository is supposed to do;
- what each important surface, module, flow, and contract is supposed to guarantee;
- which historical failure patterns are most compatible with this repo;
- where the bug is most likely hiding;
- which hypotheses are worth testing first.

It is not a simple static analyzer and not a generic “review my code” prompt.

It combines:

- repository understanding;
- product understanding;
- implementation-intent reconstruction;
- structured issue corpora;
- issue playbooks;
- graph-based contextual retrieval;
- deterministic hypothesis planning.

## Why this exists

Large models are good at code, but they are not automatically good at finding subtle, late-discovered issues in mature software.

Common failure mode:

- the model sees too much code;
- it does not understand the product deeply enough;
- it falls back to broad, generic bug guesses;
- it misses the exact failure path that real maintainers only discovered much later.

IssueAI exists to close that gap.

## Core workflow

### 1. Understanding first

Before hypotheses, IssueAI reconstructs:

- what the product is;
- the repository scope and boundaries;
- important feature surfaces;
- architecture modules and integration points;
- repository conventions and implementation tendencies.

This is intentionally similar in spirit to the recon/threat-model phase in CodexSecurity:

- understand the system first;
- then reason about failure paths.

### 2. Repository normalization

Repository files are normalized into structured records so later stages work on stable inputs rather than ad hoc raw browsing.

This helps keep:

- deterministic planning;
- cacheability;
- repeatability across runs;
- bounded context windows.

### 3. Repository map and surface selection

IssueAI builds a bounded repository map and identifies high-value surfaces.

Examples:

- async runtime paths;
- session/state/resource ownership paths;
- public boundary and normalization paths;
- integration adapters;
- implementation-drift zones.

### 4. Historical issue corpus and playbooks

IssueAI uses a structured corpus of real historical issues.

Each issue contributes structured signals such as:

- mechanism;
- mechanism family;
- boundary type;
- surface;
- condition;
- playbook family;
- playbook signature.

This is closer to consultable reference material than to “hoping the model remembers similar bugs from training.”

### 5. Contextual graph query

IssueAI does not retrieve historical issues only by technology keywords.

It also uses:

- product terms;
- contract terms;
- surface terms;
- local code/path signals;
- implementation tendencies;
- playbook narrowing.

The goal is not just “find similar projects.”
The goal is “find the historical failure patterns that are plausible here.”

### 6. Intelligent discovery plan

From local evidence plus historical context, IssueAI creates a bounded hypothesis plan:

- inventory of relevant files;
- matched historical playbooks;
- open branches to investigate;
- coverage rows that must be closed later.

This means IssueAI is not just throwing a repo at an LLM and saying “good luck.”

### 7. Validation and closure

The intended end-state is:

- every important branch is either validated, disproven, or explicitly deferred;
- the workflow can rewind, resume after failure, and preserve discarded branches for auditability;
- the final report is deterministic enough to compare iterations.

## Current benchmark result

Latest measured result in this workspace on **July 27, 2026**:

- benchmark set: 20 historical real-issue cases from mature public repositories;
- evaluation target: whether all expected real mechanisms for each case appear inside the **top 100** ranked hypotheses;
- result: **20/20 cases passed**;
- stronger observation: in the measured run, the expected mechanisms also landed inside the **top 10** for all 20 cases.

This is the most important current proof point.

It means IssueAI is already strong at:

- recall;
- not losing the real issue;
- generating valid hypothesis sets for later testing.

## What “excellent” means here

The current result is excellent for **coverage of real issue hypotheses**.

More precisely:

- excellent recall;
- excellent top-100 coverage;
- very strong viability signal for real-world bug hunting;
- not yet perfect ranking purity.

In plain terms:

- it is already good at making sure the real issue is present;
- it still needs refinement to rank the best explanation earlier and more cleanly.

## What still needs improvement

Even with 20/20 top-100 success, the current system still over-elevates some noisy mechanism classes in several cases.

The main ranking noise still comes from:

- `representation`
- `contract`
- `precedence`
- `concurrency`

Typical pattern:

- the correct issue is present;
- but side-mechanisms rise too high because they are partially correlated with the same code region.

That means the next optimization phase is **ranking refinement without losing recall**.

### Immediate improvement targets

1. Preserve 20/20 top-100 recall.
2. Improve top-5 and top-3 ordering.
3. Distinguish better between:
   - lifecycle vs concurrency
   - boundary vs representation noise
   - state reuse vs generic state handling
4. Make contextual graph retrieval even less permissive when broad examples match only weakly.
5. Expand validation/probe stages so high-recall hypothesis sets can be cheaply tested and deduplicated.

## Real test philosophy

IssueAI is being evaluated against real issue histories, not toy-only examples.

The test philosophy is:

- use mature repositories;
- use real late-discovered issues;
- reconstruct structured patterns from those issues;
- verify whether IssueAI would have generated the real hypothesis before being told the answer.

This matters because many subtle defects:

- are not obvious syntax or type failures;
- are not caught by standard happy-path tests;
- survive in respected open-source projects for a long time.

## Relationship to the plugin

IssueAI started as a plugin-driven workflow because plugins are useful for:

- deterministic orchestration;
- resume/rewind control;
- workflow decomposition;
- structured artifact production inside LLM tooling.

But the project should not stay conceptually trapped inside the plugin form.

The long-term shape is:

- standalone Python core;
- BYOK model/provider support;
- canonical host adapters.

## Host-first, BYOK-second

IssueAI should primarily be consumed by an agent host:

- Codex
- Claude
- Cursor
- similar agent-capable developer environments

That means the first-class integration shape is:

- the host imports IssueAI as a plugin, package, or adapter;
- the host handles most user interaction and tool orchestration;
- IssueAI contributes structured understanding, retrieval, planning, and validation workflows.

Manual execution still matters, but mainly for:

- compatibility;
- testing;
- local benchmarking;
- harnesses;
- automation outside a host environment.

## BYOK direction

IssueAI should still support a standalone Python execution mode where users can bring their own model/provider path when needed.

Possible provider/runtime examples:

- Codex SDK
- Claude SDK
- direct API-key based providers when necessary
- other future providers through a narrow adapter contract

The important point is:

- the bug-hunting method is the product;
- the host/editor/plugin integration is an adapter layer;
- direct terminal execution is a compatibility mode, not the main product posture.

## Canonical adapters

IssueAI is a strong candidate for canonical adapters such as:

- `issueai-adapter-codex`
- `issueai-adapter-claude`

These adapters should be thin.

They should mainly provide:

- tool wiring;
- artifact locations;
- workflow callbacks;
- provider/model invocation;
- host-specific UX integration.

The core reasoning assets should remain shared:

- issue corpus;
- playbook corpus;
- contextual retrieval logic;
- repository understanding logic;
- planning/validation flow.

## Suggested project shape

```text
IssueAI/
  README.md
  issueai/
    core/
    hosts/
    providers/
    corpus/
    retrieval/
    planning/
    validation/
    adapters/
      codex/
      claude/
  tests/
  benchmarks/
```

## Non-goals

IssueAI should not become:

- a generic linter replacement;
- a purely prompt-based “review assistant”;
- a security scanner clone;
- an unbounded brute-force repo summarizer.

The value is in structured, contextual, issue-oriented reasoning.

## Current status

Current status as of **July 27, 2026**:

- strong proof that the method can recover real issue hypotheses from mature repos;
- enough evidence to justify a dedicated standalone project;
- ranking still needs refinement;
- probe/validation loops should become first-class;
- adapters should stay thin and the Python core should become canonical.

## Short version

IssueAI already crossed the “is this real?” line.

It should now be treated as:

- a real project direction;
- a standalone BYOK candidate;
- a Python core with Codex and Claude adapters;
- a bug and issue discovery engine whose next step is ranking polish, not basic viability.
