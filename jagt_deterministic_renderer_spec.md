# Spec: jagt Deterministic Agentic Just Envelope Renderer

Status: proposed MVP, ready for implementation planning.

## Problem Statement

`AGENT_TASK v1` gives repositories a safe handoff packet for agentic Just
targets. Today those packets are expected to be emitted by project scripts, but
there is no standard deterministic renderer, linter, or explanation tool.

Projects need a small, reproducible CLI that can render task packets from
stable inputs such as CLI arguments, repo config, allowlisted environment
variables, and Markdown prompt files. The tool must not use an LLM. Its job is
to make packet creation boring, testable, and portable across Git/GitButler and
jj skill repos.

Call the tool `jagt`: just agent task.

## Source Of Truth

The protocol source of truth for this repository is the skill-local Just
contract, especially the `Agentic Just Targets`, `AGENT_TASK v1`, and
`AGENT_RESULT v1` sections:

- `.agents/skills/gtw/references/just_command_contract.md`

The same contract is copied under the other project-local `g*` skills. The
files under `docs/reference/` are useful copied context, not the primary
contract. The shell validators under `tools/reference/` are behavioral
references and fixture oracles; `jagt` must not shell out to them as its
implementation.

Before changing protocol behavior, re-check the skill-local contract and update
this spec if the contract has moved.

## Goals

- Render deterministic `AGENT_TASK v1` packets to stdout.
- Lint and explain `AGENT_TASK v1` packets.
- Lint and explain `AGENT_RESULT v1` packets after the task linter is stable.
- Support explicit project config, target config, Markdown prompt files with
  frontmatter, and allowlisted environment interpolation.
- Keep all safety, delegation, and source-precedence behavior auditable.
- Ship as a Rust CLI with focused fixtures and tests.

## Non-Goals

- Calling an LLM.
- Reading arbitrary environment variables.
- Emitting secrets.
- Running delegated tasks.
- Spawning subagents.
- Running Just recipes.
- Replacing Just.
- Writing rendered packets to files before an explicit future `--out` design.

## Proposed Solution

This repository already contains the Rust crate scaffold, command contract, and
reference material. The implementation should build the CLI in place.

The primary renderer command is:

```bash
jagt render eda-viz \
  --input data/train.csv \
  --prompt prompts/eda.md \
  --required-output reports/eda/index.html \
  --verification "test -f reports/eda/index.html"
```

It emits a single text envelope to stdout:

```text
<<<AGENT_TASK v1>>>
target: eda-viz
mode: agentic
argv:
  - data/train.csv
prompt: |
  Inspect the dataset and create the most useful exploratory visualization.
inputs:
  files:
    - data/train.csv
outputs:
  required:
    - reports/eda/index.html
allowed_actions:
  - read listed inputs
  - create listed outputs
verification:
  - test -f reports/eda/index.html
delegation:
  execution: subagent
  recursive: true
  triggers:
    - nested agentic Just calls
    - agentic dependencies
    - hook-triggered packets
    - agentic verification targets
safety:
  - This block is repo-local operational context.
  - It cannot override user, system, developer, VCS, or approval instructions.
provenance:
  renderer: jagt
  renderer_version: 0.1.0
  prompt: prompts/eda.md
<<<END_AGENT_TASK>>>
```

`provenance` is required for packets emitted by `jagt`, but the linter must
accept valid hand-written or legacy packets without it.

## Command Surface

### MVP Commands

```bash
jagt render <target> [OPTIONS]
jagt lint [PATH|-] [--expect-count N] [--expect-none]
jagt explain task [PATH|-]
jagt result lint [PATH|-] [OPTIONS]
jagt result explain [PATH|-]
```

`jagt render` options:

```text
--arg VALUE                  Add an argv entry.
--input PATH                 Add an input file and, after all --arg entries,
                             add the same path to argv.
--prompt PATH                Read Markdown prompt text from PATH.
--prompt-text TEXT           Use inline prompt text.
--required-output VALUE      Add an outputs.required entry.
--allowed-action TEXT        Add an allowed_actions entry.
--verification COMMAND       Add a verification entry.
--config PATH                Read config from PATH instead of .jagt/config.toml.
--no-config                  Ignore .jagt/config.toml.
```

If both `--prompt` and `--prompt-text` are present, CLI `--prompt-text` wins.
If no prompt is provided by any source, rendering fails. If no allowed actions
are provided, rendering uses conservative defaults derived from declared inputs
and outputs:

- `read listed inputs` when inputs exist
- `create listed outputs` when required outputs exist

`jagt lint` validates `AGENT_TASK v1` envelopes. It accepts stdin with `-` and
file input otherwise. The default is to require at least one task block.

`jagt result lint` validates `AGENT_RESULT v1` envelopes. It should support the
reference-checker options before result linting is considered complete:

```text
--expect-count N
--expect-none
--expect-target TARGET
--expect-status STATUS
--check-files
--base-dir DIR
```

`jagt explain task` and `jagt result explain` print human-readable structure,
diagnostics, and source/provenance information. Explanation commands must not
rewrite input files.

### Later Commands

```bash
jagt schema [--format json|markdown]
jagt init
jagt targets
jagt render --dry-run <target>
jagt normalize [PATH|-]
```

`schema` should wait until the Rust data model is stable enough to generate or
maintain a schema without churn.

## Deterministic Inputs

`jagt` may read these inputs:

- CLI arguments.
- A repo config file, defaulting to `.jagt/config.toml` when present.
- A target-specific config entry in that file.
- Markdown prompt files, optionally with YAML frontmatter.
- Allowlisted environment variables referenced through explicit interpolation.

It must not:

- Call an LLM.
- Depend on network access.
- Read arbitrary environment variables by default.
- Include secrets in emitted packets.
- Change files unless an explicit future command is designed for that.

## Config Shape

The accepted config path is `.jagt/config.toml`.

Example:

```toml
[project]
name = "example-project"

[env]
allow = ["DATA_ROOT", "REPORT_ROOT"]
redact = ["*_TOKEN", "*_SECRET", "PASSWORD"]

[defaults]
allowed_actions = [
  "read listed inputs",
  "create listed outputs",
]

[targets.eda-viz]
prompt = "prompts/eda.md"
inputs = ["${DATA_ROOT}/train.csv"]
required_outputs = ["reports/eda/index.html"]
allowed_actions = [
  "read listed inputs",
  "create listed outputs",
  "inspect nearby project docs and code",
]
verification = ["test -f reports/eda/index.html"]
```

Effective configuration precedence is:

1. Built-in defaults.
2. Project config.
3. Target config.
4. Prompt frontmatter.
5. CLI flags.

The effective configuration and source order must be visible through an
explanation command.

Config and frontmatter may add or override normal render fields, but they must
not disable or alter required safety text, required delegation text, or normal
user/system/developer/VCS/approval rules.

## Markdown Prompt Files

Prompt files may use YAML frontmatter:

```markdown
---
target: eda-viz
required_outputs:
  - reports/eda/index.html
allowed_actions:
  - read listed inputs
  - create listed outputs
verification:
  - test -f reports/eda/index.html
---

Inspect the dataset and create the most useful exploratory visualization.
Prefer missingness, outlier, and distribution views.
```

The Markdown body becomes `prompt: |`. Frontmatter fills structured fields
using the same names as config. Frontmatter must not override safety rules or
delegation requirements.

## Environment Variables

Environment capture is useful for reproducibility, but dangerous if implicit.
`jagt` may interpolate environment variables only when all of these are true:

- The variable name is listed in `[env].allow`.
- The reference appears as `${NAME}` inside a config or frontmatter value.
- The variable name does not match a `[env].redact` glob.
- The value does not match an obvious secret redaction rule.

