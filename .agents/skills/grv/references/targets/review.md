# The base task of `just review`

This file is the base task of the agentic target `just review`, in the commit gates of
agent_gest_git_skills. An agentic target is a recipe that writes a task packet for a fresh agent. A fresh
agent is an agent that a harness starts for one task, for example a subagent.

The packet holds this text, a language layer for each language of the project, the text of the
repository and the inputs. A language layer is the text that a profile adds for its language, in
`.agents/targets/<language>/review.md`. The text of the repository is in `.agents/targets/review.md`.

You are the fresh agent. You did not write the change, so you can see what its writer missed. Try to
break the change. Do not change a file.

## The inputs

- **The diff** of the change against the parent commit, in the input file of the packet. It holds the
  files that git does not track yet.
- **The input tree**, which is the tree of all the files of the worktree when the recipe made the packet.

## The lenses

A lens is one point of view of the review. Look at the change through each lens:

1. **Correctness.** Find inputs that give a wrong result, a crash or a hang. Run the code when that is
   the quickest way to be sure.
2. **Regressions.** Find callers and other code that the change breaks. Search the repository for each
   changed name.
3. **Tests.** Find behavior that no test checks, and tests that pass without the code that they test.
4. **Safety.** Find secrets, injection, unsafe input, and commands that delete or overwrite without a
   check.
5. **Docs.** Check that each new or changed doc says what the item is for, matches the code, and is not
   a stub. A stub is a doc that only repeats the name, such as "Returns the result." Each doc that fails
   this lens is a finding.

## The findings

Report only real defects. For each one, give a concrete reproduction, such as an input and the wrong
result.

A finding that the change already fixes needs the test that shows the fix. A finding that the change
does not need to fix needs the reason. A defect that the change does not fix and that needs a fix is an
open finding.

## The result

End with an `AGENT_RESULT v1` packet, with `target: review` and the nonce of the task packet.

- **`outputs.findings`** is a list. Each finding has a `summary`, and a `test` that shows the fix or a
  `reason` not to fix it. A list with no findings is `[]`.
- **Open findings** go in `notes`, each with its reproduction. Then the status is `partial`, and the
  result has an `error` with the `code` `open_findings` and a `message` that counts them. The writer
  fixes them, and the review runs again on the new tree.
- The status is `success` only when there is no open finding.
