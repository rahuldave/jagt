---
name: gfm
description: Gest Format. Run formatting, linting, typechecking, compile/static checks, and mechanical diff hygiene; fix mechanical issues. Use gte for tests and gdo for documentation.
license: MIT, copyright (c) 2026 Rahul Dave. The full text is in the LICENSE file of https://github.com/rahuldave/agent_gest_git_skills
---

# GFM: Gest Format

Use to fix the format of a change and to run its static checks. `gfm` does not
run the tests or check the docs. `gte` and `gdo` do that.

## Workflow

1. Run `just fmt`. It changes the files to the format of each profile.
2. Run the static steps of `just check`:

   ```bash
   just fmt-check
   just lint
   just typecheck
   just diff-check
   ```

3. Fix what they find, and run the failing step again.
4. Report each step that you ran, and whether it passed.

Each step is a recipe, so the run log has it. Do not call the tools of a
language directly, because each profile owns its tools and their settings. A step that
a profile does not have is a recipe that passes and says so.

When the repository has no `just check`, run `gsu` first. It installs the
recipes.

## The files of the change

Use `git status` and `git diff` to find the changed files. In a stack of
branches, compare each branch with the branch below it, for example
`git diff <parent-branch>...HEAD`. `just lint PATH` and `just fmt PATH` take
paths, so you can check one file.

## cx

If the project uses `cx` in its Justfile, run `just cx-lint`, or `cx lint`,
as a static check of the declarations. `cx lint` checks the build and
pipeline lines. It is not a test runner, so it does not replace `gte`. The
rules are in the `cx` skill of jnterfaces, `.agents/skills/cx/SKILL.md`. If the
cx skill is not installed, use `cx --help`.

## Tag And Dependency Checks

For code-facing changes, `gfm` may include lightweight `ast-grep` syntax or
pattern checks from `references/tag_dependency_workflow.md` when those checks
are part of the mechanical contract.
