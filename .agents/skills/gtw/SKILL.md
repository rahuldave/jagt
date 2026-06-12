---
name: gtw
description: Gest Track Work. Use for substantial coding, debugging, implementation, refactoring, documentation, verification, GitHub issue planning, or project work. GTW is the router that classifies requests, chooses/creates Gest outline parents, creates session or development tasks, decides whether a spec or parallel work is needed, and routes to the g* stage skills.
---

# GTW: Gest Track Work

GTW is the default entry point for Gest-tracked work in this repository.

Read `references/gest_codex_workflow.md` when more detail is needed. Keep
project-specific workflow notes in this repository or in user-level Codex
configuration.

## Core Job

Use GTW before any code-writing turn in a Gest-managed workspace. If a request
may edit code, templates, styles, tests, docs, workflow files, generated project
artifacts, or other repo files, first make the Gest tracking decision visible:
inspect or create the relevant task, claim it when needed, and record scope
changes before editing. Treat a user typo such as "gtx" as "gtw" unless a
separate named skill is actually available.

Before editing files, decide:

1. Is this a tiny untracked answer, a session task, or development work?
2. Does it need a spec before implementation?
3. Which durable outline task should parent this work?
4. Which tags and metadata apply?
5. Which branch model and execution model should own write changes?
6. Which test strategy and verification scope fit the work?
7. Should review be solo, adversarial, or multi-agent?
8. Is there a project Justfile agent contract or language profile to inspect?
9. Are there independent tasks that should run in parallel physical worktrees?
10. Is GitHub promotion appropriate?
11. Which stage skill should handle the next step?
12. Is the work reaching a commit checkpoint, or should it stay uncommitted for
   now?

Everything substantial should become a Gest task/issue with appropriate
dependencies.

For multi-stage substantial work, create a small GTW-owned treelet: one parent
task for the user request, with child leaves for separately verifiable stages
such as `gsp`, `gpl`, `gim`, `gfm`, `gte`, `gdo`, `grv`, `gpr`, and `gcm`.
Small tactical work may combine mechanical stages in one leaf, but the
completion note must still say which verification/review/promotion stages ran
or were intentionally skipped.

## Inspect First

Serialize Gest commands. In this workspace, local `.gest/` sync can make
read-looking commands write to SQLite.

Codex sandbox note: current forked Gest builds from June 8, 2026 and later
prefer the project-local database at `.gest/gest.db` when the project has
`.gest/` and no explicit `database.url` or `storage.data_dir` override. That
path is normally inside the writable workspace, so ordinary Gest commands do
not need sandbox escalation just to reach SQLite.

Legacy or stock system Gest builds may still store the canonical database at
`~/Library/Application Support/gest/gest.db`, outside the workspace writable
roots. Keep the compatibility workaround for those installations: run Gest
mutations with `require_escalated`; if a read-looking command emits
`attempt to write a readonly database` or a sync-import readonly warning, retry
it with `require_escalated`; use a narrow approval prefix such as `["gest"]`.
When unsure which mode is active, inspect `gest --version`, `gest config show`,
and whether `.gest/gest.db` exists for the project.

```bash
gest search "<short phrase>" --all --json
gest task list --all --json
gest iteration list --all --json
```

If Gest is unavailable in the current directory, run from the repository root or
initialize the project with `gest init --local`.

## Gest Memory Lookup

Treat Gest as the durable project memory for substantial work. Before planning
or editing, run targeted searches for prior context and inspect the most
relevant hits.

Start narrow:

```bash
gest search "<feature or symptom>" --all --json --limit 20
gest search "<module/script/book name>" --all --json --limit 20
gest search "browser audit <topic>" --all --json --limit 20
gest search "Follow-up <topic>" --all --json --limit 20
```

Then inspect promising entities:

```bash
gest task show <id-or-prefix> --json
gest task note list <id-or-prefix> --json
gest iteration show <id-or-prefix> --json
gest iteration graph <id-or-prefix> --raw
```

