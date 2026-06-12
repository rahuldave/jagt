# Gest-Codex Workflow

Last updated: 2026-05-04.

This document defines how Codex should use Gest, GitHub, and the local skill
family while working in a Gest-tracked repository. The goal is to preserve
creative flow without losing a durable task tree.

## Core Model

Every substantial request becomes Gest-tracked work. The tracker records both
durable product structure and the concrete work done in a session.

There are four distinct concepts:

- **GitHub issue**: external, human-visible durable intent.
- **Development iteration**: a Gest execution plan for larger scoped work,
  usually attached to a GitHub issue and possibly spanning many sessions.
- **Session iteration**: a Gest execution plan for the current chat/session,
  including exploratory or tactical tasks.
- **Outline task**: a durable Gest task in the internal task tree. User requests
  should be parented under the best existing outline task, or a new outline task
  should be created when needed.

The mode of an iteration does not determine whether work can run in parallel.
Parallelism depends on task independence, file overlap, and risk.

Workflow mode also does not determine how tests are written. Treat these as
orthogonal axes:

```text
workflow.kind=session|development
test.strategy=test-first|test-after|characterization-first|exploratory|no-test-needed
test.scope=focused|regression|integration|browser|full
review.depth=solo|adversarial|multi-agent
language.profile=python|ruby|typescript|go|rust|mixed|unknown
contract.source=agents-md|just-agent-contract|manual
```

Session work may use `test-first` when the behavior is small and clear, such as
a regression fix. Development work may begin with `characterization-first` or
`exploratory` when the code needs to be understood before a good red/green loop
exists. Development mode raises the expected breadth of verification and review;
it does not force one test strategy.

## Branch, Stack, And Worktree Policy

Main should stay integration-ready. Any Gest-tracked workflow that writes files
should choose an explicit VCS execution mode before editing. Keep two decisions
separate:

- **branch model**: how the work will be reviewed and integrated
- **execution model**: where agents are allowed to write

Use branch names keyed to the highest meaningful Gest task for the current
workstream, not necessarily the permanent product root:

```text
gest/<task-id-short>-two-word-summary
session/<task-id-short>-two-word-summary
```

Use these branch modes:

- `session-branch`: one tactical session branch. Good for a small session leaf
  or several small related session edits under one parent.
- `development-branch`: one durable branch for one coherent feature, bug, or
  workflow change. Multiple commits are fine when they are useful checkpoints.
- `stacked-session`: multiple meaty dependent session slices that should remain
  separately reviewable.
- `stacked-development`: multiple meaty dependent development slices that should
  become stacked branches or stacked PRs.
- `parallel-worktrees`: multiple independent meaty slices worked at the same
  time in separate physical worktrees.

Use these execution modes:

- `main-worktree`: one agent writes in the current checkout.
- `git-worktrees`: one git worktree per parallel task.
- `gitbutler-workspace`: one sequential agent in the GitButler-managed
  workspace.
- `jj-workspaces`: one jj workspace per parallel task, if the project is using
  jj.

GitButler stacks are based on GitButler's applied branch workspace model. That
is good for sequential stack curation, but not for multiple agents writing to
the same working tree. Therefore:

- never run parallel write agents in one `gitbutler-workspace`
- never use GitButler parallel lanes as the agent parallelism primitive
- if work must be parallel, use physical `git-worktrees` first and integrate the
  results into a branch or stack afterward
- when working inside GitButler mode, use current `but` CLI writes such as
  `but branch new`, `but stage`, `but commit`, `but push`, and `but pr`; do not
  use raw `git commit`, `git switch`, `git checkout`, or branch-mutating git
  commands

Default integration:

- simple branches: rebase onto the target branch, then fast-forward or squash
  when appropriate
- GitButler stacks: review/merge bottom-up; GitHub merge commits are acceptable
  for stack ergonomics when using GitButler-managed stacked PRs
