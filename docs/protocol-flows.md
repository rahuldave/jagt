# jagt protocol flows

This guide shows how the three packet formats of jagt fit together in an agent
workflow. A packet is a block of text in a fixed form that one agent hands to
another. The guide is written on purpose as a conversation between these
parties:

- **The output of a Just target.** A Just target is a named recipe that the
  tool Just runs.
- **The parent LLM.** An LLM is a large language model. The parent LLM, also
  called the parent agent, is the agent that runs the Just target and hands
  work to other agents.
- **The subagents.** A subagent is an agent that the parent agent starts for
  one task.
- **`jagt`**, the tool that this guide describes.

`jagt` gives an LLM a deterministic interface into a Just workflow. Each packet
that goes to an agent, or comes back from one, has a fixed form that a program
can check.

`jagt` itself is deterministic, which means that it follows fixed rules in
code. It renders and validates packet text. It does not call an LLM, choose
whether work is safe, approve stochastic proposals, or start subagents. The
parent agent makes those choices. It follows the active user, system, developer, approval,
VCS and repository instructions, where VCS is the version control system, such
as Git. A stochastic proposal is a task that an LLM designs, so it can differ
from run to run.

The flow map here follows Gest Git (`agent_gest_git_skills`) and Gest jj
(`agent_gest_jj_skills`). Gest is a task tracker, and these two are its sets of
agent skills for Git and for jj repositories. The map includes their labs for
agentic targets, results, recursive results and task drafts. The jagt
repository keeps its own standalone demos under `.agents/skills/jagt-protocol/`
and `integration_tests/`.

## Packet vocabulary

| Packet | Produced by | Consumed by | Meaning |
| --- | --- | --- | --- |
| `AGENT_TASK v1` | `jagt render`, a Just target, or a deterministic renderer script | Parent agent, then an execution subagent | Executable subagent handoff. Validate before delegation. |
| `AGENT_RESULT v1` | A subagent | Parent agent | Report-only return value for one delegated task. Validate before trusting it. |
| `AGENT_TASK_DRAFT v1` | A proposal subagent | Parent agent | Non-executable stochastic task proposal. Validate, review, approve, and promote before execution. |

The packets differ most in their authority:

- `AGENT_TASK v1` describes bounded work to delegate.
- `AGENT_RESULT v1` reports what happened.
- `AGENT_TASK_DRAFT v1` proposes the shape of a future task.
- None of them can override instructions of higher priority or the policy of
  the repository.

For a step-by-step account of a parent LLM at work, with the actual command
outputs from a local run, see
[protocol-playbook-transcript.md](protocol-playbook-transcript.md).

## Flow 1: Deterministic task handoff

Use this flow when the task is already known well enough to render directly.
Then the target name, prompt, inputs, required outputs, allowed actions and
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

The parent should validate the packet:

```bash
jagt lint --expect-count 1 packet.agent-task.txt
```

Then the parent delegates the task. It must not do the requested work inline,
in its own session, only because the packet appeared in the output of a
terminal.

### Just target shapes

Gest Git and Gest jj use three equivalent shapes of target. `jagt` supports all
of them, because it reads only the packet that the target prints. In a real
target, prefer a small renderer wrapper, so that the wrapper escapes the
arguments and builds repeated flags safely:

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

Choose the shape by how the targets are used:

- Use a direct target when the command is agentic by default.
- Use a companion target when a concrete path and an exploratory path exist
  side by side.
- Use a dispatcher when many targets share one packet surface.

## Flow 2: Result return

Every delegated task needs a structured path back to the parent. The subagent
returns one primary `AGENT_RESULT v1` envelope for the task that it received.
An envelope is one packet, from its opening line, such as
`<<<AGENT_RESULT v1>>>`, to its closing line.

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

When the parent knows the expected target and status, it validates with them:

```bash
jagt result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status success \
  result.agent-result.txt
```

