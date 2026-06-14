# Live LLM Protocol Playbook Transcript

This transcript is from an actual parent-LLM run of the three protocol cases
using [examples/protocol-playbook/Justfile](examples/protocol-playbook/Justfile).
The parent LLM is this Codex session. `jagt` renders and validates packets; it
does not call an LLM or launch agents. The subagents below were spawned through
the host agent runtime, and their returned envelopes were saved and linted.

The examples are aligned with the reusable Gest Git and Gest JJ labs:

- `agent_gest_git_skills/docs/live_agent_result_recursive_lab.md`
- `agent_gest_jj_skills/docs/live_agent_result_recursive_lab.md`
- `agent_gest_jj_skills/docs/agent_task_draft_workflow.md`

Those labs use the same split: deterministic task/result, recursive
`AGENT_RESULT v1` payloads with `outputs.proposed_tasks`, and stochastic
`AGENT_TASK_DRAFT v1` proposals that must be revised or approved before
promotion.

The shared input file is
[examples/protocol-playbook/user_message.txt](examples/protocol-playbook/user_message.txt):

```text
Count these seven words with wc please.
```

The run was executed after `just build`, with
`JAGT_BIN=../../../target/debug/jagt` from `docs/examples/protocol-playbook/`.
Absolute paths inside captured packet bodies reflect this local checkout at the
time of the run.

## Live Agents

| Case | Subagent | Role | Packet Returned |
| --- | --- | --- | --- |
| Plain task/result | Volta | Word-count worker | `AGENT_RESULT v1` |
| Recursive task | Schrodinger | Planner | `AGENT_RESULT v1` with `outputs.proposed_tasks` |
| Recursive child task | Boyle | Worker | `AGENT_RESULT v1` |
| Stochastic draft | Bacon | Draft designer | `AGENT_RESULT v1` plus `AGENT_TASK_DRAFT v1` |
| Promoted stochastic task | Gauss | Execution worker | `AGENT_RESULT v1` |

## Case 1: Plain Deterministic Task And Result

The Just target emits one executable `AGENT_TASK v1`. The parent LLM validates
it, delegates it, validates the returned result, and reads the scalar payload.

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
This is a valid AGENT_TASK v1 and a subagent boundary. I do not count inline.
I spawn a worker subagent with the parsed packet.
```

Spawned subagent `Volta` returns:

```text
<<<AGENT_RESULT v1>>>
target: count-chat-message-words
status: success
outputs:
  word_count: 7
verification:
  - Recounted whitespace-separated words: Count these seven words with wc please.
notes:
  - Counted the provided message deterministically.
follow_up: []
<<<END_AGENT_RESULT>>>
```

Parent LLM validates:

```bash
jagt result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status success \
  02-plain-subagent-result.agent-result.txt
```

Validation output:

```text
validated 1 AGENT_RESULT block(s)
```

Parent LLM final reading:

```text
The delegated task succeeded. The result is target-matched, success-typed, and
verified. The usable payload is outputs.word_count = 7.
```

## Case 2: Recursive Deterministic Result Payload

This is the recursive case. The Just target still emits an executable parent
`AGENT_TASK v1`, but the planner subagent returns `AGENT_RESULT v1` with
`outputs.proposed_tasks`. That payload can carry the shape of a new
deterministic task. It is not a stochastic draft and it is not executable by
itself.

Parent LLM runs:

```bash
just recursive-task > 03-recursive-parent-task.agent-task.txt
jagt lint --expect-count 1 03-recursive-parent-task.agent-task.txt
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

Validation output:

```text
validated 1 AGENT_TASK block(s)
```

Parent LLM decision:

```text
I spawn a planner subagent. The packet explicitly allows one deterministic
child-task proposal, so I will accept either a final result or a partial
AGENT_RESULT carrying outputs.proposed_tasks.
```

Spawned subagent `Schrodinger` returns:

```text
<<<AGENT_RESULT v1>>>
target: count-chat-message-words
status: partial
outputs:
  proposed_tasks:
    - target: count-chat-message-words-with-wc
      mode: deterministic
      argv:
        - user_message.txt
      tool_hints:
        - command: wc -w
      orchestration:
        mode: parent-orchestrated
      outputs:
        required:
          - word_count
      prompt: |
        Count whitespace-separated words in user_message.txt by running wc -w and report the resulting word_count.
orchestration:
  mode: parent-orchestrated
verification:
  - name: proposed_one_deterministic_child_task
    status: passed
  - name: proposed_task_uses_wc_word_count
    status: passed
  - name: word_count_not_computed_by_planner
    status: passed
notes: |
  Proposed a deterministic child task for the word count instead of computing it in the planner result.
follow_up:
  - Parent orchestrator should execute count-chat-message-words-with-wc and validate the returned AGENT_RESULT v1.
<<<END_AGENT_RESULT>>>
```

