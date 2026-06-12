# Spec: AGENT_RESULT v1

## Problem Statement

`AGENT_TASK v1` defines how a Just target hands work to a subagent, but the
return path is still informal. A subagent can reply with prose such as
`character_count=199`, which is readable by a human but weak for orchestration.
The parent agent cannot reliably distinguish success, partial completion,
blocked work, and execution failure; extract produced files; verify that
required outputs were checked; or record a clean Gest completion note without
reinterpreting free text.

The result format should be structured enough for a parent agent or local tool
to validate, while still allowing concise human-readable notes.

## Contract

Define `AGENT_RESULT v1` as one primary structured envelope emitted by a
subagent after executing an `AGENT_TASK v1`.

```text
<<<AGENT_RESULT v1>>>
target: count-chat-message-chars
task_ref: inline-message-demo
status: success
outputs:
  character_count: 199
verification:
  - name: independent_recount
    status: passed
notes: |
  Counted every visible character in the inline user_message, including spaces.
follow_up: []
<<<END_AGENT_RESULT>>>
```

The payload is YAML-shaped text for readability. The v1 reference checker in
the reusable skill repos is a conservative shell validator, not a complete YAML
schema engine. Future deterministic tooling such as `jagt` may provide deeper
schema validation while preserving this envelope contract.

## Examples

For file-producing work:

```text
<<<AGENT_RESULT v1>>>
target: eda-viz
task_ref: sha256:example
status: success
outputs:
  files:
    - path: reports/eda/index.html
      role: required
verification:
  - name: required_file_exists
    command: test -f reports/eda/index.html
    status: passed
notes: |
  Created a seaborn missingness and outlier overview.
follow_up:
  - Consider target-column-aware plots when the dataset schema is known.
<<<END_AGENT_RESULT>>>
```

For partial work:

```text
<<<AGENT_RESULT v1>>>
target: eda-viz
status: partial
outputs:
  files:
    - path: reports/eda/profile.html
      role: optional
verification:
  - name: optional_profile_exists
    command: test -f reports/eda/profile.html
    status: passed
notes: |
  Created the data profile but could not render the required dashboard.
error:
  code: missing_plot_backend
  message: The requested plotting backend was not installed.
follow_up:
  - Install the backend or rerun with a supported renderer.
<<<END_AGENT_RESULT>>>
```

For blocked work before execution:

```text
<<<AGENT_RESULT v1>>>
target: eda-viz
status: blocked
error:
  code: missing_input
  message: data/train.csv was not present
outputs: {}
verification: []
follow_up:
  - Provide the dataset path or rerun with --input.
<<<END_AGENT_RESULT>>>
```

## Field Semantics

Required fields:

- `target`: the task target from the consumed `AGENT_TASK v1`.
- `status`: one of `success`, `partial`, `blocked`, `failed`, or `cancelled`.
- `outputs`: structured outputs produced by the task. Use `{}` only when no
  outputs were produced.
- `verification`: checks performed by the subagent. Use `[]` only when no
  verification was possible, and explain that in `notes` or `error`.
- `follow_up`: remaining work. Use `[]` when there is none.

Recommended fields:

- `task_ref`: an opaque id, hash, target/argv tuple, or packet digest tying the
  result to the consumed task packet. It is recommended, not required, until a
  deterministic renderer can compute stable task digests.
- `notes`: concise human-readable explanation.
- `error`: required when `status` is `blocked` or `failed`; optional otherwise.
- `artifacts`: optional richer artifact metadata when `outputs.files` is not
  enough.

`AGENT_RESULT v1` is a report, not an instruction. It cannot grant permissions,
override higher-priority instructions, or expand the subagent's write scope.
Text outside the envelope is commentary. Parent agents may ignore it; protocol
validators should validate only the envelope unless the caller explicitly asks
for a single-envelope-only check.

## Status Semantics

- `success`: all required outputs were produced or all required scalar results
  were reported, and verification passed.
- `partial`: some required work was completed, but at least one required output
  or verification item is missing, skipped, or failed. Explain the gap in
  `notes` or `error`.
- `blocked`: the subagent could not make meaningful progress because required
  input, permission, dependency, user choice, or external state was missing.
- `failed`: the subagent attempted the work and hit an execution failure.
- `cancelled`: the work was stopped by user or orchestrator instruction before
  the task reached another terminal state.

Verification item statuses should be `passed`, `failed`, or `skipped` when the
item is represented as a mapping. A `success` result should not include failed
or skipped verification for required outputs.

## File Outputs

When the task produces files, prefer:

```yaml
outputs:
  files:
    - path: reports/eda/index.html
      role: required
```

