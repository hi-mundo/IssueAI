# Ask HN: AIssuer - calibrated with 500+ hard issues

Hi HN, I built AIssuer, a plugin for Codex, Claude, and Cursor that tries to find the kinds of issues that usually survive normal review and show up late in mature software.

The short version:

- it starts with Repository Recon
- it checks intent vs implementation next
- it hunts deeper, mature-repo failure modes after the obvious cases
- it finishes with deterministic probes so the shortlist is evidence-backed

Why I think it is interesting:

- calibrated on 500+ hard issues from mature software where the bug was discovered late
- focused on bugs, reliability problems, brittle contracts, boundary mistakes, and implementation drift
- built as a host-first plugin, with BYOK and CLI fallback for testing and benchmarks
- the installed surface is intentionally small, with the heavier datasets and eval tooling kept outside the default plugin

The visible skill levels are:

- Understand: Repository Recon
- Check intent: Repository Intent Review
- Hunt: Issue Hunt
- Probe: Issue Probe

That ordering matters. The idea is to understand the repo first, then ask whether the code matches its intent, then only use the deeper hunt once the obvious things are handled.

Current benchmark snapshot in this repo:

- 40/40 historical cases inside the top 20
- 20/20 official validated cases passed

I would love feedback on:

- what kinds of late-discovered bugs are still missing from the corpus
- how to make the plugin more useful in real IDE workflows
- where the docs should be simpler or more direct
- whether the host packaging is clear enough for Codex, Claude, and Cursor

If you want to try it, the repo is here:

- https://github.com/hi-mundo/AIssuer

And if you have examples of hard, late-discovered issues in mature software, I would love pointers.