- parallel worktrees: integrate each finished worktree intentionally before
  starting dependent follow-on work

Record branch and execution state in Gest metadata when work is more than a
tiny local edit:

```text
vcs.tool=git|git-butler|jj
vcs.base_branch=main
vcs.base_sha=<sha>
vcs.branch_mode=session-branch|development-branch|stacked-session|stacked-development|parallel-worktrees
vcs.execution=main-worktree|git-worktrees|gitbutler-workspace|jj-workspaces
vcs.parallel_allowed=true|false
vcs.branch=<branch-name>
vcs.stack_root=<branch-name>
vcs.stack_parent=<branch-name>
vcs.stack_index=<n>
vcs.workspace_path=<absolute-path>
vcs.integration=fast-forward|squash|rebase|merge|stacked-pr|local-only
vcs.owner_session=<thread-or-agent-label>
vcs.write_scope=<paths-or-subsystems>
test.strategy=test-first|test-after|characterization-first|exploratory|no-test-needed
test.scope=focused|regression|integration|browser|full
review.depth=solo|adversarial|multi-agent
language.profile=python|ruby|typescript|go|rust|mixed|unknown
contract.source=agents-md|just-agent-contract|manual
```

`vcs.parallel_allowed=false` is required when
`vcs.tool=git-butler` and `vcs.execution=gitbutler-workspace`. Parallel claims
are allowed only when each writable task has a distinct physical
`vcs.workspace_path`, such as separate git worktrees.

## Task Hierarchy

Gest parent tasks are represented with native `child-of` / `parent-of` links.
Tags help filtering, but links are the source of truth for hierarchy.

Preferred depth:

```text
depth 0: product area / GitHub-scale initiative
depth 1: coherent feature, subsystem, or workstream
depth 2: concrete implementable task
depth 3: tiny tactical subtask, only when useful
```

Every concrete implementation task should have a parent unless it is truly
standalone. Long-lived outline parents may remain open across multiple sessions.
Do not complete a parent just because one session leaf is done.

For multi-stage substantial work, create a small GTW-owned task treelet. The
parent represents the user request. Child leaves represent the stage commands
that are separately verifiable, for example `gsp`, `gpl`, `gim`, `gfm`, `gte`,
`gdo`, `grv`, `gpr`, and `gcm`. Do not create busywork tasks for trivial stages,
but do record in the completion note which stages ran or were intentionally
skipped.

## Classification

Before editing files, Codex decides which class fits the request:

- **Session leaf only**: tiny, tactical, unlikely to matter after the session.
- **Session leaf under existing outline**: small work that clearly belongs under
  a durable product/workflow area.
- **New outline task plus session leaves**: new durable area, but not yet worth a
  GitHub issue or formal spec.
- **Development iteration**: larger scoped effort with acceptance criteria,
  phases, possible parallel work, likely GitHub visibility, or multi-session
  continuation.

Promote session-shaped work to development when it needs a spec/design decision,
spans multiple sessions, should be visible on GitHub, has multiple durable
acceptance criteria, creates a reusable product area, or requires staged
delivery.

## Specs

Create a Gest spec artifact when the request needs product/design shaping before
implementation. A spec is appropriate when:

- the desired behavior is not yet clear
- there are several approaches with trade-offs
- acceptance criteria need to be negotiated
- the work affects multiple systems or future workflows
- GitHub-visible development is likely

When a spec is created, implementation should happen in follow-on Gest tasks.
Do not bury implementation work inside the spec artifact itself.

## GitHub Promotion

GitHub issues are for durable external visibility, not for every leaf task.
Promote work to GitHub when it is user-visible, architecture-relevant,
multi-session, release-worthy, or worth tracking outside the local Gest ledger.
For development depth-1 parents and development iterations, the GitHub decision
is mandatory: create or sync the issue with `gpr`, or record why the work is
staying local.

When a GitHub issue exists, store it as metadata on both the development
iteration and the top-level outline task when applicable:

```text
github.issue=<number>
github.url=<url>
workflow.kind=development
outline.root=<gest-task-id>
```

GitHub is visibility. Gest remains the local execution ledger.

## Tag And Dependency Impact

Before creating or splitting tasks, classify the request against the existing
Gest tag vocabulary. Record `classification.tags.reviewed=true`,
`classification.tags.new=<comma-separated-new-tags>`, and
`impact.ast_grep.required=true|false` where relevant. Use
`tag_dependency_workflow.md`.

For code-facing work, use `ast-grep` to inspect semantic dependers of changed
contracts. If a tag or dependency search reveals coupled surfaces, expand the
current task or create/link child tasks before implementation is complete.

## Testing Strategy

`gte` owns both test design and test execution. For implementation tasks, choose
and record a strategy before editing production code when practical:

- `test-first`: write the smallest meaningful failing test, run it to confirm a
  useful red failure, implement, confirm green, refactor, then run broader
  checks.
- `characterization-first`: capture current behavior before refactoring,
  migration, or risky semantic change.
- `test-after`: implement first only when test-first is awkward or the expected
  behavior is still forming; add focused behavior coverage before completion.
- `exploratory`: probe unknown APIs, UI affordances, or tooling; record why
  test-first does not fit and what later test boundary should be created.
- `no-test-needed`: docs-only, planning-only, or pure workflow prose, with a
  concrete reason.

For bug fixes, parsers, exports, imports, persistence, APIs, and shared
contracts, prefer `test-first` or `characterization-first` unless there is a
clear reason not to. Completion notes should include the strategy, focused
commands, broader commands, and any deferred test boundary.

## Adversarial Review

`grv` is the local review aggregator and should become adversarial for
non-trivial changes. It should review through distinct lenses:

- correctness and regression risk
- test adequacy, including whether new tests would fail on the old code
- Git/GitButler workflow safety
- docs, setup, and command-contract drift
- security, privacy, or data safety when relevant
- browser/UI behavior when relevant
- language/runtime idioms when the profile is known

Default to independent read-only review sub-agents when sub-agents are
available, authorized, and the lenses can be checked independently. If
sub-agents are not used, Codex should still apply the lenses explicitly and
record why local review was sufficient. Gest mutations and checkpoint decisions
should remain centralized unless deliberately assigned.

For reusable workflow changes, reviewers must preserve adapter boundaries:
plain Git branches, GitButler branches/stacks, and physical git worktrees are
different execution/review tools. Do not rewrite GitButler stack guidance into
jj bookmark semantics or treat GitButler parallel lanes as agent isolation.

## Tags

Use tags as filters, not as hierarchy.

Core workflow tags:

- `development`
- `session`
- `outline`
- `issue`
- `subissue`
- `github`
- `parent`
- `leaf`

Area tags:

- `close-reading`
- `workflow`
- `ai`
- `annotations`
- `ingestion`
- `export`
- `search`
- `ui`
- `db`
- `docs`
- `testing`

Work-type tags:

- `bug`
- `feature`
- `research`
- `design`
- `implementation`
- `verification`
- `cleanup`
- `regression`

Metadata should hold source-of-truth facts such as `workflow.kind`, `depth`,
`github.issue`, `github.url`, `outline.root`, `parent_task`, and `vcs.*`
branch/execution metadata.

## Completion Notes

Task descriptions are intent: what the task was created to accomplish. Do not
rewrite descriptions at completion just to record what happened.

For non-trivial completed leaf tasks, add a Gest task note before marking the
task done. Notes are first-class Gest data, appear in `gest task show` and the
web timeline, and sync under `.gest/task/notes/`.

Use this shape:

```text
Done: <one or two concrete sentences about what changed>
Verification: <commands/checks run, or why verification was limited>
Follow-up: <only if a real residual issue or next step remains>
```

Command pattern:

```bash
gest task note add <task-id> --agent codex --body "Done: ...\nVerification: ..."
gest task complete <task-id> --quiet
```

Use metadata for machine-queryable facts, for example changed files, GitHub
issue IDs, or verification command lists. Use notes for prose work logs. For
tiny mechanical tasks, the status transition and final chat summary may be
enough.

## Commit Cadence

Committing is VCS hygiene, not a Gest task by itself. Do not create a Gest task
whose only purpose is "make a commit" unless the Git history work is itself
substantial, such as splitting a messy changeset or recovering from a bad
history operation.

Session-mode work should not auto-commit every small leaf. Commit session work
when the user asks, when a coherent checkpoint would be useful, or when a
long-lived parent/subtree reaches a stable point. Small exploratory tasks may
stay uncommitted while the workflow is still moving.

Session classification alone is not a sufficient reason to skip `gcm`. A
verified slice is a commit-required checkpoint when it changes
deployment/runtime configuration, persistence, migrations, schemas, public APIs,
user-visible UI, reusable workflow material, publishable docs/templates, or a
non-trivial multi-file changeset. After verification and review, run
`git status --short --branch` before final response. If it shows Codex-owned
changes and any commit-required trigger applies, route through `gcm` before
handoff. If the worktree stays dirty intentionally, record the concrete
no-commit reason in the Gest note and final response.

Development-mode work should have stronger commit checkpoints:

- after a depth-1 feature/workstream or coherent depth-2 implementation subtree
  is complete and verified
- before switching to a substantially different product area
- before handing work to another agent/session
- after resolving a risky bug or migration where rollback clarity matters
- before pushing or syncing to a GitHub issue/PR

In development mode, do not merely ask the user whether each slice should be
committed. After completing and verifying a coherent depth-2 implementation
leaf or tightly related set of leaves, make the commit judgment yourself. If the
slice changes schema, persistence, query semantics, migrations, public APIs,
user-visible UI, or non-trivial verification, prefer committing it before
claiming the next implementation slice. Small design-only, exploratory, or
strictly dependent leaves may stay uncommitted until they combine into the next
coherent checkpoint.

When committing a slice, derive the commit body from the completed Gest task
notes: summarize `Done`, include `Verification`, mention real `Follow-up`
items, and cite changed subsystems or files when that helps future bisecting.
The commit message must not include Gest IDs. A future `git bisect` should land
on a narrow layer such as schema/indexing, repository/query behavior, UI, or
verification rather than a whole multi-layer feature.

When a commit is appropriate, inspect status/diff, stage explicit files, and use
`gcm`. Never use `git add .` by default. Never put Gest IDs in commit messages.
Use GitHub issue footers only when the relevant Gest metadata contains a real
GitHub issue and the commit semantically closes or references it.

Every Codex-created commit needs a separate push/sync decision. Do not treat
GitHub issue promotion as a substitute for `git push`. Before and after the
commit, inspect `git status --short --branch`; if the branch has an upstream
and the user has not asked for local-only work, push the verified checkpoint.
If the branch has no upstream, set one with `git push -u origin <branch>` or
the repo's equivalent; "no upstream" is not a no-push reason. If the branch is
still local or `ahead` at handoff, the checkpoint is incomplete unless a real
push blocker is explicit in the task note/final summary.

When Codex pushes changes to a branch other than the repository's mainline
branch, that push must be followed by a pull-request checkpoint: create or
update the PR for the branch, run `gpa` on that PR, report the PR review
findings/state to the user, and ask whether to merge. Only merge without a
second question when the user explicitly asked for the merge in the current
turn. For reusable workflow/template repo changes, push and PR creation are
required unless blocked; record the exact blocker instead of leaving the branch
only pushed.

After a PR is merged, inspect the repository's project instructions and command
contract for deploy/release expectations. If the repo defines a deploy command
for that kind of change, run it or record the exact blocker before handoff.

