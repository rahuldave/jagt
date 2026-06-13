# Live Agent Reaction Lab

This opt-in lab checks behavior that deterministic Rust tests cannot simulate:
a real LLM agent runs a Just target, sees an emitted `AGENT_TASK v1` packet, and
treats it as a subagent handoff boundary instead of executing the task inline.

It is transcript-based. The scripts create and validate lab artifacts, but they
do not launch an LLM.

## Bootstrap

From the repository root:

```bash
cargo build
lab_dir="$(mktemp -d "${TMPDIR:-/tmp}/jagt-live-agent.XXXXXX")"
integration_tests/live_agent_reaction/bootstrap.sh "$lab_dir" "$PWD/target/debug/jagt"
```

The bootstrap writes a fresh `AGENTS.md` that copies the relevant agentic Just
contract language from:

```text
.agents/skills/gtw/references/just_command_contract.md
```

It also creates a `Justfile` with `count-message-agentic`.

## Live LLM Step

Open a new LLM agent session in the fresh lab folder and ask it to run:

```bash
just count-message-agentic > 01-rendered-task.agent-task.txt
```

After the command emits `AGENT_TASK v1`, the parent agent should validate the
packet and delegate it instead of counting inline. Record that parent decision
in:

```text
02-parent-decision.txt
```

Minimum decision file:

```text
decision: delegated
reason: AGENT_TASK v1 is a subagent handoff packet
```

The parent transcript must not claim it executed the delegated word-count task
inline after seeing the packet.

## Validate

From the repository root:

```bash
integration_tests/live_agent_reaction/validate.sh "$lab_dir" "$PWD/target/debug/jagt"
```

The validator checks:

- the generated `AGENTS.md` contains the copied handoff contract language;
- the rendered task packet is valid according to `jagt lint`;
- the packet target is `count-chat-message-words`;
- the parent decision says `decision: delegated`;
- no transcript artifact says `decision: executed-inline`.

Later `AGENT_RESULT` support should add a subagent result artifact to this lab.
