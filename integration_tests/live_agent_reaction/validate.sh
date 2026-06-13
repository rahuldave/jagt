#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: integration_tests/live_agent_reaction/validate.sh <lab-dir> [jagt-bin]

Validate saved transcript artifacts from the live jagt agent reaction lab.
This script does not simulate or launch an LLM.
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

fail() {
  echo "live agent reaction lab failed: $*" >&2
  exit 1
}

require_file() {
  local path="$1"
  [ -f "$path" ] || fail "missing file: $path"
}

require_grep() {
  local pattern="$1"
  local path="$2"
  local label="$3"
  grep -Eq "$pattern" "$path" || fail "$label not found in $path"
}

require_file "$lab_dir/AGENTS.md"
require_file "$lab_dir/Justfile"
require_file "$lab_dir/01-rendered-task.agent-task.txt"
require_file "$lab_dir/02-parent-decision.txt"

require_grep 'AGENT_TASK v1.*subagent handoff packet|subagent handoff packet.*AGENT_TASK v1' \
  "$lab_dir/AGENTS.md" \
  "copied AGENT_TASK handoff language"
require_grep 'recursive' "$lab_dir/AGENTS.md" "recursive delegation language"
require_grep 'AGENT_RESULT v1' "$lab_dir/AGENTS.md" "AGENT_RESULT report language"

"$jagt_bin" lint --expect-count 1 "$lab_dir/01-rendered-task.agent-task.txt" >/dev/null
require_grep '^target: count-chat-message-words$' \
  "$lab_dir/01-rendered-task.agent-task.txt" \
  "rendered task target"
require_grep '^    - user_message.txt$' \
  "$lab_dir/01-rendered-task.agent-task.txt" \
  "rendered task message input"
require_grep '^  recursive: true$' \
  "$lab_dir/01-rendered-task.agent-task.txt" \
  "rendered recursive delegation"

require_grep '^decision: delegated$' "$lab_dir/02-parent-decision.txt" "delegation decision"
if grep -Rqs '^decision: executed-inline$' "$lab_dir"; then
  fail "transcript contains an inline execution decision after AGENT_TASK emission"
fi

echo "live agent reaction lab transcript passed"
