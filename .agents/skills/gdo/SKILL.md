---
name: gdo
description: Gest Docs. Audit, create, update, and verify user-facing docs, developer-facing docs, and in-code documentation affected by a task.
---

# GDO: Gest Docs

Use when a task changes user-visible behavior, developer workflow, public
commands, setup, tests, reusable process guidance, or code whose intent needs
durable explanation.

`gdo` is an explicit documentation audit. Check whether user-facing docs,
developer-facing docs, or in-code documentation should be created or updated,
then make the needed changes.

## Workflow

1. Identify documentation surfaces affected by the change:
   - user-facing docs: README, guides, in-app docs, examples, screenshots, CLI
     or workflow instructions
   - developer-facing docs: architecture notes, testing docs, setup docs,
     workflow docs, scripts, operational runbooks
   - code docs: docstrings, type annotations, concise comments, public API
     contracts, command help text
2. Create missing docs or update stale docs in the smallest durable place future
   users or agents will read.
3. Prefer documented and typed code whenever it clarifies callable behavior,
   public contracts, non-obvious domain logic, or future maintenance. Avoid
   noisy comments that merely restate the code.
4. Keep project-specific details in project docs and reusable workflow material
   in the template repository.
5. Check examples and commands for drift.
6. If docs are rendered in-app or generated, run the relevant render/build
   check.
7. Report docs changed and any docs intentionally left for later.

For reusable Gest/Codex workflow material, mirror reusable updates to the
version-controlled workflow template repository, then verify, commit, and push
that template repository unless blocked.

## Tag And Dependency Docs

When docs describe task creation, code changes, verification, or review, include the tag classification and `ast-grep` dependency-impact workflow from `docs/tag_dependency_workflow.md` where relevant.
