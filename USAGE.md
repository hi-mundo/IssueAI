# Using IssueAI

## Main usage modes

IssueAI is designed to be used in three ways:

1. plugin inside an AI coding agent
2. BYOK-compatible local usage
3. CLI usage for evals, benchmarks, and manual runs

The intended default is host-first plugin usage. BYOK and CLI are compatibility
and evaluation paths, not the main product posture.

## Plugin usage

Current primary hosts:

- Codex
- Claude

### Codex install prompt

Paste this into Codex:

```text
Add https://github.com/hi-mundo/IssueAI as a plugin source or marketplace for this workspace, install the IssueAI plugin, enable it here, and confirm the plugin is active. After installed show me the capabilities and examples of how to use.
```

### Claude install prompt

Paste this into Claude:

```text
Add https://github.com/hi-mundo/IssueAI as a plugin source or marketplace for this project, install the IssueAI plugin, enable it here, and confirm the plugin is active. After installed show me the capabilities and examples of how to use.
```

## BYOK-compatible usage

IssueAI is also compatible with teams that want to run it outside marketplace or
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
python3 -m issueai.cli --repository example/repo --signal async --signal timeout
python3 -m issueai.cli historical-case --case-id <case-id> ...
```

Use CLI mode when you need:

- direct local runs
- reproducible benchmark calls
- manual evaluation of historical cases
- host-independent experimentation

## Which mode should you choose?

- use the plugin if you want IssueAI inside your normal coding agent workflow
- use BYOK/local mode if you need compatibility or custom execution control
- use the CLI if you are running evals, benchmarks, or structured manual tests
