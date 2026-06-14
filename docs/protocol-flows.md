# jagt Protocol Flows

This guide explains how the packet formats fit together as an agent workflow.
It is intentionally written as a conversation between Just output, the parent
LLM, subagents, and `jagt`.

`jagt` is deterministic. It renders and validates packet text. It does not call
an LLM, choose whether work is safe, approve stochastic proposals, or launch
subagents. Those choices belong to the parent agent under the active user,
system, developer, approval, VCS, and repository instructions.

The flow map here is aligned with Gest Git (`agent_gest_git_skills`) and Gest
jj (`agent_gest_jj_skills`), including their agentic target, result, recursive
result, and task-draft labs. The jagt repository keeps its own standalone demos
under `.agents/skills/jagt-protocol/` and `integration_tests/`.

## Packet Vocabulary

| Packet | Produced by | Consumed by | Meaning |
| --- | --- | --- | --- |
| `AGENT_TASK v1` | `jagt render`, a Just target, or a deterministic renderer script | Parent agent, then an execution subagent | Executable subagent handoff. Validate before delegation. |
| `AGENT_RESULT v1` | A subagent | Parent agent | Report-only return value for one delegated task. Validate before trusting it. |
| `AGENT_TASK_DRAFT v1` | A proposal subagent | Parent agent | Non-executable stochastic task proposal. Validate, review, approve, and promote before execution. |

The key distinction is authority:

- `AGENT_TASK v1` describes bounded work to delegate.
- `AGENT_RESULT v1` reports what happened.
- `AGENT_TASK_DRAFT v1` proposes a future task shape.
- None of them can override higher-priority instructions or repo policy.

## Flow 1: Deterministic Task Handoff

Use this flow when the task is already known well enough to render directly:
the target name, prompt, inputs, required outputs, allowed actions, and
verification are all concrete.

```text
Parent agent
  runs Just target
Just target
  calls jagt render
stdout
  contains AGENT_TASK v1
Parent agent
  validates packet with jagt lint
Parent agent
  delegates parsed packet to a subagent
Subagent
  performs only the delegated task
```

Example render command:

```bash
jagt render count-chat-message-words \
  --no-config \
  --arg inline:user-message \
  --input user_message.txt \
  --prompt-text "Count whitespace-separated words in user_message.txt and return outputs.word_count." \
  --required-output word_count \
  --allowed-action "read listed user_message.txt input" \
  --allowed-action "compute a deterministic word count" \
  --verification "recount the message before returning AGENT_RESULT"
```

The parent should validate:

```bash
jagt lint --expect-count 1 packet.agent-task.txt
```

Then it delegates. It must not execute the requested work inline just because
the packet appeared in a terminal output stream.

### Just Target Shapes

Gest Git and Gest jj use three equivalent target shapes, and `jagt` supports all
of them because it only cares about the emitted packet. In a real target, prefer
a small renderer wrapper so arguments are escaped and repeated flags are
constructed safely:

```just
# Direct agentic target.
eda-viz +FILES:
  @scripts/render_agent_task.sh --target eda-viz --files {{FILES}}

# Companion target next to a concrete target.
eda-viz +FILES:
  uv run python scripts/eda_viz.py {{FILES}}

eda-viz-agentic +FILES:
  @scripts/render_agent_task.sh --target eda-viz --files {{FILES}}

# Generic dispatcher.
agentic TARGET +ARGS:
  @scripts/render_agent_task.sh --target {{TARGET}} --args {{ARGS}}
```

Use direct targets when the command is agentic by default, companion targets
when concrete and exploratory paths coexist, and a dispatcher when many targets
share one packet surface.

## Flow 2: Result Return

Every delegated task needs a structured return path. The subagent returns one
primary `AGENT_RESULT v1` envelope for the task it consumed.

```text
Subagent
  writes AGENT_RESULT v1
Parent agent
  validates result with jagt result lint
Parent agent
  compares target/status to the delegated task
Parent agent
  folds outputs, verification, and follow_up into Gest notes, PR summaries, or user handoff
```

Example result:

```text
<<<AGENT_RESULT v1>>>
target: count-chat-message-words
status: success
outputs:
  word_count: 14
verification:
  - name: deterministic_wc
    command: wc -w < user_message.txt
    status: passed
notes: |
  Counted whitespace-separated words in the exact input message.
follow_up: []
<<<END_AGENT_RESULT>>>
```

The parent validates with expected target and status when it knows them:

```bash
jagt result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status success \
  result.agent-result.txt
```

For file-producing results, the parent can also check required files:

```bash
jagt result lint \
  --expect-target eda-viz \
  --expect-status success \
  --check-files \
  --base-dir . \
  result.agent-result.txt
```

Result envelopes are reports. They cannot grant permission, request unrelated
edits, expand write scope, bypass approvals, or override VCS guardrails. If a
result contains task-like instruction fields such as `allowed_actions`, jagt
rejects it.

## Flow 3: Recursive Deterministic Work

Recursive work is parent-orchestrated. A subagent can propose a child task, but
the parent decides whether to render and delegate that child.

```text
Parent agent
  delegates parent AGENT_TASK v1 to planner subagent
Planner subagent
  returns AGENT_RESULT v1 with status: partial and outputs.proposed_tasks
Parent agent
  validates planner result
Parent agent
  reviews proposed task against policy and approval rules
Parent agent
  renders approved child task with jagt render
Parent agent
  validates child AGENT_TASK v1 with jagt lint
Parent agent
  delegates child task to worker subagent
Worker subagent
  returns AGENT_RESULT v1
Parent agent
  validates worker result and writes final parent result with recursion_trace
```

A planner result can look like this:

