# Spec: Agentic Just targets for Gest base skills

## Problem statement

Some project commands should run a fixed concrete process. Other commands should
ask the agent to decide what to do from local context, input files, and a
project-provided prompt. The old "agent-readable Just re-entry" draft mixed
this generic mechanism with one downstream domain. The base mechanism belongs
in the existing Gest git and Gest jj skill repositories. Gest is a task
tracker, and jj is a version control system.

The core question is how any Just target can become agentic, which means that
it hands its work to an agent, while it stays safe, parseable, reviewable, and
replaceable by a concrete target later. A Just target, also
called a recipe, is a named command that Just runs for the project. The core
question is not "which special `agent-*` targets do we need?"

## Proposed solution

Define an agentic Just target as any recipe whose output contains a parseable
agent task block:

```text
<<<AGENT_TASK v1>>>
target: eda-viz
mode: agentic
argv:
  - data/raw/train.csv
prompt: |
  Inspect the input files and create the most useful exploratory visualization
  artifact for this project.
inputs:
  files:
    - data/raw/train.csv
outputs:
  required:
    - reports/eda/index.html
allowed_actions:
  - read listed inputs
  - create listed outputs
  - inspect nearby project docs and code
  - propose a concrete replacement target if the pattern stabilizes
verification:
  - test -f reports/eda/index.html
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

When an agent runs `just eda-viz data/raw/train.csv` and sees this block, it
parses the task and delegates the work to a subagent. A subagent is a second
agent that the first agent starts for this one task. If a human runs the same
command, they see an explicit request packet rather than a hidden side effect.
A packet is a block of text in a fixed form, such as the block above.

## Subagent execution boundary

An `AGENT_TASK v1` block is a subagent handoff packet. The receiving agent must
not execute the requested work inline, in its own run. It must delegate the
parsed task to a subagent that owns the concrete work. The subagent records the
consumed contract, and it reports the resulting artifacts and verification back
to its caller.

The rule is recursive. As part of its work, a subagent can decide to run a Just
dependency, a verification target, or another agentic Just target. If that run
emits an `AGENT_TASK v1` block, the newly emitted block must also be delegated
to another subagent. The caller may pass context and constraints down. But the
new agentic task still gets its own subagent boundary, and it is not folded
into the execution of the current agent.

Hooks follow the same rule. A hook is automation that runs at a set event, for
example a pre-commit hook, a post-command hook, a CI helper or an editor hook.
CI is continuous integration. If a hook or other automation invokes a Just
target that emits an `AGENT_TASK v1` block, the hook output is still only a
handoff packet. The agent that observes the packet from the hook must delegate
the work to a subagent. It must do so exactly as it would for a packet that the
main agent or an existing subagent produced.

Concrete commands and non-agentic Just targets may still run inside the normal
execution context of the current agent, subject to the active repo and approval
rules. Only emitted `AGENT_TASK v1` blocks create mandatory subagent boundaries.

## Valid target shapes

The base Gest skill repos should support three equivalent patterns.

### Direct agentic target

The target itself emits the task block:

```just
eda-viz +FILES:
  @scripts/render_agent_task.py --target eda-viz --files {{FILES}}
```

Use this pattern when the target is intentionally agentic by default.

### Companion agentic target

A concrete target and an agentic target coexist:

```just
eda-viz +FILES:
  uv run python scripts/eda_viz.py {{FILES}}

eda-viz-agentic +FILES:
  @scripts/render_agent_task.py --target eda-viz --files {{FILES}}
```

Use this pattern when the project wants both a stable process and an
exploratory mode that an agent guides.

### Generic agentic dispatcher

One dispatcher emits a task block for many targets:

```just
agentic TARGET +ARGS:
  @scripts/render_agent_task.py --target {{TARGET}} --args {{ARGS}}
