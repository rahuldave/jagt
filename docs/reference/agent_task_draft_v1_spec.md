# Spec: AGENT_TASK_DRAFT v1

`AGENT_TASK_DRAFT v1` is a proposal envelope for agent task packets that an LLM
(a large language model) writes. An envelope is a block of text between a start
marker and an end marker, and a packet is such a block in a fixed form. A draft
is not executable work. Before any final `AGENT_TASK v1` is delegated, the draft
must be validated, reviewed, approved, and promoted through deterministic
tooling.

The reference is derived from the internal draft spec of T3Book. In `jagt`, the
implemented surface of the MVP (minimum viable product) is `jagt draft lint`.
Promotion turns an approved draft into a final `AGENT_TASK v1` packet. It
remains an explicit workflow of the parent agent, the agent that delegates the
task, which runs `jagt render` and then `jagt lint`.

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

The body is text in the shape of YAML, a text format for data. Text outside the
envelope is commentary, and it does not grant authority.

## Required fields

- `target`: proposed final task target, with the same character rules as
  `AGENT_TASK v1`.
- `mode`: must be exactly `draft`.
- `generator.kind`: must be `llm`.
- `generator.execution`: must be `subagent`. A subagent is an agent that
  another agent starts for one task.
- `proposal_reason`: non-empty reason for this task shape, which a human can
  read.
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

## Forbidden authority

A draft is invalid if it does any of these things:

- It uses `mode: agentic`.
- It claims that it is already approved or preapproved.
- It bypasses approval, sandboxing, user/system/developer instructions, VCS
  rules, Gest rules, or repo policy. VCS is the version control system, and
  Gest is a task tracker.
- It instructs the current agent or the proposal subagent to execute the draft
  inline, in its own run.
- It grants broad actions, such as unrestricted file reads and writes,
  arbitrary commands, or network access.

## Result pairing

A subagent that generates a draft should report the proposal job separately
from the future work. To do so, it should return one `AGENT_RESULT v1` envelope
followed by one `AGENT_TASK_DRAFT v1` envelope:

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

`jagt draft lint` validates only the draft envelope. When the workflow needs to
validate the full pair, use `jagt result lint` for the result envelope.

## jagt command contract

```bash
jagt draft lint [PATH|-]
jagt draft lint draft.txt --expect-count 1
jagt draft lint --expect-none -
```

The command validates these parts of a draft:

- the markers of the draft envelope
- the YAML shape
- the required fields
- the required approval and safety language
- the promotion checks
- the recursive delegation to a subagent
- the patterns of forbidden authority

It does not approve a draft, call an LLM, execute the proposed task, or compile
the draft into an executable packet.

After approval, the parent maps the approved draft fields into deterministic
`jagt render` inputs, and it validates the promoted packet:

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
