# Issue Playbooks

The base model was not trained to reliably find late-discovered bugs by
default. The issue corpus exists to reinforce those missing habits with
structured external memory.

For Bug Hunt, the atomic unit of reusable knowledge is not a label such as
`boundary` or `contract`. It is an `issue_playbook`: one explicit description
of how a real issue could have been found before it was reported.

## Why playbooks exist

A mature-project issue often escapes because the failing behavior is not local.
It usually lives in a relation:

- product expectation versus implementation guarantee
- validated object versus consumed object
- common path versus rare transition
- default implementation versus alternate cell
- abstract helper versus concrete instance

Labels help organize the corpus, but they do not tell the reviewer where to
look, what to compare, or how to falsify the hidden assumption. Playbooks do.

## One issue, one playbook

Every structured issue record should include one `issue_playbook` that answers:

- what the product or API expected invariant was
- what concrete transition or condition violated it
- what false sense of safety hid the defect
- where a reviewer should look first
- what comparison would reveal the problem
- what probe shape would close the route

Repeated playbooks are expected. That repetition is the useful signal. Later,
the corpus can collapse many issue-specific playbooks into smaller reusable
playbook families without losing the original issue-level evidence.

## Required playbook fields

Every playbook must preserve:

- `surface`
- `trigger`
- `expected_invariant`
- `broken_transition`
- `broken_control`
- `concrete_instance`
- `false_sense_of_safety`
- `where_to_look`
- `how_to_compare`
- `probe_shape`
- `playbook_family`
- `playbook_signature`

`playbook_signature` is the issue-level normalized route. It should stay stable
when the same detection logic appears in multiple repositories.

## Relationship to families

Keep the compact defect families such as `contract`, `boundary`,
`state-lifecycle`, `integration`, `compatibility`, `concurrency`,
`observability`, and `intent-drift` for balancing and coverage accounting.

Do not confuse those families with playbooks:

- family = operational bucket for bounded review
- playbook = issue-specific detection procedure

Bug Hunt improves when it retrieves the right playbooks for the current repo
context, then uses families only to bound and audit the worklist.
