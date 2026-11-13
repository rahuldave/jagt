# jagt Docs

Start with [protocol-flows.md](protocol-flows.md). It explains the whole
conversation between Just output, the parent LLM, subagents, and `jagt`.

For a concrete parent-LLM play-by-play, read
[protocol-playbook-transcript.md](protocol-playbook-transcript.md). It runs the
plain task/result, recursive `outputs.proposed_tasks`, and stochastic
`AGENT_TASK_DRAFT` cases against a real example Justfile with spawned
subagents.

For the commit gates, read [packet-file.md](packet-file.md). It says what
`jagt render` saves for each packet, and how it joins the layers of the
prompt text.

Reference docs:

- [reference/agentic_just_targets_base_spec.md](reference/agentic_just_targets_base_spec.md):
  `AGENT_TASK v1` task handoff context.
- [reference/agent_result_v1_spec.md](reference/agent_result_v1_spec.md):
  `AGENT_RESULT v1` result return context.
- [reference/agent_task_draft_v1_spec.md](reference/agent_task_draft_v1_spec.md):
  `AGENT_TASK_DRAFT v1` stochastic proposal context.

Implementation planning:

- [jagt-mvp-implementation-plan.md](https://github.com/rahuldave/jagt/blob/main/docs/jagt-mvp-implementation-plan.md)
- [jagt-testing-strategy.md](https://github.com/rahuldave/jagt/blob/main/docs/jagt-testing-strategy.md)
- [jagt-rust-prep.md](https://github.com/rahuldave/jagt/blob/main/docs/jagt-rust-prep.md)

Runnable examples:

- [examples/protocol-playbook/Justfile](https://github.com/rahuldave/jagt/blob/main/docs/examples/protocol-playbook/Justfile)
