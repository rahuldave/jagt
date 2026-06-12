#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: scripts/validate_agent_result.sh [OPTIONS] <file>

Validate AGENT_RESULT v1 blocks returned by subagents after AGENT_TASK v1 work.

Options:
  --expect-none             Require that no AGENT_RESULT block is present.
  --expect-count N          Require exactly N AGENT_RESULT blocks.
  --expect-target TARGET    Require every result block to report TARGET.
  --expect-status STATUS    Require every result block to report STATUS.
  --check-files             Require outputs.files entries with role: required to exist.
  --base-dir DIR            Base directory for --check-files; defaults to input file dir.
USAGE
}

expect_none=0
expect_count=""
expect_target=""
expect_status=""
check_files=0
base_dir=""

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
    --expect-target)
      if [ "$#" -lt 2 ]; then
        usage
        exit 2
      fi
      expect_target="$2"
      shift 2
      ;;
    --expect-status)
      if [ "$#" -lt 2 ]; then
        usage
        exit 2
      fi
      expect_status="$2"
      shift 2
      ;;
    --check-files)
      check_files=1
      shift
      ;;
    --base-dir)
      if [ "$#" -lt 2 ]; then
        usage
        exit 2
      fi
      base_dir="$2"
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

if [ -z "$base_dir" ]; then
  base_dir="$(cd "$(dirname "$input_file")" && pwd)"
fi

start_marker="<<<AGENT_RESULT v1>>>"
end_marker="<<<END_AGENT_RESULT>>>"

fail() {
  echo "invalid AGENT_RESULT block: $*" >&2
  exit 1
}

contains() {
  local body="$1"
  local pattern="$2"
  printf '%s\n' "$body" | grep -Eq "$pattern"
}

field_value() {
  local body="$1"
  local field="$2"
  printf '%s\n' "$body" | awk -F': ' -v key="$field" '$1 == key { print $2; exit }'
}

field_count() {
  local body="$1"
  local field="$2"
  printf '%s\n' "$body" | grep -Ec "^${field}:"
}

check_required_files() {
  local body="$1"
  local index="$2"
  local pending_path=""

  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      *"- path: "*)
        pending_path="${line#*- path: }"
        pending_path="${pending_path%\"}"
        pending_path="${pending_path#\"}"
        pending_path="${pending_path%\'}"
        pending_path="${pending_path#\'}"
        ;;
      *"role: required"*)
        if [ -n "$pending_path" ]; then
          case "$pending_path" in
            /*)
              fail "block $index required file path must be repo-relative: $pending_path"
              ;;
          esac
          [ -f "$base_dir/$pending_path" ] || fail "block $index missing required file: $pending_path"
          pending_path=""
        fi
        ;;
      *)
        ;;
    esac
  done <<<"$body"
}

validate_block() {
  local body="$1"
  local index="$2"
  local target status

  [ "$(field_count "$body" target)" -eq 1 ] || fail "block $index must contain exactly one target"
  [ "$(field_count "$body" status)" -eq 1 ] || fail "block $index must contain exactly one status"

  contains "$body" '^target: [A-Za-z0-9_.-]+$' || fail "block $index missing valid target"
  contains "$body" '^status: (success|partial|blocked|failed|cancelled)$' || fail "block $index missing allowed status"
  contains "$body" '^(outputs:|outputs: \{\})$' || fail "block $index missing outputs"
  contains "$body" '^(verification:|verification: \[\])$' || fail "block $index missing verification"
  contains "$body" '^(follow_up:|follow_up: \[\])$' || fail "block $index missing follow_up"

  target="$(field_value "$body" target)"
  status="$(field_value "$body" status)"

  if [ -n "$expect_target" ] && [ "$target" != "$expect_target" ]; then
    fail "block $index target mismatch: expected $expect_target, got $target"
  fi

  if [ -n "$expect_status" ] && [ "$status" != "$expect_status" ]; then
    fail "block $index status mismatch: expected $expect_status, got $status"
  fi

  case "$status" in
    blocked|failed)
      contains "$body" '^error:$' || fail "block $index status $status requires error"
      contains "$body" '^[[:space:]]+code: [A-Za-z0-9_.-]+$' || fail "block $index error missing code"
      contains "$body" '^[[:space:]]+message: .+$' || fail "block $index error missing message"
      ;;
    success)
      if printf '%s\n' "$body" | grep -Eq '^[[:space:]]+status: (failed|skipped)$'; then
        fail "block $index success result contains failed or skipped verification"
      fi
      ;;
  esac

  if printf '%s\n' "$body" | grep -Eq '^(allowed_actions|delegation|safety):$'; then
    fail "block $index contains task-like instruction fields; AGENT_RESULT is report-only"
  fi

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

  if [ "$check_files" -eq 1 ]; then
    check_required_files "$body" "$index"
  fi
}

if [ "$expect_none" -eq 1 ]; then
  if grep -q "$start_marker" "$input_file" || grep -q "$end_marker" "$input_file"; then
    fail "expected no AGENT_RESULT block"
  fi
  echo "no agent result blocks detected"
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
[ "$block_count" -gt 0 ] || fail "no AGENT_RESULT block found"

if [ -n "$expect_count" ] && [ "$block_count" -ne "$expect_count" ]; then
  fail "expected $expect_count block(s), found $block_count"
fi

echo "validated $block_count AGENT_RESULT block(s)"
