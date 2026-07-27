# Hypothesis technique examples

These examples are derived from mature-project issue shapes. They demonstrate
how to route a review; they are not claims about the current revision.

## 1. Incremental state: first run passes, second run changes

```text
contract: identical inputs produce identical diagnostics
source: source files and namespace-package imports
transformation: incremental cache read/write
control: cache validity and module discovery branch
state: .mypy_cache / derived module graph
effect: diagnostics differ on the second invocation
rare cell: second run × namespace package × installed dependency
where: incremental build/cache invalidation and the second-run tests
oracle: run N and N+1; serialized diagnostics must be equal
```

Do not stop at the CLI entrypoint. The likely defect boundary is the cache
writer/reader or module-discovery transition.

## 2. Stream lifecycle: bytes disappear only at EOF

```text
contract: all decoded input is emitted, including the final partial character
source: streaming response chunks
transformation: bytes → incremental decoder
control: if data / EOF flush branch
state: decoder buffer
effect: final text or missing bytes
rare cell: partial multibyte sequence × final empty chunk × streaming mode
where: response decoder, EOF branch, flush call, and one-chunk-vs-many tests
oracle: buffered bytes must be emitted exactly once at EOF
```

The normal path with non-empty chunks is a negative control.

## 3. Parser boundary: binary upload changes text field shape

```text
contract: multipart text fields contain only their declared value
source: multipart body with a binary part before a text part
transformation: chunked bytes → boundary parser → text field
control: partial-boundary/CRLF carry-over logic
state: parser remainder between chunks
effect: leading CRLF leaks into the field
rare cell: binary part × exact chunk boundary × following text field
where: decoder state, partial-boundary helper, and chunk-boundary fixtures
oracle: parsed field equals the source value byte-for-byte after decoding
```

Do not report “multipart is complex.” Point to the remainder-to-field
transition and create one exact chunked probe.

## 4. Precedence: explicit value is overwritten by a sentinel

```text
contract: explicit caller configuration wins over defaults
source: explicit callback/value plus an absent or sentinel parameter
transformation: argument normalization and context parameter merge
control: None/or/setdefault/default branch
state: stored callback or resolved option
effect: explicit behavior is silently replaced
rare cell: two configuration sources × null-like sentinel × chained setup
where: merge order, truthiness branch, setter and order-dependent tests
oracle: after both setters, the explicit value remains installed
```

A test that sets only one source cannot validate precedence.

## 5. Concurrency: independent calls return another worker's result

```text
contract: each operation returns the result for its own input
source: concurrent calls with distinct operands
transformation: public array operation → shared native/backend buffer
control: lock, thread-local ownership or temporary-buffer lifetime
state: shared workspace or backend handle
effect: wrong result, intermittent corruption or crash
rare cell: non-contiguous input × OpenBLAS/backend × concurrent calls
where: adapter, temporary buffer, lock boundary and threaded regression tests
oracle: every returned result equals the sequential reference for that input
```

Sequential tests and contiguous inputs are negative controls, not coverage of
the shared-state cell.

## 6. Teardown ordering: dependent fixture outlives its prerequisite

```text
contract: dependent fixture teardown runs before prerequisite teardown
source: fixture dependency graph
transformation: fixture setup registration → finalizer ordering
control: scope and dependency ordering
state: live fixture resources
effect: dependent cleanup observes an already-closed prerequisite
rare cell: same scope × dependency chain × teardown path
where: finalizer stack, dependency graph construction and teardown tests
oracle: every finalizer sees all resources it declares as prerequisites
```

Do not infer correctness from setup order; setup and teardown are different
graphs.

## 7. Compatibility: valid external version is not a package version

```text
contract: platform markers evaluate without rejecting valid platform data
source: OS/kernel-provided version string
transformation: platform value → package Version comparison
control: parser/coercion/fallback for non-PEP-440 values
state: marker environment
effect: install/resolve flow raises InvalidVersion
rare cell: Linux distribution suffix × version comparison operator
where: environment construction, coercion helper and marker evaluation
oracle: supported platform values produce True/False, never an unexpected parser error
```

The fact that the common platform uses clean versions is not a contract for
all operating systems.

## 8. Observability: retryable failure becomes silent data loss

```text
contract: expired credentials do not silently discard remote samples
source: remote-write request and expiring authentication state
transformation: send → response classification → retry queue
control: expiry detection and retry/backoff branch
state: pending sample queue and failure counters
effect: dropped samples or misleading success/metrics
rare cell: token expiration × in-flight request × retry boundary
where: response classification, queue ownership, retry scheduler and metrics
oracle: each accepted sample is either acknowledged or visibly retained/rejected
```

A log line alone is not an oracle; conservation of accepted samples is.