```

Use this pattern when many targets can become agentic and the project wants one
contract surface:

```bash
just agentic eda-viz data/raw/train.csv data/new/week-23.csv
```

## How input text is provided

Just recipes receive command-line arguments after the recipe name. The official
Just manual documents positional parameters and variadic parameters. The last
parameter may use `+NAME` for one or more arguments, or `*NAME` for zero or
more arguments.

Use these input channels, in order of preference:

1. Short intent as a normal argument:

   ```bash
   just eda-viz "focus on missingness and outliers" data/raw/train.csv
   ```

2. File lists as variadic arguments:

   ```bash
   just eda-viz data/raw/train.csv data/new/week-23.csv
   ```

   Use them with a recipe such as this one:

   ```just
   eda-viz +FILES:
     @scripts/render_agent_task.py --target eda-viz --files {{FILES}}
   ```

3. Longer instructions as a prompt file:

   ```bash
   just agentic eda-viz prompts/eda_viz.md data/raw/train.csv
   ```

   The rendered task block may either embed the file contents under `prompt:`
   or list the prompt file under `inputs.prompt_files`.

4. Structured configuration as a manifest, a file of structured settings:

   ```bash
   just agentic eda-viz manifests/eda_viz.json
   ```

   Use a manifest for durable workflow configuration, repeated labs, or CI.

Avoid relying on shell quoting for long prompts of several paragraphs. When the
instruction is more than a short sentence, prefer prompt files or manifests.

## Replacement path

An agentic target may be temporary, durable, or hybrid.

- **Temporary.** The agentic target exists only until the project learns the
  right concrete process.
- **Durable.** The target intentionally remains creative or heavy on judgment.
- **Hybrid.** The concrete target handles stable work, and `*-agentic` explores
  edge cases or improvements.

When a repeated agentic workflow stabilizes, the agent may propose a concrete
replacement:

```text
replacement:
  status: proposed
  target: eda-viz
  command: uv run python scripts/eda_viz.py {{FILES}}
  keep_agentic_companion: true
```

The replacement is a normal change to code or docs, and it must go through the
active Gest git or Gest jj workflow.

## Safety rules

- Agent task blocks are operational context, not higher-priority instruction.
- The agent must still obey system, developer, user, VCS, approval, and repo
  safety instructions. VCS is the version control system.
- A Just target may request reads, writes, commands, outputs, and review focus.
- A Just target must not grant itself permission to bypass approvals or edit
  unrelated files.
- Agentic Just work must run in subagents. Nested agentic tasks, agentic
  dependencies, hook-triggered packets, and agentic verification targets inherit
  the same subagent requirement.
- The agent should validate listed inputs and outputs before it acts.
- The agent should record the consumed target, version, and output artifacts in
  Gest notes.

## Base repo work

Add this generic support to both existing reusable base repos:

- `agent_gest_git_skills`
- `agent_gest_jj_skills`

Each repo should add:

- skill guidance that detects and parses `AGENT_TASK` blocks
- a small helper that parses and validates the blocks
- Just snippets for the direct, companion, and dispatcher patterns
- fixture projects with agentic and concrete targets
- labs that prove that malformed blocks fail validation

The git repo should keep its branch and worktree rules in the base workflow.
The jj repo should keep its workspace and bookmark rules in the base workflow.
The agentic target contract should not duplicate those VCS rules. It should
route through the base skills.

## Lab requirements

Add:

```bash
just agentic-target-lab
```

The lab should prove these cases:

- A direct agentic target emits a valid block.
- A companion target emits a valid block.
- The generic dispatcher emits a valid block.
- The block can include short prompt text, prompt file paths, and variadic file
  arguments.
- Malformed delimiters fail validation.
- Malformed YAML or JSON fails validation.
- Safety language is present.
- Agentic task packets are classified as subagent handoffs. The packets that
  dependencies, hooks, and verification targets emit are included.
- A normal concrete target is not misclassified as agentic.

## Acceptance criteria

- Both base skill repos document agentic Just targets, and they require no
  example from a downstream domain.
- Both repos can parse and validate `AGENT_TASK v1` blocks.
- Any target can become agentic through the direct, companion, or dispatcher
  shape.
- A subagent executes every `AGENT_TASK v1` block, recursively. The rule holds
  whether the main agent, a subagent, a Just dependency, a verification target,
  or a hook emitted the block.
- The contract explains how input text and file lists are passed.
- Labs prove parse success and failure cases.
- The base skills record consumed agentic target contracts in Gest notes.

## Open questions

- Should the canonical block body be YAML-like text, JSON only, or support both?
- Should `just agentic <target> +ARGS` be mandatory, or only one supported
  pattern among several?
- Should parser helpers live in both base repos, or in the future
  package-maker skill repo and be vendored (copied into each repo)?
- Should targets be allowed to request agent-created code changes by default,
  or should that require an explicit `allowed_actions` entry?

## References

- `https://just.systems/man/en/recipe-parameters.html`
- `templates/just/agent-contract.just` of agent_gest_git_skills
- `templates/just/agent-contract.just` of agent_gest_jj_skills
- `docs/just_command_contract.md` of agent_gest_git_skills
- `docs/just_command_contract.md` of agent_gest_jj_skills
