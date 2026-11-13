---
name: gfm
description: Gest Format. Run formatting, linting, typechecking, compile/static checks, and mechanical diff hygiene; fix mechanical issues. Use gte for tests and gdo for documentation.
license: MIT, copyright (c) 2026 Rahul Dave. The full text is in the LICENSE file of https://github.com/rahuldave/agent_gest_git_skills
---

# GFM: Gest Format

Use to mechanically clean and statically check a changeset. `gfm` does not own
runtime tests or documentation checks; route those to `gte` and `gdo`.

## Workflow

1. Identify project and changed files.
2. Read the project command contract in `AGENTS.md`, especially any `just`
   target mappings and focused-argument guidance.
3. Run formatting, linting, typechecking, compile/static checks, and diff
   hygiene appropriate to the project.
4. Fix mechanical issues.
5. Re-run failing checks.
6. Report every command run and whether it passed.

Use the target repository's project-specific command contract. Prefer `just`
targets when `AGENTS.md` maps them. For the reusable Just command-contract
model, read the `just` skill of jnterfaces, `.agents/skills/just/SKILL.md`, and its
contract, `.agents/skills/just/references/command_contract.md`. If jnterfaces
is not installed, use the project's `AGENTS.md` and `just --list`; the source
is https://github.com/rahuldave/jnterfaces. Common concepts include:

```bash
just fmt [path]
just lint [path]
just typecheck
just static
just build
git diff --check
```

If no command contract exists yet, inspect the project manifests and propose or
route to `gsu` to establish one. Do not substitute smoke checks for `gte`.

If the project uses `cx` in its Justfile, run `cx lint` or the mapped
`just cx-lint` target as a static declaration check. `cx lint` validates
incremental build/pipeline lines; it is not a test runner and should not be
used as a substitute for `gte`. For `cx` rules, read the `cx` skill of
jnterfaces, `.agents/skills/cx/SKILL.md`, when it is installed. If the cx
skill is not installed, `cx lint` and `cx --help` are the reference.

Use `git status` and `git diff` to find the changes of the branch before you
run the mechanical checks. In a stack of branches, compare each branch with the
branch below it, for example `git diff <parent-branch>...HEAD`.

## Tag And Dependency Checks

For code-facing changes, `gfm` may include lightweight `ast-grep` syntax or pattern checks from `references/tag_dependency_workflow.md` when those checks are part of the mechanical contract.
