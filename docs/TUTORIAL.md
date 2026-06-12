# Git And GitButler Tutorial

This tutorial creates four temporary GitHub repositories with fixed names,
runs four agent workflows, and tells you exactly what to check after each turn.
The pull-request steps create PRs first, then a later merge step merges those
PRs before cleanup deletes the temporary repositories.

You will learn:

1. ordinary git branch PR
2. ordinary git multi-commit PR
3. GitButler stacked PRs for dependent slices
4. physical git worktrees for independent parallel slices
5. tag classification and ast-grep dependency checks before code edits

Only step 3 uses GitButler as the main tool.

## Pull Request Command Map

This tutorial uses these PR creation commands:

- Step 1: `gh pr create --base main --head tutorial/plain`
- Step 2: `gh pr create --base main --head tutorial/multi`
- Step 3: `but pr new tutorial/stack-child --default --json`
- Step 4: `gh pr create --base main --head tutorial/worktree-a` and
  `gh pr create --base main --head tutorial/worktree-b`

For stacked PRs, select the top stack branch with `but pr new`. GitButler walks
the stack from bottom to top and creates the lower PR first, so one command
creates both the base and child PRs with the correct targets.

## What This Tutorial Will Do

The agent will create and later delete these GitHub repositories under your
GitHub account:

```text
agent-gest-git-tutorial-plain
agent-gest-git-tutorial-multi
agent-gest-git-tutorial-stack
agent-gest-git-tutorial-worktrees
```

Do not use those names for anything valuable. The prompts below tell the agent
to delete any existing repositories with those names before starting, then
delete them again during cleanup. Cleanup uses `gh repo delete --yes`.

Prerequisites:

- `gh auth status -h github.com` succeeds.
- Your GitHub auth has `repo` and `delete_repo` scopes.
- `git`, `gh`, `gest`, `just`, and `but` are installed.
- You are comfortable letting the agent create and delete the four temporary
  repositories named above.

## Step 0: Setup And Cleanup Contract

What this step teaches:

The agent should use fixed repo names, clean up before and after the tutorial,
and tell you where it wrote logs.

Ask the agent:

```text
Run the Git/GitButler tutorial setup.

Use my GitHub account from `gh api user -q .login`.
Use exactly these temporary private repo names:

- agent-gest-git-tutorial-plain
- agent-gest-git-tutorial-multi
- agent-gest-git-tutorial-stack
- agent-gest-git-tutorial-worktrees

Before starting, delete any existing GitHub repos with those names using
`gh repo delete <owner>/<name> --yes`, ignoring "not found" errors.

Create a local tutorial root at `/tmp/agent-gest-git-tutorial`.
Create `/tmp/agent-gest-git-tutorial/logs`.

For each following step, write a command log in that logs directory. After the
PR-opening steps finish, merge the PRs in Step 6. After the merge step, delete
the four GitHub repos unless I explicitly ask to keep them.
```

After the agent finishes, check:

```bash
test -d /tmp/agent-gest-git-tutorial/logs
```

The agent should report your GitHub owner and the exact log directory.

## Step 1: Ordinary Git Branch PR

What this step teaches:

Use ordinary git for one simple review branch. GitButler is not needed.

Repository:

```text
agent-gest-git-tutorial-plain
```

Ask the agent:

```text
Run tutorial step 1: ordinary git branch PR.

Create private GitHub repo `agent-gest-git-tutorial-plain`.
Clone or initialize it under `/tmp/agent-gest-git-tutorial/plain`.
Create `main` with README.md containing `plain tutorial base`.
Push `main`.

Create branch `tutorial/plain` with ordinary git, not GitButler.
Add `plain.txt` containing `plain branch change`.
Commit with message `test: add plain branch change`.
Push the branch.
Open a PR:

```bash
gh pr create \
  --repo "$(gh api user -q .login)/agent-gest-git-tutorial-plain" \
  --base main \
  --head tutorial/plain \
  --title 'test: plain git branch flow' \
  --body 'Tutorial plain git branch flow.'
