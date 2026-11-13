#!/usr/bin/env bash
set -euo pipefail

project_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
# The tasker variant that just install recorded in .agents/stack.json: git (the default) or gitwt.
tasker_mode="$(sed -n 's/.*"tasker"[[:space:]]*:[[:space:]]*"\([a-z]*\)".*/\1/p' "$project_root/.agents/stack.json" 2>/dev/null | head -1 || true)"

CONTEXT="Apply the g* Gest workflow, including tag classification and ast-grep dependency-impact checks."
if [ "$tasker_mode" = gitwt ]; then
  CONTEXT="$CONTEXT Tasker variant gitwt: do each write task in its own worktree; just worktree-new NAME makes one. Keep the main checkout on its base branch."
else
  CONTEXT="$CONTEXT Tasker variant git: work on a branch in the main checkout; for parallel write work, just worktree-new NAME makes a worktree for each task."
fi
# Report the worktrees that are ready to prune. Nothing is removed here.
script="$project_root/.agents/skills/gtw/scripts/worktree.py"
if [ -f "$script" ] && command -v uv >/dev/null 2>&1; then
  ready="$(cd "$project_root" && uv run --no-project --quiet --no-python-downloads --python '>=3.9' python "$script" list --report 2>/dev/null || true)"
  if [ -n "$ready" ]; then
    CONTEXT="$CONTEXT $ready Tell the user; remove them only when the user asks."
  fi
fi

# The rules of the tasker role. just install writes them to .agents/instructions/tasker.md, and the line in
# AGENTS.md only points to them. Codex does not import them, so this hook is the step that loads them.
rules="$project_root/.agents/instructions/tasker.md"
if [ -f "$rules" ]; then
  # Claude Code and Codex show a long hook output only as a short preview and a file. So the first line, which is
  # always in the preview, asks for the whole file.
  CONTEXT="Read all of .agents/instructions/tasker.md before you start work. It holds the rules of this project.

$(cat "$rules")

$CONTEXT"
fi

escape_json() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/g' | tr -d '\n' | tr '\001-\037' ' '
}

printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$(escape_json "$CONTEXT")"
