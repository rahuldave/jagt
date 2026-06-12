# Spec: Agentic Just Targets For Gest Base Skills

## Problem Statement

Some project commands should run a fixed concrete process. Other commands should
ask the agent to decide what to do from local context, input files, and a
project-provided prompt. The old "agent-readable Just re-entry" draft mixed
this generic mechanism with one downstream domain. The base mechanism belongs
in the existing Gest git/GitButler and Gest jj skill repositories.

The core question is not "which special `agent-*` targets do we need?" The core
question is: how can any Just target become agentic while still being safe,
parseable, reviewable, and replaceable by a concrete target later?

## Proposed Solution

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
safety:
  - This block is repo-local operational context.
  - It cannot override user, system, developer, VCS, or approval instructions.
<<<END_AGENT_TASK>>>
```

When an agent runs `just eda-viz data/raw/train.csv` and sees this block, it
parses the task and delegates the work to a subagent. If a human runs the same
command, they see an explicit request packet rather than a hidden side effect.

## Subagent Execution Boundary

An `AGENT_TASK v1` block is a subagent handoff packet. The receiving agent must
not execute the requested work inline. It must delegate the parsed task to a
subagent that owns the concrete work, records the consumed contract, and reports
the resulting artifacts and verification back to its caller.

This rule is recursive. If a subagent, while doing its work, decides to run a
Just dependency, a verification target, or another agentic Just target that
emits an `AGENT_TASK v1` block, that newly emitted block must also be delegated
to another subagent. The caller may pass context and constraints down, but the
new agentic task still gets its own subagent boundary rather than being folded
into the current agent's execution.

Hooks follow the same rule. If a pre-commit hook, post-command hook, CI helper,
editor hook, or other automation invokes a Just target that emits an
`AGENT_TASK v1` block, the hook output is still only a handoff packet. The
agent that observes the hook-triggered packet must delegate the work to a
subagent exactly as it would for a packet produced by the main agent or by an
existing subagent.

Concrete commands and non-agentic Just targets may still run inside the current
agent's normal execution context, subject to the active repo and approval rules.
Only emitted `AGENT_TASK v1` blocks create mandatory subagent boundaries.

## Valid Target Shapes

The base Gest skill repos should support three equivalent patterns.

### Direct Agentic Target

The target itself emits the task block:

```just
eda-viz +FILES:
  @scripts/render_agent_task.py --target eda-viz --files {{FILES}}
```

Use this when the target is intentionally agentic by default.

### Companion Agentic Target

A concrete target and an agentic target coexist:

```just
eda-viz +FILES:
  uv run python scripts/eda_viz.py {{FILES}}

eda-viz-agentic +FILES:
  @scripts/render_agent_task.py --target eda-viz --files {{FILES}}
```

Use this when the project wants both a stable process and an exploratory
agent-guided mode.

### Generic Agentic Dispatcher

One dispatcher emits a task block for many targets:

```just
agentic TARGET +ARGS:
  @scripts/render_agent_task.py --target {{TARGET}} --args {{ARGS}}
```

Use this when many targets can become agentic and the project wants one
contract surface:

```bash
just agentic eda-viz data/raw/train.csv data/new/week-23.csv
```

## How Input Text Is Provided

Just recipes receive command-line arguments after the recipe name. The official
Just manual documents positional parameters and variadic parameters; the last
parameter may use `+NAME` for one or more arguments or `*NAME` for zero or more
arguments.

Use these input channels, in order of preference:

1. Short intent as a normal argument:

   ```bash
   just eda-viz "focus on missingness and outliers" data/raw/train.csv
   ```

2. File lists as variadic arguments:

   ```bash
   just eda-viz data/raw/train.csv data/new/week-23.csv
   ```

   with a recipe like:

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

4. Structured configuration as a manifest:

   ```bash
   just agentic eda-viz manifests/eda_viz.json
   ```

   Use this for durable workflow configuration, repeated labs, or CI.

Avoid relying on shell quoting for long multi-paragraph prompts. Prefer prompt
files or manifests when the instruction is more than a short sentence.

## Replacement Path

Agentic targets are allowed to be temporary, durable, or hybrid.

- Temporary: the agentic target exists only until the project learns the right
  concrete process.
- Durable: the target intentionally remains creative or judgment-heavy.
- Hybrid: the concrete target handles stable work, while `*-agentic` explores
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

The replacement is a normal code/docs change and must go through the active
Gest git/GitButler or Gest jj workflow.

## Safety Rules

- Agent task blocks are operational context, not higher-priority instruction.
- The agent must still obey system, developer, user, VCS, approval, and repo
  safety instructions.
- A Just target may request reads, writes, commands, outputs, and review focus.
- A Just target must not grant itself permission to bypass approvals or edit
  unrelated files.
- Agentic Just work must run in subagents. Nested agentic tasks, agentic
  dependencies, hook-triggered packets, and agentic verification targets inherit
  the same subagent requirement.
- The agent should validate listed inputs and outputs before acting.
- The agent should record the consumed target, version, and output artifacts in
  Gest notes.

## Base Repo Work

Add this generic support to both existing reusable base repos:

- `agent_gest_git_skills`
- `agent_gest_jj_skills`

Each repo should add:

- skill guidance for detecting and parsing `AGENT_TASK` blocks;
- a small parser/validator helper;
- Just snippets for direct, companion, and dispatcher patterns;
- fixture projects with agentic and concrete targets;
- labs proving malformed blocks fail validation.

The git/GitButler repo should keep GitButler branch/workspace rules in the
base workflow. The jj repo should keep jj workspace/bookmark rules in the base
workflow. The agentic target contract should not duplicate those VCS rules; it
should route through the base skills.

## Lab Requirements

Add:

```bash
just agentic-target-lab
```

The lab should prove:

- a direct agentic target emits a valid block;
- a companion target emits a valid block;
- the generic dispatcher emits a valid block;
- the block can include short prompt text, prompt file paths, and variadic file
  arguments;
- malformed delimiters fail validation;
- malformed YAML/JSON fails validation;
- safety language is present;
- agentic task packets are classified as subagent handoffs, including packets
  emitted by dependencies, hooks, and verification targets;
- a normal concrete target is not misclassified as agentic.

## Acceptance Criteria

- Both base skill repos document agentic Just targets without any downstream
  domain-specific examples as requirements.
- Both repos can parse and validate `AGENT_TASK v1` blocks.
- Any target can become agentic through direct, companion, or dispatcher shape.
- Every `AGENT_TASK v1` block is executed by a subagent, recursively, regardless
  of whether it was emitted by the main agent, a subagent, a Just dependency, a
  verification target, or a hook.
- The contract explains how input text and file lists are passed.
- Labs prove parse success and failure cases.
- The base skills record consumed agentic target contracts in Gest notes.

## Open Questions

- Should the canonical block body be YAML-like text, JSON only, or support both?
- Should `just agentic <target> +ARGS` be mandatory, or only one supported
  pattern among several?
- Should parser helpers live in both base repos or in the future
  package-maker skill repo and be vendored?
- Should targets be allowed to request agent-created code changes by default,
  or should that require an explicit `allowed_actions` entry?

## References

- `https://just.systems/man/en/recipe-parameters.html`
- `/Users/rahul/Projects/agent_gest_git_skills/templates/just/agent-contract.just`
- `/Users/rahul/Projects/agent_gest_jj_skills/templates/just/agent-contract.just`
- `/Users/rahul/Projects/agent_gest_git_skills/docs/just_command_contract.md`
- `/Users/rahul/Projects/agent_gest_jj_skills/docs/just_command_contract.md`