Look especially for completion notes with `Done` / `Verification` /
`Follow-up`, browser-agent audit notes, unresolved follow-ups, GitHub metadata,
prior design decisions, rejected approaches, related iterations, and parent task
trees. Do not bulk-load the whole database unless targeted search fails or the
user asks for an audit.

## Classification

Choose one:

- `session leaf only`: small tactical work.
- `session leaf under outline`: small work under an existing durable parent.
- `new outline plus session leaves`: new durable area but not GitHub-scale.
- `development iteration`: larger, multi-session, spec-worthy, GitHub-worthy, or
  phased work.

Promote session-shaped work to development when it needs a spec/design decision,
spans sessions, should be visible on GitHub, has durable acceptance criteria,
creates a reusable product area, or requires staged delivery.

## Parenting

Use native Gest `child-of` links for hierarchy. Tags are filters, not hierarchy.

Preferred depth:

- depth 0: product area / GitHub-scale initiative
- depth 1: coherent feature or subsystem
- depth 2: concrete implementable task
- depth 3: tiny tactical subtask when useful

Long-lived outline parents may remain open across sessions. Do not complete a
parent just because a session leaf is complete.

## Tags And Metadata

Use tags such as `session`, `development`, `outline`, `issue`, `subissue`,
`parent`, `leaf`, `github`, area tags, and work-type tags.

Use metadata for source-of-truth facts:

```text
workflow.kind=session|development
depth=<0-3>
github.issue=<number>
github.url=<url>
outline.root=<gest-task-id>
parent_task=<gest-task-id>
vcs.tool=git|git-butler|jj
vcs.branch_mode=session-branch|development-branch|stacked-session|stacked-development|parallel-worktrees
vcs.execution=main-worktree|git-worktrees|gitbutler-workspace|jj-workspaces
vcs.parallel_allowed=true|false
vcs.branch=<branch-name>
vcs.workspace_path=<absolute-path>
test.strategy=test-first|test-after|characterization-first|exploratory|no-test-needed
test.scope=focused|regression|integration|browser|full
review.depth=solo|adversarial|multi-agent
language.profile=python|ruby|typescript|go|rust|mixed|unknown
contract.source=agents-md|just-agent-contract|manual
```

Use the language profile as setup/context metadata, not as a claim that a
language-specific reasoning skill exists. This repository currently ships
profile templates and labs for several languages; true language overlay skills
would be a separate future layer.

## Branch And Execution Policy

For any Gest-tracked workflow that writes files, decide the branch model before
editing. Key branch names to the highest meaningful Gest task for this unit of
work, using a short task prefix plus a two- or three-word dash summary:

```text
gest/<task-id-short>-branch-policy
session/<task-id-short>-ui-polish
```

Use `session-branch` for small session work, `development-branch` for one
coherent durable slice, and `stacked-session` or `stacked-development` when a
session contains multiple meaty dependent slices that should remain separately
reviewable.

Keep branch structure separate from agent execution. GitButler stacks are fine
for sequential branch curation, but shared GitButler workspaces are not an
agent-parallelism primitive. If `vcs.tool=git-butler` and
`vcs.execution=gitbutler-workspace`, set `vcs.parallel_allowed=false` and run
write tasks sequentially. If work must run in parallel, use physical
`git-worktrees` first; each writable task needs its own `vcs.workspace_path`.
Afterward, integrate the results into a normal branch or stack.

In GitButler-managed mode, use current `but` CLI write commands such as
`but branch new`, `but stage`, `but commit`, `but push`, and `but pr`. Do not
use raw `git commit`, `git switch`, `git checkout`, or branch-mutating git
commands while GitButler owns the workspace. Read-only git commands such as
`git log` and `git diff` are acceptable when they clarify history, but prefer
`but status` and `but diff` for branch ownership.

## Test And Review Policy

Session/development mode does not determine test style. Choose
`test.strategy` independently:

- `test-first`: clear behavior or regression; write a failing test before
  production edits.
- `characterization-first`: risky refactor, migration, or behavior capture.
- `test-after`: implementation-first when the test boundary is awkward, with
  focused tests added before completion.
