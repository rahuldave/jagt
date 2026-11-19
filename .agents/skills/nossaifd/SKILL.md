---
name: nossaifd
description: Use when you write or change Markdown that a person reads, for example a README, a spec, a plan, a report, a skill or other documentation. It gives the plain English writing rules of the nossaifd guide and a checker for the rules that a program can measure.
license: MIT, copyright (c) 2026 Rahul Dave. The full text is in the LICENSE file of https://github.com/rahuldave/nossaifd
---

# nossaifd

nossaifd is a writing guide for prose that an AI model writes and a person
reads. Its rules come from five sources:

- Simplified Technical English, ASD-STE100. Most of its rules here come from memory of the standard, and
  the file docs/why.md of nossaifd lists them.
- The plain-writing skill by Shreya Shankar.
- "Communicating Your Work", a tutorial by Rosalind Reid. It gives the order of a long document, several rules for sentences,
  and the rules for figures. Rosalind Reid lets this project use her work on
  one condition. Each place that uses it credits her. Text that comes from
  her work must keep its credit to Rosalind Reid, in every copy and in every
  changed version of this skill. Her PDFs are not under the MIT licence.
- "Five Principles for Generating Readable AI Text in Bulk", a post by Shreya
  Shankar. It gives the rules for short items that a person skims.
- The declaude skill by Oskar Austegard, under the MIT licence. It gives
  the rules for the revision of a draft that reads as if a model wrote it.
  He calls it declauding. This package ships it as the skill `declaude`, with
  three changes. They are to its name and the paths of its folder, to its
  description, and to one sentence of a reference.

The rules make the text plain and easy to read for a reader who is not a native
speaker. Each rule in the guide names its source. Most rules are preferences. A
rule can give way to the story, as the section "When to break a rule" of the
guide says.

## Steps

1. Read `references/GUIDE.md` before you write. Follow its rules for words,
   sentences, instructions, paragraphs, long documents, figures, tone,
   punctuation and short items. A short item is a title, a notification or
   a row that a person skims. For the rule you apply, read its worked
   examples in `references/EXAMPLES.md`. They come from Rosalind Reid, from
   Shreya Shankar and from the declaude skill by Oskar Austegard, and each
   one names its source.
2. Use one term for one thing. If the project has a glossary, use its terms. If
   not, define each technical term the first time that it appears on a page.
3. Write the page. Do not read the register of the declaude skill before you
   write it.
4. Run the checker of the page, and fix each hard problem:

   ```bash
   uv run --no-project --quiet python .agents/skills/nossaifd/scripts/prose_gate.py check page.md
   ```

   The checker is `scripts/check.py`. A project can name another checker
   for some pages in its map of checkers, `.agents/nossaifd-checkers.json`.
   An example is the talk checker for the slides of a talk. Then this
   command runs that checker, and so does the hook. The output names the
   checker of each page.
5. Run the command with `-v` to see the soft notes. Fix each note that makes
   the page harder to read.
6. Keep a copy of the page. Then give the page to a subagent that did not
   write it, because a writer misses its own habits. Tell the subagent these
   things:
   - Revise the page by the steps of the declaude skill by Oskar Austegard,
     in the folder `declaude` next to this skill.
   - Judge each passage that its linter marks. Then read each sentence
     against the register, because the linter finds only some patterns.
   - Follow `references/GUIDE.md` of this skill. Where the declaude skill and
     the guide disagreed, the project's author chose, and the guide gives
     each choice. A sample of the user's own writing wins over the register,
     but not over the hard problems of the checker.
   - Do not change a bad example that the page shows on purpose. Keep it even
     when the linter or the checker marks it.
   - Run the diff of the declaude skill on the copy and on the revision. Put
     back each claim that the revision lost.

   If no subagent tool exists, read the page again from the top, and do
   these things yourself. If the skill `declaude` is not installed, follow
   rules 50 to 55 of the guide.
7. Run the checker again on the revision, and fix only what the revision
   broke.
8. Run the linter of the declaude skill once more, to check that the fixes
   brought back no pattern. Then record the page:

   ```bash
   uv run --no-project --quiet python .agents/skills/nossaifd/scripts/prose_gate.py record page.md
   ```

   A project can install the hooks of this skill. Then a hook checks each
   page that your turn changed, at the end of the turn. The page must pass
   the checker and have a record. It asks once for the steps that remain. If a page is not
   prose for a person, do not record it, and tell the user so.

   Run `just prose` in place of steps 6 to 8 only when `.agents/stack.json` sets
   `choices.tasker` to the JSON value `true`, not the string `"true"`. That setting turns on the
   commit gates of agent_gest_git_skills. Then `just prose` gives the pages to a fresh agent, which is
   an agent that the harness starts for one task. The fresh agent does those steps and records each
   page. A commit needs the `prose` record of `just prose`, and the steps by hand do not give it.

   Otherwise, do steps 6 to 8 yourself. Do them yourself also when the project has no recipe
   `just prose`, or when it only runs the checkers.

   `just prose-check` only runs the checkers. It does not do the declaude pass or the record, so it
   never replaces steps 6 to 8.
9. Read the page yourself. The checker cannot judge meaning, tone or a missing
   definition.

The checker skips front matter, code, tables, link targets and quoted words.
It needs only Python 3.11 or later, which `uv run` gives.

## Files in this skill

- **`references/GUIDE.md`** has the rules.
- **`references/EXAMPLES.md`** has worked examples for the rules, from
  Rosalind Reid, Shreya Shankar and the declaude skill by Oskar Austegard.
  Each example keeps its credit.
- **`scripts/check.py`** checks a page against the rules that a program can
  measure. It exits with 1 when it finds a hard problem.
- **`scripts/prose_gate.py`** records a page after its pass. It is also the
  hook at the start and at the end of a turn of Claude Code or Codex. It
  also checks a pull request. `prose_gate.py pages` prints the paths that
  are pages, by the one rule that the hook and the commit gates use.
  `prose_gate.py check` checks a page with the checker that the map of
  checkers of the project names for it, or with `check.py`.
- **`references/targets/prose.md`** is the base task of the target
  `just prose` of the commit gates. It gives the fresh agent the
  plain-writing pass and the pass of the declaude skill by Oskar Austegard.
- **`assets/agents-prose.md`** is the instruction for the `AGENTS.md` and
  `CLAUDE.md` of a project.
- **`assets/claude-settings-hook.json`** and **`assets/codex-hooks.json`**
  are the settings of the hooks for Claude Code and for Codex.
- **`assets/prose-check.yml`** is a workflow for GitHub that checks each page
  of a pull request.

The source of these files is https://github.com/rahuldave/nossaifd. The guide
for talks is in https://github.com/rahuldave/nossaifd-talks.
