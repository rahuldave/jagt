#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: integration_tests/live_agent_reaction/bootstrap.sh <lab-dir> [jagt-bin]

Create a fresh live-agent lab folder with copied AGENTS.md contract language
and a Justfile target that emits an AGENT_TASK v1 packet through jagt.
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
  printf '%s\n' '# Live jagt Agent Reaction Lab'
  printf '%s\n' ''
  printf '%s\n' 'This temporary folder intentionally copies the relevant'
  printf '%s\n' 'agentic Just contract language so an LLM agent running here'
  printf '%s\n' 'has the same handoff instructions as the source project.'
  printf '%s\n' ''
  cat "$excerpt"
} >"$lab_dir/AGENTS.md"

cat >"$lab_dir/Justfile" <<JUSTFILE
set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

jagt_bin := "$jagt_bin"

count-message-agentic:
    @"{{jagt_bin}}" render count-chat-message-words \\
      --arg inline:user-message \\
      --input user_message.txt \\
      --prompt-text "Count the number of words in the exact chat message supplied. Treat whitespace-separated tokens as words." \\
      --required-output word_count \\
      --allowed-action "read listed user_message.txt input" \\
      --allowed-action "delegate deterministic word count to a subagent" \\
      --verification "validate any returned AGENT_RESULT before continuing"
JUSTFILE

cat >"$lab_dir/user_message.txt" <<'MESSAGE'
how about you show me an example of a target which gives an agentic contract spec and makes you go off and count the number of words in this message
MESSAGE

cat >"$lab_dir/README.md" <<'README'
# jagt Live Agent Reaction Lab

Ask a fresh LLM agent in this folder to run:

```bash
just count-message-agentic > 01-rendered-task.agent-task.txt
```

After the target emits AGENT_TASK v1, the parent agent should validate and
delegate the task rather than counting inline. Record the decision in
02-parent-decision.txt:

```text
decision: delegated
reason: AGENT_TASK v1 is a subagent handoff packet
```
README

echo "created live agent reaction lab: $lab_dir"
echo "jagt binary: $jagt_bin"
