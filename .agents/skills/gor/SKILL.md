---
name: gor
description: Gest Orchestrate. Execute a phased Gest iteration, deciding per phase whether work should run sequentially or in parallel physical worktrees/subagents.
---

# GOR: Gest Orchestrate

Use for a phased iteration. Works for both session and development iterations.

## Workflow

1. Read iteration:

```bash
gest iteration show <id> --json
gest iteration status <id> --json
gest iteration graph <id>
gest project --json
```

2. Read Gest memory for the iteration's area: inspect notes on current tasks
   and targeted `gest search "<area/topic>" --all --json --limit 20` hits,
   especially unresolved follow-ups and previous verification notes.
3. Group tasks by phase.
4. Decide execution strategy:
   - single task: run `gim` locally
   - dependent tasks: run sequentially by phase
   - independent code-touching tasks: use physical git worktrees/subagents
   - GitButler-managed workspace tasks: run sequentially unless each task has a
     distinct physical worktree
   - read-only review, test-design, and reconnaissance tasks: may use
     sub-agents without separate worktrees when they do not write files or
     mutate Gest
5. Claim with:

```bash
gest iteration next <id> --claim --agent <agent-name> --json
```

Exit code 75 means no task is currently available.

6. For parallel work, create one git worktree per task, attach it to the same
   Gest project, run implementation, integrate results, and clean up. Record
   `vcs.workspace_path` metadata for each writable task when practical.
7. Advance phases only after current-phase tasks are terminal.
8. Report successes, failures, and remaining tasks.

Do not parallelize just because there are multiple tasks. Parallelize only when
task independence and file ownership make it useful.

## Sub-Agent Roles

Distinguish sub-agent roles before dispatch:

- **write agents** implement code/docs and need isolated execution when running
  concurrently.
- **review agents** inspect diffs, tests, docs, VCS safety, or PR state and
  return findings first.
- **test-design agents** propose the smallest meaningful failing or
  characterization tests before implementation.
- **reconnaissance agents** map code, prior Gest memory, or dependency impact
  without editing.

Gest mutations, task completion, commit/push decisions, and PR decisions should
remain centralized unless a role is explicitly assigned those responsibilities.
Writable sub-agents must have disjoint write scopes. In Git/GitButler repos,
concurrent writable work uses physical git worktrees, not GitButler parallel
lanes.

Agentic Just targets add a mandatory delegation case: an emitted `AGENT_TASK v1`
block is a subagent handoff packet. The current agent validates the packet and
delegates the parsed task rather than running it inline. Nested agentic Just
calls, agentic dependencies, hook-triggered packets, and agentic verification
targets inherit the same recursive subagent boundary.

## GitButler Guardrail

GitButler parallel branches and stacked branches share one managed workspace.
They are useful for sequential branch curation, but they are not the execution
primitive for multiple write agents.

Before dispatching more than one writable task, inspect task/iteration metadata
for:

```text
vcs.tool=git-butler
vcs.execution=gitbutler-workspace
vcs.parallel_allowed=false
```

If those values apply, do not launch parallel write agents. Run the phase
sequentially, using `but status`, explicit branch targets, and current `but`
commands. If the phase truly needs parallelism, create physical git worktrees
first and update metadata to `vcs.execution=git-worktrees` with a distinct
`vcs.workspace_path` per task. After worktree tasks finish, integrate the
results back into the intended branch or stack in a separate sequential step.

## Tag And Dependency Orchestration

Before dispatching phase work, make sure each child task has gone through the tag classification pass from `references/tag_dependency_workflow.md`. For code-facing tasks, workers should know which semantic contracts and `ast-grep` patterns must be checked. Dependent surfaces found by tags or `ast-grep` should be in the same task, a linked child task, or an explicit follow-up before completion.