```text
<<<AGENT_RESULT v1>>>
target: count-chat-message-words
status: partial
outputs:
  proposed_tasks:
    - target: count-chat-message-words-with-wc
      reason: Use deterministic Unix word count instead of model counting.
      prompt: |
        Run wc -w on the exact message and report outputs.word_count.
      tool_hints:
        - command: wc -w
      orchestration:
        mode: parent-orchestrated
verification:
  - name: method_selected
    status: passed
notes: |
  I did not compute the count. I selected a deterministic child task.
follow_up:
  - Parent may spawn the proposed task after policy review.
<<<END_AGENT_RESULT>>>
```

Important boundaries:

- `outputs.proposed_tasks` is data, not a live nested task packet.
- `jagt result lint` validates the result; it does not spawn the child.
- The parent must reject unsafe or unapproved proposals.
- The child task becomes executable only after the parent renders a fresh
  `AGENT_TASK v1` packet and validates it.
- The worker result is validated separately.
- The final parent result should include a recursion trace so the handoff chain
  is visible.

The local recursive transcript lab is
[integration_tests/live_agent_result_recursive/](../integration_tests/live_agent_result_recursive/).
It follows the same pattern as the reusable Git and jj
`live_agent_result_recursive_lab.md` docs: planner subagent, parent-rendered
child task, worker subagent, final parent result, and unsafe-proposal refusal.

## Flow 4: Stochastic Task Draft

Use stochastic drafts when the task shape itself needs LLM judgment. The
proposal subagent designs a bounded future task, but it does not execute that
future task.

```text
Parent agent
  asks proposal subagent to design a task
Proposal subagent
  returns AGENT_RESULT v1 for the drafting job
Proposal subagent
  also returns AGENT_TASK_DRAFT v1
Parent agent
  validates draft with jagt draft lint
Parent agent
  reviews policy and approval requirements
Parent agent
  promotes approved fields through jagt render
Parent agent
  validates promoted AGENT_TASK v1 with jagt lint
Parent agent
  delegates promoted task to a different execution subagent
```

Draft validation:

```bash
jagt draft lint --expect-count 1 proposed.agent-task-draft.txt
```

Promotion is deterministic:

```bash
jagt render count-chat-message-chars \
  --no-config \
  --arg "Count the number of characters in this chat message I am sending." \
  --prompt-text "Count the number of characters in the first argv entry. Return the count and state what counting rule you used." \
  --required-output character_count \
  --allowed-action "read the supplied argv entry" \
  --allowed-action "compute the requested scalar result" \
  --verification "independently recount the same message before reporting success" \
  > promoted.agent-task.txt

jagt lint --expect-count 1 promoted.agent-task.txt
```

Drafts must include approval and promotion requirements. They are invalid if
they claim to be preapproved, use `mode: agentic`, bypass approval or VCS rules,
request broad authority, or instruct the proposal subagent to execute the
proposed work inline.

## Deterministic Versus Stochastic

| Situation | Use | Why |
| --- | --- | --- |
| Inputs, outputs, allowed actions, and verification are already known | `jagt render` -> `AGENT_TASK v1` | The task is deterministic enough to delegate directly. |
| A subagent discovers a deterministic child would be safer | `AGENT_RESULT v1` with `outputs.proposed_tasks` | The parent must validate and render the child before delegation. |
| The task shape requires LLM judgment | `AGENT_TASK_DRAFT v1` | The proposal must be reviewed, approved, and promoted before execution. |
| A completed delegated task reports outputs | `AGENT_RESULT v1` | Results are report-only and should be validated before use. |

## Lab Map

Run the local deterministic demo:

```bash
just build
just protocol-demo
```

It proves:

- send/render one `AGENT_TASK v1` packet;
- receive/validate one `AGENT_RESULT v1` packet;
- receive/validate recursive proposed-task and local-recursion result shapes;
- receive/validate one `AGENT_TASK_DRAFT v1` packet;
- promote the approved draft through deterministic `jagt render`.

Local jagt transcript labs:

- [integration_tests/live_agent_reaction/](../integration_tests/live_agent_reaction/):
  a fresh agent context runs a Just target, sees `AGENT_TASK v1`, and delegates
  instead of executing inline.
- [integration_tests/live_agent_result_recursive/](../integration_tests/live_agent_result_recursive/):
  planner result, parent-rendered child task, worker result, final recursion
  trace, and unsafe proposal refusal.

Gest Git and Gest jj lab names checked for parity:

- `run_agentic_target_lab.sh`: direct, companion, dispatcher, dependency,
  hook, verification, malformed delimiter, and malformed body cases.
- `run_agent_result_lab.sh`: success, partial, blocked, failed,
  target-mismatch, missing file, report-only rejection, recursive proposal, and
  local recursion trace cases.
- `run_agent_result_recursive_live_lab.sh`: transcript validator for two
  successive subagents and unsafe proposal refusal.
- `run_agent_task_draft_lab.sh`: result-plus-draft pairing, malformed/unsafe
  draft rejection, fresh context contract injection, deterministic promotion,
  and promoted task linting.

## Reading Order

Use this order when trying to understand the repository:

1. [../README.md](../README.md) for the short actor model and current command
   surface.
2. This file for the full flow map.
3. [reference/agentic_just_targets_base_spec.md](reference/agentic_just_targets_base_spec.md)
   for the `AGENT_TASK v1` source context.
4. [reference/agent_result_v1_spec.md](reference/agent_result_v1_spec.md) for
   result semantics.
5. [reference/agent_task_draft_v1_spec.md](reference/agent_task_draft_v1_spec.md)
   for stochastic draft semantics.
6. [jagt-testing-strategy.md](jagt-testing-strategy.md) for deterministic tests
   and opt-in live transcript labs.