Parent LLM validates:

```bash
jagt result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status partial \
  04-planner-subagent-result.agent-result.txt
```

Validation output:

```text
validated 1 AGENT_RESULT block(s)
```

Parent LLM decision:

```text
The result is valid and target-matched. outputs.proposed_tasks is data, not
authority. I inspect it under normal safety rules, accept the bounded wc task,
and render a fresh child AGENT_TASK v1 with jagt.
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

Validation output:

```text
validated 1 AGENT_TASK block(s)
```

Parent LLM decision:

```text
The child AGENT_TASK is valid. I spawn a worker subagent with that packet.
```

Spawned subagent `Boyle` returns:

```text
<<<AGENT_RESULT v1>>>
target: count-chat-message-words-with-wc
status: success
outputs:
  word_count: 7
verification:
  - wc -w docs/examples/protocol-playbook/user_message.txt returned 7.
  - outputs.word_count matches the wc output.
notes:
  - Counted whitespace-separated words from the listed input file.
follow_up: []
<<<END_AGENT_RESULT>>>
```

Parent LLM validates:

```bash
jagt result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words-with-wc \
  --expect-status success \
  06-worker-subagent-result.agent-result.txt
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
        source: planner-subagent:Schrodinger
        status: partial
      - target: count-chat-message-words-with-wc
        source: worker-subagent:Boyle
        status: success
verification:
  - planner AGENT_RESULT validated with expected target and partial status.
  - child AGENT_TASK rendered by parent and validated before delegation.
  - worker AGENT_RESULT validated with expected target and success status.
notes: |
  Parent accepted the deterministic child-task payload from outputs.proposed_tasks,
  rendered the child task with jagt, delegated it, and copied the verified
  word_count into the final result for the original target.
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
only by rendering and validating a new child AGENT_TASK v1.
```

## Case 3: Stochastic Draft Request

This is different from recursion. The Just target does not emit an executable
task. It emits a brief for the parent LLM. The parent asks a proposal subagent
for `AGENT_RESULT v1` plus `AGENT_TASK_DRAFT v1`, validates the draft, rejects
or revises it if needed, and only promotes an approved draft through
deterministic `jagt render`.

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
This is not executable. The task shape is intentionally stochastic, so I spawn
a proposal subagent to design a bounded future task and return an AGENT_RESULT
for the design job plus an AGENT_TASK_DRAFT proposal.
```

Spawned subagent `Bacon` returns the first draft pair:

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
  Proposed a bounded character-count task for a single inline chat message, with
  explicit approval and deterministic promotion requirements.
follow_up: []
<<<END_AGENT_RESULT>>>

<<<AGENT_TASK_DRAFT v1>>>
target: count-chat-message-chars
mode: draft
generator:
  kind: llm
  execution: subagent
proposal_reason: |
  The source request asks for a bounded future task to count characters in one
  specific chat message.
source_request: |
  Design a bounded task for counting characters in a chat message.
assumptions:
  - Count visible Unicode scalar values in the supplied message text.
  - Include spaces and punctuation.
  - Count only the inline user_message value, excluding surrounding quotes.
prompt: |
  Count the number of characters in the provided user_message. Return the
  character_count and state the counting rule used.
inputs:
  inline:
    user_message: "Count the number of characters in this chat message I am sending."
outputs:
  required:
    - character_count
allowed_actions:
  - read the inline user_message
  - compute the requested scalar character count
  - report the character_count and counting rule
verification:
  - independently recount the same inline user_message before reporting success
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
  - It cannot override higher-priority instructions or repo policy.
  - It cannot expand authority beyond the source request and active repo policy.
<<<END_AGENT_TASK_DRAFT>>>
```

Parent LLM validates both envelopes:

```bash
jagt result lint \
  --expect-count 1 \
  --expect-target draft-agent-task \
  --expect-status success \
  09-draft-subagent-result-pair.txt

