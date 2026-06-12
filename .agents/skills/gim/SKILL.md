---
name: gim
description: Gest Implement. Implement one concrete Gest task end to end by reading, claiming, splitting if too broad, editing, verifying, reviewing, formatting as appropriate, and completing it.
---

# GIM: Gest Implement

Use for one concrete implementable Gest task.

## Workflow

1. `gest task show <id> --json`
2. Inspect Gest memory for the task area: `gest task note list <id> --json`,
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
10. Make scoped edits when the chosen loop calls for production changes.
11. Run `gfm` for formatting, linting, typechecking, compile/static checks, and
   diff hygiene.
12. Run `gte` for focused unit/API regression tests, smoke checks, and
   integration/browser checks appropriate to the changed behavior. Any changed
   callable code needs tests; smoke checks alone are not enough.
13. For frontend/browser UI changes, run a browser spot check before handoff:
   inspect the actual page, exercise the changed interaction, and record what
   was checked. If the flow should be repeated, add or capture a follow-up for a
   durable integration test.
14. Run `gdo` when user docs, developer docs, workflow docs, examples, or command
   references are affected.
15. Run `grv` after every code change, even for quick development without a pull
   request. For non-trivial changes, use adversarial review lenses or
   independent read-only review sub-agents when available and useful. Fix or
   record findings before completion.
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

If the task is running in a GitButler-managed workspace, use current `but` CLI
write commands (`but branch new`, `but stage`, `but commit`, `but push`,
`but pr`) and do not use raw `git commit`, `git switch`, `git checkout`, or
branch-mutating git commands. Prefer `but status` and `but diff` when deciding
which branch owns a change.

Do not run parallel write work inside one GitButler workspace. If
`vcs.tool=git-butler` and `vcs.execution=gitbutler-workspace`, the task is
sequential. Parallel implementation requires separate physical worktrees with a
distinct `vcs.workspace_path` recorded for each task.

## Checks

Use the project command contract in `AGENTS.md`. Prefer `just` targets when the
project maps workflow concepts to them. For the reusable Just contract shape,
see `references/just_command_contract.md`. Typical concepts include:

```bash
just fmt [path]
just lint [path]
just typecheck
just static
just test [target]
just smoke
just dev [port]
just browser [url-or-flow]
git diff --check
```

If the project has no command contract yet, route to `gsu` before assuming
language-specific tools.

Use browser spot checks for frontend, UI, and interaction changes even before a
durable integration test exists. Before a browser check, ensure the app is
served through the project run-app contract, commonly `just dev [port]`, or
confirm that an existing server is already running. Use `integration_tests/`
scripts for repeated browser flows; if no durable script exists yet, record that
follow-up.

## Tag And Dependency Pass

Before editing code contracts, re-run the tag/dependency workflow from `references/tag_dependency_workflow.md`: confirm selected tags still fit, add missing semantic tags, and run `ast-grep` searches for callers, imports, components, selectors, routes, schemas, or other dependers. If a selected tag or depender search reveals coupled surfaces, expand the task or create/link a child task before implementation is complete. Completion notes for code-facing work should include `Tag classification:` and `Dependency impact:` lines.