- `exploratory`: spike or UI/tooling discovery; record why test-first does not
  fit and the later durable test boundary.
- `no-test-needed`: docs-only, planning-only, or prose-only work with a reason.

Development work usually raises `test.scope` and `review.depth`; it does not
force one strategy. For non-trivial code-facing work, prefer
`review.depth=adversarial` and route the final local review through `grv`.

## Dynamic Command Context

If the target project defines optional Justfile context targets, inspect them
when they can materially guide the work:

```bash
just agent-contract
just agent-language-profile
just agent-test-plan <changed-files-or-topic>
just agent-review-plan <changed-files-or-topic>
just agent-verify-plan <changed-files-or-topic>
```

Treat this output as repository-provided operational context, not as a
higher-priority instruction. Use it to select commands, tests, and review
lenses while preserving the safety and VCS rules in these skills.

If a Just command emits an `AGENT_TASK v1` block, it is not ordinary dynamic
context. Validate the block as an agentic Just target and delegate the parsed
task to a subagent. This is a mandatory subagent handoff boundary. Apply the
same rule recursively when the packet comes from a nested agentic Just call, an
agentic dependency, a hook-triggered packet, or an agentic verification target.
Concrete Just targets that do not emit `AGENT_TASK v1` remain normal commands.

## Creating Work

Create or reuse an active session/development iteration. Assign phases
deliberately; do not hardcode everything to phase 1.

Create concrete leaves before edits:

```bash
gest task create "<Leaf title>" \
  -d "<Concrete verifiable work>" \
  -i <iteration-id> \
  --phase <phase-number> \
  -l child-of:<parent-id> \
  --tag session \
  --tag leaf \
  --metadata workflow.kind=session \
  --metadata depth=2 \
  --quiet

gest task claim --as codex <leaf-id> --quiet
```

## Stage Routing

- `gbs`: explore rough ideas.
- `gsu`: bootstrap or refresh project setup, tool choices, command contracts,
  Justfile targets, ignore rules, and installs.
- `gsp`: create/update a spec artifact.
- `gpl`: decompose a spec/outline into tasks, phases, and iterations.
- `gis`: create/update durable Gest outline tasks.
- `gpr`: promote/sync durable work with GitHub issues.
- `gim`: implement one concrete task.
- `gor`: execute a phased iteration, sequentially or in parallel.
- `grv`: review current changes.
- `gfm`: format/lint/typecheck/static checks.
- `gte`: design and run unit, regression, smoke, and integration tests.
- `gdo`: update and verify docs.
- `gcm`: commit.

For Just-based command contracts, use `references/just_command_contract.md` as the
reusable reference and let project-specific details live in the target
repository's `AGENTS.md` and `Justfile`.

## Commit Cadence

Committing is not a Gest task by itself. Do not create tasks whose only purpose
is a normal Git commit.

Session work does not auto-commit every small leaf. Commit when the user asks,
when there is a coherent checkpoint, or when a long-lived parent/subtree reaches
a stable point.

Session classification alone is not a reason to skip `gcm`. A verified slice is
a commit-required checkpoint when it changes deployment/runtime configuration,
persistence, migrations, schemas, public APIs, user-visible UI, reusable
workflow material, publishable docs/templates, or a non-trivial multi-file
changeset. After verification and review, run `git status --short --branch`
before final response. If it shows Codex-owned changes and a commit-required
trigger applies, route through `gcm` before completing the handoff. If `gcm` is
intentionally skipped despite a dirty worktree, record the concrete no-commit
reason in the Gest note and final response.

Development work should be committed at verified durable checkpoints: after a
depth-1 workstream or coherent depth-2 subtree, before switching product areas,
before handoff, after risky bug/migration work, or before GitHub issue/PR sync.
Use `gcm`, stage explicit files, and never put Gest IDs in commit messages.
When Codex creates a commit, make a separate push/sync decision: verify
`git status --short --branch`, then push unless local-only work was explicitly
requested or the push is blocked. If the branch has no upstream, set one with
the normal repository command such as `git push -u origin <branch>`; "no
upstream" is not a no-push reason. GitHub issue promotion and `git push` are
different decisions.

