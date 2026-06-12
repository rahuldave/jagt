#!/usr/bin/env bash
set -euo pipefail

read -r -d '' CONTEXT <<'CONTEXT_EOF' || true
## GitButler VCS Context

This repository uses GitButler mode-strict while a GitButler branch or stack
series is active. Use `but` for VCS writes in the GitButler workspace:

- `but status`, `but diff`, `but branch list`
- `but branch new`, `but branch new --anchor`
- `but stage`, `but commit`, `but push`, `but pr new`

Read-only `git log`, `git show`, and `git diff` are fine for inspection. Do not
use raw `git commit`, `git checkout`, `git switch`, branch-mutating
`git branch`, `git reset`, `git merge`, `git rebase`, `git cherry-pick`,
`git revert`, `git pull`, `git push`, `git worktree`, `git clean`, `git add`,
or `git restore` while GitButler owns the workspace. Physical git worktrees are
an explicit separate execution mode, not GitButler parallel lanes. Mark that
mode explicitly with `GEST_VCS_EXECUTION=git-worktrees` when raw git worktree
commands are required.
CONTEXT_EOF

escape_json() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/g' | tr -d '\n'
}

printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}' \
  "$(escape_json "$CONTEXT")"
