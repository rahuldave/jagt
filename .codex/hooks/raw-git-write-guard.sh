#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
command_text="$(printf '%s' "$input" | sed -n 's/.*"tool_input"[^{]*{[^}]*"command"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p; s/.*"cmd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p; s/.*"command"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"

case "$command_text" in
  *"GEST_VCS_EXECUTION=git-worktrees"*|*"AGENT_GEST_ALLOW_RAW_GIT_WRITES=1"*)
    exit 0
    ;;
esac

if printf '%s' "$command_text" | grep -Eq '(^|[;&|][[:space:]]*)git[[:space:]]+(-C[[:space:]]+[^[:space:]]+[[:space:]]+)?(commit|add|restore|reset|checkout|switch|branch|worktree|merge|rebase|cherry-pick|revert|pull|push|clean|rm|mv|tag)([[:space:]]|$)'; then
  cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Raw git write command blocked by GitButler mode-strict. Use but commands while the GitButler series is active; use raw git writes only in explicit physical git-worktree execution mode."}}
JSON
fi
