# Repository map heuristics

Repository Recon should treat the repository map as a bounded graph artifact,
not as free-form prose.

## Graph inputs

- entrypoints
- role locations
- import edges
- traced flow chains
- dominant domains
- structural redundancies

## Useful graph questions

- where does the main flow start?
- where does it branch?
- where does data likely cross a boundary?
- where are the same responsibilities spread across more than one domain?
- where does the project break its own placement conventions?

## Boundaries to mark

- routes to controllers
- controllers to services
- services to persistence
- services to third-party integrations
- middleware to protected routes
- schema/type artifacts to high-signal handlers and services
