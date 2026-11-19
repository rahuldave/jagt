# The base task of `just update-docs`

This file is the base task of the agentic target `just update-docs`, in the commit gates of
agent_gest_git_skills. An agentic target is a recipe that writes a task packet for a fresh agent. A fresh
agent is an agent that a harness starts for one task, for example a subagent.

The packet holds this text, a language layer for each language of the project, the text of the
repository and the inputs. A language layer is the text that a profile adds for its language, in
`.agents/targets/<language>/update-docs.md`. The text of the repository is in
`.agents/targets/update-docs.md`. It
says which docs the repository has, for example user docs, developer docs, API docs or a change log.

You are the fresh agent. Find the docs that the change affects, and write or change them.

## The inputs

- **The diff** of the change against the parent commit, in the input file of the packet. It holds the
  files that git does not track yet.
- **The input tree**, which is the tree of all the files of the worktree when the recipe made the packet.
- **An area**, when the recipe had one, for example `api` or `user`. Then work only on the docs of that
  area.

## The steps

1. List the behavior that the change adds, changes or removes.
2. Find each doc that names that behavior. Look in the pages, the README, the docstrings, the help of
   the commands and the change log. Search the repository for each changed name.
3. Change each doc that no longer matches the code. Write a doc for each new item that a reader needs.
   A doc says what the item is for.
4. Leave alone each doc that still matches.

## Limits on your changes

- Change only docs: pages, docstrings, comments and the help text of commands. Do not change a line of
  code.
- Do not stage a file, and do not commit. The record of the target compares the trees before and after
  your work.

## The result

End with an `AGENT_RESULT v1` packet, with `target: update-docs` and the nonce of the task packet.

- **`outputs.files`** lists the changed docs, each with `role: required`. Each path is relative to the
  root of the repository.
- **`outputs.checked`** lists the paths of the docs that you checked and left alone.
- The status is `success` when each doc that the change affects matches the code.
