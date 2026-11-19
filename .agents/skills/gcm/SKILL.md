---
name: gcm
description: Gest Commit. Create a Git commit for the current changes, using conventional commit style and GitHub metadata when present.
license: MIT, copyright (c) 2026 Rahul Dave. The full text is in the LICENSE file of https://github.com/rahuldave/agent_gest_git_skills
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

Session-mode work must still use `gcm` for each commit-required checkpoint, such as
deployment/runtime configuration, persistence, migrations, schemas, public APIs,
user-visible UI, reusable workflow material, publishable docs/templates, and
non-trivial multi-file verified changes. Do not treat "session leaf" as a
standalone no-commit reason.

Development-mode work should be committed at durable checkpoints, such as after a
verified depth-1 workstream or coherent depth-2 implementation subtree, before
switching product areas, before handoff, after risky bug/migration work, or
before GitHub issue/PR sync.

In development mode, do not default to asking the user whether a verified slice
should be committed. Make the judgment yourself after each coherent depth-2
implementation leaf or tightly related set of leaves. Prefer committing before
continuing when the slice changes schema, persistence, query semantics, public
APIs, user-visible UI, or non-trivial verification. Keep the unit small enough
that `git bisect` would land on a useful layer.

Use completed Gest task notes to draft copious but focused commit bodies. Include what changed from `Done`, the exact checks from `Verification`, and any
real `Follow-up`. Never include Gest IDs.

After creating a commit, run checkpoint hygiene. Gest maintains its graphs
automatically, so no separate export is required. The review of the commit is
`grv`, which the gate needs before the commit.

Also make and verify a push/sync decision. `git push` is separate from GitHub
issue promotion. For development depth-1 parents or development iterations, run
the explicit `gpr` decision. It creates or syncs the GitHub issue and records
the metadata, or records why promotion was skipped. Report the selected PR
base, commit hash, final branch relationship, push status, review status, and
the GitHub issue decision.

## Integration and delivery policy

Read [the integration and delivery contract](references/integration_delivery_workflow.md)
for explicit branch roles, selected PR bases, independent review evidence,
CI gates, issue completion, installation provenance and safe cleanup. Apply it
throughout this skill; the repository default is not an implicit PR target.

## Workflow

Inspect:

```bash
git status --short --branch
git diff
git diff --staged
git log --oneline -10
git remote -v
```

If the branch is part of a stack, also compare it with the branch below it:

```bash
git branch --list
git diff <parent-branch>...HEAD
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

## The commit gate

Commit after the pass and the records, not before. The commit gate checks
both, so a commit without them stops.

1. Run each agentic target that the change needs. The order is
   `just update-docs`, `just prose`, `just review` and `just test-review`.
   Each one writes a packet for a fresh agent, and the hook of the harness
   writes a record from the result. The gate needs `review` for every commit,
   and the others when the change touches their files.
2. Run `just check` last, on the tree that you commit. The gate needs a pass
   for that tree, and `update-docs` and the fixes of findings change the tree.
3. Commit with plain git. The hooks do the rest:
   - The pre-commit hook runs the gate on the tree.
   - The commit-msg hook adds the trailer `Commit-Gate: patch:<id>` to the
     message.
   - The pre-push hook runs `just ci`, which checks that each pushed commit has
     the trailer.

When the repository has no `just check`, run `gsu` first. It installs the
recipes and the hooks.

### When the gate stops

The message of the gate names what is missing. Do what it says, then commit
again:

- **No pass for this tree.** Run `just check`, and fix what fails. A change
  after the pass makes a new tree, so run it again after each change. Under
  pre-commit, an unstaged edit of a tracked file gives this stop too, because
  pre-commit puts it aside. The stop then also gives the stash fix below.
- **No record of a target.** Run the targets in the order that the message
  gives. A record counts only when its status is a pass and each finding is
  fixed.
- **Only part of the changes is staged.** The gate checks the whole worktree.
  Stage all the changes, or put the rest aside:
  1. Run `git stash --keep-index -u`. The worktree now has a new tree.
  2. Run the targets that the new tree needs, then `just check`.
  3. Commit, then run `git stash pop`.
- **A finding that is not fixed.** Fix it with a test, and run the target again
  on the new tree.
- **In Codex, a write to `.agents` or `.git` is denied.** The
  `workspace-write` sandbox of Codex keeps both folders read-only, and a
  writable root of the folder above them does not help. `just check` writes
  its run log in `.agents/log` of the worktree. The targets write their
  packets in `.agents/log` of the main checkout. `git commit` writes in the
  git folder. Ask the person to approve the command outside the sandbox. Or
  ask them to start Codex with each of these folders as a writable root:
  - `<main>/.agents` and `<main>/.git`, where `<main>` is the main checkout.
  - In a worktree, also `<worktree>/.agents`, and the git folder of the
    worktree, which `git rev-parse --git-dir` prints.

  For the main checkout, the command is:

  ```bash
  codex -s workspace-write -c 'sandbox_workspace_write.writable_roots=["<main>/.agents","<main>/.git"]'
  ```

  In a worktree, it is:

  ```bash
  codex -s workspace-write -c "sandbox_workspace_write.writable_roots=[\"<main>/.agents\",\"<main>/.git\",\"$PWD/.agents\",\"$(git rev-parse --git-dir)\"]"
  ```

Do not go around the gate. `--no-verify`, `core.hooksPath`, `git commit-tree`
and `git update-ref` are stopped by the guard of the hooks, and a commit
without the trailer fails `just ci`.

### A skip

`just record-skip <target> <reason>` lets one tree through without the record
of that target. Use it only when the person agrees:

1. Ask the person first. Give the target, the tree and the reason, for example
   "a typo in a comment".
2. Run it only after a clear yes. In Claude Code the hook asks the person
   again. In Codex the hook stops the command, so ask the person to run it.

The run log keeps the reason of each skip.

## Stacked PRs With Plain Git

Commit with plain git, such as `git add <file>` and `git commit`. No hook
blocks plain git, and no command needs a marker. In the `gitwt` variant, a
commit in the main checkout gets a warning, so commit in the worktree of the
task.

A stack is a chain of dependent branches, each with its own PR. Build it with
plain git:

```bash
git switch -c <child-branch> <parent-branch>
git commit -m "<message>"
git push -u origin <child-branch>
gh pr create --base <parent-branch> --head <child-branch>
```

1. Start each branch from the branch below it.
2. Open the PR of each branch with `gh pr create --base <parent-branch>`, from
   the bottom branch up. `just stack-prs <base> <bottom-branch> ... <top-branch>`
   does this for the whole stack. It first checks that each branch contains the
   branch below it, and it pushes each branch that has no upstream. Run it with
   `--dry-run` first to see each step.
3. Commit review feedback to the branch where it belongs, and not to the top of
   the stack by default.
4. After a change to a lower branch, switch to the top branch and run
   `git rebase --update-refs --onto <lower-branch> <old-lower-tip>`, with the
   branch that changed. `<old-lower-tip>` is that branch before the change.
   Save it with `git rev-parse <lower-branch>` before you change the branch.
   `<lower-branch>@{1}` is that commit only after one change. Git replays only
   the commits above it, and moves every branch of the stack above it together.
   It does not move a branch that another worktree has checked out. Git 2.38
   and later have `--update-refs`.
5. Push each moved branch with `git push --force-with-lease origin <branch>`.

Merge and review the stack bottom-up. GitHub merge commits are acceptable for a
stack when they keep the retargeting of the PRs above smooth. A simple branch
outside a stack should still prefer a rebase with a fast-forward, or a squash.

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

After pushing a topic or stack branch, create or
update the PR for that branch, then route it through `gpa`. Report the `gpa`
review findings/state to the user and ask whether to merge. Only merge when that particular merge is already authorized; authorization
persists across turns. For reusable workflow/template repo changes, PR creation is mandatory
after push unless blocked; record the exact blocker instead of leaving only a
pushed branch.

After a PR is merged, check the repository's project instructions and command
contract for deployment or release steps. If the repo defines a deploy command
for this kind of change, run it or record the concrete blocker before handoff.
For a stack, the merge checkpoint is not complete until the local repository is
back in a consistent state after the merge:

1. Run `git fetch --prune`.
2. Switch to the merged base branch, and verify `<base> == origin/<base>`.
3. Delete each merged temporary topic branch that has no worktree and no branch
   of the stack above it.

## Tag And Dependency Context

Before committing reusable workflow or code-facing changes, check related Gest notes for `classification.tags.*` and `impact.ast_grep.*` metadata from `references/tag_dependency_workflow.md`. Mention important dependency-impact follow-ups in the commit body or PR context when they affect reviewer expectations.
