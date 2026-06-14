# jagt Docs

Start with [protocol-flows.md](protocol-flows.md). It explains the whole
conversation between Just output, the parent LLM, subagents, and `jagt`.

For a concrete parent-LLM play-by-play, read
[protocol-playbook-transcript.md](protocol-playbook-transcript.md). It runs the
plain task/result, recursive `outputs.proposed_tasks`, and stochastic
`AGENT_TASK_DRAFT` cases against a real example Justfile.

Reference docs:

- [reference/agentic_just_targets_base_spec.md](reference/agentic_just_targets_base_spec.md):
  `AGENT_TASK v1` task handoff context.
- [reference/agent_result_v1_spec.md](reference/agent_result_v1_spec.md):
  `AGENT_RESULT v1` result return context.
- [reference/agent_task_draft_v1_spec.md](reference/agent_task_draft_v1_spec.md):
  `AGENT_TASK_DRAFT v1` stochastic proposal context.

Implementation planning:

- [jagt-mvp-implementation-plan.md](jagt-mvp-implementation-plan.md)
- [jagt-testing-strategy.md](jagt-testing-strategy.md)
- [jagt-rust-prep.md](jagt-rust-prep.md)

Runnable examples:

- [examples/protocol-playbook/Justfile](examples/protocol-playbook/Justfile)
