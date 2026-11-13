---
name: gpl
description: Gest Plan. Decompose a spec, outline task, or GitHub-backed initiative into Gest tasks, dependencies, phases, and session/development iterations.
license: MIT, copyright (c) 2026 Rahul Dave. The full text is in the LICENSE file of https://github.com/rahuldave/agent_gest_git_skills
---

# GPL: Gest Plan

Use to convert a spec or outline task into executable Gest structure.

## Integration and delivery policy

Read [the integration and delivery contract](references/integration_delivery_workflow.md)
for explicit branch roles, selected PR bases, independent review evidence,
CI gates, issue completion, installation provenance and safe cleanup. Apply it
throughout this skill; the repository default is not an implicit PR target.

## Inputs

Accept a Gest artifact ID, task ID, GitHub issue URL/number, or user-described
scope. Read the entity with `gest ... show --json` when possible.

## Gest Memory

Before decomposing work, search Gest for existing parents, sibling tasks,
follow-ups, and related iterations:

```bash
gest search "<scope/topic>" --all --json --limit 20
gest search "Follow-up <scope/topic>" --all --json --limit 20
gest task show <id-or-prefix> --json
gest task note list <id-or-prefix> --json
gest iteration show <id-or-prefix> --json
```

Reuse existing durable parents when they fit. Prefer linking new leaves into
the existing tree over creating a duplicate outline area.

## Decisions

1. Is this a session plan or development plan?
2. What is the outline parent?
3. What depth should new tasks have?
4. Which tasks are independent?
5. Which phases and `blocked-by` links are needed?
6. Which branch model and execution model should write tasks use?
7. Should GitHub metadata be attached?

## Output Structure

Create tasks with native `child-of` links:

- depth 1: `issue`
- depth 2: `subissue` or concrete implementation leaf
- depth 3: tiny subtasks only when useful

Create or update an iteration and add tasks with explicit phases. Tasks in the
same phase must be safe to run concurrently.

For every non-trivial write slice, decide or leave clear metadata placeholders
for:

```text
vcs.tool=git|jj
vcs.branch_mode=session-branch|development-branch|stacked-session|stacked-development|parallel-worktrees
vcs.execution=main-worktree|git-worktrees|jj-workspaces
vcs.parallel_allowed=true|false
vcs.branch=<branch-name>
vcs.workspace_path=<absolute-path>
```

Use stacked branch modes for multiple meaty dependent slices that should be
reviewed separately. Use `parallel-worktrees` only for independent slices that
will run at the same time in separate physical worktrees. Do not plan parallel
writes in one checkout. A stack of branches is sequential work. Each branch
starts from the branch below it, and `gh pr create --base <parent-branch>`
opens its PR.

Report task IDs, phase grouping, dependencies, and whether `gor` can parallelize
the work.

## Tag And Dependency Planning

Apply `references/tag_dependency_workflow.md` while decomposing work. For every planned leaf, record selected semantic tags and `classification.tags.reviewed=true` metadata. For code-facing phases, list the semantic contracts and `ast-grep` patterns implementers must check. If a tag search reveals coupled surfaces, split or link those surfaces before implementation starts.

## Select integration before splitting

Record the selected persistent `vcs.integration_branch`, immediate
`vcs.base_branch`, resolved `vcs.base_sha`, and `vcs.branch_role`. For a stack,
the bottom base is the integration target and each child base is its predecessor.
Plan CI and independent review per slice, plus a separate promotion PR if the
experiment will eventually enter mainline. Do not assume such promotion is part
of the current task.
