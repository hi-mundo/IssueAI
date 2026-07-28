# Navigation strategies for Repository Recon

Use these as deterministic navigation defaults before asking the model to
synthesize anything.

## Preferred starting points

- If the repository is script- or app-entrypoint-first, start from `main`,
  `app`, `server`, `cli`, `manage`, or equivalent.
- If a clear `main.*` exists, start there first and follow imports outward.
- If no obvious entrypoint exists but the repository is API-first, start from
  routes and walk inward to controllers, services, and persistence.
- If neither exists, begin with folder census and dominant role locations.

## Structural traversal

- Follow local imports before broad sibling exploration.
- Count how many distinct folders appear at each tree depth.
- Count how often each role appears across separate domains.
- Prefer deterministic role markers over free-form semantic guesses.

## What to look for

- where the main flow begins
- where each responsibility usually lives
- what is colocated vs fragmented
- what looks redundant or outside the dominant domain pattern
