---
name: grv
description: Gest Review. Review the current Git changeset for correctness, safety, regressions, style, and missing tests, with findings first.
license: MIT, copyright (c) 2026 Rahul Dave. The full text is in the LICENSE file of https://github.com/rahuldave/agent_gest_git_skills
---

# GRV: Gest Review

Use for code-review stance. Run `grv`, which is `just review`, after every code
change before completing the task, even during quick local development without
a pull request.

## Integration and delivery policy

Read [the integration and delivery contract](references/integration_delivery_workflow.md)
for explicit branch roles, selected PR bases, independent review evidence,
CI gates, issue completion, installation provenance and safe cleanup. Apply it
throughout this skill; the repository default is not an implicit PR target.

## Workflow

To run `grv` by hand is to run `just review`:

1. Run `just review`. It is an agentic target, which writes a task packet for a
   fresh agent, with the diff of the change and the base task of this skill.
2. Give the packet to a fresh agent, such as a subagent. The agent that wrote
   the change does not review it, because it cannot see what it missed.
3. The fresh agent returns its findings. The hook of the harness writes the
   record of the review, and the commit gate needs that record for each
   commit.
4. Fix each finding with a test, and run `just review` again on the new tree.

When the repository has no `just check`, run `gsu` first. It installs the
recipes.

The base task is `references/targets/review.md`. It holds the five lenses of
the review, which are correctness, regressions, tests, safety and docs. The docs lens checks
that each new or changed doc says what its item is for. A doc that only
repeats the name of its item is a finding. A profile adds the lens of its
language in `.agents/targets/<language>/review.md`, and the repository adds
its own text in `.agents/targets/review.md`.

## The diff

`just review` takes the diff against the parent commit. To look at more of
the change yourself, use git:

```bash
git diff
git diff --staged
```

If the branch is part of a stack, diff it against the branch below it:

```bash
git diff <parent-branch>...HEAD
```

Search Gest for prior regressions, review findings, and browser/test notes in
the touched area:

```bash
gest search "<module/feature> regression" --all --json --limit 20
gest search "<module/feature> review" --all --json --limit 20
gest search "Follow-up <module/feature>" --all --json --limit 20
```

## The findings

Report findings first, ordered by severity, with file/line references. Treat
`Findings: None` as a precise statement about blocking or actionable code-review
findings, not as the whole review.

For a large change, more than one fresh agent can review it, each with some of
the lenses. Writable sub-agents still require separate physical git
worktrees. Gest mutations, task completion, commits, pushes, and PR decisions
should remain centralized unless deliberately assigned.

Test review should ask:

- Would the new or changed test fail against the old code?
- Does it assert behavior rather than implementation trivia?
- Are semantic dependers and edge cases covered?
- Does the test scope match the workflow kind, blast radius, and
  `test.strategy`?

After findings, add reviewer judgment when it would help the user. Call out
non-blocking opinions about clarity, maintainability, UX, naming, fit with local
patterns, or tradeoffs. Label these separately from findings so taste-level
feedback does not look like a merge blocker. If no issues are found, say so,
then still mention residual risk, test gaps, and any useful non-blocking
observations.

Missing focused tests for changed callable code or APIs are review findings.
They are not follow-ups for later.

For workflow changes, review VCS safety as behavior. Flag each of these:

- an instruction that launches parallel write agents in one checkout
- a plan that blocks plain git, or needs a marker for it
- a stacked branch flow without guidance for bottom-up integration and review

For `cx` workflow changes, review the lines as incremental build/pipeline
declarations. Flag use of `cx` for tests, lint, format, typecheck, ordinary
package-manager builds, or commands without durable file outputs. Check that
all real file inputs are declared with `--in`, all durable outputs are declared
with `--out`, Just recipe dependencies still order producers before consumers,
and `.cx` runtime state is ignored without hiding future config.

For reusable Git or JJ workflow changes, also verify adapter boundaries.
Plain Git branches, stacks of Git branches, physical git worktrees, and JJ
bookmarks and workspaces must stay separate models. In this Git skill family,
keep physical git worktrees as the way to run parallel writes. Keep stacks on
plain git, with `gh pr create --base <parent-branch>` and
`git rebase --update-refs --onto <lower-branch> <old-lower-tip>`.

## Tag And Dependency Findings

Review the current changes against `references/tag_dependency_workflow.md`. If code contracts changed, inspect the `ast-grep` patterns that were run and the dependers they found. Treat missing `ast-grep` dependency-impact checks, unhandled dependent surfaces, or missing focused tests for found dependers as review findings.

## Review evidence

For substantial code, executable setup, CI or reusable workflow changes, obtain
independent adversarial review. Record reviewer, scope, actual base/head SHAs,
findings and their dispositions. Re-review changed portions after fixes. Label
self-review honestly and report an unavailable independent reviewer as a gap;
do not manufacture approval. Inspect integration-target drift as well as head
changes before carrying evidence into GPA.
