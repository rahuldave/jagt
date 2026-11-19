# The base task of `just visualize`

This file is the base task of the agentic target `just visualize`, in the commit gates of
agent_gest_git_skills. An agentic target is a recipe that writes a task packet for a fresh agent. A fresh
agent is an agent that a harness starts for one task, for example a subagent.

The packet holds this text, a language layer for each language of the project, the text of the
repository and the inputs. The text of the repository, in `.agents/targets/visualize.md`, can name the
form of the diagrams, for example Mermaid in the pages.

You are the fresh agent. Draw a diagram of a part of the code, for a doc or for the person.

## The inputs

- **The diff** of the change against the parent commit, in the input file of the packet.
- **A topic**, when the recipe had one, for example a module or a flow. Without one, draw the part of
  the code that the diff changes.

## The steps

1. Read the code of the topic. Draw what the code does, not what its names suggest.
2. Write the diagram as a file. Use the form of the text of the repository, else Mermaid.
3. When the diagram is for a doc, add it to the doc, with a sentence that says what it shows.

Change only the diagram file and the doc that shows it. Do not stage a file, and do not commit.

## The result

End with an `AGENT_RESULT v1` packet, with `target: visualize` and the nonce of the task packet.

- **`outputs.files`** lists the diagram file and the doc that shows it, each with `role: required`.
  Each path is relative to the root of the repository.
- The status is `success` when the diagram matches the code.
