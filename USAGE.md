# Using AIssuer

## Main usage modes

AIssuer is designed to be used in three ways:

1. plugin inside an AI coding agent
2. BYOK-compatible local usage
3. CLI usage for evals, benchmarks, and manual runs

The intended default is host-first plugin usage. BYOK and CLI are compatibility
and evaluation paths, not the main product posture.

Recommended order inside the plugin:

1. run `Repository Recon`
2. run `Repository Intent Review`
3. fix or triage obvious findings
4. run `Issue Hunt`
5. run `Issue Probe` on the shortlist when you want evidence

## Plugin usage

Current primary hosts:

- Codex
- Claude

### Codex install prompt

Paste this into Codex:

```text
Add https://github.com/hi-mundo/AIssuer as a plugin source or marketplace for this workspace, install the AIssuer plugin, enable it here, and confirm the plugin is active. After installed show me the capabilities and examples of how to use.
```

### Claude install prompt

Paste this into Claude:

```text
Add https://github.com/hi-mundo/AIssuer as a plugin source or marketplace for this project, install the AIssuer plugin, enable it here, and confirm the plugin is active. After installed show me the capabilities and examples of how to use.
```

## Default plugin flow

Inside the plugin, the normal sequence is:

1. `Repository Recon`
2. `Repository Intent Review`
3. `Issue Hunt`
4. `Issue Probe`

## BYOK-compatible usage

AIssuer is also compatible with teams that want to run it outside marketplace or
plugin flows.

That mode exists for:

- local experimentation
- compatibility testing
- custom automation
- future host integrations

The long-term shape is one Python core with thin host adapters, not separate
forked products per host.

## CLI usage

Current CLI surfaces:

```bash
python3 -m issueai.cli repository-recon --repo /path/to/repo
python3 -m issueai.cli repository-intent-review --repo /path/to/repo
python3 -m issueai.cli issue-hunt --repo /path/to/repo
python3 -m issueai.cli issue-probe --repo /path/to/repo
python3 -m issueai.cli preflight --repo /path/to/repo
python3 -m issueai.cli intent-review --repo /path/to/repo
python3 -m issueai.cli --repository example/repo --signal async --signal timeout
python3 -m issueai.cli historical-case --case-id <case-id> ...
```

CLI surface meaning:

- `repository-recon`: run the structural entry workflow
- `repository-intent-review`: run the semantic intent-vs-implementation review
- `issue-hunt`: run the deeper late-stage hunt
- `issue-probe`: run deterministic follow-up evidence checks
- `preflight`: compatibility alias for `.issueai` refresh only
- `intent-review`: compatibility alias for `repository-intent-review`
- `pipeline`: lightweight compatibility path
- `historical-case`: eval-only benchmark replay, not a normal product entrypoint

Use CLI mode when you need:

- direct local runs
- reproducible benchmark calls
- manual evaluation of historical cases
- host-independent experimentation

## Which mode should you choose?

- use the plugin if you want AIssuer inside your normal coding agent workflow
- use BYOK/local mode if you need compatibility or custom execution control
- use the CLI if you are running evals, benchmarks, or structured manual tests
