---
name: gpr
description: Gest Promote. Promote or sync durable Gest work with GitHub issues using gh, storing GitHub metadata back on Gest entities.
license: MIT, copyright (c) 2026 Rahul Dave. The full text is in the LICENSE file of https://github.com/rahuldave/agent_gest_git_skills
---

# GPR: Gest Promote

Use when work should become externally visible on GitHub.

## Integration and delivery policy

Read [the integration and delivery contract](references/integration_delivery_workflow.md)
for explicit branch roles, selected PR bases, independent review evidence,
CI gates, issue completion, installation provenance and safe cleanup. Apply it
throughout this skill; the repository default is not an implicit PR target.

## Promotion Criteria

Promote durable user-visible, architecture-relevant, multi-session,
release-worthy, or externally trackable work. Do not promote every leaf task.

For every development depth-1 parent and every development iteration close, an
explicit `gpr` decision is required. Either create/sync the GitHub issue and
store metadata, or record why the work is staying local. Do not silently skip
GitHub issue integration for development work.

## Workflow

1. Read the Gest task/iteration/spec.
2. Sanitize internal details: remove Gest IDs, implementation-only paths, and
   private workflow notes.
3. Draft a GitHub issue body focused on user story, context, acceptance
   criteria, and out-of-scope.
4. Ask the user before running `gh issue create` or `gh issue edit`, unless the
   user has already agreed to GitHub issue integration for this workflow scope.
5. Store metadata after creation:

```bash
gest task meta set <id> github.issue <number>
gest task meta set <id> github.url <url>
gest task tag <id> github
```

Also attach metadata to the development iteration when applicable.

## GitHub Context From Tags

When promoting work to GitHub, include public-safe tag classification context from `references/tag_dependency_workflow.md` when it helps reviewers understand scope. Do not expose private Gest IDs unless the target repo policy allows them.

## Completion target

Record the issue's intended milestone: experimental integration, mainline, or
release. For non-default-base PRs use `Refs #N` and an explicit issue link;
GitHub does not apply PR closing keywords there. Update or close the issue
manually after merge only when its acceptance scope is actually complete and
that action is authorized. Keep parent initiatives open for remaining slices.
