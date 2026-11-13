#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
command_text="$(printf '%s' "$input" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"

case "$command_text" in
  *"git commit"*|*"git push"*|*"gh pr create"*)
    ;;
  *)
    exit 0
    ;;
esac

project_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
doc="$project_root/docs/dev/commits.md"

if [ ! -f "$doc" ]; then
  exit 0
fi

context="$(cat "$doc")"
escape_json() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/g' | tr -d '\n' | tr '\001-\037' ' '
}

printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"%s"}}' \
  "$(escape_json "$context")"
