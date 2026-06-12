#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
command_text="$(printf '%s' "$input" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"

case "$command_text" in
  *"but commit"*|*"but pr new"*|*"but push"*|*"git-butler branch commit"*|*"git commit"*)
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
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/g' | tr -d '\n'
}

printf '{"hookSpecificOutput":{"additionalContext":"%s"}}' \
  "$(escape_json "$context")"