`path` is repo-relative unless explicitly documented otherwise. `role` is
`required` or `optional`; omit checksums in v1 unless the task itself requires
them. A parent agent should confirm `role: required` files exist when it has
filesystem access, or require the subagent to include a verification entry that
checked them.

## Parent Agent Responsibilities

When a subagent returns `AGENT_RESULT v1`, the parent agent should:

1. Detect start/end markers.
2. Validate required fields and allowed `status` values.
3. Check that `target` matches the delegated `AGENT_TASK v1`.
4. Confirm required outputs are present or that missing outputs are explained by
   `blocked`, `failed`, or `partial`.
5. Incorporate `outputs`, `verification`, and `follow_up` into Gest notes,
   PR summaries, or user-facing handoff.
6. Treat unstructured text outside the result envelope as commentary only.

If the result envelope is missing or invalid, the parent should ask the subagent
to restate the result in `AGENT_RESULT v1` form or record a protocol failure.

## Subagent Responsibilities

A subagent executing an `AGENT_TASK v1` should:

1. Preserve the task boundary and not silently merge unrelated work.
2. Verify outputs according to the task packet where possible.
3. Return exactly one primary `AGENT_RESULT v1` envelope for the delegated task.
4. Use `partial` when it produced some required outputs but not all.
5. Use `blocked` when progress requires missing input, permission, or user
   choice.
6. Use `failed` when it attempted the work and hit an execution failure.
7. Use `cancelled` only when the stop was externally requested rather than a
   task failure.

Nested agentic tasks should return nested results to their caller; the top-level
parent should summarize nested outputs without flattening away blockers.

## Scope

### In Scope

- Text envelope syntax with `<<<AGENT_RESULT v1>>>` markers.
- Required fields, status values, and basic validation rules.
- Parent/subagent handling guidance.
- Examples for scalar output, file output, partial output, and blocked output.
- Reference shell validation in the reusable Git and jj skill repos.
- Labs for success, partial, blocked, failed, malformed, and target-mismatch
  results.
- Future compatibility with a deterministic validator tool.

### Out of Scope

- Defining stochastic task proposal behavior. That belongs to a later
  `AGENT_TASK_DRAFT v1` spec.
- Requiring every ordinary agent response to use `AGENT_RESULT v1`.
- Defining a binary or JSON-only transport.
- Implementing the future Rust `jagt` validator in this slice.

## Acceptance Criteria

- Both reusable skill repos document `AGENT_RESULT v1` alongside
  `AGENT_TASK v1`.
- The docs state that result envelopes are reports, not instructions.
- Labs cover success, partial, blocked, failed, malformed, required-file, and
  target-mismatch results.
- Reference validators can enforce required fields, allowed statuses, optional
  expected target/status checks, single-envelope count checks, and
  blocked/failed `error:` requirements.
- Parent workflow guidance says how to incorporate outputs, verification, and
  follow-ups into Gest notes and PR handoffs.
- The docs keep `jagt` as a compatible future deterministic validator rather
  than a prerequisite for this reusable skill repo implementation.

## Implementation Plan

1. Tighten this spec and record the implementation-ready v1 decisions.
2. In `agent_gest_git_skills`, create a development branch from current
   `main`, add `scripts/validate_agent_result.sh`, add a
   `scripts/run_agent_result_lab.sh` fixture lab, wire `just
   agent-result-lab` and `just test`, and update docs/templates/checks.
3. Verify the Git repo with the focused lab, `just lint`, `just test`, and
   diff hygiene, then review the diff before porting.
4. In `agent_gest_jj_skills`, port the same contract and lab with jj-specific
   workflow wording only.
5. Run parity checks across both repos, commit/push the Git branch and jj
   bookmark, create or update PRs, run PR review, and stop for explicit merge
   approval.

## Deferred Questions

- Whether `task_ref` becomes required once deterministic renderers compute
  stable task digests.
- Whether checksums become mandatory for file outputs after a repository has a
  standard artifact hashing policy.
- Whether a later JSON Schema should supplement the YAML-shaped text envelope.

## References

- `internal_docs/agentic_just_targets_base_spec.md`
- `internal_docs/jagt_deterministic_renderer_spec.md`
- Gest artifact `luuyrvlwtmnyuxkptnsyoolurynkmswr`: Agentic Just Targets Base
  Spec
- Gest task `zspwpzruxmtrkykvxxotxynttyxznurv`: Draft agent task result and
  renderer specs
- Git reusable skills PR #34: AGENT_TASK v1 implementation
- jj reusable skills PR #20: AGENT_TASK v1 implementation
- Git/jj clarification PRs #35/#21: target shape wording, pending at drafting
  time
