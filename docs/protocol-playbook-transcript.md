# LLM Protocol Playbook Transcript

This is a concrete run of the three protocol cases using the example Justfile
in [examples/protocol-playbook/Justfile](examples/protocol-playbook/Justfile).
The LLM in the transcript is the parent agent: it runs the targets, validates
packets with `jagt`, delegates role-played subagents, and decides the next
step.

The shared input file is
[examples/protocol-playbook/user_message.txt](examples/protocol-playbook/user_message.txt):

```text
Count these seven words with wc please.
```

The run below was executed after `just build`, with
`JAGT_BIN=../../../target/debug/jagt` from `docs/examples/protocol-playbook/`.

## Case 1: Plain Deterministic Task And Result

Here the Just target emits a final executable `AGENT_TASK v1`. The parent LLM
does not do the count inline. It validates the packet, delegates it, validates
the returned result, then records the scalar output.

Parent LLM runs:

```bash
just plain-task > 01-plain-task.agent-task.txt
jagt lint --expect-count 1 01-plain-task.agent-task.txt
```

Target output:

```text
<<<AGENT_TASK v1>>>
target: count-chat-message-words
mode: agentic
argv:
  - inline:user-message
  - user_message.txt
prompt: |
  Count whitespace-separated words in user_message.txt and return outputs.word_count.
inputs:
  files:
    - user_message.txt
outputs:
  required:
    - word_count
allowed_actions:
  - read listed user_message.txt input
  - compute a deterministic word count
verification:
  - recount the message before returning AGENT_RESULT
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
<<<END_AGENT_TASK>>>
```

Validation output:

```text
validated 1 AGENT_TASK block(s)
```

Parent LLM decision:

```text
I see a valid AGENT_TASK v1. This is a subagent boundary, so I do not count
the words inline. I delegate the parsed task to a word-count subagent.
```

Role-played word-count subagent returns:

```text
<<<AGENT_RESULT v1>>>
target: count-chat-message-words
status: success
outputs:
  word_count: 7
verification:
  - name: deterministic_wc
    command: wc -w < user_message.txt
    status: passed
notes: |
  I counted the words in user_message.txt using wc -w.
follow_up: []
<<<END_AGENT_RESULT>>>
```

Parent LLM validates:

```bash
jagt result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status success \
  02-plain-result.agent-result.txt
```

Validation output:

```text
validated 1 AGENT_RESULT block(s)
```

Parent LLM final reading:

```text
The delegated task succeeded. The report is target-matched, success-typed, and
verified. The usable payload is outputs.word_count = 7.
```

## Case 2: Recursive Deterministic Result Payload

This is the recursive case. The first Just target still emits an executable
`AGENT_TASK v1`, but the planner subagent returns a result whose payload
contains `outputs.proposed_tasks`. That payload is not stochastic draft
syntax. It is a deterministic recursive proposal carried by `AGENT_RESULT v1`.

Parent LLM runs:

```bash
just recursive-task > 03-recursive-parent-task.agent-task.txt
jagt lint --expect-count 1 03-recursive-parent-task.agent-task.txt
```

Validation output:

```text
validated 1 AGENT_TASK block(s)
```

Target output:

```text
<<<AGENT_TASK v1>>>
target: count-chat-message-words
mode: agentic
argv:
  - inline:user-message
  - user_message.txt
prompt: |
  Count whitespace-separated words in user_message.txt. If a deterministic child task is more appropriate, return status: partial with outputs.proposed_tasks instead of computing the count.
inputs:
  files:
    - user_message.txt
outputs:
  required:
    - word_count
allowed_actions:
  - read listed user_message.txt input
  - propose one deterministic child task
verification:
  - validate any returned AGENT_RESULT before continuing
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
<<<END_AGENT_TASK>>>
```

Parent LLM decision:

```text
I delegate this parent task to a planner subagent. The packet explicitly allows
one deterministic child-task proposal, so I will accept either a final result
or a partial AGENT_RESULT carrying outputs.proposed_tasks.
```

Role-played planner subagent returns:

```text
<<<AGENT_RESULT v1>>>
target: count-chat-message-words
status: partial
outputs:
  proposed_tasks:
    - target: count-chat-message-words-with-wc
      reason: Use deterministic Unix word count instead of model counting.
      prompt: |
        Run wc -w on the exact message in user_message.txt and report
        outputs.word_count.
      inputs:
        files:
          - user_message.txt
      outputs:
        required:
          - word_count
      tool_hints:
        - command: wc -w
          stdin_ref: user_message.txt
      orchestration:
        mode: parent-orchestrated
verification:
  - name: method_selected
    status: passed
notes: |
  I did not compute the count. I selected a deterministic child task.
follow_up:
  - Parent may render and delegate the proposed child task.
<<<END_AGENT_RESULT>>>
```

Parent LLM validates:

```bash
jagt result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status partial \
  04-planner-result.agent-result.txt
```

Validation output:

```text
validated 1 AGENT_RESULT block(s)
```

Parent LLM decision:

```text
The result is valid and target-matched. Because outputs.proposed_tasks is data,
not executable authority, I inspect it under normal safety rules. The proposed
child target is bounded, deterministic, and limited to wc -w on the listed
input. I will render a fresh child AGENT_TASK v1 with jagt.
```

Parent LLM renders and validates the child task:

```bash
jagt render count-chat-message-words-with-wc \
  --no-config \
  --arg inline:user-message \
  --input docs/examples/protocol-playbook/user_message.txt \
  --prompt-text "Run wc -w on the exact message in user_message.txt and report outputs.word_count." \
  --required-output word_count \
  --allowed-action "read listed user_message.txt input" \
  --allowed-action "run wc -w for deterministic word count" \
  --verification "compare wc output to outputs.word_count before returning AGENT_RESULT" \
  > 05-child-task.agent-task.txt

jagt lint --expect-count 1 05-child-task.agent-task.txt
```

Validation output:

```text
validated 1 AGENT_TASK block(s)
```

Rendered child packet:

```text
<<<AGENT_TASK v1>>>
target: count-chat-message-words-with-wc
mode: agentic
argv:
  - inline:user-message
  - /Users/rahul/Projects/jagt/docs/examples/protocol-playbook/user_message.txt
prompt: |
  Run wc -w on the exact message in user_message.txt and report outputs.word_count.
inputs:
  files:
    - /Users/rahul/Projects/jagt/docs/examples/protocol-playbook/user_message.txt
outputs:
  required:
    - word_count
allowed_actions:
  - read listed user_message.txt input
  - run wc -w for deterministic word count
verification:
  - compare wc output to outputs.word_count before returning AGENT_RESULT
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
<<<END_AGENT_TASK>>>
```

Parent LLM decision:

```text
The child AGENT_TASK is valid. I delegate it to a worker subagent.
```

Role-played worker subagent returns:

```text
<<<AGENT_RESULT v1>>>
target: count-chat-message-words-with-wc
status: success
outputs:
  word_count: 7
verification:
  - name: deterministic_wc
    command: wc -w < user_message.txt
    status: passed
notes: |
  Worker used wc -w on the delegated input file.
follow_up: []
<<<END_AGENT_RESULT>>>
```

Parent LLM validates:

```bash
jagt result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words-with-wc \
  --expect-status success \
  06-worker-result.agent-result.txt
```

Validation output:

```text
validated 1 AGENT_RESULT block(s)
```

Parent LLM records and validates the final result for the original target:

```text
<<<AGENT_RESULT v1>>>
target: count-chat-message-words
status: success
outputs:
  word_count: 7
  recursion_trace:
    mode: parent-orchestrated
    tasks:
      - target: count-chat-message-words
        source: planner-subagent
        status: partial
      - target: count-chat-message-words-with-wc
        source: worker-subagent
        status: success
verification:
  - name: planner_result_validated
    status: passed
  - name: worker_result_validated
    status: passed
notes: |
  Parent accepted a proposed deterministic child task, rendered it with jagt,
  delegated it to a worker, and copied the verified word_count into the final
  result for the original target.
follow_up: []
<<<END_AGENT_RESULT>>>
```

```bash
jagt result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status success \
  07-parent-final.agent-result.txt
```

Validation output:

```text
validated 1 AGENT_RESULT block(s)
```

Parent LLM final reading:

```text
This was recursion, not stochastic drafting. The recursive payload traveled
inside AGENT_RESULT v1 as outputs.proposed_tasks. The parent made it executable
only by rendering a new child AGENT_TASK v1 and validating that child packet.
```