Before final response for substantial work, run a dirty-worktree gate for each
edited repo. A completed Gest task is not a substitute for a Git checkpoint. If
there are Codex-owned changes and a commit-required checkpoint trigger applies,
run `gcm` or explicitly document why no commit is being made.

## Checkpoint Hygiene

At every durable checkpoint, run the project hygiene that keeps later agents
oriented. Durable checkpoints include:

- any Git commit created by Codex
- closing a depth-1 task or product/workstream parent
- completing an iteration
- handoff after a substantial implementation session

Checkpoint steps:

1. Regenerate the overall Gest graph and a focused graph for the latest relevant
   iteration. Treat graph generation as a Gest database operation: do not run it
   in parallel with any `gest` command.
2. For user-visible, architecture-relevant, multi-session, or release-worthy
   work, decide whether GitHub promotion is appropriate. For development
   depth-1 parents and development iterations, this decision is mandatory. Use
   `gpr` to create/update the GitHub issue and write `github.issue` /
   `github.url` metadata back to Gest, or record the explicit reason promotion
   was skipped in the task note or final summary.
3. For every Codex-created commit, verify push state with
   `git status --short --branch`. If an upstream exists and the branch is
   ahead, push it or record the explicit local-only/blocker reason. Report the
   final branch relationship separately from the GitHub issue decision.
4. If Codex pushed a non-mainline branch, create/update its PR, run `gpa`,
   report the PR review findings/state, and ask before merge unless the user
   already explicitly asked for that merge.
5. For every code change, run an explicit review pass before task completion.
   Use `grv` or a code-review stance over the current diff/commit, then fix or
   record any findings before closing the leaf, parent, or iteration. Missing
   focused tests for changed callable code or APIs are review findings.
6. Verify the final Gest status after closing the parent or iteration and report
   the graph paths, commit hashes, push status, review status, and GitHub issue
   decision.

## Template Sync

Reusable workflow changes should not live only in one target workspace. When
changing the `g*` skills, `AGENTS.md` workflow guidance, Gest/Codex playbook, or
reusable tools such as `gest_mermaid_graph.py`, copy the reusable parts into the
version-controlled workflow template repository. Then check, commit, and push
that repository. The template repo is the source for workflow material that
should be mixed into other projects. Keep project-specific details out of the
template repo.

## Iterations And Phases

Iterations are execution plans. Phases are parallelism boundaries.

Use a **session iteration** for current-session work, including creative
experimentation. Use a **development iteration** for larger scoped work that may
span sessions or map to GitHub.

Do not hardcode every task to `--phase 1`. Assign phases deliberately:

- Phase 1: research, reproduction, or design
- Phase 2: implementation
- Phase 3: verification
- Phase 4: docs, publishing, or cleanup

Tasks in the same phase must be independent enough to run concurrently. If one
task blocks another, put them in different phases and add a `blocked-by` link.

## Parallel Work

Parallel work can happen in session or development iterations. Decide based on
the task graph, not the iteration kind.

Use git worktrees/subagents when tasks are independent, code-touching, and risky
to interleave in one working tree. Keep work local and sequential when tasks are
tightly coupled, small, or dependent on immediate context.

For parallel Gest orchestration:

1. Claim tasks with `gest iteration next <iteration-id> --claim --agent <name>`.
2. Create one git worktree per independent task when useful.
3. Run implementation in each worktree.
4. Merge or cherry-pick results before advancing to the next phase.
5. Clean up worktrees after verification.

Gest commands should be short and serialized where possible. In this workspace,
local `.gest/` sync can make read-looking commands perform database writes.

## Serialization And Storage

Current forked Gest builds from June 8, 2026 and later prefer project-local
storage for local projects:

```text
<project-root>/.gest/gest.db
```

This is the expected path when the project has `.gest/` and the user has not
set an explicit `database.url` or `storage.data_dir` override. In Codex, that
usually avoids sandbox write failures because the SQLite file is inside the
workspace writable root. Continue to serialize Gest commands because local sync
and SQLite writes can still conflict within one workspace.