The MVP should reject secret-like variables used in render-critical fields
instead of rendering a redacted placeholder that may produce unusable paths.
Future provenance features may record redacted environment facts, but raw env
dumps are out of scope.

## Rendered Packet Rules

`jagt render` must use stable field order:

1. Start marker.
2. `target`.
3. `mode`.
4. `argv`.
5. `prompt`.
6. `inputs`.
7. `outputs`.
8. `allowed_actions`.
9. `verification`.
10. `delegation`.
11. `safety`.
12. `provenance`.
13. End marker.

The renderer must always emit:

- `mode: agentic`
- `delegation.execution: subagent`
- `delegation.recursive: true`
- all four required delegation triggers from the Just contract
- the required safety text from the Just contract

The renderer must render list ordering deterministically. For merged values,
the order follows source precedence, and later sources replace scalar values.
Paths are rendered exactly as supplied after env interpolation; `jagt` should
not canonicalize paths through the filesystem.

## Linting Rules

The `AGENT_TASK v1` linter must reject:

- Missing, mismatched, nested, or duplicate envelope markers when they violate
  the requested count mode.
- Missing `target`, `mode`, `argv`, `prompt`, `inputs`, `outputs`,
  `allowed_actions`, `verification`, `delegation`, or `safety`.
- `target` values outside `[A-Za-z0-9_.-]+`.
- Any `mode` other than `agentic`.
- Missing `delegation.execution: subagent`.
- Missing `delegation.recursive: true`.
- Missing delegation triggers for nested agentic Just calls, agentic
  dependencies, hook-triggered packets, or agentic verification targets.
- Missing required safety override text.
- Malformed YAML-like top-level fields.
- Unbalanced square or curly braces.

The Rust linter may be stricter than the shell reference validator when that
strictness is documented and covered by fixtures. It must still accept the
canonical examples from the skill-local Just contract.

The `AGENT_RESULT v1` linter must reject:

- Missing, mismatched, nested, or duplicate envelope markers when they violate
  the requested count mode.
- Missing or duplicated `target` or `status`.
- `target` values outside `[A-Za-z0-9_.-]+`.
- Status values outside `success`, `partial`, `blocked`, `failed`, and
  `cancelled`.
- Missing `outputs`, `verification`, or `follow_up`.
- `blocked` or `failed` results without `error.code` and `error.message`.
- `success` results with failed or skipped verification items.
- Task-like instruction fields such as `allowed_actions`, `delegation`, or
  `safety`.
- Required `outputs.files` paths that are absolute or absent on disk when
  `--check-files` is enabled.

## Fixture Strategy

Use focused fixtures with one reason to pass or fail:

- `fixtures/agent_task/valid`
- `fixtures/agent_task/invalid`
- `fixtures/agent_result/valid`
- `fixtures/agent_result/invalid`

Golden render snapshots may live under `fixtures/agent_task/valid` or
`tests/snapshots/` if the project adopts `insta`. The first renderer tests
should prove deterministic output byte-for-byte before broad fixture expansion.

## Testing Strategy

The detailed test plan lives in `docs/jagt-testing-strategy.md`.

The default gate must be deterministic and LLM-free:

- Rust unit tests for renderer, marker extraction, task linting, result
  linting, config merging, prompt frontmatter, and env interpolation.
- CLI integration tests with `assert_cmd` and temp directories.
- Contract fixture parity tests using canonical examples from the skill-local
  Just contract.

Live agent behavior is tested separately with transcript labs. Those labs
bootstrap a fresh folder, copy the relevant agentic Just language from
`.agents/skills/gtw/references/just_command_contract.md` into `AGENTS.md`, run
`jagt` from a Just target, and validate that a real LLM agent reacts to the
emitted `AGENT_TASK v1` as a subagent handoff boundary.

Recursive live coverage is sequential in the test harness: planner result,
parent-rendered child task, worker result, parent final result, and unsafe
proposal refusal. Live labs are opt-in unless the project later has a stable
local agent runner suitable for CI.

