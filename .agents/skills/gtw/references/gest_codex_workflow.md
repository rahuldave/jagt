# Gest-Codex workflow

Last updated: 2026-09-25.

Read [Integration branches, review, and delivery](integration_delivery_workflow.md)
for the shared contract. It covers selected bases, independent review, CI, issues,
installation and cleanup.

This document says how Codex uses Gest, GitHub and the local family of skills
in a repository that Gest tracks. The goal is to keep the creative flow of the
work and also keep a durable tree of tasks.

## Core model

Every substantial request becomes work that Gest tracks. The tracker records
the durable structure of the product and the concrete work of a session.

The model has four different concepts:

- **GitHub issue**: durable intent that people outside the tracker can see.
- **Development iteration**: a Gest plan of execution for larger work with a
  clear scope. It usually belongs to a GitHub issue, and it can last for many
  sessions.
- **Session iteration**: a Gest plan of execution for the current chat or
  session. It can include exploratory or tactical tasks.
- **Outline task**: a durable Gest task in the internal tree of tasks. Put each
  user request under the best outline task that exists. If none fits, create a
  new outline task.

The mode of an iteration does not decide whether work can run in parallel.
Parallel work depends on how independent the tasks are, on the files that they
share, and on risk.

The mode of the workflow also does not decide how you write tests. Treat these
settings as separate axes:

```text
workflow.kind=session|development
test.strategy=test-first|test-after|characterization-first|exploratory|no-test-needed
test.scope=focused|regression|integration|browser|full
review.depth=solo|adversarial|multi-agent
language.profile=python|ruby|typescript|go|rust|mixed|unknown
contract.source=agents-md|just-agent-contract|manual
```

Session work can use `test-first` when the behavior is small and clear, for
example the fix of a regression. Development work can start with
`characterization-first` or `exploratory` when you must understand the code
before a good red and green loop exists. Development mode asks for broader
verification and review, but it does not force one test strategy.

## Branch, stack, and worktree policy

The mainline and the persistent integration branches stay ready to integrate.
Each Gest workflow that writes files chooses an explicit mode of version
control (VCS) execution before it edits. Keep two decisions separate:

- **branch model**: how the work gets review and how it is integrated
- **execution model**: where agents can write

Name a branch after the highest Gest task that has meaning for the current
workstream. That task is not always the permanent root of the product:

```text
gest/<task-id-short>-two-word-summary
session/<task-id-short>-two-word-summary
```

Use these branch modes:

- `session-branch`: one tactical session branch. It suits a small session leaf,
  or several small related session edits under one parent.
- `development-branch`: one durable branch for one coherent feature, bug or
  change to the workflow. Several commits are fine when they are useful
  checkpoints.
- `stacked-session`: several large session slices that depend on each other and
  must stay separate for review.
- `stacked-development`: several large development slices that depend on each
  other and become stacked branches or stacked PRs.
- `parallel-worktrees`: several large independent slices that agents work on at
  the same time, in separate physical worktrees.

Use these execution modes:

- `main-worktree`: one agent writes in the current checkout.
- `git-worktrees`: one git worktree for each parallel task.
- `jj-workspaces`: one jj workspace for each parallel task, if the project uses
  jj.

One checkout holds one branch at a time, so several agents must not write to
the same working tree. Follow these rules:

- if work must be parallel, give each writer its own physical worktree, with
  `just worktree-new NAME` or `git worktree add`, and integrate the results into
  a branch or stack after that
- to build a stack with plain git, start each branch from the branch below it,
  and open the PR of each branch with `gh pr create --base <parent-branch>`
- after a change to a lower branch, run
  `git rebase --update-refs --onto <lower-branch> <old-lower-tip>` on the top
  branch, so that Git moves each branch of the stack together.
  `<old-lower-tip>` is the lower branch before the change, saved with
  `git rev-parse <lower-branch>`. `<lower-branch>@{1}` is that commit only
  after one change. Git 2.38 and later have `--update-refs`.