## Case 3: Stochastic Draft Request

This case is different from recursion. No deterministic target emits an
executable task for the unknown work. The Just target emits only a brief for the
parent LLM. The parent LLM starts a draft-design subagent, validates the
returned `AGENT_TASK_DRAFT v1`, records approval, promotes approved fields with
`jagt render`, and only then delegates the promoted task.

Parent LLM runs:

```bash
just draft-brief > 08-draft-brief.txt
jagt lint --expect-none 08-draft-brief.txt
```

Brief output:

```text
source_request: Design a bounded task for counting characters in a chat message.
task_shape: unknown until the proposal subagent reasons about assumptions and verification.
expected_parent_action: ask a proposal subagent for AGENT_RESULT v1 plus AGENT_TASK_DRAFT v1.
```

Validation output:

```text
no agent task blocks detected
```

Parent LLM decision:

```text
This is not an executable AGENT_TASK. The task shape is intentionally unknown,
so I ask a proposal subagent to design a bounded future task and return both an
AGENT_RESULT v1 for the design job and an AGENT_TASK_DRAFT v1 proposal.
```

Role-played proposal subagent returns:

```text
<<<AGENT_RESULT v1>>>
target: draft-agent-task
status: success
outputs:
  draft_envelope: inline-after-result
verification:
  - name: draft_self_check
    status: passed
notes: |
  Proposed a bounded character-count task with explicit approval and promotion
  requirements.
follow_up: []
<<<END_AGENT_RESULT>>>

<<<AGENT_TASK_DRAFT v1>>>
target: count-chat-message-chars
mode: draft
generator:
  kind: llm
  execution: subagent
proposal_reason: |
  The user asked for a bounded example task that counts the characters in a
  single chat message.
source_request: |
  Count the number of characters in this chat message I am sending.
assumptions:
  - Count visible Unicode scalar values in the supplied message text.
  - Include spaces and punctuation.
argv:
  - Count the number of characters in this chat message I am sending.
prompt: |
  Count the number of characters in the provided user_message. Return the count
  and state what counting rule you used.
inputs:
  inline:
    user_message: "Count the number of characters in this chat message I am sending."
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

Parent LLM validates both envelopes:

```bash
jagt result lint \
  --expect-count 1 \
  --expect-target draft-agent-task \
  --expect-status success \
  09-draft-result-pair.txt

jagt draft lint --expect-count 1 09-draft-result-pair.txt
jagt lint --expect-none 09-draft-result-pair.txt
```

Validation output:

```text
validated 1 AGENT_RESULT block(s)
validated 1 AGENT_TASK_DRAFT block(s)
no agent task blocks detected
```

Parent LLM decision:

```text
The result says the draft-design job succeeded. The draft is valid, explicitly
requires approval, and is not executable as AGENT_TASK v1. After policy review
and approval, I promote only approved fields through deterministic jagt render.
```

Parent LLM promotes and validates:

```bash
jagt render count-chat-message-chars \
  --no-config \
  --arg "Count the number of characters in this chat message I am sending." \
  --prompt-text "Count the number of characters in the first argv entry. Return the count and state what counting rule you used." \
  --required-output character_count \
  --allowed-action "read the supplied argv entry" \
  --allowed-action "compute the requested scalar result" \
  --verification "independently recount the same message before reporting success" \
  > 10-promoted-draft.agent-task.txt

jagt lint --expect-count 1 10-promoted-draft.agent-task.txt
```

Promoted task:

```text
<<<AGENT_TASK v1>>>
target: count-chat-message-chars
mode: agentic
argv:
  - Count the number of characters in this chat message I am sending.
prompt: |
  Count the number of characters in the first argv entry. Return the count and state what counting rule you used.
inputs:
  files: []
outputs:
  required:
    - character_count
allowed_actions:
  - read the supplied argv entry
  - compute the requested scalar result
verification:
  - independently recount the same message before reporting success
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
<<<END_AGENT_TASK>>>
```

Parent LLM final reading:

```text
This was stochastic drafting, not recursion. The draft was generated by an LLM
proposal subagent and stayed non-executable until the parent validated it,
approved it, promoted it through deterministic jagt render, validated the
promoted AGENT_TASK v1, and only then delegated the promoted task to an
execution subagent.
```