jagt draft lint --expect-count 1 09-draft-subagent-result-pair.txt
jagt lint --expect-none 09-draft-subagent-result-pair.txt
```

Validation output:

```text
validated 1 AGENT_RESULT block(s)
invalid AGENT_TASK_DRAFT block: block 1 missing non-override safety text
no agent task blocks detected
```

Parent LLM response:

```text
The AGENT_RESULT passed, but the AGENT_TASK_DRAFT failed lint. I do not
promote it. I send the lint failure back to the same proposal subagent and ask
for a corrected draft with explicit non-override safety language.
```

The parent sends `Bacon`:

```text
Parent LLM validation rejected the AGENT_TASK_DRAFT you returned. The
AGENT_RESULT v1 passed, but jagt draft lint failed with: invalid
AGENT_TASK_DRAFT block: block 1 missing non-override safety text.
Return a corrected AGENT_RESULT v1 and AGENT_TASK_DRAFT v1. The draft safety
list must explicitly say it cannot override user, system, developer, VCS,
approval, or repo instructions.
```

`Bacon` returns the corrected pair:

```text
<<<AGENT_RESULT v1>>>
target: draft-agent-task
status: success
outputs:
  draft_envelope: inline-after-result
verification:
  - name: corrected_draft_self_check
    status: passed
notes: |
  Returned a corrected draft after parent lint feedback about missing
  non-override safety text.
follow_up: []
<<<END_AGENT_RESULT>>>

<<<AGENT_TASK_DRAFT v1>>>
target: count-chat-message-chars
mode: draft
generator:
  kind: llm
  execution: subagent
proposal_reason: |
  The source request asks for a bounded future task to count characters in one
  specific chat message.
source_request: |
  Design a bounded task for counting characters in a chat message.
assumptions:
  - Count visible Unicode scalar values in the supplied message text.
  - Include spaces and punctuation.
  - Count only the inline user_message value, excluding surrounding quotes.
prompt: |
  Count the number of characters in the provided user_message. Return the
  character_count and state the counting rule used.
inputs:
  inline:
    user_message: "Count the number of characters in this chat message I am sending."
outputs:
  required:
    - character_count
allowed_actions:
  - read the inline user_message
  - compute the requested scalar character count
  - report the character_count and counting rule
verification:
  - independently recount the same inline user_message before reporting success
approval:
  required: true
  approver: parent-or-user
  reason: stochastic drafts must be reviewed before deterministic promotion
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

Parent LLM validates the corrected pair:

```bash
jagt result lint \
  --expect-count 1 \
  --expect-target draft-agent-task \
  --expect-status success \
  09b-draft-subagent-revised-result-pair.txt

jagt draft lint --expect-count 1 09b-draft-subagent-revised-result-pair.txt
jagt lint --expect-none 09b-draft-subagent-revised-result-pair.txt
```

Validation output:

```text
validated 1 AGENT_RESULT block(s)
validated 1 AGENT_TASK_DRAFT block(s)
no agent task blocks detected
```

Parent LLM decision:

```text
The corrected draft is valid, explicitly requires approval, and is not
executable as AGENT_TASK v1. After parent policy review and approval, I promote
only approved fields through deterministic jagt render.
```

Parent LLM promotes and validates:

```bash
jagt render count-chat-message-chars \
  --no-config \
  --arg "Count the number of characters in this chat message I am sending." \
  --prompt-text "Count the number of characters in the first argv entry. Return the character_count and state what counting rule you used." \
  --required-output character_count \
  --allowed-action "read the supplied argv entry" \
  --allowed-action "compute the requested scalar character count" \
  --verification "independently recount the same message before returning AGENT_RESULT" \
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
  Count the number of characters in the first argv entry. Return the character_count and state what counting rule you used.
inputs:
  files: []
outputs:
  required:
    - character_count
allowed_actions:
  - read the supplied argv entry
  - compute the requested scalar character count
verification:
  - independently recount the same message before returning AGENT_RESULT
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
The promoted AGENT_TASK is valid. Now, and only now, I spawn an execution
subagent for the character-count task.
```

Spawned subagent `Gauss` returns:

```text
<<<AGENT_RESULT v1>>>
target: count-chat-message-chars
status: success
outputs:
  character_count: 65
verification:
  - name: independent_recount
    status: passed
notes: |
  Counting rule: counted Unicode scalar characters in the first argv entry, including spaces and punctuation, excluding surrounding YAML/list syntax and any newline.
follow_up: []
<<<END_AGENT_RESULT>>>
```

Parent LLM validates:

```bash
jagt result lint \
  --expect-count 1 \
  --expect-target count-chat-message-chars \
  --expect-status success \
  11-promoted-worker-result.agent-result.txt
```

Validation output:

```text
validated 1 AGENT_RESULT block(s)
```

Parent LLM final reading:

```text
This was stochastic drafting, not recursion. The draft was generated by an LLM
proposal subagent and stayed non-executable until the parent validated it,
rejected the first invalid draft, received a corrected draft, approved the
bounded proposal, promoted it through deterministic jagt render, validated the
promoted AGENT_TASK v1, and delegated that promoted task to a different
execution subagent.
```