Legacy or stock system Gest builds may still store the canonical data in:

```text
~/Library/Application Support/gest/gest.db
```

For those builds, the `.gest/` directory is a local sync mirror. The database is
the source of truth, but commands can import/export mirror changes. Debug output
has shown `sync import` running before `gest task list`.

Current SQLite pragmas observed locally:

```text
journal_mode=delete
busy_timeout=0
locking_mode=normal
```

Before the project-local fork, local and global modes both used the same global
database, so the readonly warning was not inherently a local-mode issue. The
recommended legacy permission normalization is:

```bash
chmod 755 ~/Library/Application\ Support/gest/
chmod 644 ~/Library/Application\ Support/gest/gest.db
```

Those permissions were already present locally. A non-escalated Codex run with
`GEST_LOG__LEVEL=trace` reproduced `attempt to write a readonly database` during
sync import, while the same trace run outside the sandbox did not. Treat that
warning as likely environment/sandbox-related unless it also reproduces in a
normal terminal.

In Codex, the legacy failure happens because the canonical Gest database is
outside the workspace writable roots. A command such as `gest task list` can
still write before listing because local sync imports mirrored `.gest/` state
into tables such as `authors`, `tags`, `tasks`, `relationships`,
`transactions`, and `sync_digests`.

Codex command policy:

- with the newer project-local fork, prefer `.gest/gest.db` and avoid sandbox
  escalation unless another path or command requires it
- with legacy or stock system Gest, run Gest mutations with `require_escalated`
  because they may need to write to the global database
- for read-looking Gest commands, retry with `require_escalated` if they emit
  `attempt to write a readonly database` or a sync-import readonly warning
- request or use a narrow approval prefix such as `["gest"]`
- keep Gest commands serialized even when escalated, except for deliberate
  `gest iteration next --claim` orchestration

Therefore:

- do not run Gest commands in parallel during normal Codex work
- use `--json` and `--quiet` for parseable outputs
- verify state after any `database is locked` or sync warning before retrying
- when diagnosing storage, check `gest --version`, `gest config show`, and
  whether `.gest/gest.db` exists before assuming the global path is canonical

## Deferred Hooks

The current workflow is intentionally skill-and-instruction driven. Do not add
blocking hooks until the workflow has been used enough to see what actually
helps and what gets in the way.

Hook ideas to revisit:

- **Session start**: inject a concise reminder of `gtw`, the `g*` skill family,
  session/development classification, outline parenting, GitHub promotion, and
  serialized Gest commands.
- **Pre-edit**: inject project-local style and testing guidance before source
  edits, for example `project docs/dev/code-style.md`, `project docs/dev/testing.md`, and
  project-specific invariants.
- **Pre-commit**: inject commit conventions, remind Codex never to include Gest
  IDs in commit messages, and only use GitHub issue footers when metadata
  exists.
- **Gest safety**: warn or block malformed Gest commands, such as creating a
  `subissue` without a `child-of` parent or running multiple Gest writes in
  parallel.
- **Worklog/session end**: capture concise session summaries or task notes when
  a long session ends.

Questions to answer after using the workflow:

- Which reminders do agents actually forget?
- Which checks are better as hooks versus `gtw` instructions?
- Should hooks live in project-local config, global Codex config, or both?
- Should hooks only inject context, or should any of them block commands?
- Do parallel worktrees need hook support for per-worktree context?

## Skill Family

User-invoked Gest skills use three-letter names beginning with `g`.

- `gtw`: Gest Track Work. Router/default skill for substantial work.
- `gbs`: Gest Brainstorm. Explore ideas and decide whether a spec or outline is
  needed.
- `gsu`: Gest Setup. Bootstrap or refresh tool choices, installs, ignore rules,
  command contracts, Justfile targets, and project setup docs.
