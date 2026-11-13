# Spec: AGENT_RESULT v1

## Problem statement

`AGENT_TASK v1` defines how a Just target hands work to a subagent, but the
return path is still informal. A Just target is a named command that Just
runs for the project, and a subagent is an agent that another agent starts for
one task. A subagent can reply with prose such as `character_count=199`. A
human can read such a reply, but it is weak input for orchestration. The parent
agent is the agent that delegated the task, and it cannot reliably do these
jobs:

- distinguish success, partial completion, blocked work, and execution failure
- extract the produced files
- verify that the required outputs were checked
- record a clean completion note in Gest, a task tracker, without
  reinterpreting free text

The result format should be structured enough for a parent agent or a local
tool to validate. It should still allow concise notes that a human can read.

## Contract

Define `AGENT_RESULT v1` as one primary structured envelope that a subagent
emits after it executes an `AGENT_TASK v1`. An envelope is a block of text
between a start marker and an end marker.

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

The payload is text in the shape of YAML, a text format for data, so that it is
easy to read. The v1 reference checker in the reusable skill repos is a
conservative shell validator, not a complete YAML schema engine. Future
deterministic tooling such as `jagt` may provide deeper schema validation and
still preserve this envelope contract.

## Examples

For work that produces files:

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

For work that was blocked before execution:

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

## Field semantics

Required fields:

- `target`: the task target from the consumed `AGENT_TASK v1`.
- `status`: one of `success`, `partial`, `blocked`, `failed`, or `cancelled`.
- `outputs`: structured outputs that the task produced. Use `{}` only when the
  task produced no outputs.
- `verification`: checks that the subagent performed. Use `[]` only when no
  verification was possible, and explain the reason in `notes` or `error`.
- `follow_up`: remaining work. Use `[]` when there is none.

Recommended fields:

- `task_ref`: an opaque id, hash, target/argv tuple, or packet digest that ties
  the result to the consumed task packet. A packet is a block of text in a fixed
  form, and its digest is a hash of it. The field is recommended, not required,
  until a deterministic renderer can compute stable task digests.
- `notes`: a concise explanation that a human can read.
- `error`: required when `status` is `blocked` or `failed`, and optional
  otherwise.
- `artifacts`: optional richer metadata about artifacts, for when
  `outputs.files` is not enough.

`AGENT_RESULT v1` is a report, not an instruction. It cannot grant permissions,
override higher-priority instructions, or expand the write scope of the
subagent. Text outside the envelope is commentary. Parent agents may ignore it.
Protocol validators should validate only the envelope, unless the caller
explicitly asks for a single-envelope-only check.

## Status semantics

- `success`: all required outputs were produced or all required scalar results
  were reported, and verification passed. A scalar result is a single value,
  such as a count.
- `partial`: some required work was completed, but at least one required output
  or verification item is missing, skipped, or failed. Explain the gap in
  `notes` or `error`.
- `blocked`: the subagent could not make meaningful progress, because required
  input, permission, dependency, user choice, or external state was missing.
- `failed`: the subagent attempted the work and hit an execution failure.
- `cancelled`: a user or orchestrator instruction stopped the work before the
  task reached another terminal state, which is a final status.

When a verification item is a mapping, a set of named fields, its status should
be `passed`, `failed`, or `skipped`. A `success` result should not include
failed or skipped verification for required outputs.

## File outputs

When the task produces files, prefer this form:

```yaml
outputs:
  files:
    - path: reports/eda/index.html
      role: required
```

`path` is relative to the repo, unless a document explicitly says otherwise.
`role` is `required` or `optional`. Omit checksums in v1, unless the task itself
requires them. A parent agent should confirm that the `role: required` files
exist when it has access to the file system. Or it should require the subagent
to include a verification entry that checked them.

## Parent agent responsibilities

When a subagent returns `AGENT_RESULT v1`, the parent agent should:

1. Detect the start and end markers.
2. Validate the required fields and the allowed `status` values.
3. Check that `target` matches the delegated `AGENT_TASK v1`.
4. Confirm that the required outputs are present, or that `blocked`, `failed`,
   or `partial` explains the missing outputs.
