#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: .agents/skills/jagt-protocol/scripts/run_protocol_demo.sh [jagt-bin]

The jagt binary is the first argument, else $JAGT_BIN, else jagt on PATH.

Run a standalone jagt protocol demo. It needs jagt 0.3.0 or later.
- send/render one AGENT_TASK v1 packet with --no-save, so no packet file is written;
- receive/validate one AGENT_RESULT v1 packet, with the nonce of its task;
- reject a result without that nonce;
- receive/validate recursive proposed-task and local-recursion result shapes;
- receive/validate one AGENT_TASK_DRAFT v1 packet and promote it with jagt.
USAGE
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

skill_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixtures="$skill_root/assets/fixtures"
jagt_bin="${1:-${JAGT_BIN:-jagt}}"
# A packet rendered with --no-save has no nonce. The demo results use this fixed
# nonce, the one in the fixtures, as if the packet of the task had held it.
demo_nonce=d5a8c0e4f1b2937a6c4e8d0b2f7a9c31
workspace="$(mktemp -d "${TMPDIR:-/tmp}/jagt-protocol-demo.XXXXXX")"

cleanup() {
  rm -rf "$workspace"
}
trap cleanup EXIT

if [ ! -x "$jagt_bin" ] && ! command -v "$jagt_bin" >/dev/null 2>&1; then
  echo "$jagt_bin is required for the jagt protocol demo" >&2
  exit 127
fi

# Run jagt from the temporary folder, not from the folder of the caller. So
# jagt reads no layer files of the repository of the caller, unless TMPDIR is
# itself inside a git repository.
case "$jagt_bin" in
  */*) jagt_bin="$(cd "$(dirname "$jagt_bin")" && pwd)/$(basename "$jagt_bin")" ;;
esac
cd "$workspace"

run() {
  printf '$ %s\n' "$*"
  "$@"
}

cat >"$workspace/user_message.txt" <<'MESSAGE'
how about you show me a standalone jagt protocol demo that sends a task and receives a result
MESSAGE

run "$jagt_bin" render count-chat-message-words \
  --no-save \
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
if grep -q '^nonce:' "$workspace/01-sent-task.agent-task.txt"; then
  echo "jagt render --no-save gave a packet with a nonce" >&2
  exit 1
fi

word_count="$(wc -w <"$workspace/user_message.txt" | tr -d ' ')"
cat >"$workspace/02-received-result.agent-result.txt" <<RESULT
<<<AGENT_RESULT v1>>>
target: count-chat-message-words
nonce: $demo_nonce
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
  --expect-nonce "$demo_nonce" \
  "$workspace/02-received-result.agent-result.txt"

# A result without the nonce of its task is not valid.
grep -v '^nonce: ' "$workspace/02-received-result.agent-result.txt" \
  >"$workspace/04-result-without-nonce.agent-result.txt"
printf '$ %s\n' "$jagt_bin result lint --expect-nonce $demo_nonce $workspace/04-result-without-nonce.agent-result.txt"
if "$jagt_bin" result lint --expect-nonce "$demo_nonce" \
  "$workspace/04-result-without-nonce.agent-result.txt" 2>"$workspace/04-lint.err"; then
  echo "a result without the nonce of its task passed the lint" >&2
  exit 1
fi
cat "$workspace/04-lint.err"
if ! grep -q 'missing nonce' "$workspace/04-lint.err"; then
  echo "the lint of a result without a nonce failed for another reason" >&2
  exit 1
fi

run "$jagt_bin" result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status partial \
  --expect-nonce "$demo_nonce" \
  "$fixtures/proposed_tasks.agent-result.txt"
run "$jagt_bin" result lint \
  --expect-count 1 \
  --expect-target count-chat-message-words \
  --expect-status success \
  --expect-nonce "$demo_nonce" \
  "$fixtures/local_recursion.agent-result.txt"

draft_pair="$fixtures/result_pair.agent-task-draft.txt"
run "$jagt_bin" result lint \
  --expect-count 1 \
  --expect-target draft-agent-task \
  --expect-status success \
  --expect-nonce "$demo_nonce" \
  "$draft_pair"
run "$jagt_bin" draft lint --expect-count 1 "$draft_pair"
run "$jagt_bin" lint --expect-none "$draft_pair"

run "$jagt_bin" render count-chat-message-chars \
  --no-save \
  --no-config \
  --arg "Count the number of characters in this chat message I am sending." \
  --prompt-text "Count the number of characters in the first argv entry. Return the count and state what counting rule you used." \
  --required-output character_count \
  --allowed-action "read the supplied argv entry" \
  --allowed-action "compute the requested scalar result" \
  --verification "independently recount the same message before reporting success" \
  >"$workspace/03-promoted-draft.agent-task.txt"
run "$jagt_bin" lint --expect-count 1 "$workspace/03-promoted-draft.agent-task.txt"
if grep -q '^nonce:' "$workspace/03-promoted-draft.agent-task.txt"; then
  echo "jagt render --no-save gave a packet with a nonce" >&2
  exit 1
fi

echo "jagt protocol demo passed"
