---
name: gpa
description: Gest PR Accept. Review and accept a GitHub pull request as the GitHub-facing checkpoint of a Gest-tracked workstream, including PR metadata, diff review, checks, Gest context, merge recommendation, and post-merge bookkeeping.
---

# GPA: Gest PR Accept

Use when a GitHub pull request should be reviewed, approved, updated with Gest
context, merged, or held for changes.

`gpa` is different from `grv`: `grv` reviews a local diff or commit. `gpa`
reviews a pull request as an integration object with GitHub state, branch state,
checks, review history, and Gest task/artifact context.

`gpa` is mandatory after Codex pushes changes to a branch other than the
repository's mainline branch. The normal handoff is: create/update the PR, run
this skill, report the review packet to the user, and ask whether to merge.
Only merge without another question when the user explicitly asked for that
merge in the current turn.

After a PR is merged, inspect the repository instructions and command contract
for required deployment or release work. Run the applicable deploy/release step
or report the concrete blocker; a merge alone is not a completed handoff when
the project expects deployment.

## Inputs

Accept a PR number, URL, or current branch PR. If no PR is provided, discover it:

```bash
gh pr status
gh pr view --json number,url,title,headRefName,baseRefName,state
```

## Gather PR State

Inspect the PR before reviewing:

```bash
gh pr view <pr> --json \
  number,url,state,isDraft,title,body,author,headRefName,baseRefName,mergeable,reviewDecision,labels,commits,files,statusCheckRollup,latestReviews

gh pr diff <pr> --patch
gh pr checks <pr>
git status --short --branch
git log --oneline --decorate --graph --max-count=20
```

If GitButler is managing the checkout, also inspect:

```bash
but status
but branch list --all
```

## Gather Gest Context

Find Gest work related to the PR:

```bash
gest search "<pr title or branch>" --all --json --limit 20
gest search "<pr url>" --all --json --limit 20
gest task list --all --json
gest iteration list --all --json
```

Inspect likely parent and leaf tasks:

```bash
gest task show <task-id> --json
gest task note list <task-id> --json
gest iteration status <iteration-id> --json
gest iteration graph <iteration-id>
```

Look for:

- parent task and leaf tasks
- linked specs/artifacts
- iteration id and status
- completion notes with `Done`, `Verification`, and `Follow-up`
- `github.issue`, `github.url`, `github.pr`, `github.pr_url`
- `vcs.*` metadata such as branch mode, execution mode, workspace path, and
  integration method
- checkpoint graph paths

## Review

Produce findings first, as in `grv`. Review both code/docs behavior and PR
workflow safety:

- correctness, regressions, safety, error handling
- missing or insufficient tests
- docs drift
- installer or setup impact
- CI/check failures
- PR body mismatch with actual diff
- missing Gest context in the PR body
- missing task completion notes
- unsafe merge method for the branch model
- silent unpushed branches or dirty local worktrees
- GitButler violations such as raw git writes in GitButler mode or shared
  GitButler workspace parallelism

For non-trivial PRs, use adversarial review lenses. Default to independent
read-only review sub-agents when sub-agents are available, authorized, and the
lenses can be checked independently; skip sub-agents only when they are
unavailable, unsafe, or overkill for a tiny PR. Otherwise run the lenses
explicitly yourself:

- code behavior and regression risk
- test adequacy, including whether new tests would fail on the old code
- Git/GitButler branch, stack, worktree, push, and merge safety
- PR body and sanitized Gest context accuracy
- docs, setup, command-contract, release, and deployment drift
- security, privacy, data, browser/UI, or language/runtime risk when relevant

Writable sub-agents still require separate physical git worktrees. Gest
mutations, approvals, merges, and post-merge bookkeeping should remain
centralized unless deliberately assigned.

For reusable workflow PRs, preserve adapter boundaries: plain Git branches,
GitButler-managed branches/stacks, physical git worktrees, and JJ
bookmarks/workspaces must remain distinct. In this Git/GitButler skill family,
do not weaken `but` write-command guidance or treat GitButler parallel lanes as
agent isolation.

For `cx` workflow PRs, verify that `cx` is framed as incremental build/pipeline
infrastructure, not testing. Review `cx` lines for complete `--in`/`--out`
declarations, durable file outputs, producer/consumer Just ordering, and
`.cx` runtime-state ignore rules that do not hide future config.

Treat `Findings: None` as a precise statement about blocking or actionable
code-review findings, not as the whole PR review. If there are no findings, say
so clearly and list residual risk.

After findings, add reviewer judgment when it would help the user: call out
non-blocking opinions about clarity, maintainability, UX, naming, fit with local
patterns, PR shape, or tradeoffs. Label these separately from findings so
taste-level feedback does not look like a merge blocker.

