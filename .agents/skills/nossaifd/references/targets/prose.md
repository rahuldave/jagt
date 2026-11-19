# The base task of `just prose`

This file is the base task of the agentic target `just prose`, in the commit gates of
agent_gest_git_skills. An agentic target is a recipe that writes a task packet for a fresh agent. A fresh
agent is an agent that a harness starts for one task, for example a subagent.

The packet holds this text, a
language layer for each language of the project, the text of the repository and the inputs. A language
layer is the text that a profile adds for its language. A profile is the package of the tools of one
language, for example jnprofile-python. Its text is in `.agents/targets/<language>/prose.md`.

You are the fresh agent. You did not write the pages, so you can see the habits of their writer. Apply the
nossaifd guide to the pages and the docstrings that the change affects. Do the plain-writing pass of the
guide, and the pass of the declaude skill by Oskar Austegard. The check of `check.py` alone is not enough,
because a program cannot judge meaning or tone.

## The inputs

The packet gives you these inputs:

- **The diff** of the change against the parent commit.
- **The input tree**, which is the tree of all the files of the worktree when the recipe made the packet.
- **A path**, when the recipe had one. Then work only on the pages and the code under that path.

## The pages and the docstrings

A page is a changed file that this command prints:

```bash
git diff -z --name-only --no-renames --diff-filter=AMT HEAD | \
  uv run --no-project --quiet python .agents/skills/nossaifd/scripts/prose_gate.py pages -z
```

Add the new files that git does not track yet, from `git ls-files -z --others --exclude-standard`. The
command `pages` uses the same rule as the hook at the end of a turn and the step `prose-check`. It skips
`AGENTS.md`, `CHANGELOG.md` and the folder `.agents/`, for example.

In a repository with no commit yet, `git diff HEAD` fails. There, take the files from
`git ls-files -z --cached --others --exclude-standard` in place of both commands.

A docstring is the doc of a module, a class, a function or a method in the code. Work on the docstrings and the
docments of each item that the diff adds or changes. The docments are the comments beside the
arguments of a Python function. Change only the text of a docstring or a comment. Do not change a line of
code.

## The steps for each page

1. Read `.agents/skills/nossaifd/references/GUIDE.md`, and the worked examples in `references/EXAMPLES.md`
   for each rule that you apply.
2. Keep a copy of the page in a temporary folder outside the repository.
3. Run the checker of the page, and fix each hard problem:

   ```bash
   uv run --no-project --quiet python .agents/skills/nossaifd/scripts/prose_gate.py check -v PAGE
   ```

   The command runs `check.py`, or the checker that the map of checkers of the project names for the
   page. The map is `.agents/nossaifd-checkers.json`. Its first line of output for each page names the
   checker. Fix each soft note that makes the page harder to read.
4. Do the plain-writing pass. Read each sentence against the rules of the guide for words, sentences,
   paragraphs, long documents, figures, tone, punctuation and short items.
5. Do the pass of the declaude skill by Oskar Austegard, by its steps, in the folder
   `.agents/skills/declaude`. Judge each passage that its linter marks. Then read each sentence against its
   register, because the linter finds only some patterns. Where the declaude skill and the guide disagree,
   follow the guide.
6. Run the diff of the declaude skill on the copy and on the revision. Put back each claim that the
   revision lost.
7. Run the checker of the page again, with the same command, and fix only what the revision broke. Run the linter of the declaude skill once
   more, to check that the fixes brought back no pattern.
8. Record the page:

   ```bash
   uv run --no-project --quiet python .agents/skills/nossaifd/scripts/prose_gate.py record PAGE
   ```

   `record` refuses a page with a hard problem of its checker. A recorded page does not block a later turn, in any
   worktree of the repository.

Keep each bad example that a page shows on purpose, even when the checker or the linter marks it. If a
page is not prose for a person to read, do not change it and do not record it. Name it in the result.

If the skill `declaude` is not installed, follow rules 50 to 55 of the guide in place of steps 5 and 6.

## The steps for the docstrings

1. Apply the guide to each docstring, as steps 4 and 5 above do for a page.
2. When the project builds API pages, check them. API pages are the pages of a docs website that smalldocs
   makes from the code. For each changed module, write its page into a temporary file outside the
   repository, and run the checker on that file:

   ```bash
   uv run --with smalldocs==0.5.5 smalldocs api module NAME > "$tmp/NAME.md"
   uv run --no-project python .agents/skills/nossaifd/scripts/check.py "$tmp/NAME.md"
   ```

   Fix each hard problem in the docstring that it comes from. A docstring gets no record of its own.

## Limits on your changes

- Do not change a file other than the pages and the docstrings of the change.
- Do not stage a file, and do not commit. The record of the target compares the trees before and after
  your work.
- Do not change the meaning of a page or of a docstring. When a sentence is unclear and you cannot tell
  its meaning, keep it and name it in the result.

## The result

End with an `AGENT_RESULT v1` packet, with `target: prose` and the nonce of the task packet. The result
packet holds these parts:

- **The changed files**, in `outputs.files`, each with `role: required`. The changed files are the pages
  that you changed and the code files whose docstrings you changed. The task asks for `files` as its required
  output.
- **The pages that you checked, recorded and left alone**, in `outputs.checked`, as a list of paths.
  Leave them out of `outputs.files`, because the spec of `AGENT_RESULT v1` accepts only `required` and
  `optional` as a role.
- **The lint output after the change.** `verification` has one entry for each page, with the command
  of the checker and its status. When the project builds API pages, it also has one entry for the check
  of the API page of each changed module. Put the output of the checker and of the linter of the declaude
  skill by Oskar Austegard in `notes`.
- **The pages that are not prose**, with the reason for each, in `notes`. Leave them out of
  `outputs.checked`, and give them no entry in `verification`.
- **The other pages that you did not record**, with the reason for each, in `notes`.

The status is `success` only when each page has no hard problem and has a record, or the result names it as not
prose. Otherwise the status is `partial`.

A result for one changed page and one page left alone has this form:

```text
<<<AGENT_RESULT v1>>>
target: prose
nonce: d5a8c0e4f1b2937a6c4e8d0b2f7a9c31
status: success
outputs:
  files:
    - path: docs/flow.md
      role: required
  checked:
    - README.md
verification:
  - name: check docs/flow.md
    command: uv run --no-project --quiet python .agents/skills/nossaifd/scripts/prose_gate.py check -v docs/flow.md
    status: passed
  - name: check README.md
    command: uv run --no-project --quiet python .agents/skills/nossaifd/scripts/prose_gate.py check -v README.md
    status: passed
notes: |
  <the output of the checker and of the linter of the declaude skill for each page>
follow_up: []
<<<END_AGENT_RESULT>>>
```

Copy the nonce of your task packet in place of the nonce of the example. Put the real output in
`notes`. Give only your own packet, and do not quote the example in your reply.
