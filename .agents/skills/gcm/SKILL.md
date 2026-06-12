---
name: gcm
description: Gest Commit. Create a Git commit for the current changes, using conventional commit style and GitHub metadata when present.
---

# GCM: Gest Commit

Use when the user asks to commit, when the Gest workflow says a verified
development checkpoint should be committed, or when the final dirty-worktree
gate finds verified Codex-owned changes at a commit-required checkpoint.

Committing is VCS hygiene, not a Gest task by itself. Do not create a Gest task
whose only purpose is making a normal commit.

Session-mode work does not auto-commit every small leaf. Prefer committing when
the user asks, when a coherent checkpoint would help, or when a long-lived
parent/subtree reaches a stable point.

Session-mode work must still use `gcm` for commit-required checkpoints:
deployment/runtime configuration, persistence, migrations, schemas, public APIs,
user-visible UI, reusable workflow material, publishable docs/templates, and
non-trivial multi-file verified changes. Do not treat "session leaf" as a
standalone no-commit reason.

Development-mode work should be committed at durable checkpoints: after a
verified depth-1 workstream or coherent depth-2 implementation subtree, before
switching product areas, before handoff, after risky bug/migration work, or
before GitHub issue/PR sync.

In development mode, do not default to asking the user whether a verified slice
should be committed. Make the judgment yourself after each coherent depth-2
implementation leaf or tightly related set of leaves. Prefer committing before
continuing when the slice changes schema, persistence, query semantics, public
APIs, user-visible UI, or non-trivial verification. Keep the unit small enough
that `git bisect` would land on a useful layer.

Use completed Gest task notes to draft copious but focused commit bodies:
include what changed from `Done`, the exact checks from `Verification`, and any
real `Follow-up`. Never include Gest IDs.

After creating a commit, run checkpoint hygiene: regenerate the overall Gest
graph and a focused graph for the latest relevant iteration, serialized away
from `gest` commands. For any code commit, ensure `grv` has happened after the
code change or run it immediately. Also make and verify a push/sync decision:
`git push` is separate from GitHub issue promotion. For development depth-1
parents or development iterations, run the explicit `gpr` decision: create/sync
the GitHub issue and record metadata, or record why promotion was skipped.
Report graph paths, the commit hash, final branch relationship, push status,
review status, and the GitHub issue decision.

## Workflow

Inspect:

```bash
git status --short --branch
git diff
git diff --staged
git log --oneline -10
git remote -v
```

If the repository is in GitButler-managed mode, inspect with GitButler as well:

```bash
but status
but diff
but branch list --all
```

Draft a conventional commit:

```text
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Never reference Gest IDs in commit messages. If the relevant Gest task metadata
contains `github.issue`, include a GitHub footer such as `Closes #42` only when
that is semantically correct.

Ask the user for confirmation before committing only when the commit checkpoint
is ambiguous, risky, or outside the workflow's durable-checkpoint rules. If the
user has asked you to manage commits or the workflow clearly says the verified
development slice should be committed, proceed. Stage explicit files rather
than using `git add .`.

## GitButler Commit Path

When `vcs.tool=git-butler` or the checkout is on the GitButler workspace branch,
do not use raw `git commit`, `git switch`, `git checkout`, or branch-mutating
git commands. Use current `but` CLI writes:

```bash
but status
but branch list --all
but stage <file-or-hunk-id> <branch-name>
but commit -o -m "<message>" <branch-name>
but push <branch-name>
```

If there is exactly one applied GitButler branch and all uncommitted changes
belong there, `but commit -m "<message>" <branch-name>` is acceptable. When
multiple branches or staged areas exist, use explicit branch targets and
`--only` (`-o`) after staging to avoid sweeping unrelated unassigned changes
into the wrong branch.

For stacked branches, commit review feedback to the branch where it belongs,
not automatically to the top of the stack. Merge/review the stack bottom-up.
GitHub merge commits are acceptable for GitButler-managed stacks when that keeps
stack retargeting smooth; simple non-stack branches should still prefer rebase
plus fast-forward or squash.

Before returning final after substantial work, inspect `git status --short
--branch`. If it shows Codex-owned changes and a commit-required trigger
applies, this skill should run before final response. If a dirty worktree is
left intentionally, the final response and Gest note must state the exact
reason the changes were not committed.

After committing:

```bash
git status --short --branch
git push
git status --short --branch
```

Push when the user has not asked for local-only work. If the branch has no
upstream, set one with the normal repository command such as
`git push -u origin <branch>`; "no upstream" is not a no-push reason. If the
branch is ahead and you do not push, record the exact blocker in the Gest note
and final summary. A checkpoint is not complete while a Codex-created commit is
silently local or ahead of its upstream. For reusable workflow/template repo
changes, push is mandatory unless blocked.

After pushing a branch other than the repository's mainline branch, create or
update the PR for that branch, then route it through `gpa`. Report the `gpa`
review findings/state to the user and ask whether to merge. Only merge without
another question when the user explicitly asked for that merge in the current
turn. For reusable workflow/template repo changes, PR creation is mandatory
after push unless blocked; record the exact blocker instead of leaving only a
pushed branch.

After a PR is merged, check the repository's project instructions and command
contract for deployment or release steps. If the repo defines a deploy command
for this kind of change, run it or record the concrete blocker before handoff.
For GitButler-managed workstreams, the merge checkpoint is not complete until
the local repository is back in a consistent post-merge state: fetch/prune,
switch to the merged base branch, verify `<base> == origin/<base>`, delete
merged local `session/*` or `gest/*` work branches when they are not checked out
elsewhere, and run `but teardown` when no active GitButler stack work remains.
Do not leave the user on `gitbutler/workspace` at handoff unless continuing
GitButler work is explicit.

## Tag And Dependency Context

Before committing reusable workflow or code-facing changes, check related Gest notes for `classification.tags.*` and `impact.ast_grep.*` metadata from `references/tag_dependency_workflow.md`. Mention important dependency-impact follow-ups in the commit body or PR context when they affect reviewer expectations.
