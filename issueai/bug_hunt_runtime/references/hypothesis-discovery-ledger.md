# Hypothesis discovery ledger

This ledger adapts the strongest discovery discipline from security review to
non-security defects. It is a worklist, not a findings list.

## Candidate tuple

Every candidate must preserve this tuple:

```text
input/source → transformation → control/decision → state/resource → output/effect
```

For each tuple record:

| Field | Required content |
| --- | --- |
| candidate id | stable id for one reachable behavior path |
| contract | what the public/API/product behavior promises |
| source | caller, input, event, configuration or prior state |
| transformation | parse, normalize, merge, convert, cache, schedule or delegate step |
| control | guard, branch, default, lock, validator, cleanup or retry decision |
| state/resource | cache, stream, socket, file, worker, transaction or derived value |
| sink/effect | return, exception, write, close, queue, emitted event or user-visible output |
| rare cell | exact input × lifecycle × environment × execution mode conjunction |
| missing coverage | the test/fixture dimension that does not exercise the cell |
| oracle | invariant that proves or falsifies the hypothesis |
| evidence | file/symbol/line, test, docs, history or reference id |
| exact location | concrete file:line:symbol; a file-only bucket is not probe-ready |
| disposition | open, selected, duplicate, rejected, inconclusive or validated |

## Discovery passes

Run separate passes and merge by candidate tuple, not by keyword:

1. **Contract pass:** public exports, examples, schemas, types, errors and
   compatibility promises.
2. **Boundary pass:** every place where shape, ownership, authority, encoding,
   time or execution context changes.
3. **Transition pass:** cache reuse, EOF, close, teardown, retry, redirect,
   cancellation, reload, restart, rollback and worker handoff.
4. **Adapter pass:** alternate backend, plugin, driver, platform, dependency,
   subprocess and optional implementation.
5. **Concurrency pass:** queues, callbacks, locks, async tasks, shared state,
   signal handling and cancellation ordering.
6. **Test-gap pass:** compare each candidate cell against tests and fixtures;
   record negative controls instead of assuming absence means failure.
7. **History pass:** inspect fixes, version guards, TODOs, fallback branches and
   deleted tests only after a concrete candidate exists.

The history pass is a localization aid. A file changed by a later fix is not a
finding until the old snapshot, contract, trigger and oracle are independently
established.

## Candidate expansion rules

- A shared helper does not close its concrete callers. Enumerate each caller
  whose input or lifecycle differs.
- A broad family such as “all parsers” or “all adapters” must be split into
  concrete exported operations or branches before validation.
- A passing sibling is a negative control for that sibling, not proof that the
  candidate is safe.
- A category match is not a candidate. The candidate needs an exact node and a
  falsifiable oracle.
- A missing dependency or unavailable platform keeps the row `inconclusive`; it
  never becomes `validated` or `found`.

## Coverage accounting

Report these separately:

```text
inventory coverage = nodes examined / nodes in bounded worklist
route coverage     = candidates with source/control/state/effect tuple
oracle coverage    = candidates with explicit falsifier
probe coverage     = candidates with executable direct probe
finding coverage   = candidates confirmed by observed mismatch
```

Do not convert route coverage or category overlap into finding coverage.
Do not convert category overlap into route quality either. A route is stronger
when its source/control/effect tuple is anchored to an exact symbol and line,
and when the contract, escape cell and oracle are independently closed.
