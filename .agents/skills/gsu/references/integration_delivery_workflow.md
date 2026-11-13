# Integration branches, review, and delivery

## Branch roles

Each branch has one role, and project policy states it. Do not infer the role
from the name or the prefix of a branch.

- **The default branch** of the repository, often `main`, is its normal
  mainline.
- **A persistent integration branch** collects the work of many tasks for an
  experiment or a line of releases.
- **A topic branch** is temporary, and it holds one change that a person can
  review.
- **A stack** is a set of topic branches that depend on each other.

The mainline and each integration branch get changes only through reviewed pull
requests (PRs).

Before you edit, find the default branch, the integration target that the user
chose, and the current remote SHA of that target. The project instructions can
already name the target. Create the topic branch from the target, and open its
PR back to the target. Record these values:

```text
vcs.default_branch=<repository default>
vcs.integration_branch=<persistent target>
vcs.base_branch=<immediate PR base>
vcs.base_sha=<resolved starting base commit>
vcs.branch_role=topic|stack-topic|integration
vcs.branch=<work branch>
vcs.integration_sha=<resolved integration commit>
```

For an ordinary topic, the base branch and the integration branch are the same.
Do not choose `main` only because it is the default branch. Keep the mainline
and each persistent integration branch in a state that builds. Do not push work
directly to either of them.

You can create a new persistent branch at a reviewed commit that already
exists. The new branch becomes a target, and it does not need an empty PR. When
you publish that branch, you do not also open a PR from the whole experiment
into the mainline. The promotion of an experiment to the mainline is a separate
PR, with its own scope and its own authorization.

The branch prefix of the project wins over the examples in these skills. A
worker branch inside a task can merge into its topic locally, and you can then
remove it without its own remote PR. Do so only when the review of the topic
includes the changes of the worker branch. Record each such local merge.
Never use one to go around the PR to the target.

## Dependent stacks and parallel work

Use a normal topic PR for a change that is complete in itself. Use a stack when
the parts of a change depend on each other and are easier to review one by
one. The bottom PR of the stack targets the chosen integration branch.
Each higher PR targets the PR directly below it. Record `vcs.stack_root`,
`vcs.stack_parent` and `vcs.stack_index`, together with the integration target
that all the PRs share.

Merge the stack from the bottom up. After each merge, do these steps before you
merge the next PR:

1. Read the actual base and head of each PR on GitHub.
2. Retarget or restack the PRs as necessary.
3. Run the affected checks and the review again.

Do not delete a lower branch while a PR above it still depends on it.

Build the stack with plain git. Git 2.38 and later have each command:

1. Start each branch from the branch directly below it, for example
   `git switch -c <child> <parent-branch>`.
2. Open the PR of each branch with `gh pr create --base <parent-branch>`. The
   bottom PR uses the chosen integration branch as its base.
3. After a change to a lower branch, check out the top branch of the stack, and
   run `git rebase --update-refs --onto <lower-branch> <old-lower-tip>`.
   `<old-lower-tip>` is the lower branch before the change. Save it with
   `git rev-parse <lower-branch>` before you change the branch.
   `<lower-branch>@{1}` is that commit only after one change. Git then moves
   each branch of the stack together, and it replays only the commits above
   the lower branch. It does not move a branch that another worktree has
   checked out, so restack where no worktree holds a branch of the stack.
4. Push the moved branches with `git push --force-with-lease`.

One checkout holds one branch at a time. So two writers in parallel need
separate physical worktrees, and you merge their work later on purpose.

## Independent adversarial review

An adversarial review is a review by someone who tries to find what is wrong
with a change. Before you recommend a merge, get an independent adversarial
review for each change of these kinds:

- substantial code;
- setup that runs commands;
- CI;
- a workflow that other projects reuse.

Give the reviewer the requirements, the scope, the actual base and head
commits, the diff and the evidence of verification. Ask the reviewer to look
for counterexamples, missing tests, paths to a regression and unsafe results of
the workflow. The reviewer must not be the one who implements the change. An
independent subagent with read-only access is a good reviewer when one is
available and authorized. A review of your own work is useful, but label it as
a self-review. If no independent reviewer is available, report that gap and do
not recommend the merge.

Record the identity of the reviewer, `review.base_sha`, `review.head_sha`, the
scope and the findings. For each finding, record one of these dispositions:

- fixed, with evidence;
- rejected, with the reason;
- accepted on purpose as a remaining risk.

