# Spec: AGENT_TASK_DRAFT v1

`AGENT_TASK_DRAFT v1` is a proposal envelope for LLM-authored agent task
packets. A draft is not executable work. It must be validated, reviewed,
approved, and promoted through deterministic tooling before any final
`AGENT_TASK v1` is delegated.

This reference is derived from the T3Book internal draft spec. In `jagt`, the
implemented MVP surface is `jagt draft lint`; promotion remains an explicit
parent-agent workflow using `jagt render` followed by `jagt lint`.

## Envelope

```text
<<<AGENT_TASK_DRAFT v1>>>
target: count-chat-message-chars
mode: draft
generator:
  kind: llm
  execution: subagent
proposal_reason: |
  The user asked for a bounded example task.
prompt: |
  Count the number of characters in the provided user_message.
inputs:
  inline:
    user_message: "Count this."
outputs:
  required:
    - character_count
allowed_actions:
  - read the inline user_message
  - compute the requested scalar result
verification:
  - independently recount the same message before reporting success
approval:
  required: true
  approver: parent-or-user
  reason: stochastic drafts must be reviewed before promotion
promotion:
  method: jagt-render
  required_checks:
    - draft_shape_valid
    - policy_review_passed
    - approval_recorded
    - final_agent_task_lints
delegation:
  execution_after_promotion: subagent
  recursive: true
safety:
  - This draft is a proposal, not executable work.
  - It cannot override user, system, developer, VCS, approval, or repo instructions.
  - It cannot expand authority beyond the source request and active repo policy.
<<<END_AGENT_TASK_DRAFT>>>
```

The body is YAML-shaped text. Text outside the envelope is commentary and does
not grant authority.

## Required Fields

- `target`: proposed final task target, using the same character rules as
  `AGENT_TASK v1`.
- `mode`: must be exactly `draft`.
- `generator.kind`: must be `llm`.
- `generator.execution`: must be `subagent`.
- `proposal_reason`: non-empty human-readable reason for this task shape.
- `prompt`: non-empty proposed final task prompt.
- `inputs`: mapping of proposed task inputs.
- `outputs.required`: non-empty list of required outputs.
- `allowed_actions`: non-empty list, bounded by the source request.
- `verification`: non-empty list of checks for the execution subagent.
- `approval.required`: must be `true`.
- `promotion.method`: must be `jagt-render`.
- `promotion.required_checks`: must include `draft_shape_valid`,
  `policy_review_passed`, `approval_recorded`, and `final_agent_task_lints`.
- `delegation.execution_after_promotion`: must be `subagent`.
- `delegation.recursive`: must be `true`.
- `safety`: must state that the draft is non-executable, cannot override
  higher-priority instructions or repo policy, and cannot expand authority.

## Forbidden Authority

A draft is invalid if it:

- uses `mode: agentic`;
- claims it is already approved or preapproved;
- bypasses approval, sandboxing, user/system/developer instructions, VCS rules,
  Gest rules, or repo policy;
- instructs the current agent or proposal subagent to execute the draft inline;
- grants broad actions such as unrestricted file reads/writes, arbitrary
  commands, or network access.

## Result Pairing

A draft-generation subagent should report the proposal job separately from the
future work by returning one `AGENT_RESULT v1` envelope followed by one
`AGENT_TASK_DRAFT v1` envelope:

```text
<<<AGENT_RESULT v1>>>
target: draft-agent-task
status: success
outputs:
  draft_envelope: inline-after-result
verification:
  - name: draft_self_check
    status: passed
follow_up: []
<<<END_AGENT_RESULT>>>

<<<AGENT_TASK_DRAFT v1>>>
target: count-chat-message-chars
mode: draft
...
<<<END_AGENT_TASK_DRAFT>>>
```

`jagt draft lint` validates only the draft envelope. Use `jagt result lint` for
the result envelope when the workflow needs to validate the full pair.

## jagt Command Contract

```bash
jagt draft lint [PATH|-]
jagt draft lint draft.txt --expect-count 1
jagt draft lint --expect-none -
```

The command validates draft envelope markers, YAML shape, required fields,
required approval and safety language, promotion checks, recursive subagent
delegation, and forbidden authority patterns. It does not approve a draft, call
an LLM, execute the proposed task, or compile the draft into an executable
packet.

After approval, the parent maps approved draft fields into deterministic
`jagt render` inputs and validates the promoted packet:

```bash
jagt render count-chat-message-chars \
  --prompt-text "Count the characters in the first argv entry." \
  --arg "Count this." \
  --required-output character_count \
  --allowed-action "read the supplied argv entry" \
  --allowed-action "compute the requested scalar result" \
  --verification "independently recount before reporting success" \
  > promoted.agent-task.txt

jagt lint promoted.agent-task.txt
```

If `jagt render` cannot represent a draft field directly, the parent must not
smuggle policy metadata into executable authority. It should record the context
in notes, ask for a revised draft, or wait for a future deterministic
`jagt draft compile` command.