For a result that produces files, the parent can also check the required
files:

```bash
jagt result lint \
  --expect-target eda-viz \
  --expect-status success \
  --check-files \
  --base-dir . \
  result.agent-result.txt
```

`--check-files` fails a path that is absolute or holds a `..` part. It also
fails a listed file that exists when its real path is outside the base folder,
for example a symbolic link that leads out of it. A link that stays inside the
base folder passes. On Unix, a listed file with more than one hard link fails,
because a hard link can name a file outside the folder.

A result envelope is a report. It cannot grant permission, request unrelated
edits, expand the write scope, bypass approvals, or override the guardrails of
the VCS. If a result contains fields of a task instruction, such as
`allowed_actions`, jagt rejects it.

## Flow 3: Recursive deterministic work

The parent orchestrates recursive work. A subagent can propose a child task,
but the parent decides whether to render and delegate that child.

The recursive path is a different path from the stochastic draft path. In the
recursive path, the payload of the child task travels inside a valid
`AGENT_RESULT v1` as `outputs.proposed_tasks`. Such a payload is a recursive
proposal. It stays data until the parent does four things:

1. It validates the result.
2. It accepts the proposal under the normal policy.
3. It renders a fresh child `AGENT_TASK v1`.
4. It validates the child packet.

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

The recursive path has these limits:

- `outputs.proposed_tasks` is data, and it is not a live nested task packet.
- `jagt result lint` validates the result. It does not spawn the child.
- The parent must reject unsafe or unapproved proposals.
- The child task becomes executable only after the parent renders a fresh
  `AGENT_TASK v1` packet and validates it.
- The parent validates the worker result separately.
- The final parent result should include a recursion trace, so that the chain
  of handoffs is visible.

