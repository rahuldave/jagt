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
- `jagt result lint [PATH|-]` validates `AGENT_RESULT v1` report envelopes,
  including expected target/status checks and optional required-file checks.
- `jagt result explain [PATH|-]` summarizes result status, outputs,
  verification, follow-up, and report-only state.
- `jagt draft lint [PATH|-]` validates non-executable `AGENT_TASK_DRAFT v1`
  proposal envelopes before human or parent-agent approval and deterministic
  promotion.
- Render input can come from CLI flags, `.jagt/config.toml`, target config,
  Markdown prompt files with YAML frontmatter, and explicitly allowlisted
  `${VAR}` interpolation.
- Rendered packets always include the required safety and recursive subagent
  delegation language from the agentic Just contract.
- Focused Rust unit tests, CLI integration tests, invalid fixtures, and opt-in
  live agent transcript labs live under `tests/`, `fixtures/`, and
  `integration_tests/`.
- The repo-local `.agents/skills/jagt-protocol/` skill supplies standalone
  protocol context, jagt lint wrappers, and the send/receive/draft demo for
  jagt labs.
- Stable command contract in `Justfile`.
- `AGENT_TASK v1`, `AGENT_RESULT v1`, and `AGENT_TASK_DRAFT v1` references live under
  `docs/reference/`.

## Render Example

```bash
jagt render eda-viz \
  --config .jagt/config.toml \
  --prompt prompts/eda.md \
  --required-output reports/eda/index.html
```

`--prompt-text` wins over `--prompt` when both are present. `--no-config`
ignores `.jagt/config.toml` and any explicit `--config` path.

## Result Example

```bash
jagt result lint result.agent-result.txt \
  --expect-target eda-viz \
  --expect-status success \
  --check-files \
  --base-dir .
```

## Draft Example

```bash
jagt draft lint proposed.agent-task-draft.txt --expect-count 1
```

Draft linting checks shape, required approval, safety language, promotion
checks, recursive subagent delegation, and forbidden authority patterns. It does
not approve, execute, or compile a draft.

## Protocol Demo

```bash
just protocol-demo
```

The demo is standalone inside this repository. It renders and validates an
outbound task, validates inbound result shapes, checks recursive result
fixtures, validates a draft proposal, and promotes it through `jagt render`.
It uses `.agents/skills/jagt-protocol/` for packet-contract context and
skill-local wrappers, so the `jagt` repository does not need the Git or jj Gest
skill repositories installed to run its protocol labs.

The demo exercises the three packet classes that `jagt` owns:

- `AGENT_TASK v1`: deterministic executable handoff emitted by `jagt render`
  and verified by `jagt lint`.
- `AGENT_RESULT v1`: report-only subagent response verified by
  `jagt result lint`, including recursive result trace fixtures.
- `AGENT_TASK_DRAFT v1`: stochastic LLM proposal verified by `jagt draft lint`,
  then promoted only through deterministic `jagt render` after approval.

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
just protocol-demo
just docs
just verify
```

`just verify` is the normal local gate. It currently checks formatting, clippy,
typecheck, build, tests, smoke help output, the standalone protocol demo, and
whitespace hygiene.

## Fresh Codex Kickoff

For a new Codex project session, open this folder directly:

```bash
cd /Users/rahul/Projects/jagt
```

Then start with `gtw` for any implementation or project work. The new session
should inspect the active Gest iteration before editing so the next slice
continues from the current MVP state.

## Next Decisions

The remaining MVP slices are schema/product polish and final
verification/review.
