---
name: gte
description: Gest Test. Run unit, API regression, smoke, regression, and integration tests appropriate to the changed code; add missing tests when the task changes callable behavior.
license: MIT, copyright (c) 2026 Rahul Dave. The full text is in the LICENSE file of https://github.com/rahuldave/agent_gest_git_skills
---

# GTE: Gest Test

Use to design and verify behavior with executable tests. `gte` owns test design
and test execution; `gfm` owns format/lint/typecheck/static checks, and `gdo`
owns documentation.

## Integration and delivery policy

Read [the integration and delivery contract](references/integration_delivery_workflow.md)
for explicit branch roles, selected PR bases, independent review evidence,
CI gates, issue completion, installation provenance and safe cleanup. Apply it
throughout this skill; the repository default is not an implicit PR target.

## Test Policy

Any changed callable code needs focused tests near that code. Smoke checks are
not a substitute for inner-function or API regression tests.

Choose a `test.strategy` before or during implementation:

- `test-first`: write the smallest meaningful failing test before production
  edits; run it and confirm the failure is about the intended behavior.
- `characterization-first`: lock current behavior before refactoring,
  migration, or risky semantic changes.
- `test-after`: add focused behavior tests after implementation when the
  red/green boundary was not practical up front.
- `exploratory`: record why the boundary is not yet testable and identify the
  future durable test layer.
- `no-test-needed`: docs-only, planning-only, or prose-only work with a stated
  reason.

Recommended test layout:

- `tests/`: unit tests for inner functions, repositories, parsers, context
  builders, renderers, and other callable code.
- `regression_tests/`: bug and API regression tests that preserve previously
  fixed behavior.
- `integration_tests/`: slower end-to-end or browser-agent-driven checks.

For browser-agent flows that become recurring checks, store the commands in
shell scripts under `integration_tests/` so they can be rerun outside chat
history.

Browser spot checks are different from integration tests. Spot checks are
exploratory page/interaction inspections during implementation; they should be
reported in verification notes, but they do not replace durable tests when a
flow needs regression coverage.

`cx` is not a test runner. When a change adds or modifies `cx`-backed
incremental build/pipeline stages, verify the build or pipeline target by
running it once, running it again to confirm expected `up-to-date` behavior,
changing a source input, and confirming the expected downstream artifacts
rerun. That build/pipeline verification does not replace focused tests for
changed callable code. The cx skill, `.agents/skills/cx/SKILL.md`, has the full
`cx` check. If the cx skill is not installed, use the steps above.

## A good test

- It checks a result that a caller can see, such as a return value, an
  output, a file or an exit code. A test that only runs the code, or that
  checks a value that it set itself, checks nothing.
- It fails without its change. Run a new test before the code that it tests,
  when you can, and see it fail for the right reason. `just test-review`
  runs each changed test file on the parent commit, and a new test that
  passes there is a finding.
- It extends the test that already covers the behavior, rather than a copy
  of it.
- A pragma or an exclude, such as `# pragma: no cover`, has its reason next
  to it.

## Workflow

1. Identify changed behavior and the smallest meaningful test layer.
2. For substantial or ambiguous behavior, design the test first. Decide what
   should fail before implementation, which assertion proves the behavior,
   and which existing test to extend.
3. Search Gest for prior failures, browser-agent audits, smoke-check findings,
   and unresolved follow-ups in the touched area:

```bash
gest search "<feature/module> test" --all --json --limit 20
gest search "browser audit <feature/module>" --all --json --limit 20
gest search "Follow-up <feature/module>" --all --json --limit 20
```

4. Add or update tests for changed inner functions and APIs when coverage is
   missing.
5. For `test-first`, run the focused test before production code changes and
   confirm a meaningful red failure. If the test passes before implementation,
   revise the test or record why it is not a valid red check.
6. Run the tests through the recipes only, so the run log has each run:

```bash
just test [target]          # the unit tests, or one file or test of them
just integration [flow]     # the slower end-to-end checks
just coverage-check         # the lines that no test ran
```

7. For frontend, UI or interaction changes, run `just visual-check`, and give
   its packet to a fresh agent. Before it, start the app with `just dev
   [port]`, or confirm that a server already runs.
8. Run `just test-review`, and give its packet to a fresh agent. Fix each
   finding with a test, or give the reason not to fix it.
9. Report the strategy, the red check when it applies, the recipes and the
   results. If a layer cannot run, say exactly why.

When the repository has no `just check`, run `gsu` first. It installs the
recipes. The contract of the recipes is in the `just` skill of jnterfaces,
`.agents/skills/just/references/command_contract.md`. If the just skill is not
installed, use `just --list` and the `AGENTS.md` of the project.

For non-trivial test design, prefer a read-only test-design sub-agent when
sub-agents are available, authorized, and the behavior can be reasoned about
independently. The main agent remains responsible for editing tests, running
the recipes, and recording verification.

## The base tasks

This skill holds the base tasks of two agentic targets:

- `references/targets/test-review.md`, for `just test-review`
- `references/targets/visual-check.md`, for `just visual-check`

## Testing Dependency Impact

Inspect tag/dependency notes from `references/tag_dependency_workflow.md`; tests must cover the file that was edited and each depender that semantic tags or `ast-grep` find. Smoke checks alone are not enough for changed callable code or shared contracts.

## CI verification

Verify that the selected PR base receives all required checks, including a
non-default integration target. For a conditional matrix or summary gate, test
failure/skipped-job handling rather than trusting a green summary unconditionally.
Distinguish local evidence, remote CI, artifact/clean-install verification and
opt-in live tests. Credentialed or paid tests need their own explicit scope.
Confirm test-owned servers and children exit; never reuse a user's service.
