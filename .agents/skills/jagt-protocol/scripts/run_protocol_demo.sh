#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: .agents/skills/jagt-protocol/scripts/run_protocol_demo.sh [jagt-bin]

Run a standalone jagt protocol demo:
- send/render one AGENT_TASK v1 packet;
- receive/validate one AGENT_RESULT v1 packet;
- receive/validate recursive proposed-task and local-recursion result shapes;
- receive/validate one AGENT_TASK_DRAFT v1 packet and promote it with jagt.
USAGE
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
jagt_bin="${1:-${JAGT_BIN:-$repo_root/target/debug/jagt}}"
workspace="$(mktemp -d "${TMPDIR:-/tmp}/jagt-protocol-demo.XXXXXX")"

cleanup() {
  rm -rf "$workspace"
}
trap cleanup EXIT

if [ ! -x "$jagt_bin" ] && ! command -v "$jagt_bin" >/dev/null 2>&1; then
  echo "$jagt_bin is required for the jagt protocol demo" >&2
  exit 127
fi

run() {
  printf '$ %s\n' "$*"
  "$@"
}

cat >"$workspace/user_message.txt" <<'MESSAGE'
how about you show me a standalone jagt protocol demo that sends a task and receives a result
MESSAGE

run "$jagt_bin" render count-chat-message-words \
  --no-config \
  --arg inline:user-message \
  --input user_message.txt \
  --prompt-text "Count whitespace-separated words in user_message.txt and return outputs.word_count." \
  --required-output word_count \
  --allowed-action "read listed user_message.txt input" \
  --allowed-action "compute a deterministic word count" \
  --verification "recount the message before returning AGENT_RESULT" \
  >"$workspace/01-sent-task.agent-task.txt"
run "$jagt_bin" lint --expect-count 1 "$workspace/01-sent-task.agent-task.txt"

word_count="$(wc -w <"$workspace/user_message.txt" | tr -d ' ')"
cat >"$workspace/02-received-result.agent-result.txt" <<RESULT
<<<AGENT_RESULT v1>>>
target: count-chat-message-words
status: success
outputs:
  word_count: $word_count
verification:
  - name: deterministic_wc
    command: wc -w < user_message.txt
    status: passed
notes: |
  Received a successful worker result for the sent task.
follow_up: []
<<<END_AGENT_RESULT>>>
RESULT
run "$jagt_bin" result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status success \
  "$workspace/02-received-result.agent-result.txt"

run "$jagt_bin" result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status partial \
  "$repo_root/fixtures/agent_result/valid/proposed_tasks.agent-result.txt"
run "$jagt_bin" result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status success \
  "$repo_root/fixtures/agent_result/valid/local_recursion.agent-result.txt"

draft_pair="$repo_root/fixtures/agent_task_draft/valid/result_pair.agent-task-draft.txt"
run "$jagt_bin" result lint \
  --expect-count 1 \
  --expect-target draft-agent-task \
  --expect-status success \
  "$draft_pair"
run "$jagt_bin" draft lint --expect-count 1 "$draft_pair"
run "$jagt_bin" lint --expect-none "$draft_pair"

run "$jagt_bin" render count-chat-message-chars \
  --no-config \
  --arg "Count the number of characters in this chat message I am sending." \
  --prompt-text "Count the number of characters in the first argv entry. Return the count and state what counting rule you used." \
  --required-output character_count \
  --allowed-action "read the supplied argv entry" \
  --allowed-action "compute the requested scalar result" \
  --verification "independently recount the same message before reporting success" \
  >"$workspace/03-promoted-draft.agent-task.txt"
run "$jagt_bin" lint --expect-count 1 "$workspace/03-promoted-draft.agent-task.txt"

echo "jagt protocol demo passed"
