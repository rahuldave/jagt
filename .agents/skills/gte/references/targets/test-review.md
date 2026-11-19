# The base task of `just test-review`

This file is the base task of the agentic target `just test-review`, in the commit gates of
agent_gest_git_skills. An agentic target is a recipe that writes a task packet for a fresh agent. A fresh
agent is an agent that a harness starts for one task, for example a subagent.

The packet holds this text, a language layer for each language of the project, the text of the
repository and the inputs. A language layer is the text that a profile adds for its language, in
`.agents/targets/<language>/test-review.md`. The text of the repository is in
`.agents/targets/test-review.md`.

You are the fresh agent. Judge the tests of the change. Do not change a file.

## The inputs

- **The diff** of the change against the parent commit, in the input file of the packet. It holds the
  files that git does not track yet.
- **The input tree**, which is the tree of all the files of the worktree when the recipe made the packet.
- **The result of `test-parent`**, in the second input file. `test-parent` ran the added and changed test files
  on the parent commit, each file alone. The case of each file is one of "passed on the parent", "failed on the
  parent", "no test ran on the parent" and "the runner failed". The output of the run is next to it. A packet
  without this file says so in its notes.

## The checks

1. **Each new behavior has a test.** A behavior is a result that a caller can see, such as a return
   value, an output, a file or an exit code.
2. **Each new test checks a result.** A test that only runs the code, or that checks a value that it
   set itself, checks nothing.
3. **A new test fails without its change.** A new test that passes on the parent commit is a finding,
   unless the change is a refactor that keeps the behavior. Read the result of `test-parent`. For "failed on the parent",
   read the line of each test in the output, because a test of that file can still pass. For "no test ran on the
   parent" and "the runner failed", judge the tests from the diff.
4. **Each new pragma or exclude has a reason.** A pragma is a comment that turns off a check, such as
   `# pragma: no cover` or `# noqa`. An exclude is a path in `.agents/coverage-exclude.txt` or
   `.agents/generated.txt`. The reason is next to it.

## The findings

A finding that the change already fixes needs the test that shows the fix. A finding that the change
does not need to fix needs the reason. A missing or empty test that needs a fix is an open finding.

## The result

End with an `AGENT_RESULT v1` packet, with `target: test-review` and the nonce of the task packet.

- **`outputs.findings`** is a list. Each finding has a `summary`, and a `test` that shows the fix or a
  `reason` not to fix it. A list with no findings is `[]`.
- **Open findings** go in `notes`, each with the behavior or the test that it names. Then the status is
  `partial`, and the result has an `error` with the `code` `open_findings` and a `message` that counts
  them.
- The status is `success` only when there is no open finding.
