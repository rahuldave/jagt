#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
command_text="$(printf '%s' "$input" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"

# The tasker variant that just install recorded in .agents/stack.json: git (the default) or gitwt.
project_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
tasker_mode="$(sed -n 's/.*"tasker"[[:space:]]*:[[:space:]]*"\([a-z]*\)".*/\1/p' "$project_root/.agents/stack.json" 2>/dev/null | head -1 || true)"
# In the gitwt variant the main checkout stays on its base branch, so a commit there gets a warning. The hook never
# blocks a command.
warning=""
git_options='(-[cC][[:space:]]+[^[:space:]]+[[:space:]]+)*'
if [ "$tasker_mode" = gitwt ] \
  && printf '%s' "$command_text" | grep -Eq "(^|[;&|][[:space:]]*)git[[:space:]]+${git_options}commit([[:space:]]|\$)"; then
  # The checkout of the commit: the folder of git -C, else this folder.
  commit_dir="$(printf '%s' "$command_text" | sed -nE "s/.*git[[:space:]]+(-c[[:space:]]+[^[:space:]]+[[:space:]]+)*-C[[:space:]]+([^[:space:]]+).*/\2/p" | head -1 || true)"
  git_dir="$(git -C "${commit_dir:-.}" rev-parse --path-format=absolute --git-dir 2>/dev/null || true)"
  common_dir="$(git -C "${commit_dir:-.}" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
  if [ -n "$git_dir" ] && [ "$git_dir" = "$common_dir" ]; then
    warning="This project uses the gitwt variant: commit in a worktree, and keep the main checkout on its base branch. just worktree-new NAME makes one."
  fi
fi
if [ -n "$warning" ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"%s"}}\n' "$warning"
fi
