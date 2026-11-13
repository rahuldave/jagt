# jagt

`jagt` means "just agent task." It is the deterministic tool in an
agentic Just workflow. It renders, lints, and explains packet envelopes without
calling an LLM, opening the network, or starting subagents. The one random part
is the nonce of each packet.

The important idea is that an agentic Just target is a conversation boundary:

```text
Just target stdout
  -> AGENT_TASK v1 packet
  -> parent LLM validates with jagt
  -> parent LLM delegates to a subagent
  -> subagent returns AGENT_RESULT v1
  -> parent LLM validates, records, and decides what happens next
```

`jagt` owns the packet mechanics. The parent LLM owns the decisions of
orchestration. It decides whether to delegate, whether a recursive proposal is
safe, whether a stochastic draft needs user approval, and how outputs and
follow-ups are recorded in Gest.

Start with [docs/protocol-flows.md](docs/protocol-flows.md) for the complete
task, result, recursive, deterministic, and stochastic draft flows.
Then read
[docs/protocol-playbook-transcript.md](docs/protocol-playbook-transcript.md)
for a concrete parent-LLM transcript generated from a runnable example
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

Check the install with `jagt --version`. The commit gates need jagt 0.3.0 or
later, for the nonce of a packet.

## The Actors

| Actor | Responsibility |
| --- | --- |
| `Justfile` target | Emits ordinary command output or an agentic packet. |
| `jagt render` | Deterministically creates executable `AGENT_TASK v1` packets. |
| `jagt lint` | Validates `AGENT_TASK v1` packets before delegation. |
| Parent LLM | Runs the Just target, validates packets, delegates to subagents, handles recursive proposals, and records results. |
| Subagent | Executes one delegated packet and returns `AGENT_RESULT v1`. |
| `jagt result lint` | Validates subagent result envelopes and expected target/status checks. |
| `jagt draft lint` | Validates non-executable `AGENT_TASK_DRAFT v1` proposals before approval and promotion. |

An `AGENT_TASK v1` block is never an instruction to do the work inline. It is a
handoff packet. If the current agent sees one, it validates it and delegates it
through the host agent runtime. If no subagent path is available, that is a
blocker to report, not permission to silently execute the task.

## Current Packet Flows

### 1. Deterministic Task Handoff

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

The parent agent validates the emitted packet:

```bash
jagt lint --expect-count 1 packet.agent-task.txt
```

Then it delegates the parsed task to a subagent. The task packet includes
required safety language and recursive delegation triggers for nested agentic
Just calls, agentic dependencies, hook-triggered packets, and agentic
verification targets.

### 2. Result Return

The subagent reports back with exactly one primary `AGENT_RESULT v1` envelope:

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

The parent validates the result before trusting it:

```bash
jagt result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status success \
  result.agent-result.txt
```

`AGENT_RESULT v1` is report-only. It cannot grant permissions, widen write
scope, or override user, system, developer, approval, VCS, or repo rules.

### 3. Recursive Work

Recursive work uses a trampoline. A planner subagent can return
`status: partial` with `outputs.proposed_tasks`, but that proposal is only
data. The parent validates the planner result, and checks the proposed child
task against normal safety rules. Then it renders a fresh child `AGENT_TASK v1`
with `jagt render`, and delegates that child to a worker subagent. Last, it
validates the worker result, and records a final parent result with
`outputs.recursion_trace`.

The second task is not spawned by `jagt result lint`, a Just recipe, or the
`AGENT_RESULT` block itself. It is spawned only by the parent/orchestrator after
validation and policy checks.

### 4. Stochastic Drafts

When the task shape itself requires judgment, ask a proposal subagent for a
draft instead of rendering an executable task directly. The proposal subagent
returns one `AGENT_RESULT v1` for the drafting job plus one
`AGENT_TASK_DRAFT v1` envelope.

Drafts are non-executable. The parent must validate them:

```bash
jagt draft lint --expect-count 1 proposed.agent-task-draft.txt
```

Then the parent reviews policy, records or requests approval, promotes approved
fields through deterministic `jagt render`, validates the promoted
`AGENT_TASK v1`, and delegates the promoted packet to a different execution
subagent.

## Try The Deterministic Demo

