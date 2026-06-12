---
name: gsp
description: Gest Spec. Draft or update a Gest spec artifact for substantial or unclear work, then ensure implementation happens through follow-on Gest tasks.
---

# GSP: Gest Spec

Use when work needs product/design shaping before implementation.

## When To Spec

Create a spec when behavior is unclear, there are meaningful trade-offs,
acceptance criteria need negotiation, multiple systems are affected, or GitHub
visible development is likely.

## Gest Memory

Before drafting or updating a spec, search Gest for related specs, tasks,
iterations, prior decisions, and follow-ups:

```bash
gest search "<spec topic>" --all --json --limit 20
gest search "<affected feature/module>" --all --json --limit 20
```

Inspect relevant hits with `gest task show`, `gest task note list`, and
`gest iteration show`. Include durable references in the spec's `References`
section when they shape the proposal.

## Spec Shape

```markdown
# Spec: <Title>

## Problem Statement
## Proposed Solution
## Scope
### In Scope
### Out of Scope
## Acceptance Criteria
## Open Questions
## References
```

Keep specs concise enough to read quickly.

## Save

Save as a Gest artifact tagged `spec` plus area tags:

```bash
gest artifact create "<title>" --tag spec --tag <area> --body "<body>" --quiet
```

Link to outline tasks where appropriate. Do not implement directly from the
artifact; use `gpl`/`gis` to create follow-on tasks.

## Tag And Dependency Discovery

Specs should run the discovery pass from `docs/tag_dependency_workflow.md` so the spec identifies existing semantic tags, new tags if needed, and coupled code or UI concepts that should later be checked with `ast-grep`.
