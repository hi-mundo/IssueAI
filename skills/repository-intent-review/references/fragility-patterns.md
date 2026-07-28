# Fragility patterns for Repository Intent Review

Repository Intent Review should bias toward patterns that make software easy to
break or easy to misunderstand.

## High-signal checks

- middleware or guard expected, but not obviously wired
- schema or validator expected, but absent
- implicit typing in high-signal code paths
- nullability or undefined assumptions hidden by UI or client-side flow
- async boundaries that look misleading or under-protected
- contract drift between role boundaries

## Review mindset

- ask what the seam is supposed to guarantee
- ask whether the current implementation visibly enforces that guarantee
- ask whether a small unexpected input or branch would break the assumption

## Typical repository guarantees

- routes are protected when they should be
- services receive valid data
- persistence receives normalized data
- integrations do not bypass contracts
- async code does not hide weak failure paths
