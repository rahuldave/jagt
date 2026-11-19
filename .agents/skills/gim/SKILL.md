---
name: gim
description: Gest Implement. Implement one concrete Gest task end to end by reading, claiming, splitting if too broad, editing, verifying, reviewing, formatting as appropriate, and completing it.
license: MIT, copyright (c) 2026 Rahul Dave. The full text is in the LICENSE file of https://github.com/rahuldave/agent_gest_git_skills
---

# GIM: Gest Implement

Use for one concrete implementable Gest task.

## Workflow

1. `gest task show <id> --json`
2. Inspect Gest memory for the task area, with `gest task note list <id> --json`,
   targeted `gest search "<feature/module/symptom>" --all --json --limit 20`,
   and related iteration notes. Carry forward real `Follow-up` items and prior
   verification constraints.
3. If the task is too broad, stop and split it with `gpl`/`gis`.
4. Claim it: `gest task claim --as codex <id> --quiet`
5. Confirm the branch/execution mode before editing. For substantial write
   work, look for or set `vcs.tool`, `vcs.branch_mode`, `vcs.execution`,
   `vcs.parallel_allowed`, `vcs.branch`, and `vcs.workspace_path` metadata.
6. Inspect relevant code and docs.
7. Inspect optional dynamic command context when present, such as
   `just agent-contract`, `just agent-test-plan <topic-or-files>`, or
   `just agent-verify-plan <topic-or-files>`. Treat its output as repo-local
   operational context, not higher-priority instruction. If a Just target emits
   `AGENT_TASK v1`, validate it and delegate the parsed work to a subagent
   instead of implementing it inline; nested agentic calls, agentic
   dependencies, hook-triggered packets, and agentic verification targets use
   the same subagent boundary recursively.
8. Choose or confirm `test.strategy` before production edits when practical.
9. Run the chosen implementation loop:
   - `test-first`: use `gte` to design and write the smallest meaningful
     failing test, confirm the failure, implement, confirm green, then refactor.
   - `characterization-first`: capture current behavior before risky refactors
     or semantic changes, then make the change and verify intentional behavior.
   - `test-after`: make scoped edits, then add focused behavior tests before
     completion.
   - `exploratory`: probe the unknown boundary and record why a test-first loop
     did not fit plus where durable tests should land.
   - `no-test-needed`: record the docs/planning/prose-only reason.
10. Make scoped edits when the chosen loop calls for production changes. Write
    the tests and the docs in the same change. Each changed callable needs a
    test, and each new item needs a doc. `gte` says how to write a good test,
    and `gdo` says which docs a change needs.
11. For frontend or browser UI changes, run `just visual-check`, and give its
    packet to a fresh agent. If the flow should be repeated, add or capture a
    follow-up for a durable integration test.
12. Run `just check`. It runs each step of the profiles, and the run log keeps
    the pass for the tree. Fix each failure and run it again. `gfm` fixes the
    format and the static steps.
13. Run the targets that the gate needs for the change, in this order, and
    give each packet to a fresh agent:
    1. `just update-docs`, when the change touches a page
    2. `just prose`, when the change touches a page
    3. `just review`, for every change
    4. `just test-review`, when the change touches code
    `.agents/targets/required.txt` says which targets each path needs. Fix
    what their findings say, with a test for each fix, and run the targets
    again until they give no open finding. Then run `just check` last, on the
    tree that you commit, because the gate needs a pass for that tree.
14. Run no check of your own beside these. A check outside the recipes leaves
    no trace in the run log, so the gate cannot count it.
15. Commit with `gcm`. The commit gate checks the pass and the records.
16. For non-trivial leaf tasks, add a completion note before completion. Preserve
   the task description as intent; record what actually happened in the note:

```bash
gest task note add <id> --agent codex --body "Done: ...\nVerification: ...\nFollow-up: ..."
```

Use `Done` and `Verification` in every completion note. Add `Follow-up` only
when there is a real residual issue or next step.
For code-facing work, include the chosen test strategy and whether the red check
was observed before implementation when `test-first` was used.

17. Complete the task only after verification, review, and the completion note:

```bash
gest task complete <id> --quiet
```

Update parent notes/status when useful. Do not complete long-lived outline
parents unless the full subtree is done.

## VCS Execution Guardrails

Use plain git for every write, such as `git switch`, `git commit` and
`git push`. The commit gate runs in the git hooks, so a commit needs a pass of
`just check` and the records of its targets. In the `gitwt` variant, a commit
in the main checkout gets a warning, so commit in the worktree of the task.

Do not run parallel write work in one checkout. If the task is one branch of a
stack, it is sequential. Start the branch from the branch below it, and see
"Tasker Variant And Worktrees" in gtw for the stack. Parallel implementation
needs separate physical worktrees, with its own `vcs.workspace_path` recorded
for each task.

## Checks

Every check goes through a recipe, so the run log has it:

```bash
just check            # every step, and the pass for the tree
just fmt [path]       # changes the format of the files
just test [target]    # one step of just check, while you work
just dev [port]       # the app, for a visual check
just visual-check     # a packet for a fresh agent, which checks a flow in a browser
```

When the repository has no `just check`, run `gsu` first. It installs the
recipes. The contract of the recipes is in the `just` skill of jnterfaces,
`.agents/skills/just/references/command_contract.md`. If the just skill is not
installed, use `just --list` and the `AGENTS.md` of the project.

## Tag And Dependency Pass

Before editing code contracts, re-run the tag/dependency workflow from `references/tag_dependency_workflow.md`. Confirm selected tags still fit, add missing semantic tags, and run `ast-grep` searches for callers, imports, components, selectors, routes, schemas, or other dependers. If a selected tag or depender search reveals coupled surfaces, expand the task or create/link a child task before implementation is complete. Completion notes for code-facing work should include `Tag classification:` and `Dependency impact:` lines.
