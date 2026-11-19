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

### Push a topic that has merged its PR base

This procedure requires the tasker pre-push hook, which runs `just ci` and its
`ci-gate` trailer check. Use the project's `just install` composition to install
or refresh the tasker role. Commit through its hooks to generate the
`Commit-Gate` trailers; this push command only checks them.

Verify the PR's target branch on GitHub, then read its current remote tip with
`git ls-remote origin refs/heads/<PR-target>`. Pin that tip's full commit SHA as
the base. For a topic branch that already exists on the remote, set
`JN_CI_BASE` to that verified SHA for the normal push:

```bash
JN_CI_BASE=<verified-PR-target-tip-SHA> git push origin <topic>
```

The gate checks every commit in `BASE..HEAD`. The range contains commits
reachable from the pushed head, excluding those reachable from the selected
base. This includes original feature commits and the local integration merge.

The gate checks that the supplied base resolves to a commit and is an ancestor
of the pushed head. It also checks that each commit of the base is already on
the remote of the push. Fetch the PR target before the push, so that the
remote-tracking branch holds its tip. A base of the topic, or of a commit that is
new in this push, stops the push. The gate prints the number of commits that the
base selects.

Give `JN_CI_BASE` on the command line of the push only, and do not export it in
the shell. The operator must verify that it is the PR target's tip; the gate
does not validate PR acceptance. The hook supplies the pushed head, and a
conflicting `JN_CI_HEAD` fails. Inspect the complete range with
`git log <verified-PR-target-tip-SHA>..<topic>` before pushing. Do not select a
topic commit as the base to omit unaccepted feature work. Never give the
remote-tracking branch of the topic, such as `origin/<topic>`, as the base.

Without an explicit base, the hook checks the ordinary push range, from the
remote topic's old tip to its pushed head. For a new-history push, the pre-commit
framework finds no shared history on the remote and supplies only the local
branch. In that case, the gate checks all commits, even with `JN_CI_BASE` set.
This setting does not establish independent review, CI success or acceptance.

## Release tags

Every repository gets semantic version tags. A semantic version is a number
`X.Y.Z` with three parts, MAJOR, MINOR and PATCH. A release tag is an
annotated Git tag `vX.Y.Z`. An annotated tag is a Git object with its own
message, which you make with `git tag -a`. Follow these rules:

- **Tag each release.** A merge to the integration branch that changes what a
  project installs or runs gets a release tag. Push the tag to the remote. A
  merge that changes only docs or only CI can wait for the next release, and
  share its tag. The integration branch here is the branch that the project
  releases from, usually the mainline. A merge to an experimental branch gets
  no release tag.
- **The merge authorization covers the tag.** The tag is part of the merge, so
  you do not ask again before you push it. But if the push of a tag starts a
  job that publishes a package, follow the delivery policy above, and ask
  before you push when nobody authorized that publication.
- **Choose the number by semver.** Raise MAJOR for a change that breaks an
  installed project, MINOR for a new feature and PATCH for a fix. Below
  `1.0.0`, a breaking change raises MINOR.
- **Match the manifest.** A manifest is the file that names the package and its
  version, such as `Cargo.toml`, `pyproject.toml` or `package.json`. When a
  manifest has a version, the tag is that version with a `v` in front. Put the
  tag on the commit that has that version. A version of a file format, such as
  `"version": 1` in `skill-package.json`, is not a release version.
- **Tag after the merge and the post-merge CI.** The post-merge CI is the CI
  run on the integration branch after the merge. Tag only when it passes.
- **Never move or delete a pushed tag.** Other projects and installs can pin
  it. When a tagged release is wrong, release a new version.

### Tag with `just release`

Nobody tags by hand. `just release` makes the tag. It runs
`.agents/skills/gpa/scripts/release_tag.py`, which needs only Python 3.9 and
Git. The CI starter `.github/workflows/release.yml` runs `just check` on each
push to `main`. When the check passes, it runs `just release`. The job has
`contents: write`, to push the tag, and it runs no agent.

The step `release-check` of `just check` runs the script with `--check`. So a
commit or a PR that needs a higher version fails before the merge, and CI
checks it through `just check`.

`just check` runs before the commit, so it cannot read the message of that
commit. A `fix:` commit with the tagged version would pass `just check`, and
`just release` would fail after the push. So the `commit-msg` hook of the
commit gate runs `just release-check` again. The variable
`JN_RELEASE_MESSAGE` names the message file, and the check counts that
message as one more commit. For an amend, the new message replaces the
message of HEAD. The hook skips the check for a merge and during a rebase.

