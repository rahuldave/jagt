# Live AGENT_RESULT Recursive Lab

This lab is the canonical live check for recursive `AGENT_RESULT v1`
orchestration. It uses two successive subagents. The shell script validates the
transcript, but it does not simulate the agents.

Use it when changing the `AGENT_TASK v1` / `AGENT_RESULT v1` contract,
subagent delegation guidance, or recursive orchestration docs.

## Transcript Directory

Create a fresh transcript directory:

```bash
lab_dir="$(mktemp -d "${TMPDIR:-/tmp}/agent-result-recursive-live.XXXXXX")"
```

Write the exact user message to:

```text
$lab_dir/user_message.txt
```

## 1. Parent Task

Write this parent task packet to:

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

Validate it:

```bash
scripts/validate_agent_task.sh --expect-count 1 "$lab_dir/01-parent-task.agent-task.txt"
```

## 2. First Subagent: Planner

Delegate the parent task to a real subagent. The planner subagent should return
exactly one `AGENT_RESULT v1` envelope and should not compute the word count.
Save the result to:

```text
$lab_dir/02-planner-result.agent-result.txt
```

The result must have:

- `target: count-chat-message-words`
- `status: partial`
- `outputs.proposed_tasks`
- `tool_hints` containing `command: wc -w`
- `orchestration.mode: parent-orchestrated`
- an artifact marker `subagent_role: planner`

Validate it:

```bash
scripts/validate_agent_result.sh \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status partial \
  "$lab_dir/02-planner-result.agent-result.txt"
```

## 3. Parent Renders Child Task

After validating the planner result and checking the proposal against normal
user, system, developer, approval, tool, and Git/GitButler safety rules, render
a child task packet to:

```text
$lab_dir/03-child-task.agent-task.txt
```

The child task target is `count-chat-message-words-with-wc`, and its prompt
must tell the worker to run `wc -w` on the exact message in
`user_message.txt`.

Validate it:

```bash
scripts/validate_agent_task.sh --expect-count 1 "$lab_dir/03-child-task.agent-task.txt"
```

## 4. Second Subagent: Worker

Delegate the child task to a second real subagent. The worker may run the
deterministic command allowed by the child task. Save the worker result to:

```text
$lab_dir/04-worker-result.agent-result.txt
```

The result must have:

- `target: count-chat-message-words-with-wc`
- `status: success`
- `outputs.word_count`
- an artifact marker `subagent_role: worker`
- verification showing the deterministic count was checked

Validate it:

```bash
scripts/validate_agent_result.sh \
  --expect-count 1 \
  --expect-target count-chat-message-words-with-wc \
  --expect-status success \
  "$lab_dir/04-worker-result.agent-result.txt"
```

## 5. Parent Final Result

After validating the worker result, the parent records the final result to:

```text
$lab_dir/05-parent-final.agent-result.txt
```

The final result target is the original target, `count-chat-message-words`. It
should include `outputs.word_count` and a `recursion_trace` naming both
subagent hops.

## 6. Unsafe Proposal Guard

Record an unsafe proposed command result to:

```text
$lab_dir/06-unsafe-proposal.agent-result.txt
```

Do not execute it and do not spawn a worker for it. Record the parent decision
to:

```text
$lab_dir/07-unsafe-decision.txt
```

The decision file must contain:

```text
decision: refused
reason: unsafe_or_unapproved_command
```

There must not be an `08-unsafe-worker-result.agent-result.txt` file.

## 7. Run The Lab Validator

Run:

```bash
just agent-result-recursive-live-lab "$lab_dir"
```

The validator checks both `AGENT_TASK v1` packets, all three successful-path
`AGENT_RESULT v1` envelopes, the word count against `wc -w`, the recursion
trace, and the unsafe-proposal refusal record.