- `gsp`: Gest Spec. Draft or update a Gest spec artifact.
- `gpl`: Gest Plan. Decompose a spec or outline task into tasks, phases, links,
  and iterations.
- `gis`: Gest Issue. Create or update durable Gest outline tasks.
- `gpr`: Gest Promote. Promote or sync durable Gest work with GitHub issues.
- `gim`: Gest Implement. Implement one concrete Gest task end to end.
- `gor`: Gest Orchestrate. Execute a phased iteration, sequentially or in
  parallel depending on task independence.
- `grv`: Gest Review. Review the current changeset.
- `gfm`: Gest Format. Run formatting, linting, typechecking, compile/static
  checks, and diff hygiene.
- `gte`: Gest Test. Run unit, regression, smoke, API, and integration tests.
- `gdo`: Gest Docs. Check, create, update, and verify user-facing,
  developer-facing, and in-code docs affected by the task.
- `gpa`: Gest PR Accept. Review and accept GitHub pull requests as the
  GitHub-facing checkpoint of Gest-tracked workstreams.
- `gcm`: Gest Commit. Create a Git commit tied to GitHub metadata when present.

Optional later skills:

- `gcl`: Gest Changelog.
- `gdc`: Gest Doc Code.
- `gps`: Gest Promote Spec.

`gtw` should route to these stages conceptually. The user may invoke any stage
directly, but ordinary requests can simply use `gtw` or natural language.

## Stage Responsibilities

### GTW

1. Inspect existing Gest state.
2. Classify request as session/development and spec/no-spec.
3. Choose or create the best outline parent.
4. Decide tags, metadata, and depth.
5. Decide if parallel work is useful.
6. Decide the branch model and execution model, recording `vcs.*` metadata for
   non-trivial writes.
7. Create/claim concrete leaf tasks before edits. For multi-stage work, create
   a treelet with child leaves for separately verifiable stage commands.
8. Route to the appropriate stage skill.
9. Complete leaf tasks after verification and report IDs.

### GBS

1. Explore existing code/docs/Gest context.
2. Ask clarifying questions when necessary.
3. Propose approaches and trade-offs.
4. Decide whether to create a spec, issue, plan, or session leaf.

### GSP

1. Draft problem, scope, proposed behavior, acceptance criteria, and open
   questions.
2. Review with the user when the direction is not settled.
3. Save as a Gest artifact tagged `spec`.
4. Link the artifact to outline tasks when appropriate.

### GPL

1. Read a spec, outline task, or GitHub-backed task.
2. Decide single-task vs multi-task decomposition.
3. Create depth 1/depth 2 tasks.
4. Assign explicit phases and blocking links.
5. Create or update session/development iterations.
6. Report parallelization opportunities.

### GIS

1. Draft user story, context, and acceptance criteria.
2. Create or update a durable Gest task.
3. Apply `outline`, `issue`, or `subissue` tags.
4. Link with `child-of` and set depth metadata.

### GPR

1. Read the task/iteration/spec to promote.
2. Sanitize internal details.
3. Draft GitHub issue body.
4. Ask user confirmation before `gh issue create` or `gh issue edit`.
5. Store GitHub metadata on Gest entities.

### GIM

1. Read and claim one concrete task.
2. Split it first if it is too broad.
3. Confirm the task's branch/execution mode before editing. In GitButler mode,
   use only `but` writes and keep execution sequential unless a physical
   worktree was assigned.
4. Implement minimal scoped changes.
5. Run `gfm` for mechanical checks.
6. Run `gte` for tests; changed callable code and APIs need focused tests.
7. Run `gdo` when user-facing docs, developer-facing docs, or in-code docs are
   affected.
8. Run `grv` after every code change.
9. Complete the leaf task and add parent notes/status updates.

### GOR

