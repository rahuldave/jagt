---
name: gpa
description: Gest PR Accept. Review and accept a GitHub pull request as the GitHub-facing checkpoint of a Gest-tracked workstream, including PR metadata, diff review, checks, Gest context, merge recommendation, and post-merge bookkeeping.
license: MIT, copyright (c) 2026 Rahul Dave. The full text is in the LICENSE file of https://github.com/rahuldave/agent_gest_git_skills
---

# GPA: Gest PR Accept

Use when a GitHub pull request should be reviewed, approved, updated with Gest
context, merged, or held for changes.

`gpa` is different from `grv`: `grv` reviews a local diff or commit. `gpa`
reviews a pull request as an integration object with GitHub state, branch state,
checks, review history, and Gest task/artifact context.

`gpa` is mandatory after Codex pushes a topic or stack branch for integration
into either mainline or a persistent non-default target. The normal handoff is: create/update the PR, run
this skill, report the review packet to the user, and ask whether to merge.
Only merge when that particular merge is already authorized; authorization
persists across turns.

After a PR is merged, inspect the repository instructions and command contract
for required deployment or release work. Run the applicable deploy/release step
or report the concrete blocker; a merge alone is not a completed handoff when
the project expects deployment.

## Integration and delivery policy

Read [the integration and delivery contract](references/integration_delivery_workflow.md)
for explicit branch roles, selected PR bases, independent review evidence,
CI gates, issue completion, installation provenance and safe cleanup. Apply it
throughout this skill; the repository default is not an implicit PR target.

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
  number,url,state,isDraft,title,body,author,headRefName,headRefOid,baseRefName,baseRefOid,mergeable,reviewDecision,labels,commits,files,statusCheckRollup,latestReviews

gh pr diff <pr> --patch
gh pr checks <pr>
git status --short --branch
git log --oneline --decorate --graph --max-count=20
```

If the PR is part of a stack, also check that its base is the branch below it:

```bash
gh pr view <pr> --json baseRefName,headRefName
git diff <parent-branch>...<head-branch>
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
- selected integration target and actual reviewed base/head commits

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
- a stacked PR whose base is not the branch below it, or parallel write
  agents in one checkout

For non-trivial PRs, use adversarial review lenses. Default to independent
read-only review sub-agents when sub-agents are available, authorized, and the
lenses can be checked independently; skip sub-agents only when they are
unavailable, unsafe, or overkill for a tiny PR. Otherwise run the lenses
explicitly yourself:

- code behavior and regression risk
- test adequacy, including whether new tests would fail on the old code
- Git branch, stack, worktree, push, and merge safety
- PR body and sanitized Gest context accuracy
- docs, setup, command-contract, release, and deployment drift
- security, privacy, data, browser/UI, or language/runtime risk when relevant

Writable sub-agents still require separate physical git worktrees. Gest
mutations, approvals, merges, and post-merge bookkeeping should remain
centralized unless deliberately assigned.

