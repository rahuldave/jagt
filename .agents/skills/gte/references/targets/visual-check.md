# The base task of `just visual-check`

This file is the base task of the agentic target `just visual-check`, in the commit gates of
agent_gest_git_skills. An agentic target is a recipe that writes a task packet for a fresh agent. A fresh
agent is an agent that a harness starts for one task, for example a subagent.

The packet holds this text, a language layer for each language of the project, the text of the
repository and the inputs. The text of the repository, in `.agents/targets/visual-check.md`, says how
to start the app.

You are the fresh agent. Run the app, go through a flow in a browser, and take screenshots.

## The inputs

- **The diff** of the change against the parent commit, in the input file of the packet.
- **A URL or a flow**, when the recipe had one. Without one, check the flows that the diff changes.

## The steps

1. Start the app as the text of the repository says. Without that text, use the recipe `just run`
   when it exists.
2. Go through each step of the flow in a browser. Take a screenshot after each step.
3. Save the screenshots in a temporary folder outside the repository, so that they do not change the
   tree. Show them to the person.
4. Stop the app.

Do not change a file of the repository.

## The result

End with an `AGENT_RESULT v1` packet, with `target: visual-check` and the nonce of the task packet.

- **`outputs.screenshots`** lists the absolute paths of the screenshots. They are not in
  `outputs.files`, because each path there is a file of the repository.
- **`outputs.steps`** lists each step of the flow, with `pass` or `fail` and what you saw.
- The status is `success` only when each step passed. When a step failed, the status is `partial`, and
  the result has an `error` with the `code` `failed_steps` and a `message` that names the steps.
