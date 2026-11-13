---
name: gor
description: Gest Orchestrate. Execute a phased Gest iteration, deciding per phase whether work should run sequentially or in parallel physical worktrees/subagents.
license: MIT, copyright (c) 2026 Rahul Dave. The full text is in the LICENSE file of https://github.com/rahuldave/agent_gest_git_skills
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
   - the branches of a stack run in order, from the bottom branch up, unless
     each task has its own physical worktree
   - read-only review, test-design, and reconnaissance tasks: may use
     sub-agents without separate worktrees when they do not write files or
     mutate Gest
5. Claim with:

```bash
gest iteration next <id> --claim --agent <agent-name> --json
```

Exit code 75 means no task is currently available.

6. For parallel work, create one git worktree per task with
   `just worktree-new NAME` (see "Tasker Variant And Worktrees" in gtw), attach
   it to the same Gest project, run implementation, and integrate results. Record the owned
   absolute `vcs.workspace_path`, topic `vcs.branch`, worker/task, selected
   integration branch and stack parent before dispatch. Record the primary
   checkout path and branch separately. After workers and their owned
   processes finish, retire only owned worktrees using the checks in
   `references/integration_delivery_workflow.md`.
   Preserve the primary checkout and unrelated or user-retained worktrees.
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
Writable sub-agents must have disjoint write scopes. Concurrent writable work
uses physical git worktrees, one for each agent.

Agentic Just targets add a mandatory delegation case: an emitted `AGENT_TASK v1`
block is a subagent handoff packet. The current agent validates the packet and
delegates the parsed task rather than running it inline. Nested agentic Just
calls, agentic dependencies, hook-triggered packets, and agentic verification
targets inherit the same recursive subagent boundary.

## Stacks With Plain Git

A stack is a chain of dependent branches. Each branch starts from the branch
below it, and each has its own PR. The branches of a stack share one checkout,
so a stack is sequential work and not a way to run several write agents.

Before you dispatch more than one writable task, read the metadata of the task
and the iteration for:

```text
vcs.execution=main-worktree
vcs.parallel_allowed=false
```

If those values apply, do not launch parallel write agents. Run the phase in
order, and switch to each branch with `git switch <branch>`.

Open the PR of
each branch with `gh pr create --base <parent-branch>`, from the bottom branch
up. After a change to a lower branch, run
`git rebase --update-refs --onto <lower-branch> <old-lower-tip>` on the top
branch, so the stack above it moves together. `<old-lower-tip>` is the lower
branch before the change, saved with `git rev-parse <lower-branch>`.
`<lower-branch>@{1}` is that commit only after one change. Restack where no
worktree holds a branch of the stack, because `--update-refs` skips such a
branch. Git 2.38 and later have `--update-refs`.

If the phase needs parallel work, make physical git worktrees first. Set the
metadata to `vcs.execution=git-worktrees`, with its own `vcs.workspace_path` for
each task. After the worktree tasks finish, merge the results into the intended
branch or stack in a separate step.

## Tag And Dependency Orchestration

Before dispatching phase work, make sure each child task has gone through the tag classification pass from `references/tag_dependency_workflow.md`. For code-facing tasks, workers should know which semantic contracts and `ast-grep` patterns must be checked. Dependent surfaces found by tags or `ast-grep` should be in the same task, a linked child task, or an explicit follow-up before completion.