For reusable workflow PRs, preserve adapter boundaries. Plain Git branches,
stacks of Git branches, physical git worktrees, and JJ bookmarks and workspaces
must stay distinct. In this Git skill family, do not treat the branches of a
stack in one checkout as agent isolation. Physical git worktrees isolate
parallel agents.

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
- Reviewed base/head commits and reviewer identity:

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
- Integration target: <branch>
- Reviewed commits: <base SHA> / <head SHA>
- Independent reviewer and findings: <evidence>
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
gh pr merge <pr> --merge --match-head-commit <reviewed-head-sha>
gh pr merge <pr> --squash --match-head-commit <reviewed-head-sha>
gh pr merge <pr> --rebase --match-head-commit <reviewed-head-sha>
```

After merging:

1. Verify the merged branch actually contained the intended changes. For a
stacked PR especially, inspect the branch or merge diff instead of trusting the
PR title or an empty commit:

```bash
gh pr diff <pr> --patch
git show --stat <merge-or-head-sha>
```

An empty commit with no file changes is a red flag. Reconcile it before the
merge, or create a follow-up PR from a clean checkout.

2. Restore a consistent local state without moving the primary checkout off
its recorded branch. Before cleanup, record `<primary-path>` and
`<primary-branch>` independently of the selected PR `<base>`, and inspect
`git worktree list --porcelain` for a checkout already on `<base>`.

For plain Git, fetch the selected target from a normal-Git checkout:

```bash
git fetch --prune origin
git rev-parse origin/<base>
```

If `<base>` is checked out in a known clean normal-Git checkout, run:

```bash
git -C <base-checkout> status --short --branch
git -C <base-checkout> pull --ff-only origin <base>
git -C <base-checkout> rev-parse HEAD
git -C <base-checkout> rev-parse origin/<base>
```

Confirm the two SHAs match. If `<base>` is not checked out,
use the fetched remote-tracking ref as integration evidence and defer moving
the local `<base>` branch until an appropriate checkout is available. Do not
`git switch <base>` in the primary checkout merely to perform cleanup.

For a stack, merge the PRs bottom-up. After a lower PR merges, retarget the
next PR to the new base with `gh pr edit <next-pr> --base <base>`. Then fetch,
and run `git rebase --update-refs --onto origin/<base> <old-lower-tip>` on the
top branch. `<old-lower-tip>` is the commit of the merged branch before the
merge. It is the local `<lower-branch>`, which the merge on GitHub does not
move.
With `--onto`, Git replays only the commits above the merged branch, so
a squash merge does not apply the merged commits twice. Push each moved branch
with `git push --force-with-lease`. Git 2.38 and later have `--update-refs`.

Only delete a temporary PR/topic branch after its role, integration and
worktree/stack dependencies are verified. For a normal merge, independently
check `git merge-base --is-ancestor <branch> <target-ref>`; `git branch -d`
may compare against the branch's configured upstream instead of HEAD and is
not integration proof. Prefer a clean checkout on the actual merged target (or
immediate stack parent) when running `git branch -d <branch>` so its HEAD
fallback is meaningful. If no suitable checkout exists or deletion is refused,
retain the branch. A squash/cherry-pick needs a separate patch-equivalence and disposal decision,
not automatic forced deletion. Preserve persistent integration branches,
including an experimental head promoted into mainline.

If this PR used worker-owned physical worktrees, retire each one only after its
worker and owned processes stop, its tracked/untracked and valuable ignored
files are accounted for, its commits are verified in the intended base or
stack parent, and no active task or stack depends on it. Check the recorded
owner/path/branch against `git worktree list --porcelain`; use ordinary
`git worktree remove <owned-absolute-path>` from another checkout and verify
removal before considering the temporary topic branch. Keep the selected
primary checkout, persistent integration branches and unrelated or
user-retained worktrees. Follow the full retirement policy in
`references/integration_delivery_workflow.md`.

`just worktrees` shows which worktrees are clean and merged. When the user asks
to clean up worktrees, run `just worktrees-prune --dry-run`, show the result,
then run `just worktrees-prune`.

At handoff, verify `git -C <primary-path> symbolic-ref --short HEAD` equals the
recorded `<primary-branch>`. If the cleanup changed it, switch back only when
that checkout is clean and the branch is not checked out elsewhere. Otherwise
stop and report a blocker, and do not disturb another checkout. If the cleanup
fails, verify that the intended PR diff is merged before recovery, and record
the exact state in the Gest note.

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

5. Update the linked issue according to its intended delivery milestone;
   experimental integration does not imply release completion. Gest maintains
   its own graphs automatically.

## Tag And Dependency Review

PR review should inspect tag/dependency context from `references/tag_dependency_workflow.md`, especially selected semantic tags, `ast-grep` dependers, and follow-up tasks for coupled surfaces. Missing tag classification or missing dependency-impact coverage for changed code contracts is a review finding.
