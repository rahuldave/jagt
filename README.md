# jagt

jagt brings an LLM into a Just workflow through a deterministic interface.
[Just](https://just.systems) is a command runner, and a Justfile holds its
recipes.

A Just recipe that needs an agent prints an `AGENT_TASK` packet. The packet has
a fixed form. It says what to do, what the agent may change, and what it must
return. The agent answers with an `AGENT_RESULT` packet, also in a fixed form.
jagt renders the `AGENT_TASK` packet and checks both packets, without an LLM. So the work of the agent
starts and ends at a seam that a program can verify.

jagt renders, lints and explains packets without calling an LLM, opening the
network or starting subagents. The one random part of a packet is its nonce. A
nonce is a random value of 32 lowercase hex digits, of which the first is a
letter, new for each packet. `jagt render` gives a packet a nonce when it saves
the packet file, in a git worktree and without `--no-save`. The agent must
return the nonce in its result, so that the result matches the one packet it
answers.

The name jagt means "just agent task."

The rest of this page also calls a Just recipe a Just target. A Just target
that prints an `AGENT_TASK` packet is an agentic Just target. An agentic Just
target is a boundary in the conversation:

```text
Just target stdout
  -> AGENT_TASK v1 packet
  -> parent LLM validates with jagt
  -> parent LLM delegates to a subagent
  -> subagent returns AGENT_RESULT v1
  -> parent LLM validates, records, and decides what happens next
```

The parent LLM is the agent that runs the Just target. A subagent is an agent
that the parent LLM starts for one delegated packet.

`jagt` owns the mechanics of the packet. The parent LLM owns the decisions of
orchestration. It decides whether to delegate, and whether a recursive
proposal is safe. A recursive proposal is a child task that a subagent
proposes. The parent LLM also decides whether a stochastic draft needs the
approval of the user. Last, it decides how outputs and follow-ups are recorded
in Gest, a task tracker.

A stochastic draft is an `AGENT_TASK_DRAFT` packet that an LLM proposes when
the shape of a task needs judgment. A draft cannot run until it is approved and
rendered as an `AGENT_TASK` packet.

Start with [docs/protocol-flows.md](docs/protocol-flows.md) for the complete
task, result, recursive, deterministic, and stochastic draft flows.
Then read
[docs/protocol-playbook-transcript.md](docs/protocol-playbook-transcript.md)
for a concrete transcript of a parent LLM, generated from a runnable example
Justfile.

## Install

jagt is a Rust program. Install it with Cargo, from GitHub:

```bash
cargo install --git https://github.com/rahuldave/jagt jagt
```

Or install it from a clone of this repository:

```bash
cargo install --path .
```

Check the install with `jagt --version`. The commit gates are checks, from the
commit gates spec of agent_gest_git_skills, that stop a commit when they fail.
A hook of the gates turns the result of an agent into a record. The gates need
jagt 0.3.0 or later, for the nonce of a packet.

## The actors

| Actor | Responsibility |
| --- | --- |
| `Justfile` target | Emits ordinary command output or an agentic packet. |
| `jagt render` | Deterministically creates executable `AGENT_TASK v1` packets. |
| `jagt lint` | Validates `AGENT_TASK v1` packets before delegation. |
| Parent LLM | Runs the Just target, validates packets, delegates to subagents, handles recursive proposals, and records results. |
| Subagent | Executes one delegated packet and returns `AGENT_RESULT v1`. |
| `jagt result lint` | Validates subagent result envelopes and expected target/status checks. |
| `jagt draft lint` | Validates non-executable `AGENT_TASK_DRAFT v1` proposals before approval and promotion. |

An `AGENT_TASK v1` block is a handoff packet. It is never an instruction to do
the work inline, in the current agent. If the current agent sees one, it
validates it and delegates it through the host agent runtime. If no subagent
path is available, the agent reports a blocker. The missing path gives no
permission to execute the task silently.

## Current packet flows

### 1. Deterministic task handoff

A Just target or script calls `jagt render` with known inputs, outputs, allowed
actions, and verification:

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

The parent LLM validates the emitted packet:

```bash
jagt lint --expect-count 1 packet.agent-task.txt
```

Then it delegates the parsed task to a subagent. The task packet includes the
required safety language. It also includes the triggers of recursive
delegation for nested agentic Just calls, agentic dependencies, hook-triggered
packets, and agentic verification targets.

### 2. Result return

The subagent reports back with exactly one primary `AGENT_RESULT v1` packet:

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
follow_up: []
<<<END_AGENT_RESULT>>>
```

The parent LLM validates the result before it trusts it:

```bash
jagt result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status success \
  result.agent-result.txt
```

`AGENT_RESULT v1` is report-only. It reports the work, and it cannot grant
permissions, widen write scope, or override user, system, developer, approval,
VCS, or repo rules.

### 3. Recursive work

Recursive work uses a trampoline. Each subagent returns to the parent LLM, and
the parent LLM starts the next task. A planner subagent can return
`status: partial` with `outputs.proposed_tasks`, but that proposal is only
data. The parent LLM validates the planner result, and checks the proposed
child task against normal safety rules. Then it renders a fresh child
`AGENT_TASK v1` with `jagt render`, and delegates that child to a worker
subagent. Last, it validates the worker result, and records a final parent
result with `outputs.recursion_trace`.

Only the parent LLM spawns the second task, after validation and policy
checks. `jagt result lint`, a Just recipe and the `AGENT_RESULT` block itself
do not spawn it.

### 4. Stochastic drafts

If the shape of the task itself needs judgment, ask a proposal subagent for a
draft, and do not render an executable task directly. The proposal subagent
returns one `AGENT_RESULT v1` for the drafting job, and one
`AGENT_TASK_DRAFT v1` packet.

Drafts are non-executable. The parent LLM must validate them:

```bash
jagt draft lint --expect-count 1 proposed.agent-task-draft.txt
```

Then the parent LLM reviews policy, and records or requests approval. It
promotes the approved fields through deterministic `jagt render`, and
validates the promoted `AGENT_TASK v1`. Last, it delegates the promoted packet
to a different execution subagent.

## Try the deterministic demo

Build the binary and run the standalone protocol demo:

```bash
just build
just protocol-demo
```

The demo renders and validates an outbound `AGENT_TASK v1`, and validates an
inbound `AGENT_RESULT v1`. It checks the shapes of the recursive result
fixtures. Last, it validates a stochastic `AGENT_TASK_DRAFT v1`, and promotes
that draft through `jagt render`. `just verify` includes this demo in the
normal local gate.

## Implementation surface

- `jagt render <target>` emits `AGENT_TASK v1` packets. In a git worktree,
  each packet gets a random nonce, and jagt saves the packet file
  `.agents/log/packets/<nonce>.json` in the log folder of the main checkout.
  The prompt text joins the base task, the language layer of each language in
  `.agents/stack.json`, and the repository text. `--no-save` renders the text
  only. [docs/packet-file.md](docs/packet-file.md) gives the details.
- `jagt lint [PATH|-]` validates the structure of an `AGENT_TASK v1` packet.
- `jagt explain task [PATH|-]` summarizes task packets and the precedence of
  their sources.
- `jagt result lint [PATH|-]` validates `AGENT_RESULT v1` report packets.
  `--expect-nonce <nonce>` fails a result that does not hold the nonce of its
  packet. `--check-files` checks the files that a result lists in
  `outputs.files`. Each required file must exist under `--base-dir`. A listed
  file that exists fails when its real path is outside the base folder, for
  example through a symbolic link. On Unix, it also fails when it has more than
  one hard link.
- `jagt result explain [PATH|-]` summarizes the status, outputs,
  verification, follow-up, and report-only state of a result.
- `jagt draft lint [PATH|-]` validates non-executable `AGENT_TASK_DRAFT v1`
  proposal packets.

Render input can come from CLI flags, `.jagt/config.toml`, target config,
Markdown prompt files with YAML frontmatter, and explicitly allowlisted
`${VAR}` interpolation. `--prompt-text` wins over `--prompt`. `--no-config`
ignores the project config file and an explicit config file.

## Docs and labs

- [docs/protocol-flows.md](docs/protocol-flows.md): complete conversation
  flows and a map of the labs.
- [docs/protocol-playbook-transcript.md](docs/protocol-playbook-transcript.md):
  live transcript of a parent LLM with spawned subagents, for plain, recursive,
  and stochastic cases.
- [docs/reference/agentic_just_targets_base_spec.md](docs/reference/agentic_just_targets_base_spec.md):
  source context for `AGENT_TASK v1`.
- [docs/reference/agent_result_v1_spec.md](docs/reference/agent_result_v1_spec.md):
  source context for `AGENT_RESULT v1`.
- [docs/reference/agent_task_draft_v1_spec.md](docs/reference/agent_task_draft_v1_spec.md):
  proposal context for `AGENT_TASK_DRAFT v1`.
- [docs/jagt-testing-strategy.md](https://github.com/rahuldave/jagt/blob/main/docs/jagt-testing-strategy.md): deterministic
  tests and opt-in live transcript labs.
- [integration_tests/live_agent_reaction/](https://github.com/rahuldave/jagt/tree/main/integration_tests/live_agent_reaction):
  lab of a single-hop live agent reaction.
- [integration_tests/live_agent_result_recursive/](https://github.com/rahuldave/jagt/tree/main/integration_tests/live_agent_result_recursive):
  transcript lab of a recursive planner and worker.

This README and the flow guide were checked against the labs of Gest Git
(`agent_gest_git_skills`) and Gest jj (`agent_gest_jj_skills`). The labs cover
the agentic target, the result, the recursive result, and the task draft.
`jagt` keeps its local demos self-contained through
`.agents/skills/jagt-protocol/`. It does not need those external repositories
installed to run `just protocol-demo`.

## Commands

```bash
just setup
just fmt
just fmt-check
just lint
just typecheck
just build
just test
just smoke
just protocol-demo
just docs
just verify
```

`just verify` runs formatting checks, clippy, typecheck, build, tests, smoke
help output, the standalone protocol demo, and whitespace hygiene.

## Fresh Codex kickoff

To start a new Codex project session, go to the repository:

```bash
cd path/to/jagt
```

Then start with `gtw`, the Gest router skill, for implementation, docs,
debugging, verification, or project work. The session should inspect the
active Gest iteration before it edits. The next slice then continues from the
current state of the MVP, the minimum viable product.

## Current design status

[jagt_deterministic_renderer_spec.md](https://github.com/rahuldave/jagt/blob/main/jagt_deterministic_renderer_spec.md)
holds the design that the MVP implements. The staged plan of its implementation is
in
[docs/jagt-mvp-implementation-plan.md](https://github.com/rahuldave/jagt/blob/main/docs/jagt-mvp-implementation-plan.md).
All MVP slices are done, and so are the fixes of the final review. CI runs
`just verify` on each pull request. The changes of each version are in
[CHANGELOG.md](CHANGELOG.md).

jagt has no formal schema. The protocol contract of the `jagt-protocol` skill,
from jnterfaces, defines each packet, and the lint commands check it.

## License

The license of jagt is MIT. See
[LICENSE](https://github.com/rahuldave/jagt/blob/main/LICENSE).
