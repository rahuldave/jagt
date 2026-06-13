# jagt MVP Implementation Plan

Status: proposed for approval before implementation.

This plan decomposes `jagt_deterministic_renderer_spec.md` into small,
verifiable Rust slices. The recommended branch/execution model is one normal
development branch in the main worktree:

- Branch: `gest/mprkvltw-jagt-mvp-plan`
- Execution: `main-worktree`
- Parallel writes: no

The detailed test design lives in `docs/jagt-testing-strategy.md`. In short:
normal `just test`/`just verify` must stay deterministic and LLM-free, while
agent reaction and recursive orchestration are covered by explicit live
transcript labs.

## Phase 1: Task Render And Lint Core

Goal: create a useful CLI-only core without config or prompt-file complexity.

Deliverables:

- Replace the scaffold-only binary with a thin `main.rs` plus reusable library
  modules.
- Add `clap` parsing for:
  - `jagt render <target>`
  - `jagt lint [PATH|-]`
  - `jagt explain task [PATH|-]`
- Render deterministic `AGENT_TASK v1` packets from `--prompt-text`, `--arg`,
  `--input`, `--required-output`, `--allowed-action`, and `--verification`.
- Parse envelope markers and YAML body for `AGENT_TASK v1`.
- Lint required task fields, target syntax, `mode: agentic`, recursive
  delegation, required triggers, and safety text.
- Add focused fixtures and integration tests proving render determinism,
  stdin linting, malformed marker rejection, missing safety rejection, and
  missing recursive delegation rejection.
- Add the live agent-reaction lab scaffold: a script or documented procedure
  that creates a fresh temporary folder, copies the relevant Just contract
  language into `AGENTS.md`, invokes a `Justfile` target backed by `jagt`, and
  validates saved transcript artifacts after a real LLM run.

Suggested crates:

- Runtime: `clap`, `serde`, `serde_yaml`, `thiserror`
- Dev/test: `assert_cmd`, `predicates`, `tempfile`

Verification:

- Focused integration tests first.
- `just test`
- Agent-reaction lab scaffold can be generated locally; the live LLM run is
  opt-in and transcript-based, not part of default `just verify`.
- `just verify` at the phase checkpoint.

## Phase 2: Config, Prompt Files, And Env Interpolation

Goal: make renderer inputs useful for real Just recipes while keeping source
precedence auditable.

Deliverables:

- Add `.jagt/config.toml` loading and `--config` / `--no-config`.
- Add target config lookup and merge precedence.
- Add Markdown prompt files with optional YAML frontmatter.
- Add explicit `${VAR}` interpolation only for allowlisted env vars.
- Reject secret-like variables in render-critical fields.
- Expand `jagt explain task` to show effective config values and source order.

Suggested crates:

- Runtime: `toml`, `regex`, `globset`

Verification:

- Tests for CLI override precedence, target config, frontmatter merge,
  env allowlist, secret rejection, and missing prompt errors.
- `just test`
- `just verify` at the phase checkpoint.

## Phase 3: AGENT_RESULT Lint And Explain

Goal: support the return envelope described by the skill-local Just contract.

Deliverables:

- Add `jagt result lint [PATH|-]`.
- Add `jagt result explain [PATH|-]`.
- Support `--expect-count`, `--expect-none`, `--expect-target`,
  `--expect-status`, `--check-files`, and `--base-dir`.
- Validate result statuses, required fields, report-only behavior, failed or
  blocked error blocks, and optional required-file existence checks.
- Add valid and invalid result fixtures.
- Add the sequential recursive live lab modeled on
  `agent_gest_git_skills/docs/live_agent_result_recursive_lab.md`: planner
  result with `outputs.proposed_tasks`, parent-rendered child `AGENT_TASK v1`,
  worker result, parent final result with `recursion_trace`, and unsafe
  proposal refusal.

Verification:

- Tests matching the copied reference validator behavior.
- `just test`
- Optional live recursive transcript validation when a real agent runner is
  available.
- `just verify` at the phase checkpoint.

## Phase 4: Schema And Product Polish

Goal: finish the first public-quality pass after the core behavior is stable.

Deliverables:

- Decide whether to generate JSON Schema, maintain schema by hand, or defer
  schema output.
- Add `jagt schema` only if the schema source-of-truth decision is settled.
- Decide whether `jagt init`, `jagt targets`, `normalize`, or `render --dry-run`
  has enough immediate value for MVP.
- Add CI, license, packaging, and release follow-ups if this is becoming a
  public project.

Verification:

- `just verify`
- Review pass focused on command contract drift, protocol compatibility,
  fixture coverage, and package-readiness gaps.

## Implementation Notes

- Use a hand-controlled renderer for deterministic YAML-like output. Use
  `serde_yaml` for parsing/linting, not for byte-for-byte render formatting.
- Keep marker extraction separate from YAML parsing.
- Keep `main.rs` thin and test behavior through library functions plus
  integration tests.
- Treat `tools/reference/*.sh` as behavioral references only.
- Keep live LLM labs outside the default deterministic test gate unless a
  stable local agent runner exists. They validate saved transcripts; they do
  not replace unit or CLI integration tests.
- Run `ast-grep` dependency impact searches once implementation symbols exist,
  especially for parser/linter/render function contracts.

## Approval Recommendation

Start implementation with Phase 1 only. It creates the smallest durable core,
keeps config/frontmatter/env risk out of the first slice, and gives every later
phase a real parser and deterministic renderer to build on.