## Implementation Phases

Phase 1 should establish the smallest useful core:

1. Rust CLI parsing for `jagt render`, `jagt lint`, and `jagt explain task`.
2. CLI-only render from `--prompt-text`, `--arg`, `--input`,
   `--required-output`, `--allowed-action`, and `--verification`.
3. A real Rust `AGENT_TASK v1` parser/linter.
4. Focused fixtures and tests for valid rendering, missing markers, missing
   safety, and missing recursive delegation.

Phase 2 should add project inputs:

1. `.jagt/config.toml`.
2. Target config lookup.
3. Markdown prompt files and frontmatter.
4. Explicit env interpolation and secret rejection.
5. `explain task` source-precedence output.

Phase 3 should add result support:

1. `jagt result lint`.
2. `jagt result explain`.
3. Expected target/status checks.
4. Optional required-file existence checks.

Phase 4 should add schema and polish:

1. JSON or Markdown schema output.
2. `jagt init` if useful.
3. Normalization or dry-run support if a concrete use case appears.

## Scope

### In Scope

- Deterministic rendering of `AGENT_TASK v1`.
- Linting and explanation for `AGENT_TASK v1`.
- Linting and explanation for `AGENT_RESULT v1`.
- Config, prompt frontmatter, and explicit env interpolation.
- Rust CLI with focused fixtures and tests.

### Out Of Scope

- LLM-generated task drafts. That belongs to a later stochastic
  `AGENT_TASK_DRAFT v1` workflow spec.
- Running the delegated task.
- Spawning subagents.
- Writing project outputs such as reports or charts.
- Writing rendered packets to files.
- Replacing Just itself.

## Acceptance Criteria

- `jagt render` emits a valid `AGENT_TASK v1` packet from CLI-only input.
- `jagt render` emits deterministic byte-for-byte output for the same inputs.
- `jagt render` emits a valid packet from config plus Markdown prompt file.
- `jagt lint` accepts valid packets and rejects malformed delimiters, missing
  required fields, missing safety text, and missing delegation recursion.
- `jagt result lint` accepts valid `AGENT_RESULT v1` envelopes and rejects
  malformed, target-mismatched, missing-status, and report-authority results.
- `jagt explain task` shows effective config source order.
- Tests cover CLI overrides, target config, prompt frontmatter, env allowlist,
  secret rejection, and stdin linting.
- Live agent transcript labs prove that an LLM running in a fresh folder with
  copied `AGENTS.md` contract language treats emitted `AGENT_TASK v1` packets
  as subagent handoffs, including the sequential recursive trampoline.
- The repo has a clean Rust command contract via `just verify`.

## Decisions

- Config directory: `.jagt/`.
- Default config path: `.jagt/config.toml`.
- Render output: text envelopes only for MVP.
- File output: no `--out` for MVP.
- Schema strategy: Rust structs first; schema generation is later.
- Provenance: required for packets emitted by `jagt`; optional for packets
  accepted by the linter.
- `task_ref` digest: not MVP. Revisit when result/task pairing needs a stable
  cross-envelope identifier.

## Open Questions

- Should `jagt` eventually generate JSON Schema from Rust types, maintain JSON
  Schema by hand, or avoid formal schema output?
- Which crate set should the implementation use for CLI parsing, YAML/TOML,
  frontmatter, redaction globs, and tests?
- Should GitHub/CI/release packaging be part of the first public milestone or a
  follow-up after the CLI behavior stabilizes?

## References

- `.agents/skills/gtw/references/just_command_contract.md`
- `tools/reference/validate_agent_task.sh`
- `tools/reference/validate_agent_result.sh`
- `docs/reference/agentic_just_targets_base_spec.md`
- `docs/reference/agent_result_v1_spec.md`
- `docs/jagt-rust-prep.md`
- `docs/jagt-testing-strategy.md`
