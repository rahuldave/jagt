# jagt Testing Strategy

Status: proposed test plan for MVP implementation.

`jagt` needs two different kinds of confidence:

- deterministic confidence that the Rust CLI renders, parses, and lints exactly
  what the contract says;
- live agent confidence that an LLM running in a fresh project sees an emitted
  `AGENT_TASK v1` packet and treats it as a subagent handoff boundary.

The first kind belongs in normal `cargo test` / `just test` / `just verify`.
The second kind belongs in explicit integration labs with saved transcripts.

## Deterministic Test Layers

These tests should run without network access and without an LLM.

### Unit Tests

Add Rust unit tests near the modules they exercise:

- `render`: stable field order, literal-block indentation, argv ordering,
  input/output list rendering, conservative allowed-action defaults, and
  provenance behavior.
- `envelope`: start/end marker extraction, missing marker diagnostics,
  mismatched markers, nested marker rejection, `--expect-count`, and
  `--expect-none`.
- `task_lint`: required fields, target syntax, `mode: agentic`, required safety
  text, `delegation.execution: subagent`, `delegation.recursive: true`, and all
  four recursive delegation triggers.
- `result_lint`: required fields, unique `target`/`status`, allowed statuses,
  failed/blocked error blocks, report-only rejection of task-like fields, and
  required-file checks.
- `config`: built-in/project/target/frontmatter/CLI precedence, `.jagt`
  discovery, explicit env interpolation, allowlist enforcement, and secret
  rejection.

Prefer test-first for each new callable surface. If a red test is awkward for a
new parser boundary, write the smallest CLI integration test first and then add
inner unit coverage as soon as the internal shape exists.

### CLI Integration Tests

Use `assert_cmd`, `predicates`, and `tempfile` under `tests/`.

Required deterministic CLI flows:

- `jagt render ... --prompt-text ...` emits byte-for-byte stable output.
- Rendered task output piped to `jagt lint -` succeeds.
- Invalid fixtures fail with precise diagnostics and non-zero exit codes.
- `jagt lint --expect-none` succeeds on ordinary command output and fails when
  an `AGENT_TASK v1` block appears.
- Config plus prompt/frontmatter produces the same effective packet every run.
- `jagt explain task` reports source precedence without rewriting files.
- `jagt result lint` validates success, partial proposed-task, blocked, failed,
  target mismatch, status mismatch, report-only rejection, and required-file
  checks.

### Contract Fixture Parity

Keep canonical fixtures derived from the skill-local Just contract:

- source: `.agents/skills/gtw/references/just_command_contract.md`
- fixtures: `fixtures/contract/agent_task` and `fixtures/contract/agent_result`

The Rust linter must accept the canonical contract examples. When Rust behavior
is stricter than the copied shell validators in `tools/reference/`, add an
explicit fixture and a short note explaining why.

The shell validators may be used as test oracles during development, but the
Rust implementation must not shell out to them.

## Live Agent Integration Labs

Live labs are not ordinary unit tests. They exercise the host LLM behavior that
the Rust process cannot simulate. They should be explicit, slower, transcript
based, and opt-in outside `just verify` unless a stable local agent runner is
available.

### Fresh AGENTS Lab

Create a fresh temporary folder for each live lab. The lab bootstrap should
write an `AGENTS.md` that copies the relevant agentic Just language from:

```text
.agents/skills/gtw/references/just_command_contract.md
```

The copied language must include:

- `AGENT_TASK v1` as a subagent handoff packet;
- required validation before acting on a packet;
- recursive handling of nested agentic Just calls, agentic dependencies,
  hook-triggered packets, and agentic verification targets;
- `AGENT_RESULT v1` as report-only;
- proposed recursive tasks as data that the parent may approve and render as a
  fresh child `AGENT_TASK v1`.

The fresh folder should also contain:

- a `Justfile` target that invokes the local `jagt` binary;
- a prompt file or inline message fixture;
- an expected transcript layout;
- a validator script that checks saved artifacts after the LLM run.

This lab catches the behavior the deterministic tests cannot: whether the LLM
sees a packet emitted by a command, treats it as a handoff boundary, and does
not silently execute the delegated work inline.

### Agent Reaction Lab

The first live lab lives in `integration_tests/live_agent_reaction/` and checks
the single-hop handoff boundary:

1. Bootstrap a fresh folder with the copied `AGENTS.md`.
2. Provide a `Justfile` target such as `count-message-agentic` that runs
   `jagt render count-chat-message-words ...`.
3. Ask the LLM agent to run that target.
4. Save the emitted packet as `01-rendered-task.agent-task.txt`.
5. Require the agent transcript to show that it validated the packet and
   delegated the parsed task instead of counting inline.
6. Validate the rendered packet with `jagt lint` and reject transcripts where
   the parent executed the delegated count inline.

The validator should reject transcripts where the parent computes the answer
inline after seeing `AGENT_TASK v1`.

### Sequential Recursive Lab

The recursive lab lives in
`integration_tests/live_agent_result_recursive/`. It is sequential in the test
harness even though it proves the recursive protocol boundary. It follows the
same trampoline pattern as
`agent_gest_git_skills/docs/live_agent_result_recursive_lab.md`:

1. Parent task: `count-chat-message-words`.
2. Planner subagent returns `status: partial` with
   `outputs.proposed_tasks`, a `wc -w` tool hint, and
   `orchestration.mode: parent-orchestrated`.
3. Parent validates the planner result, applies normal safety rules, and uses
   `jagt render` to create a fresh child `AGENT_TASK v1`.
4. Worker subagent runs the deterministic `wc -w` task and returns
   `status: success`.
5. Parent validates the worker result and records a final
   `AGENT_RESULT v1` with `outputs.recursion_trace`.
6. Unsafe proposal guard: an unsafe proposed command is refused, no worker is
   spawned, and a decision artifact records `decision: refused`.

Expected transcript artifacts:

```text
user_message.txt
01-parent-task.agent-task.txt
02-planner-result.agent-result.txt
03-child-task.agent-task.txt
04-worker-result.agent-result.txt
05-parent-final.agent-result.txt
06-unsafe-proposal.agent-result.txt
07-unsafe-decision.txt
```

The validator checks all task/result envelopes, compares worker and parent word
counts against `wc -w`, requires planner/worker role markers, requires the
recursion trace, and proves no unsafe worker artifact exists. A deterministic
Rust integration test exercises the bootstrap and validator with representative
saved transcript artifacts; running a real LLM agent through the lab remains
opt-in.

## Command Contract Implications

The normal gate remains:

```bash
just test
just verify
```

When live labs are added, expose them separately so they never surprise normal
CI:

```bash
just integration-live-agent <lab-dir>
just integration-live-recursive <lab-dir>
```

If those Just recipes are added, update `AGENTS.md` and the project command
contract in the same change.
