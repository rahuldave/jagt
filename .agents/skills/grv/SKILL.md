---
name: grv
description: Gest Review. Review the current Git changeset for correctness, safety, regressions, style, and missing tests, with findings first.
---

# GRV: Gest Review

Use for code-review stance. Run `grv` after every code change before completing
the task, even during quick local development without a pull request.

## Workflow

Inspect:

```bash
git diff
git diff --staged
```

If the checkout is GitButler-managed, also inspect branch ownership:

```bash
but status
but diff
but branch list --all
```

If reviewing a commit, diff that commit directly.

Search Gest for prior regressions, review findings, and browser/test notes in
the touched area:

```bash
gest search "<module/feature> regression" --all --json --limit 20
gest search "<module/feature> review" --all --json --limit 20
gest search "Follow-up <module/feature>" --all --json --limit 20
```

Report findings first, ordered by severity, with file/line references. Focus on
bugs, behavioral regressions, safety, error handling, and missing tests. Treat
`Findings: None` as a precise statement about blocking or actionable code-review
findings, not as the whole review.

For non-trivial changes, act as an adversarial review aggregator. Default to
independent read-only review sub-agents when sub-agents are available,
authorized, and the lenses can be checked independently; skip sub-agents only
when they are unavailable, unsafe, or overkill for a tiny change. Apply distinct
review lenses:

- correctness and regression risk
- test adequacy and missing edge cases
- Git/GitButler workflow safety
- docs, setup, and command-contract drift
- security, privacy, or data safety when relevant
- browser/UI behavior when relevant
- language/runtime idioms when the project profile is known

If sub-agents are not used, run the lenses explicitly yourself. Writable
sub-agents still require separate physical git worktrees. Gest mutations, task
completion, commits, pushes, and PR decisions should remain centralized unless
deliberately assigned.

Test review should ask:

- Would the new or changed test fail against the old code?
- Does it assert behavior rather than implementation trivia?
- Are semantic dependers and edge cases covered?
- Does the test scope match the workflow kind, blast radius, and
  `test.strategy`?

After findings, add reviewer judgment when it would help the user: call out
non-blocking opinions about clarity, maintainability, UX, naming, fit with local
patterns, or tradeoffs. Label these separately from findings so taste-level
feedback does not look like a merge blocker. If no issues are found, say so,
then still mention residual risk, test gaps, and any useful non-blocking
observations.

Missing focused tests for changed callable code or APIs are review findings, not
just nice-to-have follow-ups.

For workflow changes, review VCS safety as behavior: flag any instruction that
allows raw `git commit`/`git switch`/`git checkout` in GitButler mode, any plan
that launches parallel write agents in one GitButler workspace, or any stacked
branch flow that lacks bottom-up integration/review guidance.

For `cx` workflow changes, review the lines as incremental build/pipeline
declarations. Flag use of `cx` for tests, lint, format, typecheck, ordinary
package-manager builds, or commands without durable file outputs. Check that
all real file inputs are declared with `--in`, all durable outputs are declared
with `--out`, Just recipe dependencies still order producers before consumers,
and `.cx` runtime state is ignored without hiding future config.

For reusable Git/GitButler/JJ workflow changes, also verify adapter boundaries:
plain Git branches, GitButler-managed branches/stacks, physical git worktrees,
and JJ bookmarks/workspaces must not be collapsed into one generic model. In
this Git/GitButler skill family, preserve `but` write commands in GitButler
mode and preserve physical git worktrees as the parallel write primitive.

## Tag And Dependency Findings

Review the current changes against `references/tag_dependency_workflow.md`. If code contracts changed, inspect the `ast-grep` patterns that were run and the dependers they found. Treat missing `ast-grep` dependency-impact checks, unhandled dependent surfaces, or missing focused tests for found dependers as review findings.
