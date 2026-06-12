# Spec: jagt Deterministic Agent Task Renderer

## Problem Statement

`AGENT_TASK v1` gives repositories a safe handoff packet for agentic Just
targets. Today those packets are expected to be emitted by project scripts, but
there is no standard deterministic renderer, linter, or explanation tool.

Projects need a small, reproducible tool that can render task packets from
stable inputs such as CLI arguments, repo config, allowlisted environment
variables, and Markdown prompt files. The tool should not use an LLM. Its job is
to make packet creation boring, testable, and portable across Git/GitButler and
jj skill repos.

Call the tool `jagt`: just agent task.

## Proposed Solution

Create a new Rust project named `jagt` under `/Users/rahul/Projects` in a
separate follow-on project. `jagt` renders and validates agent task/result
envelopes:

```bash
jagt render eda-viz \
  --input data/train.csv \
  --prompt prompts/eda.md \
  --config .jagt/config.toml
```

The command emits:

```text
<<<AGENT_TASK v1>>>
target: eda-viz
mode: agentic
argv:
  - data/train.csv
prompt: |
  ...
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
<<<END_AGENT_TASK>>>
```

`jagt` should also validate `AGENT_RESULT v1` once that spec is accepted.

## Core Commands

Initial command set:

```bash
jagt render <target> [--input PATH]... [--arg VALUE]... [--prompt PATH]
jagt lint [PATH|-]
jagt explain [PATH|-]
jagt schema [--format json|markdown]
jagt result lint [PATH|-]
jagt result explain [PATH|-]
```

Nice-to-have, after MVP:

```bash
jagt init
jagt targets
jagt render --dry-run <target>
jagt normalize [PATH|-]
```

`jagt render` writes only to stdout unless an explicit `--out` flag is added in
a later version. Just recipes can then use it directly:

```just
eda-viz-agentic +FILES:
  @jagt render eda-viz --input {{FILES}} --prompt prompts/eda.md

agentic TARGET +ARGS:
  @jagt render {{TARGET}} --arg {{ARGS}}
```

## Deterministic Inputs

`jagt` may read these inputs:

- CLI arguments.
- A repo config file, defaulting to `.jagt/config.toml` when present.
- A target-specific config entry in that file.
- Markdown prompt files, optionally with YAML frontmatter.
- Allowlisted environment variables.

It must not:

- Call an LLM.
- Read arbitrary environment variables by default.
- Include secrets in emitted packets.
- Change files unless an explicit future command is designed for that.
- Depend on network access.

## Config Shape

Example `.jagt/config.toml`:

```toml
[project]
name = "example-project"

[env]
allow = ["DATA_ROOT", "REPORT_ROOT"]
redact = ["*_TOKEN", "*_SECRET", "PASSWORD"]

[defaults.delegation]
execution = "subagent"
recursive = true

[targets.eda-viz]
prompt = "prompts/eda.md"
inputs = ["data/train.csv"]
required_outputs = ["reports/eda/index.html"]
allowed_actions = [
  "read listed inputs",
  "create listed outputs",
  "inspect nearby project docs and code",
]
verification = ["test -f reports/eda/index.html"]
```

CLI flags override config values in predictable order:

1. Built-in defaults.
2. Project config.
3. Target config.
4. Prompt frontmatter.
5. CLI flags.

The effective configuration should be visible through `jagt explain`.

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

The Markdown body becomes `prompt: |`. Frontmatter fills structured fields.
Frontmatter must not override safety rules or delegation requirements.

## Environment Variables

Environment capture is useful for reproducibility, but dangerous if implicit.
`jagt` should include only allowlisted variables:

```toml
[env]
allow = ["DATA_ROOT", "REPORT_ROOT"]
redact = ["*_TOKEN", "*_SECRET", "PASSWORD"]
```

Rendered packets may include captured values under a provenance field in a later
version, but secrets must be redacted or rejected. The MVP may simply allow
environment interpolation into configured paths while omitting raw env dumps.