Build the binary and run the standalone protocol demo:

```bash
just build
just protocol-demo
```

The demo renders and validates an outbound `AGENT_TASK v1`, validates an
inbound `AGENT_RESULT v1`, checks recursive result fixture shapes, validates a
stochastic `AGENT_TASK_DRAFT v1`, and promotes that draft through
`jagt render`.

`just verify` includes this demo in the normal local gate.

## Implementation Surface

- `jagt render <target>` emits `AGENT_TASK v1` packets. In a git worktree,
  each packet gets a random nonce, and jagt saves the packet file
  `.agents/log/packets/<nonce>.json` in the log folder of the main checkout.
  The prompt text joins the base task, the language layer of each language in
  `.agents/stack.json`, and the repository text. `--no-save` renders the text
  only. [docs/packet-file.md](docs/packet-file.md) gives the details.
- `jagt lint [PATH|-]` validates `AGENT_TASK v1` packet structure.
- `jagt explain task [PATH|-]` summarizes task packets and source precedence.
- `jagt result lint [PATH|-]` validates `AGENT_RESULT v1` report envelopes.
  `--expect-nonce <nonce>` fails a result that does not hold the nonce of its
  packet.
- `jagt result explain [PATH|-]` summarizes result status, outputs,
  verification, follow-up, and report-only state.
- `jagt draft lint [PATH|-]` validates non-executable `AGENT_TASK_DRAFT v1`
  proposal envelopes.

Render input can come from CLI flags, `.jagt/config.toml`, target config,
Markdown prompt files with YAML frontmatter, and explicitly allowlisted
`${VAR}` interpolation. `--prompt-text` wins over `--prompt`; `--no-config`
ignores project and explicit config files.

## Docs And Labs

- [docs/protocol-flows.md](docs/protocol-flows.md): complete conversation
  flows and lab map.
- [docs/protocol-playbook-transcript.md](docs/protocol-playbook-transcript.md):
  live parent-LLM transcript with spawned subagents for plain, recursive, and
  stochastic cases.
- [docs/reference/agentic_just_targets_base_spec.md](docs/reference/agentic_just_targets_base_spec.md):
  `AGENT_TASK v1` source context.
- [docs/reference/agent_result_v1_spec.md](docs/reference/agent_result_v1_spec.md):
  `AGENT_RESULT v1` source context.
- [docs/reference/agent_task_draft_v1_spec.md](docs/reference/agent_task_draft_v1_spec.md):
  `AGENT_TASK_DRAFT v1` proposal context.
- [docs/jagt-testing-strategy.md](docs/jagt-testing-strategy.md): deterministic
  tests and opt-in live transcript labs.
- [integration_tests/live_agent_reaction/](integration_tests/live_agent_reaction/):
  single-hop live agent reaction lab.
- [integration_tests/live_agent_result_recursive/](integration_tests/live_agent_result_recursive/):
  recursive planner/worker transcript lab.

This README and the flow guide were checked against the labs of Gest Git
(`agent_gest_git_skills`) and Gest jj (`agent_gest_jj_skills`). The labs cover
the agentic target, the result, the recursive result, and the task draft. `jagt` keeps local
demos self-contained through `.agents/skills/jagt-protocol/`; it does not need
those external repositories installed to run `just protocol-demo`.

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

## Fresh Codex Kickoff

For a new Codex project session:

```bash
cd path/to/jagt
```

Then start with `gtw` for implementation, docs, debugging, verification, or
project work. The session should inspect the active Gest iteration before
editing so the next slice continues from the current MVP state.

## Current Design Status

The accepted MVP design lives in
[jagt_deterministic_renderer_spec.md](jagt_deterministic_renderer_spec.md), with
the staged implementation plan in
[docs/jagt-mvp-implementation-plan.md](docs/jagt-mvp-implementation-plan.md).
All MVP slices are done, and so are the fixes of the final review. CI runs
`just verify` on each pull request. The changes of each version are in
[CHANGELOG.md](CHANGELOG.md).

jagt has no formal schema. The protocol contract of the `jagt-protocol` skill,
from jnterfaces, defines each packet, and the lint commands check it.

## License

MIT. See [LICENSE](LICENSE).