```

Write all commands and key outputs to
`/tmp/agent-gest-git-tutorial/logs/01-plain-git-branch.log`.
```

After the agent finishes, check:

```bash
gh pr view tutorial/plain \
  --repo "$(gh api user -q .login)/agent-gest-git-tutorial-plain" \
  --json state,baseRefName,headRefName,title
```

Expected:

```text
state: OPEN
baseRefName: main
headRefName: tutorial/plain
title: test: plain git branch flow
```

Commands it should have used:

- `git checkout -b tutorial/plain` or equivalent ordinary git branch creation
- `git commit`
- `git push`
- `gh pr create`

Commands it should not have used:

- `but setup`
- `but branch new`
- `but commit`

## Step 2: Ordinary Git Multi-Commit PR

What this step teaches:

Use ordinary git when one review branch needs more than one commit.
GitButler is still not needed.

Repository:

```text
agent-gest-git-tutorial-multi
```

Ask the agent:

```text
Run tutorial step 2: ordinary git multi-commit PR.

Create private GitHub repo `agent-gest-git-tutorial-multi`.
Clone or initialize it under `/tmp/agent-gest-git-tutorial/multi`.
Create `main` with README.md containing `multi tutorial base`.
Push `main`.

Create branch `tutorial/multi` with ordinary git, not GitButler.
Add `session.txt` containing `session edit one`.
Commit with message `test: add first session edit`.
Append `session edit two` to `session.txt`.
Commit with message `test: add second session edit`.
Push the branch.
Open a PR:

```bash
gh pr create \
  --repo "$(gh api user -q .login)/agent-gest-git-tutorial-multi" \
  --base main \
  --head tutorial/multi \
  --title 'test: multi commit git branch flow' \
  --body 'Tutorial multi-commit git branch flow.'
```

Write all commands and key outputs to
`/tmp/agent-gest-git-tutorial/logs/02-multi-commit-git-branch.log`.
```

After the agent finishes, check:

```bash
owner="$(gh api user -q .login)"
gh pr view tutorial/multi \
  --repo "$owner/agent-gest-git-tutorial-multi" \
  --json state,baseRefName,headRefName,title,commits
```

Expected:

```text
state: OPEN
baseRefName: main
headRefName: tutorial/multi
title: test: multi commit git branch flow
commits: two commits on the PR branch
```

Commands it should not have used:

- `but setup`
- `but branch new`
- `but commit`

## Step 3: GitButler Stacked PRs

What this step teaches:

Use GitButler when you have multiple dependent, meaty slices that should be
reviewed separately. This is the GitButler step.

Repository:

```text
agent-gest-git-tutorial-stack
```

Ask the agent:

```text
Run tutorial step 3: GitButler stacked PRs.

Create private GitHub repo `agent-gest-git-tutorial-stack`.
Clone or initialize it under `/tmp/agent-gest-git-tutorial/stack`.
Create `main` with README.md containing `stack tutorial base`.
Push `main`.

Run `but setup`.
Create GitButler branch `tutorial/stack-base`.
Add `stack.txt` containing `stack base`.
Commit to `tutorial/stack-base` with message `test: stack base flow`.

Create GitButler branch `tutorial/stack-child` anchored on
`tutorial/stack-base`.
Append `stack child` to `stack.txt`.
Commit to `tutorial/stack-child` with message `test: stack child flow`.

Push both branches.
Open two PRs:
- `tutorial/stack-base` into `main`, title `test: stack base flow`
- `tutorial/stack-child` into `tutorial/stack-base`, title `test: stack child flow`

Create the stacked PRs with one `but pr new` command on the top branch:

```bash
but pr new tutorial/stack-child --default --json
```

Do not create the base PR in a separate earlier command. `but pr new` walks the
stack from bottom to top for the selected branch, so the top-branch command
creates both PRs in the right order.

Write all commands and key outputs to
`/tmp/agent-gest-git-tutorial/logs/03-gitbutler-stack.log`.
```

After the agent finishes, check:

```bash
owner="$(gh api user -q .login)"
gh pr list \
  --repo "$owner/agent-gest-git-tutorial-stack" \
  --state open \
  --json title,baseRefName,headRefName
```

