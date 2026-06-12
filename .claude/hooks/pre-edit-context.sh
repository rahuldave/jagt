#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
file_path="$(printf '%s' "$input" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"

case "$file_path" in
  */docs/*|*/tmp/*|*.md|*.toml|*.yaml|*.yml|*.json|*.lock|*.gitignore|*.editorconfig)
    exit 0
    ;;
esac

project_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
context=""

if [ -f "$project_root/docs/dev/code-style.md" ]; then
  context="$(cat "$project_root/docs/dev/code-style.md")"
fi

if [ -f "$project_root/docs/dev/testing.md" ]; then
  if [ -n "$context" ]; then
    context="$context

---

"
  fi
  context="$context$(cat "$project_root/docs/dev/testing.md")"
fi

if [ -z "$context" ]; then
  exit 0
fi

escape_json() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/g' | tr -d '\n'
}

printf '{"hookSpecificOutput":{"additionalContext":"%s"}}' \
  "$(escape_json "$context")"
