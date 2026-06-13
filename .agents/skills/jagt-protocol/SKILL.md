---
name: jagt-protocol
description: Use when working in the jagt repository on standalone AGENT_TASK v1, AGENT_RESULT v1, or AGENT_TASK_DRAFT v1 packet workflows, live labs, send/receive demos, recursive subagent handoffs, or protocol validation with jagt lint/result lint/draft lint. This skill keeps jagt demos independent of the reusable Git and jj Gest skill repositories.
---

# Jagt Protocol

Use this skill when a task needs the protocol contract for `jagt` itself. Do
not depend on the Git or jj Gest skill repositories for demos, bootstrap
fixtures, or validation behavior.

## Core Workflow

1. Render outbound executable handoff packets with `jagt render`.
2. Validate outbound `AGENT_TASK v1` packets with `jagt lint`.
3. Validate inbound `AGENT_RESULT v1` packets with `jagt result lint`.
4. Validate stochastic proposal packets with `jagt draft lint`.
5. Promote approved drafts deterministically with `jagt render`, then validate
   the promoted packet with `jagt lint`.
6. Keep live-agent demos transcript-based: scripts create and validate
   artifacts, but do not pretend shell can launch portable LLM subagents.

## Bundled Resources

- Read `references/protocol_contract.md` when a fresh agent context needs the
  standalone packet contract.
- Run `scripts/run_protocol_demo.sh [jagt-bin]` for a deterministic send,
  receive, recursive-result, and draft-promotion demo.
- Use `scripts/jagt_lint_agent_task.sh`,
  `scripts/jagt_lint_agent_result.sh`, and
  `scripts/jagt_lint_agent_task_draft.sh` as skill-local wrappers when a lab
  wants stable command names.
