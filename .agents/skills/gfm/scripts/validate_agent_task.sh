#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: scripts/validate_agent_task.sh [--expect-none] [--expect-count N] <file>

Validate AGENT_TASK v1 blocks emitted by agentic Just targets.
USAGE
}

expect_none=0
expect_count=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --expect-none)
      expect_none=1
      shift
      ;;
    --expect-count)
      if [ "$#" -lt 2 ]; then
        usage
        exit 2
      fi
      expect_count="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      usage
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

if [ "$#" -ne 1 ]; then
  usage
  exit 2
fi

input_file="$1"

if [ ! -f "$input_file" ]; then
  echo "missing input file: $input_file" >&2
  exit 2
fi

start_marker="<<<AGENT_TASK v1>>>"
end_marker="<<<END_AGENT_TASK>>>"

fail() {
  echo "invalid AGENT_TASK block: $*" >&2
  exit 1
}

contains() {
  local body="$1"
  local pattern="$2"
  printf '%s\n' "$body" | grep -Eq "$pattern"
}

validate_block() {
  local body="$1"
  local index="$2"

  contains "$body" '^target: [A-Za-z0-9_.-]+$' || fail "block $index missing target"
  contains "$body" '^mode: agentic$' || fail "block $index missing mode: agentic"
  contains "$body" '^argv:$' || fail "block $index missing argv"
  contains "$body" '^prompt: \|$' || fail "block $index missing prompt"
  contains "$body" '^inputs:$' || fail "block $index missing inputs"
  contains "$body" '^outputs:$' || fail "block $index missing outputs"
  contains "$body" '^allowed_actions:$' || fail "block $index missing allowed_actions"
  contains "$body" '^verification:$' || fail "block $index missing verification"
  contains "$body" '^safety:$' || fail "block $index missing safety"
  contains "$body" '^delegation:$' || fail "block $index missing delegation"
  contains "$body" '^[[:space:]]+execution: subagent$' || fail "block $index must delegate to a subagent"
  contains "$body" '^[[:space:]]+recursive: true$' || fail "block $index must declare recursive delegation"
  contains "$body" 'nested agentic Just calls' || fail "block $index missing nested-task delegation trigger"
  contains "$body" 'agentic dependencies' || fail "block $index missing dependency delegation trigger"
  contains "$body" 'hook-triggered packets' || fail "block $index missing hook delegation trigger"
  contains "$body" 'agentic verification targets' || fail "block $index missing verification delegation trigger"
  contains "$body" 'cannot override user, system, developer, VCS, or approval instructions' || fail "block $index missing safety override text"

  if printf '%s\n' "$body" | grep -Eq '^[A-Za-z_][A-Za-z0-9_.-]*[[:space:]][^:]+$'; then
    fail "block $index contains malformed top-level YAML-like field"
  fi

  local open_square close_square open_curly close_curly
  open_square="$(printf '%s\n' "$body" | tr -cd '[' | wc -c | tr -d ' ')"
  close_square="$(printf '%s\n' "$body" | tr -cd ']' | wc -c | tr -d ' ')"
  open_curly="$(printf '%s\n' "$body" | tr -cd '{' | wc -c | tr -d ' ')"
  close_curly="$(printf '%s\n' "$body" | tr -cd '}' | wc -c | tr -d ' ')"
  [ "$open_square" = "$close_square" ] || fail "block $index has unbalanced square brackets"
  [ "$open_curly" = "$close_curly" ] || fail "block $index has unbalanced curly braces"
}

if [ "$expect_none" -eq 1 ]; then
  if grep -q "$start_marker" "$input_file" || grep -q "$end_marker" "$input_file"; then
    fail "expected no AGENT_TASK block"
  fi
  echo "no agent task blocks detected"
  exit 0
fi

block_count=0
in_block=0
body=""

while IFS= read -r line || [ -n "$line" ]; do
  if [ "$line" = "$start_marker" ]; then
    [ "$in_block" -eq 0 ] || fail "nested start marker"
    in_block=1
    body=""
    continue
  fi

  if [ "$line" = "$end_marker" ]; then
    [ "$in_block" -eq 1 ] || fail "end marker without start marker"
    block_count=$((block_count + 1))
    validate_block "$body" "$block_count"
    in_block=0
    body=""
    continue
  fi

  if [ "$in_block" -eq 1 ]; then
    body="${body}${line}"$'\n'
  fi
done <"$input_file"

[ "$in_block" -eq 0 ] || fail "start marker without end marker"
[ "$block_count" -gt 0 ] || fail "no AGENT_TASK block found"

if [ -n "$expect_count" ] && [ "$block_count" -ne "$expect_count" ]; then
  fail "expected $expect_count block(s), found $block_count"
fi

echo "validated $block_count AGENT_TASK block(s)"
