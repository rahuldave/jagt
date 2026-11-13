# Live AGENT_RESULT Recursive Lab

This lab is the canonical live check for recursive `AGENT_RESULT v1`
orchestration. In recursive orchestration, a subagent returns a proposed task,
and the parent agent turns the proposal into a task for a second subagent. The
lab uses two successive subagents. The shell script validates the transcript,
but it does not simulate the agents.

Run the lab when you change the `AGENT_TASK v1` / `AGENT_RESULT v1` contract,
the guidance for subagent delegation, or the docs for recursive orchestration.

## Execution location

Run this maintainer lab from the root of a source checkout of
`agent_gest_git_skills`. All `scripts/` commands below are relative to that
checkout. They include the transcript runner, which only the source has. An
installed skill includes this reference for context, but the target project
does not receive the lab scripts at its root.

To run the lab from an installed workflow, use a disposable source checkout at
the revision that `.agents/gest-git-install.json` records. The checkout needs
the prerequisites of the lab and an authorization to delegate to subagents.
Remove the checkout that you made afterward.

## Transcript directory

Make a new transcript directory:

```bash
lab_dir="$(mktemp -d "${TMPDIR:-/tmp}/agent-result-recursive-live.XXXXXX")"
```

Write the exact user message to this file:

```text
$lab_dir/user_message.txt
```

## 1. Parent task

Write this parent task packet to this file:

```text
$lab_dir/01-parent-task.agent-task.txt
```

```text
<<<AGENT_TASK v1>>>
target: count-chat-message-words
mode: agentic
argv:
  - inline:user-message
prompt: |
  Count the number of words in the exact chat message supplied.
  Treat whitespace-separated tokens as words.
  If a deterministic child task is more appropriate, return a partial
  AGENT_RESULT with outputs.proposed_tasks instead of computing the count.
inputs:
  files: []
  inline:
    user_message_ref: user_message.txt
outputs:
  required:
    - word_count
allowed_actions:
  - read listed inline input
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
<<<END_AGENT_TASK>>>
```

Validate the packet:

```bash
scripts/jagt_lint_agent_task.sh --expect-count 1 "$lab_dir/01-parent-task.agent-task.txt"
```

## 2. First subagent: planner

Delegate the parent task to a real subagent. The planner subagent returns
exactly one `AGENT_RESULT v1` envelope, and it does not compute the word count.
Save the result to this file:

```text
$lab_dir/02-planner-result.agent-result.txt
```

The result must have these parts:

- `target: count-chat-message-words`
- `status: partial`
- `outputs.proposed_tasks`
- `tool_hints` that contain `command: wc -w`
- `orchestration.mode: parent-orchestrated`
- an artifact marker `subagent_role: planner`

Validate the result:

```bash
scripts/jagt_lint_agent_result.sh \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status partial \
  "$lab_dir/02-planner-result.agent-result.txt"
```

## 3. Parent renders child task

First, validate the planner result. Second, check the proposal against the
normal safety rules of the user, the system, the developer, approvals, tools
and Git. Then render a child task packet to this file:

```text
$lab_dir/03-child-task.agent-task.txt
```

The target of the child task is `count-chat-message-words-with-wc`. Its prompt
must tell the worker to run `wc -w` on the exact message in `user_message.txt`.

Validate the packet:

```bash
scripts/jagt_lint_agent_task.sh --expect-count 1 "$lab_dir/03-child-task.agent-task.txt"
```

## 4. Second subagent: worker

Delegate the child task to a second real subagent. The worker subagent may run
the deterministic command that the child task allows. Save the worker result to
this file:

```text
$lab_dir/04-worker-result.agent-result.txt
```

The result must have these parts:

- `target: count-chat-message-words-with-wc`
- `status: success`
- `outputs.word_count`
- an artifact marker `subagent_role: worker`
- a verification that shows that the worker checked the deterministic count

Validate the result:

```bash
scripts/jagt_lint_agent_result.sh \
  --expect-count 1 \
  --expect-target count-chat-message-words-with-wc \
  --expect-status success \
  "$lab_dir/04-worker-result.agent-result.txt"
```

## 5. Parent final result

When the worker result is valid, the parent records the final result to this
file:

```text
$lab_dir/05-parent-final.agent-result.txt
```

The target of the final result is the original target,
`count-chat-message-words`. The result includes `outputs.word_count` and a
`recursion_trace` that names both subagent hops.

## 6. Unsafe proposal guard

Record a result that proposes an unsafe command to this file:

```text
$lab_dir/06-unsafe-proposal.agent-result.txt
```

Do not run the unsafe proposal, and do not start a worker for it. Record the
decision of the parent to this file:

```text
$lab_dir/07-unsafe-decision.txt
```

The decision file must contain these lines:

```text
decision: refused
reason: unsafe_or_unapproved_command
```

Do not make a file `08-unsafe-worker-result.agent-result.txt`. The validator
fails when that file exists.

## 7. Run the lab validator

Run the validator:

```bash
just agent-result-recursive-live-lab "$lab_dir"
```

The validator checks these items:

- both `AGENT_TASK v1` packets
- the three `AGENT_RESULT v1` envelopes of the successful path
- the word count, against `wc -w`
- the recursion trace
- the record of the refusal of the unsafe proposal