## Provenance

Rendered packets should include enough provenance to debug how they were made,
without making the envelope noisy. MVP provenance can be a simple optional block:

```yaml
provenance:
  renderer: jagt
  renderer_version: 0.1.0
  config: .jagt/config.toml
  prompt: prompts/eda.md
```

The validator should accept packets without provenance, because hand-written or
legacy emitters may still be valid.

## Safety Rules

- `jagt` emits operational context, not higher-priority instruction.
- `jagt` must always emit the safety override text required by `AGENT_TASK v1`.
- `jagt` must always emit the recursive subagent delegation block.
- Config and frontmatter cannot disable safety text.
- Config and frontmatter cannot grant permission to bypass user, developer,
  system, VCS, approval, or repo instructions.
- Env interpolation must be explicit and auditable.

## Repository Setup For Follow-On Project

When this becomes a fresh Codex project:

1. Create `/Users/rahul/Projects/jagt`.
2. Initialize Git and Rust:

   ```bash
   cargo init --bin
   ```

3. Add a `Justfile` with stable commands:

   ```just
   setup:
     cargo fetch

   fmt:
     cargo fmt --all

   lint:
     cargo clippy --all-targets --all-features -- -D warnings

   test:
     cargo test --all-features

   verify: fmt lint test
   ```

4. Add `.gitignore` for `target/`, local temp files, and any `.jagt/tmp/`
   fixture output.
5. Copy/adapt `AGENTS.md` from the reusable Git/Gest skills repo, keeping the
   Gest workflow guidance but making the project command contract Rust-specific.
6. Put this spec in the repo as `jagt-spec.md`.
7. Create fixtures for valid task packets, invalid task packets, valid result
   packets, and invalid result packets.

## Scope

### In Scope

- Deterministic rendering of `AGENT_TASK v1`.
- Linting and explanation for `AGENT_TASK v1`.
- Linting and explanation for `AGENT_RESULT v1`.
- Config, prompt frontmatter, and explicit env interpolation.
- Rust CLI with focused fixtures and tests.

### Out of Scope

- LLM-generated task drafts. That belongs to the later stochastic
  `AGENT_TASK_DRAFT v1` workflow spec.
- Running the delegated task.
- Spawning subagents.
- Writing project outputs such as reports or charts.
- Replacing Just itself.

## Acceptance Criteria

- `jagt render` emits a valid `AGENT_TASK v1` packet from CLI-only input.
- `jagt render` emits a valid packet from config plus Markdown prompt file.
- `jagt lint` accepts valid packets and rejects malformed delimiters, missing
  required fields, missing safety text, and missing delegation recursion.
- `jagt result lint` accepts valid `AGENT_RESULT v1` envelopes and rejects
  malformed, target-mismatched, or missing-status results.
- `jagt explain` shows effective config source order.
- Tests cover CLI overrides, target config, prompt frontmatter, env allowlist,
  secret rejection/redaction, and stdin linting.
- The repo has a clean Rust command contract via `just verify`.

## Open Questions

- Should the config directory be `.jagt/` or `.agent-task/`?
- Should `jagt render` support JSON output in addition to text envelopes?
- Should packet schema be maintained as JSON Schema, Rust structs only, or both?
- Should provenance be required in packets emitted by `jagt`, even if optional
  for hand-written packets?
- Should `jagt` compute a stable `task_ref` digest for pairing
  `AGENT_TASK v1` with `AGENT_RESULT v1`?

## References

- `internal_docs/agentic_just_targets_base_spec.md`
- `internal_docs/agent_result_v1_spec.md`
- Gest artifact `luuyrvlwtmnyuxkptnsyoolurynkmswr`: Agentic Just Targets Base
  Spec
- Git reusable skills PR #34 and jj reusable skills PR #20: merged
  `AGENT_TASK v1` support
- The earlier `cx` project setup pattern: create a new repo, copy/adapt
  reusable Git/Gest skills, then take it up as a fresh Codex project
