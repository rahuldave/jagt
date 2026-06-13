# jagt

`jagt` means "just agent task." It is a Rust CLI that deterministically renders,
lints, and explains agentic Just handoff envelopes without calling an LLM or
using network access.

The accepted MVP design lives in `jagt_deterministic_renderer_spec.md`, with
the staged implementation plan in `docs/jagt-mvp-implementation-plan.md`.

## Current Implementation

- `jagt render <target>` emits deterministic `AGENT_TASK v1` packets.
- `jagt lint [PATH|-]` validates `AGENT_TASK v1` packet structure.
- `jagt explain task [PATH|-]` summarizes rendered task packets and source
  precedence when provenance is present.
- Render input can come from CLI flags, `.jagt/config.toml`, target config,
  Markdown prompt files with YAML frontmatter, and explicitly allowlisted
  `${VAR}` interpolation.
- Rendered packets always include the required safety and recursive subagent
  delegation language from the agentic Just contract.
- Focused Rust unit tests, CLI integration tests, invalid fixtures, and an
  opt-in live agent reaction lab live under `tests/`, `fixtures/`, and
  `integration_tests/`.
- Stable command contract in `Justfile`.
- Git/GitButler Gest Codex skills installed into `.agents/skills/` with
  `npx skills add`.
- `AGENT_TASK v1` and `AGENT_RESULT v1` references copied under
  `docs/reference/`.

`AGENT_RESULT v1` lint/explain support is still planned work.

## Render Example

```bash
jagt render eda-viz \
  --config .jagt/config.toml \
  --prompt prompts/eda.md \
  --required-output reports/eda/index.html
```

`--prompt-text` wins over `--prompt` when both are present. `--no-config`
ignores `.jagt/config.toml` and any explicit `--config` path.

## Commands

```bash
just setup
just fmt
just fmt-check
just lint
just typecheck
just build
just test
just smoke
just docs
just verify
```

`just verify` is the normal local gate. It currently checks formatting, clippy,
typecheck, build, tests, smoke help output, and whitespace hygiene.

## Fresh Codex Kickoff

For a new Codex project session, open this folder directly:

```bash
cd /Users/rahul/Projects/jagt
```

Then start with `gtw` for any implementation or project work. The new session
should inspect the active Gest iteration before editing so the next slice
continues from the current MVP state.

## Next Decisions

The remaining MVP slices are AGENT_RESULT lint/explain support, the sequential
recursive live lab, schema/product polish, and final verification/review.