The check cleans up the message as git does. The gate reads the option
`--cleanup` of the git command and puts it in `JN_RELEASE_CLEANUP`. Without
the option, the check reads `commit.cleanup`. In a hook, git sets
`GIT_EDITOR` to `:` when it runs no editor. So the check knows if git
strips the comment lines.

A person can set `GIT_EDITOR` to `:` too, so the
gate sets `JN_RELEASE_EDITOR=1` when the options show an editor. When git
may clean up the message in more than one way, the reading with the
biggest bump counts.

The gate sets `JN_RELEASE_AMEND=1` only when `--amend` comes before the
message in the git command. After the message, the word may be text, so
HEAD counts too. On HEAD with a release tag, that commit stops too. Give
such a message with `-F`.

An amend of a commit with a release tag stops, because the tag stays on the
old commit. Make a new commit instead.

The step needs no network and no remote. It fails on the errors of the
version that the rules below list. In a shallow checkout, or in a checkout
with no release tag, it says so and passes. So CI fetches the whole history
and the tags first, with `fetch-depth: 0`.

Where the gpa skill is not installed, `release-check` is a step that does nothing. jnterfaces adds the
step to `just check`. Until it does, `just check` does not run it.

The last tag is the newest tag `vX.Y.Z` that is an ancestor of HEAD. The
script reads the messages of the commits since the last tag, and skips the
merge commits. Each message is a conventional commit, such as
`fix(cli): stop a crash`, and asks for a bump:

| Message | Bump |
|---|---|
| A `!` after the type, as in `feat!:`, or a line `BREAKING CHANGE:` in the body | MAJOR, or MINOR below `1.0.0` |
| `feat` | MINOR |
| `fix`, `perf`, `refactor`, any other type, or a message that is not a conventional commit | PATCH |
| `docs`, `test`, `ci`, `chore`, `style` | No release |

A bullet line of the body with a conventional subject, such as
`* feat!: drop the flag`, asks for its bump too. A squash commit of GitHub
lists the commits of its PR that way. The bullet counts only when its type is
`feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `chore`, `ci`, `build`,
`style` or `revert`, in lower case. A labelled bullet, such as
`- Removed: the old copies`, is not a commit and asks for no bump. The largest
bump of the commits gives the next number. With no tag yet, the next tag is `v0.1.0`.

A language profile gives the version of its manifest with the recipe
`<profile>::version`. The recipe prints `X.Y.Z`, or nothing when the manifest
has no version, and it exits 2 when it cannot read the manifest. The Python
profile reads `pyproject.toml`, the TypeScript profile `package.json`, and the
Rust profile `Cargo.toml`. The recipe reads only the local file, and needs no
network, because the step `release-check` runs it.

The script runs the recipe of each profile in the key
`profiles` of `.agents/stack.json`. A profile without the recipe, such as a
profile from before the recipe came, gives no version. When a profile gives a version, these rules apply:

- The tag is `v<version>`. The script makes it only when that tag does not exist
  yet.
- The script fails when two profiles give different versions.
- The script fails when the version is lower than the last tag, or lower than
  the bump that the commits ask for. So a PR that needs a bump also raises the
  version of the manifest.
- A version higher than the bump that the commits ask for is allowed.
- With no tag yet, the tag is the version.

These cases stop the script with an error:

- The checkout is shallow, so the script cannot see the last tag.
- The remote has a release tag that the checkout does not have, or has on
  another commit. Then the next number can be wrong. Run
  `git fetch --tags origin`, then run the script again.
- A tag of the next number exists on another commit. The script does not move
  it.

When there is nothing to tag, the script prints `no release` and exits 0. So a
second run on the same commit is safe. A tag at or above the next number on a
later commit also gives `no release`. That case occurs when the CI of an older
push ends after the CI of a newer push.

When a project has no CI release job, run the release by hand after the
post-merge CI passes, in a clean checkout of the integration branch:

```bash
just release --dry-run
just release
```

The dry run prints the next tag and the reason, and changes nothing. Without
it, the script makes an annotated tag on HEAD, pushes it and checks with
`git ls-remote` that the remote tag points at HEAD.

A tag is a release of the source. It is not a published package. If the
project also publishes a package, follow the delivery policy above for that
step.


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

## Recommendations

Before pushing a topic that merged its base, verify the current remote PR-target
tip and inspect the complete range from that tip to the topic. Set `JN_CI_BASE`
to that tip's full SHA for the push. Check the PR's required CI results on
GitHub for the exact published head, as the CI and delivery contract requires.
