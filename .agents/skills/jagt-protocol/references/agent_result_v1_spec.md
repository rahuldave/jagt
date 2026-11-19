# Spec of AGENT_RESULT v1

This page is the canonical spec of `AGENT_RESULT v1`. It ships with the
jagt-protocol skill of jnterfaces. The jagt repository keeps
[a copy](https://github.com/rahuldave/jagt/blob/main/docs/reference/agent_result_v1_spec.md).
If the two differ, this page wins.

The page agrees with
[the contract of the agentic packets](protocol_contract.md). The contract
gives the whole protocol. This page gives the details of the result packet.

The rules for a check describe what `jagt result lint` of jagt 0.6.0 does.
Earlier versions miss some of these checks. jagt 0.5.0
passes a symbolic link that leads out of the base folder, and a file with a
second hard link. jagt 0.3.0 and 0.4.0 also pass a YAML merge key, and 0.3.0
passes a path with a `..` part.

## Terms

The page uses these terms:

| Term | Meaning |
|---|---|
| Packet | A block of text between a start marker line and an end marker line. Older text calls it an envelope. |
| Task packet | An `AGENT_TASK v1` packet. A parent agent gives it to a subagent. |
| Result packet | An `AGENT_RESULT v1` packet. The subagent returns it to the parent. |
| Parent | The agent that gives a task packet to a subagent. |
| Subagent | The agent that runs the task and returns the result packet. |
| Nonce | A random value of 32 lowercase hex digits. The first digit is a letter from `a` to `f`. |
| Gest | A task tracker that agents use. |

## The problem

A task packet tells a Just recipe how to hand work to a subagent. The return
path needs a form too. A subagent can reply in prose, such as
`character_count=199`. A person can read that reply, but a parent cannot use
it well.

From prose, a parent cannot tell success from partial work, blocked work or a
failure. It cannot find the files that the subagent made. It cannot see
whether the subagent checked the required outputs. It also cannot write a
clean Gest note without a new reading of the free text.

So a result has a fixed form. A parent or a tool can check the form, and the
packet can still hold short notes for a person.

## The packet

A subagent that runs an `AGENT_TASK v1` returns one result packet:

```text
<<<AGENT_RESULT v1>>>
target: count-chat-message-chars
nonce: d5a8c0e4f1b2937a6c4e8d0b2f7a9c31
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

The start line and the end line must each be a whole line, with no spaces
before or after the marker. The text between them is YAML, and it must be a
mapping.

## Examples

### File outputs

```text
<<<AGENT_RESULT v1>>>
target: eda-viz
nonce: d5a8c0e4f1b2937a6c4e8d0b2f7a9c31
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

### Partial work

The subagent made one file, and a missing tool stopped the rest. The result is
`partial`, so the subagent adds an `error` that names the stop:

```text
<<<AGENT_RESULT v1>>>
target: eda-viz
nonce: d5a8c0e4f1b2937a6c4e8d0b2f7a9c31
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

### Blocked work

The subagent could not start, because an input was missing:

```text
<<<AGENT_RESULT v1>>>
target: eda-viz
nonce: d5a8c0e4f1b2937a6c4e8d0b2f7a9c31
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

## Fields

### Required fields

Each result must have these fields:

- **`target`** names the recipe of the task packet. It holds only ASCII
  letters, digits, `_`, `.` and `-`.
- **`status`** is `success`, `partial`, `blocked`, `failed` or `cancelled`.
- **`outputs`** is a mapping of what the task made. Use `{}` only when the
  task made no output.
- **`verification`** is a list of the checks that the subagent ran. Use `[]`
  only when no check was possible, and say why in `notes` or `error`.
- **`follow_up`** is a list of the work that is left. Use `[]` when no work is
  left.

Two fields are required only in some cases:

- **`nonce`** is required when the task packet has a `nonce` field. The
  subagent copies it exactly into the top level of the result.
- **`error`** is required when `status` is `blocked` or `failed`. It is a
  mapping with a `code` and a `message`. Each of them is a string that is not
  blank.

### Optional fields

A result can also have these fields:

- **`error`** for any other status, in the same form. A `partial` result
  should have one when a block or a failure stopped the rest of the work.
  `jagt result lint` checks `error` only for `blocked` and `failed`.
- **`task_ref`** ties the result to its task, for example with an id or a
  hash. The `nonce` does that job when the task packet has one.
- **`notes`** is a short explanation for a person.
- **`artifacts`** holds more details about the output files, when
  `outputs.files` does not hold enough.

### Fields that a result must not have

A result reports. It gives no orders. It cannot grant a permission, override
a rule of higher priority or widen what the subagent can write. So a result
must not have the fields `allowed_actions`, `delegation` or `safety`. Those
fields belong to a task packet.

## Statuses

Choose the status by what happened:

- **`success`** means that the task made each required output or reported
  each required value, and each check passed.
- **`partial`** means that the subagent made some output, but at least one
  required output or check is missing, was skipped or failed. Say what is
  missing in `notes` or `error`.
- **`blocked`** means that the subagent made no output. A missing input,
  permission, dependency, choice of the user or outside state stopped it.
- **`failed`** means that the subagent tried the work, hit a failure and made
  no output.
- **`cancelled`** means that the user or the parent stopped the work before it
  reached another status.

### Partial, blocked or failed

Sometimes the subagent makes some output, and then the rest waits for an
input or a permission, or hits a failure. Then `partial` wins over `blocked`
and `failed`. Use `blocked` or `failed` only when the subagent made no
output, so that its `outputs` is `{}`. `jagt result lint` does not check
this rule.

A `partial` result that stopped on a block or a failure should have an
`error` with a `code` and a `message`. The code names the cause, for example
`missing_input` or `needs_permission`. Put the step that clears it in
`follow_up`. `jagt result lint` does not ask for an `error` in a `partial`
result, so a `partial` result without one still passes.

A `partial` result that hands the rest of the work back in
`outputs.proposed_tasks` needs no `error`. The proposal is the next step, and
nothing stopped the subagent.

### Checks in `verification`

An item of `verification` is usually a mapping. When the item has a `status`,
the status is `passed`, `failed` or `skipped`. A `success` result must not
hold any item with the status `failed` or `skipped`.

## File outputs

When the task makes files, list them in `outputs.files`:

```yaml
outputs:
  files:
    - path: reports/eda/index.html
      role: required
```

`outputs.files` is a list of mappings, and each mapping has a `path`. Each
`path` is relative to the root of the repository. It must not be an absolute
path, and it must not hold a `..` part. The `role` is `required` or
`optional`. A file without a `role` counts as `optional`.

A listed file that exists must stay inside the base folder, also through a
symbolic link. On Unix, it must have one hard link only. `jagt result lint`
checks these rules only with `--check-files`.

In v1, leave out checksums. Add them only when the task asks for them.

If the parent can read the files, it checks that each required file exists.
If not, it asks for an item of `verification` that checked them.

## What `jagt result lint` checks

`jagt result lint [FILE]` reads a text, such as the reply of a subagent. With
no file, or with `-`, it reads standard input.

### The default check

By default, the command checks each result packet in the text. It finds at
least one packet, and it checks every packet that it finds. It does these
checks:

- **Markers:** the text has one or more packets. A start line with no end
  line, an end line with no start line, or a start line inside a packet fails.
- **YAML:** the body is valid YAML and a mapping, for both YAML readers of
  jagt. A repeated key fails. A `<<` key or value, a `!!merge` tag, a tagged
  key or an alias key fails too.
- **Line breaks:** a raw U+0085, U+2028 or U+2029 fails. Write such a
  character escaped, in double quotes.
- **Fields:** the required fields are there, with the forms that the section
  "Fields" gives. The fields `allowed_actions`, `delegation` and `safety` fail.
- **Status:** the status is a known one. A `success` result holds no failed
  or skipped check.
- **Error:** a `blocked` or `failed` result has an `error` with a `code` and a
  `message`.

The default check ignores the text outside the packets. The one exception is
a line that is exactly a marker, because it opens or closes a packet. A
parent can treat the other text as comment, or ignore it.

### Options that add checks

These options add checks to the default check:

- **`--expect-count N`** asks for exactly `N` packets, and `N` is 1 or more.
  Use `--expect-count 1` to check that the reply holds exactly one packet. It
  still ignores the text outside the packet.
- **`--expect-none`** asks for no packet. The check then fails on any marker
  line, and checks nothing else.
- **`--expect-target T`** asks that each packet names the target `T`.
- **`--expect-status S`** asks that each packet has the status `S`.
- **`--expect-nonce N`** asks that each packet holds the top-level field
  `nonce` with the value `N`. A missing nonce or another nonce fails. `N`
  must be a nonce, as the section "Terms" defines it.
- **`--check-files`** checks `outputs.files` by the rules of the section
  "File outputs". Each required file must exist and be a file. A missing
  required file fails as missing. A missing optional file, or an optional link
  whose target is missing, is not checked further.
  - **A symbolic link.** The check follows it, but a listed file that exists
    must have its real path inside the real base folder. So a link that leads
    out of the base folder fails, for a required or an optional file.
  - **A hard link.** On Unix, a listed file that exists and has more than one
    hard link fails. A hard link has no real path of its own, so a second link
    can name a file outside the base folder.
  - **Older versions.** jagt 0.5.0 and earlier pass both kinds of link.
- **`--base-dir D`** works with `--check-files`. It gives the folder that the
  file paths are relative to. Its default is the current folder, so run the
  check from the root of the repository, or pass the root as `D`.

Except for marker lines, no option fails a reply because of the text outside
the packets.

### The nonce

In a git worktree, and without `--no-save`, `jagt render` puts a nonce in
each task packet. The nonce
is in the top-level field `nonce:`. The field `result_rules` of the packet
asks the subagent to return it.

The subagent copies the `nonce` of its task packet, exactly, into the top
level of its result. A result without the nonce of its packet is not valid.
Check it with
`jagt result lint --expect-target <target> --expect-nonce <nonce>`. The lint
fails when the result holds no nonce or another nonce. A YAML mapping cannot
hold a key twice, so two `nonce` fields fail too.

Without `--expect-nonce`, the command does not check the `nonce` field. With
it, a `nonce` that is not a string, such as `12345`, counts as missing.

## What the parent does

When a subagent returns a result, the parent does these steps:

1. Find the start and end lines of the packet.
2. Check the packet with `jagt result lint`. Add `--expect-target`, and
   `--expect-nonce` when the task packet has a nonce.
3. Check that `target` is the target of the task that it gave.
4. Check that each required output is there. If one is missing, check that
   the status is `partial`, `blocked`, `failed` or `cancelled`. Check also
   that the result says why.
5. Copy `outputs`, `verification` and `follow_up` into the Gest notes, the
   pull request or the report to the user.
6. Treat the text outside the packet as comment only.

If the result is missing or not valid, the parent asks the subagent to give
the result again as `AGENT_RESULT v1`. Otherwise it records a protocol
failure.

## What the subagent does

A subagent that runs an `AGENT_TASK v1` does these things:

1. It keeps to the task, and does not join other work to it.
2. It checks the outputs as the task packet says, where it can.
3. It returns exactly one result packet for the task.
4. It copies the `nonce` of the task packet into the result.
5. It uses `partial` when it made some output but not all required outputs.
6. It uses `blocked` when it made no output, because it needs an input, a
   permission, a dependency, a choice of the user or outside state.
7. It uses `failed` when it tried the work, hit a failure and made no output.
8. It uses `cancelled` only when someone else asked it to stop. A failure of
   the task is never `cancelled`.

A nested task returns its result to its caller. The parent at the top sums up
the nested outputs. It keeps in the summary each `blocked` status and each
`error` of a nested result.

## Scope

The spec covers these things:

- the form of the packet, with the markers `<<<AGENT_RESULT v1>>>` and
  `<<<END_AGENT_RESULT>>>`
- the fields, the statuses and the rules of the check
- what the parent and the subagent do
- examples of a value, of files, of partial work and of blocked work

The spec does not cover these things:

- task drafts that a model writes, which the contract describes as
  `AGENT_TASK_DRAFT v1`
- a rule that every reply of an agent must be a result packet
- a form for binary data or for JSON only

## Open questions

- **Task reference:** should `task_ref` become required? The `nonce` already
  ties a result to the packet file of its task.
- **Checksums:** should file outputs need checksums once a repository has a
  rule for the hashes of its files?
- **JSON Schema:** should a JSON Schema join the YAML form?

## References

- [The contract of the agentic packets](protocol_contract.md), in this skill.
- [The base spec of agentic Just targets](https://github.com/rahuldave/jagt/blob/main/docs/reference/agentic_just_targets_base_spec.md),
  in the jagt repository.
- [The spec of the deterministic renderer](https://github.com/rahuldave/jagt/blob/main/jagt_deterministic_renderer_spec.md),
  in the jagt repository.
- [The packet file and the nonce](https://github.com/rahuldave/jagt/blob/main/docs/packet-file.md),
  in the jagt docs.
- [The first contract of agentic Just targets](https://github.com/rahuldave/agent_gest_git_skills/pull/34),
  pull request 34 of agent_gest_git_skills.
- [The same contract for jj](https://github.com/rahuldave/agent_gest_jj_skills/pull/20),
  pull request 20 of agent_gest_jj_skills.
