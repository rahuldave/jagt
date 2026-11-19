---
name: gdo
description: Gest Docs. Audit, create, update, and verify user-facing docs, developer-facing docs, and in-code documentation affected by a task.
license: MIT, copyright (c) 2026 Rahul Dave. The full text is in the LICENSE file of https://github.com/rahuldave/agent_gest_git_skills
---

# GDO: Gest Docs

Use when a task changes user-visible behavior, developer workflow, public
commands, setup, tests, reusable process guidance, or code whose intent needs
durable explanation.

`gdo` asks for the docs of a change, and the steps and targets check them:

- **You write the doc of each item.** The author has the context of the
  change, so each new or changed function, class, command and option gets
  its doc from you, in the same change. A doc says what the item is for.
- **`just docstring-check` checks that each doc exists.** It is a step of
  `just check`. Read its output, and write each doc that it names.
- **`just docs-check` checks the docs site**, when the project has one.
- **`just update-docs` writes the pages.** It is an agentic target, which writes
  a task packet for a fresh agent. The agent finds the pages that the change
  affects, such as the README and the guides, and changes them. The gate
  needs its record when the change touches a page.
- **The docs lens of `just review` checks that the docs are good.** A doc that
  only repeats the name of its item is a finding.

## Workflow

1. Write the doc of each item that the change adds or changes:
   - code docs: docstrings, type annotations, short comments, the help of
     the commands
   - developer docs: setup, testing, workflow and architecture notes
   - user docs: the README, guides and examples
2. Run `just docstring-check`, and write each doc that it names.
3. Run `just update-docs`, and give its packet to a fresh agent.
4. Report the docs that changed, and each doc that you left for later, with
   the reason.

When the repository has no `just check`, run `gsu` first. It installs the
recipes.

Keep the details of a project in its own docs, and reusable workflow text in
this repository.

## The base tasks

This skill holds the base tasks of two agentic targets:

- `references/targets/update-docs.md`, for `just update-docs`
- `references/targets/visualize.md`, for `just visualize`, which draws a
  diagram of a part of the code

## Tag And Dependency Docs

When docs describe task creation, code changes, verification, or review,
include the tag classification and `ast-grep` dependency-impact workflow from
`references/tag_dependency_workflow.md` where relevant.
