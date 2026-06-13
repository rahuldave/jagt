#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: integration_tests/live_agent_result_recursive/bootstrap.sh <lab-dir> [jagt-bin]

Create a fresh recursive live-agent lab folder with copied AGENTS.md contract
language and Justfile targets that emit AGENT_TASK v1 packets through jagt.
USAGE
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  usage
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
lab_dir="$1"
jagt_bin="${2:-$repo_root/target/debug/jagt}"
contract="$repo_root/.agents/skills/jagt-protocol/references/protocol_contract.md"
excerpt="$lab_dir/agentic_just_contract.md"

mkdir -p "$lab_dir"

if [ ! -f "$contract" ]; then
  echo "missing standalone jagt protocol contract: $contract" >&2
  exit 2
fi

awk '
  /^## Agentic Just Targets$/ { copy = 1 }
  /^## Agent Context Targets$/ { copy = 0 }
  copy { print }
' "$contract" >"$excerpt"

{
  printf '%s\n' '# Live jagt Recursive Agent Result Lab'
  printf '%s\n' ''
  printf '%s\n' 'This temporary folder intentionally copies the relevant'
  printf '%s\n' 'agentic Just contract language so an LLM agent running here'
  printf '%s\n' 'has the same recursive handoff instructions as the source project.'
  printf '%s\n' ''
  cat "$excerpt"
} >"$lab_dir/AGENTS.md"

cat >"$lab_dir/Justfile" <<JUSTFILE
set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

jagt_bin := "$jagt_bin"

count-message-recursive-agentic:
    @"{{jagt_bin}}" render count-chat-message-words \\
      --no-config \\
      --arg inline:user-message \\
      --input user_message.txt \\
      --prompt-text "Count the number of words in the exact chat message supplied. Treat whitespace-separated tokens as words. If a deterministic child task is more appropriate, return a partial AGENT_RESULT with outputs.proposed_tasks instead of computing the count." \\
      --required-output word_count \\
      --allowed-action "read listed user_message.txt input" \\
      --allowed-action "propose one deterministic child task" \\
      --verification "validate any returned AGENT_RESULT before continuing"

render-approved-child-agentic:
    @"{{jagt_bin}}" render count-chat-message-words-with-wc \\
      --no-config \\
      --arg inline:user-message \\
      --input user_message.txt \\
      --prompt-text "Run wc -w on user_message.txt and report the whitespace-separated word count as outputs.word_count. Do not edit files." \\
      --required-output word_count \\
      --allowed-action "read listed user_message.txt input" \\
      --allowed-action "run wc -w on user_message.txt" \\
      --allowed-action "report the deterministic word count" \\
      --verification "validate wc -w output before returning AGENT_RESULT"
JUSTFILE

cat >"$lab_dir/user_message.txt" <<'MESSAGE'
how about you show me an example of a target which gives an agentic contract spec and makes you go off and count the number of words in this message
MESSAGE

cat >"$lab_dir/README.md" <<'README'
# jagt Recursive Agent Result Lab

Run the parent target:

```bash
just count-message-recursive-agentic > 01-parent-task.agent-task.txt
```

After receiving the parent task, validate it and delegate it to a planner
subagent. Save the planner result to `02-planner-result.agent-result.txt`.

If the planner returns a safe deterministic child proposal, render it:

```bash
just render-approved-child-agentic > 03-child-task.agent-task.txt
```

Delegate the child task to a worker subagent. Save the worker result to
`04-worker-result.agent-result.txt`, then save the parent final result to
`05-parent-final.agent-result.txt`.

For the unsafe branch, save `06-unsafe-proposal.agent-result.txt`, refuse it in
`07-unsafe-decision.txt`, and do not create
`08-unsafe-worker-result.agent-result.txt`.
README

echo "created live recursive agent result lab: $lab_dir"
echo "jagt binary: $jagt_bin"