5. Incorporate `outputs`, `verification`, and `follow_up` into Gest notes,
   PR summaries, or the handoff to the user.
6. Treat unstructured text outside the result envelope as commentary only.

If the result envelope is missing or invalid, the parent should ask the subagent
to restate the result in `AGENT_RESULT v1` form, or record a protocol failure.

## Subagent responsibilities

A subagent that executes an `AGENT_TASK v1` should:

1. Preserve the task boundary, and not silently merge unrelated work.
2. Verify outputs as the task packet says, where possible.
3. Return exactly one primary `AGENT_RESULT v1` envelope for the delegated task.
4. Use `partial` when it produced some required outputs but not all.
5. Use `blocked` when progress requires missing input, permission, or user
   choice.
6. Use `failed` when it attempted the work and hit an execution failure.
7. Use `cancelled` only when the stop was externally requested, and was not a
   task failure.

Nested agentic tasks should return nested results to their caller. The
top-level parent should summarize nested outputs, and it should not flatten
away the blockers.

## Scope

### In scope

- The syntax of the text envelope, with `<<<AGENT_RESULT v1>>>` markers.
- Required fields, status values, and basic validation rules.
- Guidance on how the parent and the subagent handle a result.
- Examples for scalar output, file output, partial output, and blocked output.
- Reference shell validation in the reusable Git and jj skill repos. jj is a
  version control system.
- Labs for success, partial, blocked, failed, malformed, and target-mismatch
  results.
- Future compatibility with a deterministic validator tool.

### Out of scope

- The behavior of stochastic task proposal, in which a model can propose a
  different task each time. A later `AGENT_TASK_DRAFT v1` spec defines it.
- A requirement that every ordinary agent response use `AGENT_RESULT v1`.
- A binary or JSON-only transport.
- The implementation of the future Rust `jagt` validator in this slice.

## Acceptance criteria

- Both reusable skill repos document `AGENT_RESULT v1` alongside
  `AGENT_TASK v1`.
- The docs state that result envelopes are reports, not instructions.
- Labs cover success, partial, blocked, failed, malformed, required-file, and
  target-mismatch results.
- Reference validators can enforce required fields, allowed statuses, optional
  expected target/status checks, single-envelope count checks, and
  blocked/failed `error:` requirements.
- Parent workflow guidance says how to incorporate outputs, verification, and
  follow-ups into Gest notes and PR handoffs. A PR is a pull request.
- The docs keep `jagt` as a compatible future deterministic validator. It is not
  a prerequisite for the implementation in this reusable skill repo.

## Implementation plan

1. Tighten this spec, and record the v1 decisions that make it ready for
   implementation.
2. In `agent_gest_git_skills`, create a development branch from current
   `main`, add `scripts/validate_agent_result.sh`, add a
   `scripts/run_agent_result_lab.sh` fixture lab, wire `just
   agent-result-lab` and `just test`, and update docs/templates/checks.
3. Verify the Git repo with the focused lab, `just lint`, `just test`, and
   diff hygiene. Then review the diff before porting.
4. In `agent_gest_jj_skills`, port the same contract and lab, and change only
   the workflow wording that is specific to jj.
5. Run parity checks across both repos. Commit and push the Git branch and the
   jj bookmark, and create or update the PRs. Run the PR review, and stop for
   explicit merge approval.

## Deferred questions

- Whether `task_ref` becomes required once deterministic renderers compute
  stable task digests.
- Whether checksums become mandatory for file outputs after a repository has a
  standard policy for artifact hashes.
- Whether a later JSON Schema should supplement the YAML-shaped text envelope.

## References

- `internal_docs/agentic_just_targets_base_spec.md`
- `internal_docs/jagt_deterministic_renderer_spec.md`
- Gest artifact `luuyrvlwtmnyuxkptnsyoolurynkmswr`: Agentic Just Targets Base
  Spec
- Gest task `zspwpzruxmtrkykvxxotxynttyxznurv`: Draft agent task result and
  renderer specs
- Git reusable skills PR #34, the AGENT_TASK v1 implementation
- jj reusable skills PR #20, the AGENT_TASK v1 implementation
- Git/jj clarification PRs #35/#21, on the wording of the target shape, pending
  at drafting time
