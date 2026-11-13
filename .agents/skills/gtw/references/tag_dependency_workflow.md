# Tag classification and dependency impact workflow

The workflow gives agents two more kinds of memory before and during a task:

- **Tag classification**: classify every new Gest task against the existing tag
  vocabulary of the project. Add a new dynamic tag only when it describes a
  concept that no existing tag covers.
- **Dependency impact**: for every change to code, inspect the semantic
  dependers, preferably with `ast-grep`. A depender is code that uses the
  changed contract. Then check or update the coupled surfaces and their tests
  together.

The goal is to catch a case such as a change to the colors of a histogram that
forgets the colors of the pills. Both sets of colors encode the same concept
of a count or a probability.

## Tag vocabulary pass

Before you create or split a task, collect the current tags of the project:

```bash
gest task list --all --json
gest artifact list --all --json
gest iteration list --all --json
```

From the JSON output, build a vocabulary of unique tags, with counts and
examples. Then run a classification pass with a model. It reads the title and
description of the task, the related files, the words of the user and the
nearby Gest memory.

The output of the classifier should include these parts:

```text
Tag classification:
Selected existing tags:
- <tag>: <why it applies>

New dynamic tags:
- <tag>: <why no existing tag covers it>

Near misses / rejected tags:
- <tag>: <why it was not selected>

Coupled concepts to search:
- <semantic concept or UI behavior>
```

Apply the selected tags when you create the task:

```bash
gest task create "<title>"   --tag <selected-existing-tag>   --tag <new-dynamic-tag>   --metadata classification.tags.reviewed=true   --metadata classification.tags.new="<comma-separated-new-tags>"   --quiet
```

To add missing tags to a task that already exists, run:

```bash
gest task tag <task-id> <tag>
```

If the reason for a classification is not obvious, add a note:

```bash
gest task note add <task-id> --agent codex --body "Tag classification: ..."
```

Do not use tags as a hierarchy. Use `child-of` and `parent-of` links for
structure, and tags for semantic retrieval.

## Tag-driven coupling search

After you select the tags, search Gest memory for each tag or semantic concept
that gives a strong signal:

```bash
gest search "<selected-tag>" --all --json --limit 20
gest search "<semantic concept>" --all --json --limit 20
gest search "Follow-up <semantic concept>" --all --json --limit 20
```

Read the related tasks and notes. Sometimes the task touches one surface of a
coupled concept. Then expand the current task, or create a child task for the
other surface and link it.

Example:

```text
User asks: change histogram color scale.

Selected tag:
- count-or-probability-coloring

Coupled search finds:
- histogram bin color
- pill probability color
- legend color key

Action:
- update all three in one task if they share the same code path
- otherwise create a child task for pill/legend parity before implementation
```

## ast-grep dependency impact pass

Use `ast-grep` when a change to code alters a semantic contract. Examples of a
contract are a function, a constant, a component, a selector, a route, a field
of a schema, a style token and an exported API.

Start with the changed symbols. Inspect the changes with these commands:

```bash
git status --short --branch
git diff
git branch --list
```

In a normal git checkout or a physical git worktree, use these commands:

```bash
git status --short --branch
git diff
git diff --name-only
```

Then search for the structured dependers, for example with these patterns:

```bash
ast-grep run --lang javascript --pattern 'countOrProbabilityColorScale($$$)' src
ast-grep run --lang javascript --pattern 'import { $$$ } from "$MODULE"' src
ast-grep run --lang typescript --pattern '$COMPONENT($$$)' app
ast-grep run --lang python --pattern '$FUNC($$$)' .
```

If you must record the result or process it later, use `--json=compact`:

```bash
ast-grep run --lang javascript   --pattern 'countOrProbabilityColorScale($$$)'   --json=compact src
```

Use `rg` in place of `ast-grep` only in these cases:

- `ast-grep` does not support the language.
- The target is in a stylesheet or template format.
- A search for a literal string is the right query.

Choose the verification from the output of the dependency pass:

```text
Dependency impact:
Changed contract:
- countOrProbabilityColorScale

ast-grep patterns:
- countOrProbabilityColorScale($$$)
- import { $$$ } from "./colors"

Dependers found:
- HistogramBins
- ProbabilityPill
- LegendKey

Verification:
- focused unit tests for color scale
- UI/browser check for histogram and pills
- regression test for shared color mapping
```

If a depender is outside the scope of the current task, create or link a
follow-up task before completion. Give it the same semantic tag.

To try the workflow as a dry run in the style of an agent, run:

```bash
just tag-dependency-dry-run
```

The dry run builds a small fixture. It classifies a change to the colors of a
histogram against the existing tags `count-or-probability-coloring`,
`histogram-colors` and `probability-pill-colors`. Then it uses `ast-grep` to
show that both the histogram dependers and the pill dependers need a check.

## Completion notes

The completion note of a task that changes code should mention both passes:

```text
Done: ...
Verification: ...
Tag classification: selected <tags>; added <new tags or none>.
Dependency impact: ast-grep searched <patterns>; checked <dependers>; follow-ups <none or IDs>.
Follow-up: ...
```

For a task that changes only docs or plans, record why it did not need the
dependency pass.
