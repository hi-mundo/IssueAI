# Issue search technique

Use the corpus at `tests/bug-hunt-evals/corpus/real-issues-1000.json` as a
research aid. It contains 1,000 closed issue records from 30 projects, sampled
at up to 35 records per project. The deeper interpretation is in
`tests/bug-hunt-evals/corpus/late-discovery-analysis.md`. The data is
time-sensitive and must be refreshed before serving as a benchmark.

## Query matrix

Search each repository with independent families and merge by issue URL:

| Family | Queries | What it reveals |
| --- | --- | --- |
| behavior | `bug`, `incorrect`, `unexpected`, `wrong` | wrong output and contract drift |
| stability | `crash`, `hang`, `deadlock`, `timeout`, `leak` | failure and lifecycle paths |
| compatibility | `regression`, `upgrade`, `breaking`, `version`, `platform` | release and environment boundaries |
| data | `corrupt`, `lost`, `duplicate`, `encoding`, `unicode`, `truncat` | integrity and representation defects |
| state | `cache`, `stale`, `reload`, `rollback`, `session`, `race` | temporal and concurrent defects |

## Relevance score

Use a transparent score only to prioritize reading, never as proof:

```text
relevance =
  3 * has_reproduction
  + 3 * has_expected_observed_pair
  + 2 * has_linked_fix_or_test
  + 2 * has_affected_version
  + 1 * has_environment
  - 3 * is_feature_or_roadmap
  - 2 * is_duplicate_or_support
```

Read the top candidates from every project, not only the global top score, to
avoid allowing one project's issue culture to dominate the learned patterns.

## Late-discovery gate

Do not label a report “found many versions later” because it stayed open for a
long time. Require an explicit introduction/affected version and a later
observation, or mark the timeline unknown. Extract the escape mechanism: rare
boundary, state transition, environment cell, probabilistic execution,
cross-project integration, or missing telemetry.

## Repository search map

After extracting the issue pattern, route the search to the code locations most
likely to hide it:

| Mechanism | Search first | Typical evidence |
| --- | --- | --- |
| state reuse | cache, session, reload and invalidation code | first run passes, second differs |
| lifecycle | stream, EOF, close, cancel, teardown and retry paths | data or resource survives/disappears at transition |
| precedence | config merge, env/default resolution, `setdefault`, `or` | explicit value loses to fallback |
| representation | encoding, URL/path, version and identity helpers | valid value changes shape or collides |
| integration | adapters, plugins, drivers, backends and shims | default backend passes, consumer fails |
| concurrency | queues, workers, callbacks, locks and async state | loss, duplicate, deadlock or nondeterminism |
| compatibility | version guards, feature detection and release diffs | runtime/dependency change alters behavior |
| observability | retries, fallbacks, logs, metrics and health checks | failure becomes plausible success |

Then inspect tests and fixtures for the missing dimension: first versus repeated
run, complete versus partial input, one platform versus another, sequential
versus concurrent, direct caller versus adapter, and success versus cleanup or
failure path.

## Unmapped repositories: where to start

For a repository absent from the issue corpus, use the repository's own
structure as the map. Rank locations by the number of contract transitions they
perform, not by file size or keyword frequency:

| Order | Repository evidence | Search locations | Hidden cell to construct |
| --- | --- | --- | --- |
| 1 | public input becomes an internal object | parser, handler, decorator, schema adapter, serializer | null/empty/partial/extra shape |
| 2 | state is reused across calls | cache, session, reload, retry, memoization | first run vs second run/restart |
| 3 | ownership changes | stream, socket, file, worker, transaction, generator | complete vs partial read/close/cancel |
| 4 | multiple authorities can set a value | config merge, env, defaults, fallback, CLI | explicit value vs inherited/default value |
| 5 | representation or identity changes | URL/path/version/name/label/cache-key helpers | normalization, collision, encoding loss |
| 6 | control crosses a boundary | plugin, driver, backend, subprocess, callback, async task | alternate implementation/platform/interleaving |
| 7 | tests replace the runtime boundary | mocks, fakes, fixtures, setup/teardown | real lifecycle and failure path |

The output is a route, not a verdict:

```text
public contract
  → exact symbol/file boundary
  → rare transition or environment cell
  → missing test dimension
  → invariant oracle
  → direct probe
```

Examples: a second-run mismatch routes to cache invalidation and reload code;
a parser leak routes to byte/text conversion plus EOF cleanup; an explicit
configuration value being ignored routes to merge precedence and truthiness
branches; a thread-only numerical failure routes to non-contiguous input,
backend adapter and shared-state synchronization.

## Conversion gate

Convert an issue into a mutation only when all of these are known:

1. the current intended behavior;
2. the exact code boundary that can violate it;
3. a normal-path input that still works after mutation;
4. a rare-path input that exposes the mismatch;
5. a direct probe and expected output;
6. a source URL and rationale stored outside the blind review context.

## Technique v2: discovery is a coverage problem

The improved technique is not “search for bug words.” It is a bounded coverage
loop:

```text
inventory → contract map → boundary map → candidate ledger
→ independent discovery passes → negative controls → oracle → probe
```

For each candidate, require four independent anchors:

1. **contract anchor:** documentation, type, schema, caller or test says what
   must happen;
2. **boundary anchor:** an exact function, method, branch or file changes shape,
   ownership, authority, representation, time or execution context;
3. **escape-cell anchor:** a conjunction such as partial input × EOF,
   second-run × cache, alternate backend × concurrency, or explicit value ×
   sentinel;
4. **oracle anchor:** a conservation, equality, ordering, lifecycle, type or
   visibility invariant that a small probe can falsify.

Score discovery quality separately:

```text
route_quality = contract + boundary + escape_cell + oracle
```

Do not use `route_quality` as break-score, severity or evidence of a defect.
An issue is only probe-ready when all four anchors exist. The examples in
`references/hypothesis-technique-examples.md` show the expected level of
specificity.

## Evidence from the 2,000-issue corpus

The two 1,000-issue samples are overlapping evidence, not mutually exclusive
labels. Their useful signal is the shape of the escape chain:

| Corpus signal | Count | What it changes in the search |
| --- | ---: | --- |
| compatibility | 422 | inspect runtime, platform, dependency and release seams |
| concurrency | 210 | inspect interleavings, queues, locks, callbacks and cancellation |
| encoding/representation | 145 | inspect parse, normalize, convert, identity and round-trip boundaries |
| regression | 129 | compare old invariant, changed branch and missing regression dimension |
| state reuse | 126 | compare first call, second call, reload, rollback and stale state |
| boundary | 114 | construct null, empty, partial, oversized and invalid-shape inputs |
| lifecycle | 105 | inspect EOF, close, retry, teardown, redirect and ownership transfer |
| precedence | 87 | compare explicit, environment, default, fallback and inherited values |
| data integrity | 58 | check conservation, ordering, uniqueness and atomic update or rollback |
| two or more interacting conditions | 520 | do not test axes independently only; cross them into one cell |
| delayed effect | 258 | inspect later calls, restart, retry, background work and telemetry |
| transition involved | 129 | prioritize state/resource transitions over steady-state code |
| common path passes | 424 | passing normal behavior is a negative control, not closure |
| observability gap | 101 | inspect silent fallback, swallowed error, retry exhaustion and false success |

The categories overlap. The actionable conclusion is not that a repository has
“422 compatibility bugs”; it is that mature-project defects concentrate where
at least two dimensions cross. The default discovery order is therefore:

```text
contract/boundary
× state or resource transition
× environment, integration, or concurrency cell
× delayed/observable effect
```

### Where to look for each part

| Escape-chain part | First locations | Concrete question |
| --- | --- | --- |
| contract | exports, schemas, types, examples, errors, focused tests | what must remain true? |
| boundary | parser, handler, serializer, adapter, converter, config merge | where does shape, authority, ownership or representation change? |
| transition | cache, stream, socket, worker, transaction, retry, teardown | what changes after the first event or on failure? |
| alternate cell | backend, plugin, driver, platform, dependency, async callback | which assumption belongs only to the default implementation? |
| delayed effect | persistence, queue, restart, metrics, logs, health, retry | can the failure appear later or as plausible success? |
| oracle | conservation, equality, ordering, type, lifecycle, visibility invariant | what exact observation falsifies the claim? |

The deterministic implementation is
`scripts/build_discovery_worklist.py`. It emits balanced concrete rows instead
of one global top-score list. `scripts/generate_structural_hypotheses.py
--worklist` then turns those rows into hypotheses while preserving the four
anchors and negative controls. Both outputs are discovery artifacts only.
When later history is available, merge it with
`scripts/merge_discovery_worklists.py`. History-seeded rows are prioritized and
retain commit evidence, but they do not replace the structural tuple or close
the contract/oracle anchors.

### Metrics that must not be confused

```text
mechanism coverage = mechanisms represented in the bounded worklist
location quality   = rows anchored to file:line:symbol
route quality      = rows with contract + boundary + escape-cell + oracle anchors
probe readiness    = rows whose inferred contract is closed by repository evidence
finding coverage   = rows confirmed by an observed mismatch
```

The first metric should improve search breadth. The last metric is the only one
that can support a claim that a bug was found. Category overlap with an issue's
historical label is a calibration signal, not success.
