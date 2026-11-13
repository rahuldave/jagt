# jagt docs

Start with [protocol-flows.md](protocol-flows.md). It explains the whole
conversation between Just output, the parent LLM, subagents, and `jagt`. The
parent LLM is the agent that runs the Just recipe. A subagent is an agent that
the parent LLM starts for a delegated packet.

For a concrete step-by-step account of a parent LLM, read
[protocol-playbook-transcript.md](protocol-playbook-transcript.md). It runs a
real example Justfile with spawned subagents, for the plain task and result,
the recursive `outputs.proposed_tasks`, and the stochastic `AGENT_TASK_DRAFT`.
In the stochastic case, an agent drafts the task.

For the commit gates, read [packet-file.md](packet-file.md). A hook of the
commit gates turns a result into a record. The page says what `jagt render`
saves for each packet, and how it joins the layers of the prompt text.

Reference docs:

- [reference/agentic_just_targets_base_spec.md](reference/agentic_just_targets_base_spec.md):
  context for the `AGENT_TASK v1` task handoff.
- [reference/agent_result_v1_spec.md](reference/agent_result_v1_spec.md):
  context for the `AGENT_RESULT v1` result return.
- [reference/agent_task_draft_v1_spec.md](reference/agent_task_draft_v1_spec.md):
  context for the `AGENT_TASK_DRAFT v1` stochastic proposal.

Implementation planning:

- [jagt-mvp-implementation-plan.md](https://github.com/rahuldave/jagt/blob/main/docs/jagt-mvp-implementation-plan.md)
- [jagt-testing-strategy.md](https://github.com/rahuldave/jagt/blob/main/docs/jagt-testing-strategy.md)
- [jagt-rust-prep.md](https://github.com/rahuldave/jagt/blob/main/docs/jagt-rust-prep.md)

Runnable examples:

- [examples/protocol-playbook/Justfile](https://github.com/rahuldave/jagt/blob/main/docs/examples/protocol-playbook/Justfile)