- plain `git commit`, `git switch` and `git checkout` need no marker

Default integration:

- simple branches: rebase onto the target branch, then fast-forward or squash
  when that is correct
- stacks: review and merge from the bottom up. GitHub merge commits are
  acceptable for stacked PRs, because they make the stack easier to handle.
- parallel worktrees: integrate each finished worktree on purpose before you
  start follow-on work that depends on it

When work is more than a tiny local edit, record the state of the branch and of
the execution in Gest metadata:

```text
vcs.tool=git|jj
vcs.default_branch=<repository-default>
vcs.integration_branch=<selected-persistent-target>
vcs.base_branch=<immediate-PR-base>
vcs.branch_role=topic|stack-topic|integration
vcs.base_sha=<sha>
vcs.branch_mode=session-branch|development-branch|stacked-session|stacked-development|parallel-worktrees
vcs.execution=main-worktree|git-worktrees|jj-workspaces
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

If `vcs.execution=main-worktree`, set `vcs.parallel_allowed=false`. Parallel
claims are allowed only when each task that writes has its own physical
`vcs.workspace_path`, for example separate git worktrees.

## Task hierarchy

Native `child-of` and `parent-of` links show the parent tasks in Gest. Tags help
you filter, but the links are the source of truth for the hierarchy.

The preferred depth:

```text
depth 0: product area / GitHub-scale initiative
depth 1: coherent feature, subsystem, or workstream
depth 2: concrete implementable task
depth 3: tiny tactical subtask, only when useful
```

Give each concrete implementation task a parent, if the task does not stand
alone. Outline parents can stay open across many sessions. Do not complete a parent only because one session leaf is done.

For substantial work in several stages, create a small tree of tasks that GTW
owns. The parent stands for the user request. Each child leaf stands for a stage
command that you can verify on its own. Examples are `gsp`, `gpl`, `gim`, `gfm`,
`gte`, `gdo`, `grv`, `gpr` and `gcm`. Do not create busywork tasks for trivial
stages. But the completion note must say which stages ran, and which stages
you skipped on purpose.

## Classification

Before Codex edits files, it decides which class fits the request:

- **Session leaf only** is for tiny and tactical work that is not likely to
  matter after the session.
- **Session leaf under existing outline** is for small work that belongs
  under a durable area of the product or the workflow.
- **New outline task plus session leaves** is for a new durable area that does
  not yet need a GitHub issue or a formal spec.
- **Development iteration** is for a larger effort with a clear scope. It has
  acceptance criteria and phases, and it can have parallel work. It probably
  needs to be visible on GitHub, or it continues over several sessions.

Promote session work to development work when any of these is true:

- it needs a decision about the spec or the design
- it continues over several sessions, or it must be visible on GitHub
- it has several durable acceptance criteria
- it creates a reusable area of the product, or it needs delivery in stages

## Specs

Create a Gest spec artifact when the request needs the shape of the product or
the design before implementation. A spec is correct when:

- the wanted behavior is not yet clear
- several approaches exist, and each has its trade-offs
- the acceptance criteria need agreement
- the work changes several systems or future workflows
- the development will probably be visible on GitHub

After you create a spec, do the implementation in follow-on Gest tasks. Do not
hide implementation work inside the spec artifact.

## GitHub promotion

GitHub issues give durable visibility outside the tracker, and they are not for
every leaf task. Promote work to GitHub in these cases:

- users can see the work, or it changes the architecture
- it continues over several sessions, or it belongs in a release
- it needs tracking outside the local Gest ledger

Development parents at depth 1 and development iterations must have a GitHub
decision. Create or sync the issue with `gpr`, or record why the work stays
local.

When a GitHub issue exists, store it as metadata on the development iteration.
Also store it on the top-level outline task, when there is one:

```text
github.issue=<number>
github.url=<url>
workflow.kind=development
outline.root=<gest-task-id>
```

The GitHub issue makes the work visible to other people, and Gest still
records its execution locally.

## Tag and dependency impact

Before you create or split tasks, classify the request against the existing
vocabulary of Gest tags. Where it applies, record
`classification.tags.reviewed=true`,
`classification.tags.new=<comma-separated-new-tags>` and
`impact.ast_grep.required=true|false`. Use the
[tag dependency workflow](tag_dependency_workflow.md).

For work on code, use `ast-grep` to find the semantic dependers of each changed
contract. A depender is code that uses the contract. If a search of tags or
dependencies finds coupled surfaces, expand the current task, or create and
link child tasks, before the implementation is complete.

## Testing strategy

`gte` owns the design of the tests and their execution. For an implementation
task, choose and record a strategy before you edit production code, when you
can:

- `test-first`: write the smallest meaningful test that fails. Run it to see a
  useful red failure. Then implement, see green, refactor and run broader
  checks.
- `characterization-first`: record the current behavior before a refactor, a
  migration or a risky change of semantics.
- `test-after`: implement first only when test-first is awkward, or when the
  expected behavior is still not clear. Add focused tests of the behavior
  before completion.
- `exploratory`: probe unknown APIs, UI affordances or tools. Record why
  test-first does not fit, and which test boundary to create later.
- `no-test-needed`: work on docs only, on planning only, or on workflow prose
  only, with a concrete reason.

For bug fixes, parsers, exports, imports, persistence, APIs and shared
contracts, prefer `test-first` or `characterization-first`. Use another
strategy only for a clear reason. Completion notes give the strategy, the
focused commands, the broader commands and each test boundary that you put off.

## Adversarial review

`grv` collects the local review, and it becomes adversarial for changes that are
not trivial. It reviews through separate lenses:

- correctness and the risk of a regression
- whether the tests are enough, including whether new tests fail on the old code
- the safety of the Git workflow
- drift in the docs, the setup and the command contract
- security, privacy or data safety, when relevant
- browser and UI behavior, when relevant
- the idioms of the language and the runtime, when Codex knows the profile

By default, use independent read-only review subagents when subagents are
available, you have permission to use them, and each lens can be checked on its
own. If Codex does not use subagents, it still applies
each lens explicitly. It also records why a local review was enough. Keep Gest
changes and checkpoint decisions in one place, if you do not assign them on
purpose.

Reviewers of reusable workflow changes keep the boundaries between adapters.
Plain Git branches, stacks of branches, and physical git worktrees are
different tools for execution and review. Do not rewrite the guidance for
stacks into the semantics of jj bookmarks. Do not treat two branches in one
checkout as isolation for agents.

## Tags

Use tags as filters, and not as a hierarchy.

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

Put the facts that are the source of truth in metadata. Examples are
`workflow.kind`, `depth`, `github.issue`, `github.url`, `outline.root`,
`parent_task`, and the `vcs.*` metadata of the branch and the execution.

## Completion notes

A task description is its intent. It says what the task was created to do. At
completion, do not rewrite the description only to record what happened.

For each leaf task that is not trivial, add a Gest task note before you mark the
task done. Notes are first-class Gest data. They appear in `gest task show` and
in the web timeline, and they sync under `.gest/task/notes/`.

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

Use metadata for facts that a machine queries. Examples are the changed files,
the IDs of GitHub issues, and the lists of verification commands. Use notes for
the work log in prose. For a tiny mechanical task, the change of status and the
final summary in the chat can be enough.

## Commit cadence

A commit is part of the hygiene of version control, and it is not a Gest task by
itself. Do not create a Gest task only to make a commit. The exception is
substantial work on the Git history, for example the split of a messy changeset
or a recovery from a bad history operation.

Session-mode work does not commit each small leaf automatically. Commit session
work at these times:

- when the user asks
- when a coherent checkpoint is useful
- when a long-lived parent or subtree gets to a stable point

Small exploratory tasks can stay uncommitted while the workflow still changes.

A session classification alone is not enough reason to skip `gcm`. A verified
slice is a checkpoint that needs a commit when it changes one of these things:

- the configuration of deployment or of the runtime
- persistence, migrations or schemas
- public APIs or the UI that users see
- reusable workflow material, or docs and templates that you publish
- a changeset of several files that is not trivial

After verification and review, run `git status --short --branch` before the
final response. If the output shows changes that Codex owns, and a trigger for a
commit applies, go through `gcm` before the handoff. If the worktree stays dirty
on purpose, record the concrete reason for no commit. Put it in the Gest note
and in the final response.

Development-mode work has stronger commit checkpoints:

- after a feature or workstream at depth 1, or a coherent implementation
  subtree at depth 2, is complete and verified
- before you change to a very different area of the product
- before you give the work to another agent or session
- after you fix a risky bug or migration, where a clear rollback is important
- before you push or sync to a GitHub issue or PR

In development mode, make the commit decision yourself. Do not leave each
slice to a question to the user. Decide after you complete and verify a coherent
implementation leaf at depth 2, or a set of closely related leaves.

Some slices change the schema, persistence, the semantics of queries, migrations, public
APIs, the UI that users see, or verification that is not trivial. Prefer to
commit such a slice before you claim the next implementation slice. Small
leaves that are only design, exploratory, or strictly dependent can stay
uncommitted. Commit them when they join into the next coherent checkpoint.

When you commit a slice, make the commit body from the notes of the completed
Gest tasks:

- summarize `Done`
- include `Verification`
- mention each real item of `Follow-up`
- name the changed subsystems or files, when that helps a later bisect

The commit message must not include Gest IDs. A later `git bisect` must land on
a narrow layer. Examples are schema and indexing, the behavior of the repository
and its queries, the UI, and verification. It must not land on a whole feature of
several layers.

When a commit is correct, read the status and the diff, stage explicit files,
and use `gcm`. Never use `git add .` by default. Never put Gest IDs in commit
messages. Use GitHub issue footers only when the Gest metadata has a real GitHub
issue and the commit closes it or refers to it.

Each commit that Codex creates needs its own decision about push and sync. The
promotion of a GitHub issue does not replace `git push`.

Read `git status --short --branch` before and after the commit. If the branch has an
upstream and the user did not ask for local-only work, push the verified
checkpoint. If the branch has no upstream, set one with
`git push -u origin <branch>` or the equivalent of the repository. "No
upstream" is not a reason to not push. If the branch is still local or `ahead`
at the handoff, the checkpoint is incomplete. The exception is a real push
blocker that the task note or the final summary states.

When Codex pushes a topic or stack branch, a pull-request checkpoint must follow
the push:

1. Create or update the PR for the branch.
2. Run `gpa` on that PR.
3. Report the review findings and the state of the PR to the user.
4. Ask whether to merge.

Merge only when the user already gave permission for that particular merge. The
permission stays valid across turns. For changes to a reusable workflow or
template repository, the push and the creation of the PR are required, if
nothing blocks them. If something blocks them, record the exact blocker. Do not
leave the branch pushed with no PR.

After a PR is merged, read the project instructions and the command contract of
the repository for what they expect about deploy and release. If the repository
defines a deploy command for that kind of change, run it, or record the exact
blocker before the handoff.

Before the final response for substantial work, check each repository that you
edited for a dirty worktree. A completed Gest task does not replace a
Git checkpoint. If there are changes that Codex owns, and a trigger for a
commit checkpoint applies, run `gcm`. Otherwise, write down why you make no
commit.

## Checkpoint hygiene

At every durable checkpoint, run the project hygiene that keeps later agents
oriented. Durable checkpoints include:

- any Git commit that Codex creates
- the close of a task at depth 1, or of a parent of a product area or workstream
- the completion of an iteration
- the handoff after a substantial implementation session

Checkpoint steps:

1. Keep the native links of the task hierarchy and of dependencies current.
   Gest keeps its graphs up to date by itself. Look at them when you need to,
   with no export checkpoint.
2. Some work is visible to users, changes the architecture, continues over
   several sessions or belongs in a release. For such work, decide whether to
   promote it to GitHub. For development parents at depth 1 and for development
   iterations, the decision is mandatory. Use `gpr` to create or update the
   GitHub issue. Then write the `github.issue` and `github.url` metadata back to
   Gest. Otherwise, record the explicit reason that you skipped the promotion,
   in the task note or the final summary.
3. For each commit that Codex creates, check the push state with
   `git status --short --branch`. If an upstream exists and the branch is
   ahead, push it, or record the explicit reason for local-only work or the
   blocker. Report the final relationship of the branch apart from
   the decision about the GitHub issue.
4. If Codex pushed a topic or stack branch, create or update its PR and run
   `gpa`. Report the review findings and the state of the PR. Ask before the
   merge, if the user did not already ask for that merge explicitly.
5. For each code change, do an explicit review pass before the task is
   complete. Use `grv`, or a stance of code review over the current diff or
   commit. Then fix or record each finding before you close the leaf, the
   parent or the iteration. Missing focused tests for changed callable code or
   APIs are review findings.
6. After you close the parent or the iteration, check the final Gest status.
   Report the selected base, the commit hashes, the push status, the review
   status and the decision about the GitHub issue.

## Template sync

Reusable workflow changes must not live only in one target workspace. Some
changes are to the `g*` skills, the workflow guidance in `AGENTS.md`, the
Gest/Codex playbook or reusable tools. Copy the reusable parts of such a change
into the workflow template repository, which is under version control. Then
check, commit and push that repository. The template repository is the source of
the workflow material that other projects take in. Keep the details of one
project out of the template repository.

## Iterations and phases

Iterations are plans of execution. Phases are the boundaries of parallel work.

Use a **session iteration** for the work of the current session, including
creative experiments. Use a **development iteration** for larger work with a
clear scope that can continue over several sessions or map to GitHub.

Do not give every task `--phase 1`. Choose the phases on purpose:

- Phase 1: research, reproduction, or design
- Phase 2: implementation
- Phase 3: verification
- Phase 4: docs, publishing, or cleanup

Tasks in the same phase must be independent enough to run at the same time. If
one task blocks another, put them in different phases, and add a `blocked-by`
link.

## Parallel work

Parallel work can happen in session iterations or in development iterations.
Decide from the graph of tasks, and not from the kind of iteration.

Use git worktrees and subagents when the tasks are independent, touch code, and
are risky to mix in one working tree. Keep the work local and sequential when
the tasks are closely coupled, small, or need the context of the moment.

For parallel Gest orchestration:

1. Claim tasks with `gest iteration next <iteration-id> --claim --agent <name>`.
2. Create one git worktree for each independent task, when it helps.
3. Run the implementation in each worktree.
4. Merge or cherry-pick the results before you go to the next phase.
5. Remove the worktrees after verification.

Keep Gest commands short, and run them one at a time where you can. In this
workspace, a command that seems only to read can still write to the database,
because of the local `.gest/` sync.

## Serialization and storage

Current forked Gest builds from June 8, 2026 and later prefer storage in the
project for local projects:

```text
<project-root>/.gest/gest.db
```

Gest expects this path when the project has `.gest/` and the user did not set
an explicit override in `database.url` or `storage.data_dir`. In Codex, the path
usually prevents write failures in the sandbox. The reason is that the SQLite
file is inside the root of the workspace that Codex can write. Run Gest commands
one at a time anyway, because local sync and SQLite writes can still conflict
in one workspace.

Legacy or stock system Gest builds can still store the canonical data in:

```text
~/Library/Application Support/gest/gest.db
```

For those builds, the `.gest/` directory is a local sync mirror. The database is
the source of truth, but commands can import changes from the mirror and export
changes to it. Debug output showed `sync import` that ran before
`gest task list`.

Current SQLite pragmas, as seen on the local machine:

```text
journal_mode=delete
busy_timeout=0
locking_mode=normal
```

Before the fork that stores data in the project, local mode and global mode both
used the same global database. So the readonly warning was not a problem of
local mode as such. The recommended normalization of permissions for legacy
builds is:

```bash
chmod 755 ~/Library/Application\ Support/gest/
chmod 644 ~/Library/Application\ Support/gest/gest.db
```

Those permissions were already set on the local machine. A Codex run without
escalation, with `GEST_LOG__LEVEL=trace`, reproduced
`attempt to write a readonly database` during sync import. The same trace run
outside the sandbox did not. Treat that warning as a probable result of the
environment or the sandbox, if it does not also appear in a normal terminal.

In Codex, the legacy failure happens because the canonical Gest database is
outside the roots of the workspace that Codex can write. A command such as
`gest task list` can still write before it lists. The reason is that local sync
imports the mirrored `.gest/` state into tables, for example `authors`, `tags`,
`tasks`, `relationships`, `transactions` and `sync_digests`.

Codex command policy:

- with the newer fork that stores data in the project, prefer `.gest/gest.db`.
  Do not escalate out of the sandbox, if another path or command does not
  require it.
- with legacy or stock system Gest, run Gest changes with `require_escalated`,
  because they can need to write to the global database
- if a Gest command that seems to only read gives
  `attempt to write a readonly database` or a readonly warning from sync
  import, run it again with `require_escalated`
- ask for or use a narrow approval prefix, for example `["gest"]`
- run Gest commands one at a time even with escalation. The exception is
  deliberate orchestration with `gest iteration next --claim`.

So follow these rules:

- do not run Gest commands in parallel during normal Codex work
- use `--json` and `--quiet` for output that a program parses
- after a `database is locked` or sync warning, check the state before you try
  again
- when you diagnose storage, check `gest --version`, `gest config show`, and
  whether `.gest/gest.db` exists. Do this before you assume that the global
  path is canonical.

## Deferred hooks

The current workflow works through skills and instructions on purpose. Do not
add hooks that block commands until people have used the workflow enough. Then
they can see what helps and what gets in the way.

Hook ideas to look at again:

- **Session start**: add a short reminder of `gtw` and the `g*` family of
  skills. Also remind the agent of the classification as session or
  development, outline parents, GitHub promotion, and Gest commands one at a
  time.
- **Pre-edit**: before source edits, add the local guidance of the project
  about style and tests. Examples are the code-style and testing guides of the
  project, and the invariants of the project.
- **Pre-commit**: add the commit conventions. Remind Codex never to put Gest IDs
  in commit messages, and to use GitHub issue footers only when metadata
  exists.
- **Gest safety**: warn about or block malformed Gest commands. Examples are a
  `subissue` with no `child-of` parent, and several Gest writes in parallel.
- **Worklog/session end**: record short session summaries or task notes when a
  long session ends.

Questions to answer after people use the workflow:

- Which reminders do agents forget in practice?
- Which checks are better as hooks, and which as `gtw` instructions?
- Should hooks live in the local config of the project, in the global Codex
  config, or in both?
- Should hooks only add context, or should some of them block commands?
- Do parallel worktrees need hook support for the context of each worktree?

## Skill family

Gest skills that the user calls have names of three letters that start with
`g`.

- `gtw`: Gest Track Work. The router and default skill for substantial work.
- `gbs`: Gest Brainstorm. Explore ideas, and decide whether a spec or an outline
  is necessary.
- `gsu`: Gest Setup. Set up or refresh the choice of tools, installs, ignore
  rules, command contracts, Justfile targets and the setup docs of the project.
- `gsp`: Gest Spec. Write or update a Gest spec artifact.
- `gpl`: Gest Plan. Break a spec or an outline task into tasks, phases, links
  and iterations.
- `gis`: Gest Issue. Create or update durable Gest outline tasks.
- `gpr`: Gest Promote. Promote or sync durable Gest work with GitHub issues.
- `gim`: Gest Implement. Implement one concrete Gest task from start to end.
- `gor`: Gest Orchestrate. Run a phased iteration, in sequence or in parallel,
  as the independence of the tasks lets it.
- `grv`: Gest Review. Review the current changeset.
- `gfm`: Gest Format. Run the format, lint, typecheck, compile and static checks,
  and diff hygiene.
- `gte`: Gest Test. Run unit, regression, smoke, API and integration tests.
- `gdo`: Gest Docs. Check, create, update and verify the docs that the task
  changes. The docs can be for users, for developers or in the code.
- `gpa`: Gest PR Accept. Review and accept GitHub pull requests. A pull request
  is the checkpoint on GitHub of a workstream that Gest tracks.
- `gcm`: Gest Commit. Create a Git commit, with GitHub metadata when it exists.

Optional later skills:

- `gcl`: Gest Changelog.
- `gdc`: Gest Doc Code.
- `gps`: Gest Promote Spec.

`gtw` routes to these stages as a concept. The user can call any stage directly.
But an ordinary request can use `gtw` or natural language.

## Stage responsibilities

### GTW

1. Read the existing Gest state.
2. Classify the request as session or development, and as spec or no spec.
3. Choose or create the best outline parent.
4. Decide the tags, metadata and depth.
5. Decide whether parallel work is useful.
6. Decide the branch model and the execution model. For writes that are not
   trivial, record the `vcs.*` metadata.
7. Create or claim concrete leaf tasks before edits. For work in several stages,
   create a small tree with a child leaf for each stage command that you can
   verify on its own.
8. Route to the correct stage skill.
9. Complete the leaf tasks after verification, and report their IDs.

### GBS

1. Explore the existing code, docs and Gest context.
2. Ask clarifying questions when necessary.
3. Propose approaches and their trade-offs.
4. Decide whether to create a spec, an issue, a plan or a session leaf.

### GSP

1. Write the problem, the scope, the proposed behavior, the acceptance criteria
   and the open questions.
2. Review them with the user when the direction is not settled.
3. Save them as a Gest artifact with the tag `spec`.
4. Link the artifact to outline tasks when that is correct.

### GPL

1. Read a spec, an outline task, or a task that a GitHub issue backs.
2. Decide between one task and a breakdown into several tasks.
3. Create tasks at depth 1 and depth 2.
4. Assign explicit phases and blocking links.
5. Create or update session or development iterations.
6. Report where work can run in parallel.

### GIS

1. Write the user story, the context and the acceptance criteria.
2. Create or update a durable Gest task.
3. Apply the tag `outline`, `issue` or `subissue`.
4. Link with `child-of`, and set the depth metadata.

### GPR

1. Read the task, iteration or spec to promote.
2. Remove the internal details.
3. Write the body of the GitHub issue.
4. Ask the user to confirm before `gh issue create` or `gh issue edit`.
5. Store the GitHub metadata on the Gest entities.

### GIM

1. Read and claim one concrete task.
2. If the task is too broad, split it first.
3. Confirm the branch and execution mode of the task before you edit. Keep the
   execution sequential, if no one assigned a physical worktree.
4. Make small changes inside the scope.
5. Run `gfm` for mechanical checks.
6. Run `gte` for tests. Changed callable code and APIs need focused tests.
7. Run `gdo` when the change touches docs for users, docs for developers or
   docs in the code.
8. Run `grv` after every code change.
9. Complete the leaf task, and add notes and status updates to the parent.

### GOR

1. Read the status and the graph of the iteration.
2. Group the tasks by phase.
3. For each phase, decide between sequential and parallel execution.
4. Block parallel work in one shared checkout. If
   `vcs.execution=main-worktree`, run the tasks in sequence, even when they are
   in the same phase.
5. Use physical git worktrees and subagents for independent tasks when that
   helps. Record each `vcs.workspace_path`.
6. Integrate the results into the selected branch or stack, and go to the next
   phase.
7. Remove only the physical worktrees that workers own. First do the checks of
   ownership, dirty files, integration and dependencies in the
   integration-delivery policy. Report each worktree that you keep.

### GRV

Review the current changeset for correctness, safety, regressions, style and
test coverage. Give the findings first. Run it after every code change, before
the task is complete.

### GFM

Run the format, lint, typecheck, compile and static checks, and diff hygiene.
Fix mechanical issues. Do not use `gfm` in place of tests.

### GTE

Run the unit tests, API regression tests, smoke checks, and integration and
browser checks that suit the change. A browser spot check is an exploratory
verification of the implementation. A durable browser integration test is a
script or test that you can run again. Add tests when changed callable code has
no focused tests.

### GDO

Check whether the task needs docs for users, docs for developers or docs in the
code, and then create or update them. Prefer code with docs and types when they
make clear the callable behavior, public contracts, domain logic that is not
obvious, or future maintenance.

### GPA

Review a GitHub pull request as a checkpoint of integration. Collect these
facts about the PR:

- its metadata, diff, commits and checks
- its review state, whether it can merge, and the state of its branch
- the related Gest tasks, artifacts and iterations

Give the findings first. Then give an appendix of the Gest context and a checklist
for human review. End with a recommendation about the merge, and a plan for the
bookkeeping after the merge. If the body of the PR has no Gest context, offer to
update it before approval or merge.

The bookkeeping after the merge must bring back a consistent local state. To
mark the GitHub PR merged is not enough. Before the merge, check with
`gh pr diff` or `git show --stat` that the PR branch contains the intended
changes. Empty commits, and commits with no changes, are warning signs.

After the merge, do these things:

- fetch and prune the remotes
- update the selected base in a suitable clean checkout, when one exists
- check the base against `origin/<base>`
- delete only the merged temporary topic branches that you checked and that
  have no worktree or stack dependents
- keep the primary checkout branch, which is recorded separately, even when the
  base of the PR is a different integration branch

Keep the persistent integration branches, whatever their names are. Remove only
the physical worktrees that workers own. First confirm that their changes
reached the intended target, that all valuable files are accounted for, and
that no task or stack depends on them. The integration-delivery policy gives the
details. Confirm that each remaining PR belongs to follow-on work that someone
intends.

For a stack, merge from the bottom up. After each merge, retarget the next PR
with `gh pr edit <number> --base <new-base>`. Then fetch, and run
`git rebase --update-refs --onto origin/<new-base> <old-lower-tip>` on the top
branch of the stack. `<old-lower-tip>` is the commit of the merged branch
before the merge, which is the local branch, because the merge on GitHub does
not move it. With `--onto`, Git does not replay the merged commits after a
squash merge.

### GCM

Read the status, the diff and the log. Write a conventional commit, ask for
confirmation when necessary, stage explicit files and commit with plain git.
Include GitHub issue footers only
when metadata exists. Never include Gest IDs in commit messages.

## Project defaults

In each target repository, replace this section with the command contract of the
project. Prefer `just` targets when they exist, and document the arguments of
each target. When you create or change Just recipes, read these pages:

- Just dependencies: https://just.systems/man/en/dependencies.html
- Just skill reference: https://raw.githubusercontent.com/casey/just/refs/heads/master/skills/just/SKILL.md

In Just, the order of dependencies has a meaning. Dependencies run before the
recipe that depends on them, and in the order of the list. For recipes that run
in order, prefer native Just dependencies to a recursive call of `just` inside a
recipe. An example is `verify: lint typecheck static test smoke diff-check`.
Dependencies with the same arguments run once in each call of `just`. Just does
not check whether files are fresh, as Make does.

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

- `tests/`: unit tests of inner functions and focused tests of callable code.
- `regression_tests/`: regression tests of bugs and of APIs.
- `integration_tests/`: end-to-end checks and checks that a browser agent
  drives. Prefer shell scripts that you can run again for UI flows that repeat.