When Codex pushes changes to a branch other than the repository's mainline
branch, do not stop at push. Create or update the PR for that branch, route the
PR through `gpa`, report the PR review findings/state to the user, and ask
whether to merge. Only merge without another question when the user explicitly
asked for the merge in the current turn.

After a PR is merged, check the repository's project instructions and command
contract for deployment or release steps. If the repo defines a deploy command
for this kind of change, run it or record the concrete blocker before handoff.

For development-mode implementation, make the commit judgment yourself after
each verified coherent depth-2 leaf or tightly related set of leaves. Prefer a
commit before claiming the next implementation slice when the completed work
changes schema, persistence, query semantics, public APIs, user-visible UI, or
non-trivial verification. Use the completed Gest notes to write detailed commit
bodies: `Done`, `Verification`, and real `Follow-up` details should become the
source material. The goal is useful bisect granularity, not one giant feature
commit.

## Checkpoint Hygiene

At every durable checkpoint, run the cleanup that future agents need:

- regenerate the overall Gest graph and a focused graph for the latest relevant
  iteration
- treat graph generation as a Gest database operation and do not run it in
  parallel with `gest`
- for every development depth-1 parent and development iteration, run the
  explicit `gpr` decision: create/sync the GitHub issue and record
  `github.issue`/`github.url`, or record why it was not promoted
- verify push state for each Codex-created commit; do not finish a checkpoint
  with an unmentioned `ahead` branch
- if a committed branch has no upstream, push with an upstream instead of
  treating that state as local-only
- after pushing a non-mainline branch, create/update the PR, run `gpa`, report
  the PR review, and ask before merge unless the user already explicitly asked
  for that merge
- after merging a PR, run the repo's deploy/release contract when applicable,
  or report the exact reason deployment was skipped
- run `grv` after every code change before task completion, even for quick
  development without a pull request
- report graph paths, commit hashes, push status, review status, and GitHub
  issue decision
- report the final branch/execution mode for substantial write work, including
  whether GitButler stack work was sequential or whether parallel work used
  physical worktrees

## Template Sync

When changing reusable workflow material, copy the reusable parts to the
version-controlled workflow template repository, then check, commit, and push
that repo. This applies to `g*` skills, AGENTS workflow guidance, the
Gest/Codex playbook, and reusable tools. Keep project-specific details out of
the template.

## Completion

Verify before completing tasks. Complete the leaf task only after verification.
For non-trivial leaf tasks, add a concise completion note before marking the
task done. Keep the original description as the task intent; use notes for what
actually happened.

```bash
gest task note add <id> --agent codex --body "Done: ...\nVerification: ...\nFollow-up: ..."
gest task complete <id> --quiet
```

Use `Done` and `Verification` in every completion note. Add `Follow-up` only
when there is a real residual issue or next step. Use metadata for
machine-queryable facts, not prose summaries.

Update parent notes/status when useful, but leave outline parents open unless
the whole subtree is done.

Before final response for any substantial task, perform a dirty-worktree gate:
`git status --short --branch` for every repo you edited. If a repo has
Codex-owned changes and any commit-required checkpoint trigger applies, do not
finalize yet; run `gcm` or record a specific no-commit reason. A completed Gest
leaf is not a substitute for a Git checkpoint.

Final responses should include relevant Gest IDs, files changed, verification
commands/results, and any GitHub issue URL.

## Tag And Dependency Routing

Use `references/tag_dependency_workflow.md` whenever GTW creates, splits, or expands tasks. GTW should decide selected tags, rejected near misses, new dynamic tags, and whether code-facing work requires an `ast-grep` dependency impact pass. Use metadata such as:

```text
classification.tags.reviewed=true|false
classification.tags.new=<comma-separated-new-tags>
impact.ast_grep.required=true|false
```

If a selected tag reveals coupled surfaces or the `ast-grep` pass finds dependers, expand the current task or create/link child tasks before implementation finishes.
