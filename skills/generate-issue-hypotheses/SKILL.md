---
name: generate-issue-hypotheses
description: Generate falsifiable issue, bug, reliability, and implementation-intent hypotheses from repository context after intended behavior and important surfaces are understood.
---

# Generate Issue Hypotheses

Use this when the user explicitly wants hypothesis generation without the full
end-to-end review report.

## Output

Produce a bounded set of strong hypotheses, each tied to:

- a likely mechanism
- relevant files or surfaces
- expected intended behavior
- why the branch is plausible
- what evidence would validate or reject it next

## Guardrails

- do not present benchmark or mutation-only hypotheses as user-facing defaults
- do not treat a hypothesis as a confirmed issue
- require understanding and surface selection first
