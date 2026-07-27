# Bug and reliability defect taxonomy

Bug Hunt uses eight category-mãe for corpus balance, search routing, and
hypothesis diversity. The point is not to reduce every bug to a slogan; the
point is to keep the search budget balanced while preserving more precise
subtypes underneath each family.

## The eight category-mãe

1. `contract`
   - public API contract, schema, type/shape, serialization, return semantics,
     sentinel values, optional/null/undefined handling, and forbidden internal
     value leakage;
2. `boundary`
   - exact limits, empty/zero/null edges, off-by-one, truncation, rounding,
     path and ownership crossings, and invalid-input handling;
3. `state-lifecycle`
   - setup/use/close ordering, teardown, cancellation, retry, restart, cache
     coherence, partial update, rollback, stale state, and recovery behavior;
4. `integration`
   - adapters, plugins, drivers, framework bridges, optional dependencies,
     subprocess or protocol seams, and default-versus-alternate implementation
     assumptions;
5. `compatibility`
   - platform, runtime, dependency, language-version, execution-mode, and
     cross-environment matrix failures;
6. `concurrency`
   - races, lost wakeups, duplicate work, lock ordering, callback scheduling,
     shared-state coordination, and nondeterministic interleavings;
7. `observability`
   - wrong or missing error/reporting behavior, event emission mismatches,
     logging, metrics, traces, diagnostics, alertability, and “plausible
     success” where the system appears fine while hiding a defect;
8. `intent-drift`
   - product-purpose mismatch, implementation-intent drift, duplicated or
     inconsistent rules, wrong ownership or folder placement, structural mess,
     naming drift, branching style drift, and maintainability patterns that
     raise future break probability.

## Subtypes stay explicit

The eight families are the balancing layer, not the end of reasoning. Keep
subtypes such as:

- `representation`
- `precedence`
- `resource`
- `type_schema`
- `purpose_mismatch`
- `organizational_drift`

These are preserved as explanation detail, search cues, or future graph edges.
They do not need to become separate top-level balancing families when they fit
cleanly under one of the eight category-mãe.

## Mapping guidance

- `representation` usually rolls up into `contract` unless the dominant risk is
  cross-system data exchange, in which case it may also inform `integration`.
- `precedence` usually rolls up into `boundary` or `state-lifecycle`,
  depending on whether the failure is value-selection or transition-ordering.
- `resource` usually rolls up into `state-lifecycle`, unless the primary escape
  cell is concurrent ownership, then it informs `concurrency`.
- `type_schema` rolls up into `contract`.
- product-purpose mismatch and structural mess roll up into `intent-drift`.

## Important rule

Category membership is routing evidence, not proof. Every finding still needs:

- a concrete symbol/file boundary;
- a trigger conjunction;
- an invariant or oracle;
- the suspected deviation;
- validation evidence or an explicit proof gap.

Every finding has severity from `low` to `critical`, separate confidence, and a
numeric `break_score`. A balanced category count is never itself a detection
claim.
