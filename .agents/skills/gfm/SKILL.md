---
name: gfm
description: Gest Format. Run formatting, linting, typechecking, compile/static checks, and mechanical diff hygiene; fix mechanical issues. Use gte for tests and gdo for documentation.
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
model, see `references/just_command_contract.md`. Common concepts include:

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
used as a substitute for `gte`.

When a repository is GitButler-managed, use `but status` or `but diff` to
identify branch-owned changes before running mechanical checks. Read-only git
diff commands are acceptable, but do not use raw git write commands in
GitButler mode.

## Tag And Dependency Checks

For code-facing changes, `gfm` may include lightweight `ast-grep` syntax or pattern checks from `references/tag_dependency_workflow.md` when those checks are part of the mechanical contract.