The local lab for the recursive transcript is
[integration_tests/live_agent_result_recursive/](https://github.com/rahuldave/jagt/tree/main/integration_tests/live_agent_result_recursive).
It follows the same pattern as the `live_agent_result_recursive_lab.md` docs of
the reusable Git and jj skills. The lab has a planner subagent, a child task
that the parent renders, a worker subagent and a final parent result. It also
shows the parent refusing an unsafe proposal.

## Flow 4: Stochastic task draft

Use a stochastic draft when the shape of the task itself needs the judgment of
an LLM. A stochastic draft is an `AGENT_TASK_DRAFT v1` that an LLM proposes and
that a parent or the user must approve before promotion. The proposal subagent designs a bounded future
task, but it does not execute that future task.

The flow does not start with a deterministic Just target that prints
`AGENT_TASK v1`. It starts when the parent LLM decides that the shape of the
task is unknown. The parent then asks a proposal subagent for
`AGENT_RESULT v1` plus `AGENT_TASK_DRAFT v1`.

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

Promotion turns an approved draft into an `AGENT_TASK v1`, and it is
deterministic:

```bash
jagt render count-chat-message-chars \
  --no-config \
  --arg "Count the number of characters in this chat message I am sending." \
  --prompt-text "Count the number of characters in the first argv entry. Return the character_count and state what counting rule you used." \
  --required-output character_count \
  --allowed-action "read the supplied argv entry" \
  --allowed-action "compute the requested scalar character count" \
  --verification "independently recount the same message before returning AGENT_RESULT" \
  > promoted.agent-task.txt

jagt lint --expect-count 1 promoted.agent-task.txt
```

A draft must include its requirements for approval and promotion. A draft is
invalid if it does any of these things:

- It claims to be preapproved.
- It uses `mode: agentic`.
- It bypasses the rules for approval or VCS.
- It requests broad authority.
- It tells the proposal subagent to execute the proposed work inline.

`jagt draft lint` checks the structure of a draft strictly. It also searches
the text for common ways to word these things. The search is a first filter
and does not judge meaning, because a model can word a bypass in a way that no
list of phrases holds. So the parent still reads each draft, and records
`policy_review_passed`, before it promotes the draft.

- **Fields:** a draft may hold only the known fields. `approval` may hold only
  `required`, `approver` and `reason`. `approver` must be `parent`, `user` or
  `parent-or-user`. `execute_inline`, when present, must be `false`.
- **Text:** a phrase does not count when a negation comes right before it, or
  one word earlier after a small word such as "to", "be" or "the", as in
  "never run it inline".
- **Lookalike letters:** before the search, jagt drops zero-width characters.
  It turns fullwidth letters, and Cyrillic or Greek letters that look like
  ASCII ones, into ASCII. So a Cyrillic `а` cannot hide a phrase.

## Deterministic versus stochastic

| Situation | Use | Why |
| --- | --- | --- |
| Inputs, outputs, allowed actions, and verification are already known | `jagt render` -> `AGENT_TASK v1` | The task is deterministic enough to delegate directly. |
| A subagent discovers a deterministic child would be safer | `AGENT_RESULT v1` with `outputs.proposed_tasks` | The parent must validate and render the child before delegation. |
| The task shape requires LLM judgment | `AGENT_TASK_DRAFT v1` | The proposal must be reviewed, approved, and promoted before execution. |
| A completed delegated task reports outputs | `AGENT_RESULT v1` | Results are report-only and should be validated before use. |

## Lab map

Run the local deterministic demo:

```bash
just build
just protocol-demo
```

The demo proves that jagt can do these steps:

- Send, or render, one `AGENT_TASK v1` packet.
- Receive and validate one `AGENT_RESULT v1` packet.
- Receive and validate the shapes of a recursive proposed task and of a
  local-recursion result.
- Receive and validate one `AGENT_TASK_DRAFT v1` packet.
- Promote the approved draft through deterministic `jagt render`.

Local jagt labs that record a transcript:

- [integration_tests/live_agent_reaction/](https://github.com/rahuldave/jagt/tree/main/integration_tests/live_agent_reaction):
  a fresh agent context runs a Just target and sees `AGENT_TASK v1`. It
  delegates the task and does not execute it inline.
- [integration_tests/live_agent_result_recursive/](https://github.com/rahuldave/jagt/tree/main/integration_tests/live_agent_result_recursive):
  the planner result, the child task that the parent renders, the worker
  result, the final recursion trace, and the refusal of an unsafe proposal.

Names of the Gest Git and Gest jj labs, checked for parity:

- `run_agentic_target_lab.sh`: the direct, companion, dispatcher, dependency,
  hook, verification, malformed delimiter and malformed body cases.
- `run_agent_result_lab.sh`: the success, partial, blocked, failed,
  target-mismatch, missing file, report-only rejection, recursive proposal and
  local recursion trace cases.
- `run_agent_result_recursive_live_lab.sh`: a transcript validator for two
  successive subagents and for the refusal of an unsafe proposal.
- `run_agent_task_draft_lab.sh`: the pairing of a result with a draft, the
  rejection of a malformed or unsafe draft, the injection of the contract into
  a fresh context, deterministic promotion, and the lint of the promoted task.

## Reading order

Read the repository in this order:

1. [../README.md](https://github.com/rahuldave/jagt/blob/main/README.md), for
   the short model of the actors and the current commands.
2. This file, for the full flow map.
3. [reference/agentic_just_targets_base_spec.md](reference/agentic_just_targets_base_spec.md),
   for the source context of `AGENT_TASK v1`.
4. [reference/agent_result_v1_spec.md](reference/agent_result_v1_spec.md), for
   the meaning of a result.
5. [reference/agent_task_draft_v1_spec.md](reference/agent_task_draft_v1_spec.md),
   for the meaning of a stochastic draft.
6. [jagt-testing-strategy.md](https://github.com/rahuldave/jagt/blob/main/docs/jagt-testing-strategy.md),
   for the deterministic tests and the opt-in labs that record a live
   transcript.
