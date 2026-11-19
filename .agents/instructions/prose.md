## Prose

When you write or change Markdown that a person reads, use the nossaifd skill, and follow all of its
steps. Its step 6 gives the page to a subagent that did not write it, for the pass of the declaude skill
by Oskar Austegard. After step 8, record each page:

```bash
uv run --no-project --quiet python .agents/skills/nossaifd/scripts/prose_gate.py record page.md
```

A hook checks, when you end your turn, that each page that the turn changed passed the checker and has a
record. If a page is not prose for a person, do not record it, and tell the user so. Keep each bad
example that a page shows on purpose.

Run `just prose` in place of steps 6 to 8 only when `.agents/stack.json` sets `choices.tasker` to the
JSON value `true`, not the string `"true"`. That setting turns on the commit gates. Then a fresh agent
does the steps and records each page, and a commit needs the `prose` record of `just prose`. Otherwise,
do steps 6 to 8 yourself. Do them yourself also when the project has no recipe `just prose`, or when it
only runs the checkers.

`just prose-check` only runs the checkers. It does not do the declaude pass or the record, so it never
replaces steps 6 to 8.