A fix needs a review of the changed part, and of the contracts that it affects,
at the new head. A change to the base needs an assessment of the new
integration context. It also needs a new run of the affected checks and the
review. A clean review of earlier commits does not carry over to new commits.
A passing CI is a different thing from a review. The authorization of a person
to merge is different from both.

On GitHub, the author of a PR cannot approve it. An independent agent that uses
the GitHub account of the author can give evidence of review. But GitHub does
not count it as a different approver. Set the rules to match the real team.
Never invent an approval, and never go around a required reviewer.

## CI and delivery contract

Each skill has its own part in CI. GSU records the commands and the triggers.
GTE verifies the behavior and the paths of failure. GPA checks the results of
the exact PR.

Every supported target gets checks on its PRs. Do not use a filter on the base
or on the path that stops a required workflow from reporting. If some jobs run
only on a condition, add a stable summary job that is a required status check. Run it
with `always()`, and make it fail if any expected job did not succeed. A skipped
test is not evidence that the test passes. Where the project contract asks for
it, also verify the pushes to an integration branch.

Pin the dependencies, and document the versions of the tools. Map each
boundary that is relevant to a check:

- static checks;
- focused tests;
- integration tests;
- validation of the build and the package;
- a clean installation.

In the workflow labs, use an integration target that is not the default branch.
Some checks need credentials, cost money or destroy something outside the
project. Keep each of them explicit, and run it only when someone asks. An ordinary
PR job from an untrusted source gets no credentials to publish. Keep the evidence.
Document which platform checks and live checks stay outside the automatic
coverage.

Delivery has its own policy, with three possible milestones:

1. Reviewed source integrated into the selected branch.
2. Installable snapshot/artifacts built and checked at an exact commit.
3. Versioned release published and independently verified.

A merge into an experimental branch usually reaches the first milestone, and it
can reach the second. It does not authorize the publication of a stable
release. Record what the actual target needs after a merge. Do not run a
generic deploy command in every case.

For a skill package, do these things:

1. Validate the manifest and the local references.
2. Test the installation into a project that already exists.
3. Record the source revision.
4. Publish a requested version or tag only from content that you checked.

A project can use a protected tag or a manual release job. Protect its
credentials, and verify the artifacts that it makes. Do not call a delivery of
source only a package release.

## Issues and task completion

Promote to GitHub each durable initiative and each feature that can ship on its
own. Keep the small leaves of execution in Gest. Link each PR to its issue, and
store the URLs of the issue and the PR back in Gest. Define the completion
target of the issue at the start. The target is one of these:

- experimental integration;
- mainline integration;
- a published release.

GitHub reads the closing keywords of a PR only when the PR targets the default
branch of the repository. For any other target, use `Refs #N`, an explicit link
to the issue and an update to the issue after the merge. Close an issue by hand
only when its stated scope of acceptance is complete, and only when someone
authorized the close. Keep a release issue or an initiative issue open when a
slice only reached the experiment. Do not put closing footers in experimental
commits. A later promotion of those commits can close an issue that nobody
meant to close.

Gest keeps its graphs up to date by itself. Keep creating the native links for
the hierarchy and the dependencies, and read `gest iteration graph` when it
helps. You do not need a separate graph exporter, graph file or checkpoint for
the path of a graph.

## Installation and resource ownership

During an installation, keep the existing project instructions, hooks and
unrelated settings. Review each conflict of configuration explicitly, and test
that a second install works. Record the URL of the repository, the exact source
commit and whether the source had uncommitted changes. A branch name alone is
not enough provenance, because a branch can move. Refresh the installed skills
on purpose, and keep the mirrored references the same.

Record the temporary directories, server processes, ports and child processes
that the task owns. Use isolated resources that you can throw away for tests.
Stop only the processes that the task started, and verify that they stopped.
Remove only the temporary files that the task owns. Never stop a server of the
user to make a test pass. Never reuse a port that is in use without saying so.

## Merge and cleanup

Just before the merge, GPA verifies these things:

- the intended base;
- the reviewed head and base;
- the checks;
- the disposition of each finding;
- the existing authorization to merge.

Keep the authorization of the user from one turn to the next. Ask only when the
user did not authorize this particular merge.

After a merge that you confirmed, fetch the actual integration target. If a
known clean checkout has that branch checked out, update it there with
`git pull --ff-only`. Then verify that it matches `origin/<base>`. If no
clean checkout has the branch, verify the fetched ref `origin/<base>`, and
leave the local branch as it is
until an appropriate checkout can fast-forward it.

Never switch the primary checkout to `<base>` only for the cleanup. Record and verify the separate path and branch of
the primary checkout.