Expected:

```text
PR: test: stack base flow
baseRefName: main
headRefName: tutorial/stack-base

PR: test: stack child flow
baseRefName: tutorial/stack-base
headRefName: tutorial/stack-child
```

Commands it should have used:

- `but setup`
- `but branch new tutorial/stack-base`
- `but branch new --anchor tutorial/stack-base tutorial/stack-child`
- `but commit`
- `but push`
- `but pr new tutorial/stack-child --default --json`

This step should not use physical git worktrees.

## Step 4: Physical Git Worktrees

What this step teaches:

Use physical git worktrees for independent parallel slices. Do not use
GitButler parallel lanes as an agent parallelism primitive.

Repository:

```text
agent-gest-git-tutorial-worktrees
```

Ask the agent:

```text
Run tutorial step 4: physical git worktrees.

Create private GitHub repo `agent-gest-git-tutorial-worktrees`.
Clone or initialize it under `/tmp/agent-gest-git-tutorial/worktrees`.
Create `main` with README.md containing `worktree tutorial base`.
Push `main`.

Create two physical git worktrees:
- `/tmp/agent-gest-git-tutorial/worktree-a` on branch `tutorial/worktree-a`
- `/tmp/agent-gest-git-tutorial/worktree-b` on branch `tutorial/worktree-b`

Prefix the raw worktree creation commands with
`GEST_VCS_EXECUTION=git-worktrees`.

In worktree A, add `worktree-a.txt` containing `worktree a isolated change`,
commit with message `test: add worktree a change`, push the branch, and open a
PR:

```bash
gh pr create \
  --repo "$(gh api user -q .login)/agent-gest-git-tutorial-worktrees" \
  --base main \
  --head tutorial/worktree-a \
  --title 'test: worktree a flow' \
  --body 'Tutorial physical worktree A flow.'
```

In worktree B, add `worktree-b.txt` containing `worktree b isolated change`,
commit with message `test: add worktree b change`, push the branch, and open a
PR:

```bash
gh pr create \
  --repo "$(gh api user -q .login)/agent-gest-git-tutorial-worktrees" \
  --base main \
  --head tutorial/worktree-b \
  --title 'test: worktree b flow' \
  --body 'Tutorial physical worktree B flow.'
```

Remove both physical worktrees after the PRs are open.

Write all commands and key outputs to
`/tmp/agent-gest-git-tutorial/logs/04-physical-worktrees.log`.
```

After the agent finishes, check:

```bash
owner="$(gh api user -q .login)"
gh pr list \
  --repo "$owner/agent-gest-git-tutorial-worktrees" \
  --state open \
  --json title,baseRefName,headRefName
```

Expected:

```text
PR: test: worktree a flow
baseRefName: main
headRefName: tutorial/worktree-a

PR: test: worktree b flow
baseRefName: main
headRefName: tutorial/worktree-b
```

Commands it should have used:

- `GEST_VCS_EXECUTION=git-worktrees git worktree add ...`
- ordinary `git commit` inside each physical worktree
- `gh pr create`

Commands it should not have used:

- GitButler parallel lanes
- two write agents in one GitButler workspace

## Step 5: Tags And ast-grep Dependency Check

What this step teaches:

Before the agent edits code, it should classify the task with project tags and
run ast-grep against the semantic contract that is changing. If another surface
depends on that contract, the agent should expand the task or create a tagged
child task before implementation.

This is a live local TypeScript repo lab. It demonstrates two different
dependency signals:

- tag dependency: Gest tasks already tagged with the same semantic concern
- ast-grep dependency: TypeScript call sites that use the changing function

Local fixture:

```text
/tmp/agent-gest-git-tutorial/tag-ast-grep-live
```

If you are running from this reusable skills repository, this command performs
the whole step:

```bash
scripts/run_tag_dependency_typescript_lab.sh \
  /tmp/agent-gest-git-tutorial/tag-ast-grep-live \
  /tmp/agent-gest-git-tutorial/logs/05-tag-ast-grep.log
```