1. Read iteration status and graph.
2. Group tasks by phase.
3. Decide sequential vs parallel execution per phase.
4. Block shared GitButler workspace parallelism. If `vcs.tool=git-butler` and
   `vcs.execution=gitbutler-workspace`, run tasks sequentially even when they
   are in the same phase.
5. Use physical git worktrees/subagents for independent tasks when useful, and
   record each `vcs.workspace_path`.
6. Integrate results and advance phases.
7. Clean up worktrees and report failures.

### GRV

Review the current changeset for correctness, safety, regressions, style, and
test coverage. Findings come first. Run after every code change before task
completion.

### GFM

Run formatting, linting, typechecking, compile/static checks, and diff hygiene.
Fix mechanical issues. Do not use `gfm` as a substitute for tests.

### GTE

Run unit tests, API regression tests, smoke checks, and integration/browser
checks appropriate to the change. Browser spot checks are exploratory
implementation verification; durable browser integration tests are rerunnable
scripts or tests. Add tests when changed callable code lacks focused coverage.

### GDO

Check whether user-facing docs, developer-facing docs, or in-code docs are
needed, then create or update them. Prefer documented and typed code when it
clarifies callable behavior, public contracts, non-obvious domain logic, or
future maintenance.

### GPA

Review a GitHub pull request as an integration checkpoint. Gather PR metadata,
diff, commits, checks, review state, mergeability, branch state, and related
Gest tasks/artifacts/iterations. Produce findings first, then a Gest context
appendix, human review checklist, merge recommendation, and post-merge
bookkeeping plan. If the PR body lacks Gest context, offer to update it before
approval or merge.

Post-merge bookkeeping must restore a consistent local state, not merely mark
the GitHub PR merged. Before merge, verify the PR branch actually contains the
intended changes with `gh pr diff` or `git show --stat`; empty GitButler
commits and zero-change `WIP Assignments` commits are red flags. After merge,
plain-Git workstreams should fetch/prune remotes, switch to the merged base
branch, verify the local base and `origin/<base>` are equal, delete merged local
`session/*` and `gest/*` branches when they are not checked out elsewhere, and
confirm no open PRs remain for the workstream. GitButler workstreams must not
run raw branch-mutating Git while GitButler owns the workspace; run
`but teardown` first when the stack is done, then synchronize the base branch in
normal Git mode. Do not leave the user's terminal on `gitbutler/workspace`
unless active GitButler work is explicitly continuing.

### GCM

Inspect status/diff/log, draft a conventional commit, ask for confirmation when
needed, stage explicit files, and commit. In GitButler-managed workspaces, use
`but status`, `but diff`, `but branch list`, `but stage`, and `but commit`
instead of raw git writes. Include GitHub issue footers only when metadata
exists. Never include Gest IDs in commit messages.

## Project Defaults

Replace this section in each target repository with the project-specific command
contract. Prefer `just` targets when present, and document target arguments.
When creating or changing Just recipes, consult:

- Just dependencies: https://just.systems/man/en/dependencies.html
- Just skill reference: https://raw.githubusercontent.com/casey/just/refs/heads/master/skills/just/SKILL.md

For Just, dependency order is meaningful: dependencies run before the recipe
that depends on them, and in the listed order. Prefer native Just dependencies
for ordered recipe composition, such as
`verify: lint typecheck static test smoke diff-check`, instead of recursively
calling `just` inside a recipe. Dependencies with the same arguments run once
per `just` invocation. This is not Make-style file freshness analysis.

Common checks include:

```bash
<format command or just fmt [path]>
<lint command or just lint [path]>
<typecheck command or just typecheck>
<compile/static command or just static>
<build command or just build>
<focused test command or just test [target]>
<smoke command or just smoke>
git diff --check
```

Recommended test layout:

- `tests/`: inner-function and focused callable-code unit tests.
- `regression_tests/`: bug and API regression tests.
- `integration_tests/`: end-to-end and browser-agent-driven checks, preferably
  as rerunnable shell scripts for repeated UI flows.
