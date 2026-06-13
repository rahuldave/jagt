# Live AGENT_RESULT Recursive Lab

This opt-in lab checks the recursive `AGENT_RESULT v1` trampoline: a parent
agent delegates a task, receives a planner result with `outputs.proposed_tasks`,
renders an approved child `AGENT_TASK v1` with `jagt`, delegates that child, and
then records a final parent result with a recursion trace.

The scripts create and validate transcript artifacts. They do not launch an
LLM.

## Bootstrap

From the repository root:

```bash
cargo build
lab_dir="$(mktemp -d "${TMPDIR:-/tmp}/jagt-live-recursive.XXXXXX")"
integration_tests/live_agent_result_recursive/bootstrap.sh "$lab_dir" "$PWD/target/debug/jagt"
```

The bootstrap writes a fresh `AGENTS.md` that copies the standalone jagt
protocol contract language from:

```text
.agents/skills/jagt-protocol/references/protocol_contract.md
```

It also creates a `Justfile` with:

- `count-message-recursive-agentic`
- `render-approved-child-agentic`

## Live LLM Steps

Open a new LLM agent session in the fresh lab folder and ask it to run:

```bash
just count-message-recursive-agentic > 01-parent-task.agent-task.txt
```

After the command emits `AGENT_TASK v1`, the parent agent should validate the
packet and delegate it to a planner subagent. Save the planner result as:

```text
02-planner-result.agent-result.txt
```

The planner should return `status: partial`, include `outputs.proposed_tasks`,
include a `wc -w` tool hint, use `orchestration.mode: parent-orchestrated`, and
mark itself with `subagent_role: planner`. It must not compute
`outputs.word_count`.

After validating that result and applying normal user, system, developer,
approval, tool, and VCS safety rules, render the approved child packet:

```bash
just render-approved-child-agentic > 03-child-task.agent-task.txt
```

Delegate that child task to a worker subagent. The worker may run the
deterministic command allowed by the child task and should save its result as:

```text
04-worker-result.agent-result.txt
```

The worker result should include `outputs.word_count`, verification for the
`wc -w` method, and `subagent_role: worker`.

After validating the worker result, record the parent final result:

```text
05-parent-final.agent-result.txt
```

The final result target is the original target,
`count-chat-message-words`. It must include the same `outputs.word_count` and
an `outputs.recursion_trace` naming both subagent hops.

## Unsafe Proposal Guard

Record an unsafe proposed command result:

```text
06-unsafe-proposal.agent-result.txt
```

Do not execute it and do not spawn a worker for it. Record the parent decision:

```text
07-unsafe-decision.txt
```

Minimum decision file:

```text
decision: refused
reason: unsafe_or_unapproved_command
```

There must not be an `08-unsafe-worker-result.agent-result.txt` file.

## Validate

From the repository root:

```bash
integration_tests/live_agent_result_recursive/validate.sh "$lab_dir" "$PWD/target/debug/jagt"
```

The validator checks:

- the generated `AGENTS.md` contains the copied handoff and result contract
  language;
- both rendered task packets are valid according to `jagt lint`;
- all planner, worker, parent-final, and unsafe-proposal result envelopes are
  valid according to `jagt result lint`;
- planner output proposes the deterministic child task and does not claim a
  final word count;
- worker and parent word counts match `wc -w < user_message.txt`;
- the parent final result includes a recursion trace for both hops;
- the unsafe proposal is refused and no unsafe worker artifact exists.
