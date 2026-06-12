---
name: gbs
description: Gest Brainstorm. Explore rough ideas or ambiguous requests, inspect existing code/docs/Gest context, ask clarifying questions when needed, and decide whether to create a spec, outline issue, plan, or session task.
---

# GBS: Gest Brainstorm

Use when the user has a rough idea, fuzzy feature, or exploratory direction.

## Workflow

1. Inspect local code, docs, and Gest memory relevant to the idea. Use targeted
   `gest search "<topic>" --all --json --limit 20`, then inspect likely hits
   with `gest task show`, `gest task note list`, or `gest iteration show`.
2. Identify existing patterns, constraints, risks, and open questions.
3. For workflow/VCS ideas, separate branch model from execution model. Call out
   whether GitButler work would be sequential stack curation or physical
   worktree parallelism.
4. Ask clarifying questions one at a time when needed.
5. Propose 2-3 approaches with trade-offs.
6. Recommend one of:
   - stay in session exploration
   - create/update an outline task with `gis`
   - create a spec with `gsp`
   - plan implementation with `gpl`
   - promote to GitHub with `gpr`

## Gest Use

Brainstorming itself can be tracked as a session leaf when it is part of a
larger workflow. Do not create implementation tasks until the desired behavior
is clear enough to write acceptance criteria.

Use Gest notes to recover prior decisions, rejected approaches, browser-audit
findings, and unresolved follow-ups before recommending a path.

## Tag And Dependency Awareness

For brainstorms that may become tasks, use `docs/tag_dependency_workflow.md` to surface existing semantic tags, likely near-miss tags, and coupled concepts early. This is a lightweight discovery pass, not a reason to over-plan tiny discussions.
