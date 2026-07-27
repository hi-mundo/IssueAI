# IssueAI Paper

## Abstract

IssueAI is a hypothesis-driven issue and bug discovery system for real
codebases. It is designed to reduce false negatives in mature repositories
where the real problem often survives many releases before somebody finally
notices it.

The core claim is that subtle bug discovery improves when the system:

1. understands the repository and product before guessing
2. uses structured historical issue corpora and playbooks
3. narrows retrieval through contextual graphs instead of generic similarity
4. generates many valid hypotheses, but does so in a bounded workflow
5. preserves deterministic enough artifacts to support benchmarked iteration

## Problem statement

Large coding models are good at code generation and local reasoning, but they
are not automatically good at recovering late-discovered bugs in mature
software.

Typical failure pattern:

- the model sees too much code
- product intent remains underspecified
- implementation conventions are not modeled
- historical failure modes are not retrieved explicitly
- the model falls back to broad, generic bug guesses
- the exact real issue path gets missed

IssueAI is designed to close that gap.

## System overview

IssueAI combines:

- repository understanding
- product understanding
- implementation-intent reconstruction
- structured issue corpora
- issue playbooks
- contextual graph retrieval
- deterministic hypothesis planning

It is not intended to be a generic linter replacement or an unbounded “review
my repo” prompt.

## Method

### 1. Understanding first

Before hypothesis generation, IssueAI reconstructs:

- what the product is
- repository scope and boundaries
- important feature surfaces
- architecture modules and integration points
- repository conventions and implementation tendencies

This is intentionally similar in spirit to the recon-first posture used by
security workflows such as CodexSecurity.

### 2. Repository normalization

Repository files are normalized into stable records so later phases operate on
bounded inputs rather than ad hoc browsing.

Benefits:

- deterministic planning
- cacheability
- repeatability across runs
- bounded context windows

### 3. Repository map and surface selection

IssueAI builds a bounded repository map and identifies high-value surfaces such
as:

- async runtime paths
- session/state/resource ownership paths
- public boundaries and normalization paths
- integration adapters
- implementation-drift zones

### 4. Historical issue corpus and playbooks

IssueAI uses a structured corpus of real historical issues.

Each issue contributes structured signals such as:

- mechanism
- mechanism family
- boundary type
- surface
- condition
- playbook family
- playbook signature

This is meant to function as consultable reference material rather than as
implicit training-memory hope.

### 5. Contextual graph query

IssueAI does not retrieve issue references only through technology keywords.

It also uses:

- product terms
- contract terms
- surface terms
- local code/path signals
- implementation tendencies
- playbook narrowing

The target is not “find similar projects.” The target is “find the historical
failure patterns that are plausible here.”

### 6. Intelligent discovery plan

From local evidence plus historical context, IssueAI creates a bounded
hypothesis plan:

- inventory of relevant files
- matched historical playbooks
- open branches to investigate
- coverage rows that must eventually close

This avoids the unstructured mode of simply throwing a repository at an LLM and
asking it to figure things out.

### 7. Validation and closure

The intended end state is:

- important branches are validated, disproven, or explicitly deferred
- the workflow can rewind and resume after failure
- discarded branches remain inspectable
- outputs are deterministic enough to compare iterations

## Benchmark framing

IssueAI is currently benchmarked against real issue histories, not toy-only
examples.

Current validated result in this workspace on **July 27, 2026**:

- benchmark set: 20 historical real-issue cases from mature public repositories
- evaluation target: whether all expected real mechanisms for each case appear
  inside the top 100 ranked hypotheses
- result: **20/20 cases passed**
- stronger observation: in the measured run, the expected mechanisms also
  landed inside the top 10 for all 20 cases

This supports a strong recall claim, not a claim of perfect ranking purity.

## Interpretation of current result

The current result is excellent for recovery coverage of real issue hypotheses.

More precisely:

- excellent recall
- excellent top-100 coverage
- strong evidence that the real issue is not being dropped
- ranking quality still needs refinement

The main current ranking noise still tends to involve:

- `representation`
- `contract`
- `precedence`
- `concurrency`

Typical pattern:

- the correct issue is present
- side-mechanisms correlated with the same code region sometimes rank too high

## Benchmark philosophy

The benchmark intentionally uses:

- mature repositories
- real late-discovered issues
- structured pattern reconstruction outside the runtime
- blind runtime inputs

This matters because many subtle defects:

- are not obvious syntax or type failures
- are not caught by standard happy-path tests
- survive for a long time in respected open-source projects

## Packaging and product direction

IssueAI began as a plugin-driven workflow, but it should not stay conceptually
trapped inside a single host.

The long-term shape is:

- standalone Python core
- BYOK-compatible runtime paths
- thin host adapters
- marketplace-ready manifests for major agent environments

The repository already carries parallel manifest roots for Codex, Claude, and
Cursor. Copilot-specific packaging is deferred until the host-facing bundle is
more stable.

## Benchmark sequencing

The benchmark roadmap is intentionally staged.

Current phase:

- add more independent historical batches
- preserve blind evaluation and structural comparability

Later phase:

- compare IssueAI against strong-prompt baseline runs from other agent hosts

That comparison matters, but it is intentionally deferred until the product is
more optimized as a usable/installable marketplace tool.

## Conclusion

IssueAI already looks like a real project direction rather than a prompt
experiment.

The next step is not basic viability proof. The next step is product and method
refinement:

- improve ranking without losing recall
- expand the historical benchmark
- strengthen validation/probe loops
- finish professional multi-host packaging