## Acceptance Packet

Present a compact packet before any approval or merge:

```markdown
## Codex PR Review

Findings:
- None / <findings ordered by severity>

Reviewer Notes:
- <non-blocking opinions, maintainability/UX/readability judgment, or None>

PR State:
- PR: <url>
- Branch: <head> -> <base>
- Mergeability:
- Checks:
- Review decision:

Gest Context:
- Parent task:
- Leaf tasks:
- Iteration:
- Artifacts/specs:
- Completion notes:
- Verification notes:
- Follow-ups:
- GitHub metadata:
- Graph links:

Human Checklist:
- <what the user should inspect manually>

Adversarial Review:
- Code behavior:
- Test adequacy:
- Workflow/VCS safety:
- Docs/setup/contract drift:
- Residual risk:

Recommendation:
- approve/request changes/hold
- merge method: merge/squash/rebase
- post-merge steps
```

## Gest Context Appendix

Every PR for Gest-tracked work should include a Gest context appendix unless the
repo is public and the context is too internal. Prefer a concise sanitized
version in GitHub and full details in Gest notes.

Suggested PR body section:

```markdown
## Gest Context

- Parent: `<id>` <title>
- Leaves:
  - `<id>` <title>
- Iteration: `<id>` <title>
- Artifacts/specs: <none or list>
- Verification: <commands/checks>
- Follow-ups: <none or list>
- Graphs:
  - overall: <path-or-url>
  - focused: <path-or-url>
```

If the PR body lacks this context, offer to update it:

```bash
gh pr edit <pr> --body-file <file>
```

## Safe Actions

Ask before approving, requesting changes, or merging unless the user explicitly
asked you to perform that action.

Possible actions:

```bash
gh pr checkout <pr>
gh pr review <pr> --approve --body-file <file>
gh pr review <pr> --request-changes --body-file <file>
gh pr review <pr> --comment --body-file <file>
gh pr merge <pr> --merge --delete-branch
gh pr merge <pr> --squash --delete-branch
gh pr merge <pr> --rebase --delete-branch
```

After merging:

1. Verify the merged branch actually contained the intended changes. For
GitButler work especially, inspect the branch/merge diff instead of trusting
workspace assignments or an empty commit:

```bash
gh pr diff <pr> --patch
git show --stat <merge-or-head-sha>
```

Empty GitButler commits or `WIP Assignments` commits with no file changes are
red flags: reconcile them before merge or create a follow-up PR from a clean
checkout.

2. Restore a consistent local state.

For a plain-Git workstream, synchronize the local mainline and prune deleted
remotes:

```bash
git fetch --prune origin
git switch <base>
git pull --ff-only
git status --short --branch
```

For a GitButler workstream, do not run raw branch-mutating Git while GitButler
owns the workspace. If no further GitButler stack work remains, exit GitButler
mode first:

```bash
but teardown
git status --short --branch
```

Then, after teardown has left the repository in normal Git mode, synchronize the
base branch:

```bash
git fetch --prune origin
git switch <base>
git pull --ff-only
git status --short --branch
```

Confirm `<base>` and `origin/<base>` point to the same commit. If the PR branch
is still present locally and is merged or patch-equivalent to `<base>`, delete
it with `git branch -d <branch>`. This applies to both `session/*` and `gest/*`
work branches; those names are review/workflow handles, not durable records.
Do not delete a branch that is checked out in another worktree.

The final handoff should not leave the user on `gitbutler/workspace` unless
active GitButler work is intentionally continuing. `gitbutler/target` and
`gitbutler/workspace` are GitButler implementation refs, not normal work
branches to keep after teardown. If teardown fails, verify the worktree is
clean, `<base> == origin/<base>`, and the intended PR diff is merged before
recovering to `<base>`; record the exact recovery in the Gest note.

3. Add a Gest note to the parent and relevant leaf:

```text
Done: PR <url> merged with <method>. Merge commit: <sha>.
Verification: <checks reviewed or run>.
Follow-up: <real residual issue only>.
```

4. Store metadata when useful:

```bash
gest task meta set <task-id> github.pr <number>
gest task meta set <task-id> github.pr_url <url>
gest task meta set <task-id> github.merge_method <method>
gest task meta set <task-id> github.merged_commit <sha>
```

5. Regenerate checkpoint graphs for durable workflow changes.

## Tag And Dependency Review

PR review should inspect tag/dependency context from `references/tag_dependency_workflow.md`, especially selected semantic tags, `ast-grep` dependers, and follow-up tasks for coupled surfaces. Missing tag classification or missing dependency-impact coverage for changed code contracts is a review finding.
