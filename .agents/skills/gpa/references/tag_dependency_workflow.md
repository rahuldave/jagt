# Tag Classification And Dependency Impact Workflow

This workflow gives agents two extra kinds of memory before and during a task:

- **Tag classification**: every new Gest task should be classified against the
  project's existing tag vocabulary, with new dynamic tags added only when they
  describe a genuinely missing concept.
- **Dependency impact**: every code-facing change should inspect semantic
  dependers, preferably with `ast-grep`, so coupled surfaces and tests are
  checked or updated together.

The goal is to catch cases such as changing histogram colors while forgetting
pill colors that encode the same count/probability concept.

## Tag Vocabulary Pass

Before creating or splitting a task, collect current project tags:

```bash
gest task list --all --json
gest artifact list --all --json
gest iteration list --all --json
```

Use the JSON output to build a unique tag vocabulary with counts and examples.
Then run a model classification pass over the task title, description, related
files, user language, and nearby Gest memory.

Classifier output should include:

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

Apply selected tags at creation time:

```bash
gest task create "<title>"   --tag <selected-existing-tag>   --tag <new-dynamic-tag>   --metadata classification.tags.reviewed=true   --metadata classification.tags.new="<comma-separated-new-tags>"   --quiet
```

For existing tasks, add missing tags with:

```bash
gest task tag <task-id> <tag>
```

Add a note when the classification is non-obvious:

```bash
gest task note add <task-id> --agent codex --body "Tag classification: ..."
```

Do not treat tags as hierarchy. Use `child-of` / `parent-of` links for
structure, and tags for semantic retrieval.

## Tag-Driven Coupling Search

After selecting tags, search Gest memory for each high-signal tag or semantic
concept:

```bash
gest search "<selected-tag>" --all --json --limit 20
gest search "<semantic concept>" --all --json --limit 20
gest search "Follow-up <semantic concept>" --all --json --limit 20
```

Inspect related tasks and notes. If the task touches one surface of a coupled
concept, either expand the current task or create/link a child task for the
other surface.

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

## ast-grep Dependency Impact Pass

Use `ast-grep` when code changes alter a function, constant, component,
selector, route, schema field, style token, exported API, or other semantic
contract.

Start with the changed symbols. In a GitButler-managed workspace, inspect:

```bash
but status
but diff
but branch list --all
```

In a normal git checkout or a physical git worktree, inspect:

```bash
git status --short --branch
git diff
git diff --name-only
```

Then search structured dependers. Examples:

```bash
ast-grep run --lang javascript --pattern 'countOrProbabilityColorScale($$$)' src
ast-grep run --lang javascript --pattern 'import { $$$ } from "$MODULE"' src
ast-grep run --lang typescript --pattern '$COMPONENT($$$)' app
ast-grep run --lang python --pattern '$FUNC($$$)' .
```

Use `--json=compact` when the result should be recorded or post-processed:

```bash
ast-grep run --lang javascript   --pattern 'countOrProbabilityColorScale($$$)'   --json=compact src
```

Fallback to `rg` only when the language is unsupported, the target is a
stylesheet/template format, or a literal string search is the right query.

Dependency output should drive verification:

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

If a depender is out of scope for the current task, create or link a follow-up
task before completion and tag it with the same semantic tag.

To exercise the workflow as an agent-style dry run, use:

```bash
just tag-dependency-dry-run
```

The dry run builds a small fixture, classifies a histogram color change against
the existing tags `count-or-probability-coloring`, `histogram-colors`, and
`probability-pill-colors`, then uses `ast-grep` to prove both histogram and pill
dependers need to be checked.

## Completion Notes

Completion notes for code-facing tasks should mention both passes:

```text
Done: ...
Verification: ...
Tag classification: selected <tags>; added <new tags or none>.
Dependency impact: ast-grep searched <patterns>; checked <dependers>; follow-ups <none or IDs>.
Follow-up: ...
```

For docs-only or planning-only tasks, record why the dependency pass was not
needed.