Ask the agent:

```text
Run tutorial step 5: live TypeScript tag and ast-grep dependency lab.

Create or replace `/tmp/agent-gest-git-tutorial/tag-ast-grep-live`.
Initialize it as a git repo and a local Gest project.
Create `/tmp/agent-gest-git-tutorial/logs/05-tag-ast-grep.log`.

In Gest, create these existing tasks and tags:

- `Shared count/probability color contract`
  - tags: `count-or-probability-coloring`, `design`
- `Render histogram bin colors`
  - tags: `count-or-probability-coloring`, `histogram-colors`
- `Render probability pill colors`
  - tags: `count-or-probability-coloring`, `probability-pill-colors`
- `Polish reader hover affordance`
  - tags: `reader-ui`

Collect the existing tag vocabulary from Gest before choosing tags:

```bash
gest task list --all --json
gest artifact list --all --json
gest iteration list --all --json
```

Create a small TypeScript project with:

- `src/colors.ts`, exporting `countOrProbabilityColorScale`
- `src/histogram.ts`, calling `countOrProbabilityColorScale`
- `src/pill.ts`, calling `countOrProbabilityColorScale`
- `src/readerHover.ts`, not calling `countOrProbabilityColorScale`

Run `npm install` and `npm exec -- tsc --noEmit`.

Before editing anything, classify the requested change "change histogram colors
for low-count bins" against the Gest vocabulary:

- selected existing tag: `count-or-probability-coloring`
- selected existing tag: `histogram-colors`
- selected existing tag: `probability-pill-colors`
- rejected near miss: `reader-ui`
- new dynamic tags: none

Then run:

```bash
ast-grep run \
  --lang typescript \
  --pattern 'countOrProbabilityColorScale($$$)' \
  --json=compact \
  src
```

The tag dependency expansion should show the histogram and probability-pill
tasks are linked by `count-or-probability-coloring`. The ast-grep dependency
expansion should find both `src/histogram.ts` and `src/pill.ts`, and it should
not match `src/readerHover.ts`.

Write the selected tags, rejected tag, new-tag decision, tag-linked work,
ast-grep command, matched files, non-matched reader file, and dependency-impact
conclusion to `/tmp/agent-gest-git-tutorial/logs/05-tag-ast-grep.log`.
```

After the agent finishes, check:

```bash
rg "tag dependency expansion|ast-grep dependency expansion|count-or-probability-coloring|src/histogram.ts|src/pill.ts|src/readerHover.ts|reader-ui" \
  /tmp/agent-gest-git-tutorial/logs/05-tag-ast-grep.log
```

Expected:

```text
tag dependency expansion
ast-grep dependency expansion
count-or-probability-coloring
src/histogram.ts
src/pill.ts
src/readerHover.ts
reader-ui
```

The agent should report that a histogram-color implementation must also account
for the probability-pill color surface, or create a child task tagged with the
same semantic dependency before completion.

Commands it should have used:

- `gest task list --all --json`, `gest artifact list --all --json`, and
  `gest iteration list --all --json` before choosing tags
- `npm install` and `npm exec -- tsc --noEmit`
- `ast-grep run --lang typescript --pattern 'countOrProbabilityColorScale($$$)'`

Commands it should not have used:

- invented "existing" tags without first collecting a Gest tag vocabulary
- raw string-only dependency search as the primary check when `ast-grep` is
  available for the language

## Step 6: Merge The Tutorial PRs

What this step teaches:

Opening PRs is not the end of a durable checkpoint. Review and accept each PR
before merging, then merge the PRs before cleanup so branch deletion, PR state,
and stacked-PR ordering are exercised.

Ask the agent:

```text
Run tutorial step 6: accept and merge tutorial PRs.

Use my GitHub account from `gh api user -q .login`.

Before merging, record each PR number with `gh pr view <branch> --json number`.
For each PR, run the PR acceptance checkpoint first:

- inspect `gh pr view <number> --json number,url,state,isDraft,title,body,headRefName,baseRefName,mergeable,reviewDecision,commits,files,statusCheckRollup,latestReviews`
- inspect `gh pr diff <number> --patch`
- inspect `gh pr checks <number>`, treating "no checks reported" as an
  explicit state to report, not as a silent pass
- report findings first
- report PR state, checks, branch/base, mergeability, and the exact merge
  recommendation
- stop and ask before merging if there are findings, mergeability is not clean,
  or the PR target/branch shape is not the expected tutorial shape

Then merge these PRs with `gh pr merge <number> --merge --delete-branch`, and
verify each PR state is `MERGED` by PR number:

- repo `agent-gest-git-tutorial-plain`, PR branch `tutorial/plain`
- repo `agent-gest-git-tutorial-multi`, PR branch `tutorial/multi`
- repo `agent-gest-git-tutorial-worktrees`, PR branch `tutorial/worktree-a`
- repo `agent-gest-git-tutorial-worktrees`, PR branch `tutorial/worktree-b`

For repo `agent-gest-git-tutorial-stack`, merge in this order:

1. merge PR branch `tutorial/stack-child` into `tutorial/stack-base`
2. merge PR branch `tutorial/stack-base` into `main`

Write all commands and key outputs to
`/tmp/agent-gest-git-tutorial/logs/06-merge-prs.log`.
```

After the agent finishes, check:

```bash
owner="$(gh api user -q .login)"

gh pr list \
  --repo "$owner/agent-gest-git-tutorial-plain" \
  --state merged \
  --search "head:tutorial/plain" \
  --json state,baseRefName,headRefName,title

gh pr list \
  --repo "$owner/agent-gest-git-tutorial-multi" \
  --state merged \
  --search "head:tutorial/multi" \
  --json state,baseRefName,headRefName,title

gh pr list \
  --repo "$owner/agent-gest-git-tutorial-stack" \
  --state merged \
  --json title,baseRefName,headRefName

gh pr list \
  --repo "$owner/agent-gest-git-tutorial-worktrees" \
  --state merged \
  --json title,baseRefName,headRefName
```

Expected:

```text
plain PR: state MERGED, baseRefName main, headRefName tutorial/plain
multi PR: state MERGED, baseRefName main, headRefName tutorial/multi
stack child PR: state MERGED, baseRefName tutorial/stack-base
stack base PR: state MERGED, baseRefName main
worktree A PR: state MERGED, baseRefName main
worktree B PR: state MERGED, baseRefName main
```

Commands it should have used:

- `gh pr view <branch> --json number` before deleting PR branches
- `gh pr view <number> --json ...`, `gh pr diff <number> --patch`, and
  `gh pr checks <number>` as the PR acceptance checkpoint before merging
- `gh pr merge <number> --merge --delete-branch`
- `gh pr view` or `gh pr list --state merged`

Commands it should not have used:

- deleting the temporary repositories before PR state is verified as `MERGED`
- deleting stacked branches before the child and base stack PRs are merged

## Step 7: Cleanup

Ask the agent:

```text
Run tutorial cleanup.

Delete these GitHub repositories if they exist:
- agent-gest-git-tutorial-plain
- agent-gest-git-tutorial-multi
- agent-gest-git-tutorial-stack
- agent-gest-git-tutorial-worktrees

Use `gh repo delete <owner>/<repo> --yes`.
Remove `/tmp/agent-gest-git-tutorial/worktree-a` and
`/tmp/agent-gest-git-tutorial/worktree-b` if they still exist.
Keep `/tmp/agent-gest-git-tutorial/logs` unless I ask you to remove logs.
```

After cleanup, check one repo:

```bash
owner="$(gh api user -q .login)"
gh repo view "$owner/agent-gest-git-tutorial-plain"
```

Expected:

```text
repository not found
```

## Automated Regression Labs

The scripts in this repo are regression checks, not the beginner tutorial:

```bash
just workflow-lab
just tag-dependency-live-lab
just language-profile-labs
just integration-live
```

They intentionally stress GitButler itself. Read this tutorial first; use those
scripts when you want to verify the reusable skill repository.