Keep the persistent branches. Delete a temporary topic only after you verify
that it is merged and that no worktree or stack depends on it. Do not use
`--delete-branch` on a persistent experimental branch when you promote it to
the mainline. It is better to merge first and to decide about the cleanup
separately. Report each of these states separately:

- the source integration;
- the artifact installation;
- the state of the issue;
- the state of the publication.

### Retire an owned physical worktree

A physical worktree that you create for a worker is a separate checkout, with
its own branch. Before you dispatch the worker, record these facts
about the worktree:

- its absolute path;
- its topic branch;
- its owner and task;
- the chosen integration branch;
- the stack parent directly below it, if there is one.

Also record the absolute path **and current branch** of the primary checkout,
separately. The project chooses the primary branch. It can be `main` or another
persistent target, and it does not have to be the integration branch of this
task. Use `git worktree list --porcelain` to compare the record with the real
worktrees. Never infer ownership from the prefix of a path. Never delete the
primary checkout, a checkout that is not related to the task, or a checkout
that the user chose to keep.

After the worker finishes, wait until its agent and each process that it started
have stopped. Confirm that no active task, child worktree, open stack or open PR
depends on its branch. In the owned worktree, run
`git status --porcelain=v1 --untracked-files=all` and
`git status --short --ignored`. Account for the tracked, untracked and valuable
ignored files before you remove the checkout. Keep valuable files on purpose, or
leave the worktree in place and report why.

Before you retire the worktree, verify that the commits of the worker reached
the chosen integration branch or the stack parent directly below it. For a
normal merge, the ancestry of the commits is enough. A cherry-pick or a squash
merge changes the commit IDs. So it needs a reviewed decision, from the diff,
that the patches are equivalent. An open PR, a push or a completed Gest task is
not evidence of integration. If the state of the integration or of a dependency
is uncertain, keep the worktree and the topic branch.

To remove the worktree, do these steps in order:

1. From another checkout, run `git worktree remove <owned-absolute-path>`
   without `--force`.
2. Verify that `git worktree list --porcelain` no longer lists the worktree.
   Do not use a routine `rm -rf`, a forced removal of the worktree or a prune
   to get past a dirty state.
3. Only then, think about the topic branch, if it is temporary and can go. For
   a normal merge, verify `git merge-base --is-ancestor <topic> <target-ref>`
   yourself. `git branch -d` is not proof of integration into the target,
   because Git can compare the topic with its configured upstream and not with
   the current HEAD.
4. Run `git branch -d <topic>`, if possible from a clean checkout of the actual
   merged target or of the stack parent directly below. In that checkout, HEAD
   is the target, so a comparison with HEAD is a comparison with the target. If that checkout is not available, or Git refuses
   the deletion, keep the topic and report why.
5. For a cherry-pick or a squash merge, make an explicit, reviewed decision
   about the equivalence of the patches and about the disposal of the branch.
   Do not force the deletion automatically when `git branch -d` refuses it.
6. Verify that `git -C <primary-path> symbolic-ref --short HEAD` still names
   the recorded primary branch. If a step changed it, restore that branch only
   in the clean primary checkout. First check that no other checkout holds the
   branch. If you cannot, keep the state and report what blocks you.

Keep these things intact:

- persistent integration branches;
- stack parents that have dependents;
- primary branches;
- worktrees that the user chose to keep.

Record what you removed and what remains.

`just worktrees` lists every worktree with its state. The state tells whether
the worktree is clean or dirty, and whether it is merged into the base branch
or its branch on origin. The list also names the ignored files that a removal
deletes.

`just worktrees-prune` removes each worktree that is clean, merged
and idle for two hours, with ordinary `git worktree remove`. A worktree is
merged when the base has its commits. It is also merged when `git merge-tree`
of the worktree into the base leaves the base tree unchanged. So work that
reached the base through a rebase or a squash counts as merged. Work that the
base later reverted does not count.

Prune keeps these worktrees:

- a locked worktree;
- the worktree it runs in;
- a detached worktree whose commits are on no branch;
- a worktree with ignored files that setup did not put there.
  `--with-ignored` removes those too.

Ignored files that `.worktreedisposable` names, such as `.venv/`, can be made
again, so they do not keep a worktree. Prune keeps all branches. It does not
check ownership, so an agent runs it only when the user asks, after
`just worktrees-prune --dry-run`.

## References

- [GitHub issue linking and non-default targets](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)
- [Required checks and skipped workflows](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)
- [GitHub approval restrictions](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews)
