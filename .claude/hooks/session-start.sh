#!/usr/bin/env bash
set -euo pipefail

project_root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
# The tasker variant that just install recorded in .agents/stack.json: git (the default) or gitwt.
tasker_mode="$(sed -n 's/.*"tasker"[[:space:]]*:[[:space:]]*"\([a-z]*\)".*/\1/p' "$project_root/.agents/stack.json" 2>/dev/null | head -1 || true)"

read -r -d '' CONTEXT <<'CONTEXT_EOF' || true
## Gest Workflow Reminder

Use the project-local `g*` skills for substantial work:

- `gtw`: route project work into Gest
- `gsp`: create/update specs
- `gpl`: plan tasks and iterations
- `gis`: create durable tasks
- `gim`: implement one concrete task
- `gor`: execute phased work, on one branch in order or in physical git worktrees for parallel writes
- `gfm`: format/lint/static checks
- `gte`: tests and smoke/integration checks
- `gdo`: docs audit
- `grv`: review current changes
- `gcm`: commit, push and PR checkpoint, with stacked PRs in plain git
- `gpr`: GitHub issue promotion decision
- `gpa`: GitHub PR acceptance review

Keep Gest commands serialized. Use task notes with Done and Verification before
completing non-trivial leaves. Apply tag classification and ast-grep dependency
impact checks from .agents/skills/gtw/references/tag_dependency_workflow.md.
CONTEXT_EOF

if [ "$tasker_mode" = gitwt ]; then
  CONTEXT="$CONTEXT

Tasker variant gitwt: do each write task in its own worktree. \`just worktree-new NAME\`
makes one in ../<repo>.worktrees/NAME and sets it up. Keep the main checkout on
its base branch."
else
  CONTEXT="$CONTEXT

Tasker variant git: work on a branch in the main checkout. For parallel write
work, \`just worktree-new NAME\` makes a worktree for each task."
fi
# Report the worktrees that are ready to prune. Nothing is removed here.
script="$project_root/.agents/skills/gtw/scripts/worktree.py"
if [ -f "$script" ] && command -v uv >/dev/null 2>&1; then
  ready="$(cd "$project_root" && uv run --no-project --quiet --no-python-downloads --python '>=3.9' python "$script" list --report 2>/dev/null || true)"
  if [ -n "$ready" ]; then
    CONTEXT="$CONTEXT

$ready Tell the user; remove them only when the user asks."
  fi
fi

# The rules of the tasker role. just install writes them to .agents/instructions/tasker.md, and AGENTS.md has the
# line "Read and follow @.agents/instructions/tasker.md". Claude Code imports the rules through that line when
# CLAUDE.md imports AGENTS.md, so the hook leaves them out then, and they are not in the context twice. Markdown
# decides what is an import, so the hook leaves the rules out only for the files that the installer writes:
# - CLAUDE.md at the top of the project holds only the line @AGENTS.md, or is a symlink to AGENTS.md.
# - AGENTS.md is a file and not a symlink. It has the pointer on a line of its own, and before it only blank lines,
#   comments of one line and the pointers of other roles.
# - No settings file that the hook can read names claudeMdExcludes. The hook cannot see claude --settings.
# In each other case the hook prints the rules, so at worst they are in the context twice. With no CLAUDE.md,
# Claude Code 2.1.277 and later also read AGENTS.md, so the rules are there twice; older versions need the hook.
rules="$project_root/.agents/instructions/tasker.md"
# points FILE: FILE has the pointer of the rules on a line of its own. Before it are only the lines that the
# installer writes: blank lines, comments of one line, and the pointers of other roles. Any other line before it
# could make the pointer code, HTML or front matter, so the hook is not sure.
points() {
  awk '
    { sub(/\r$/, "") }
    $0 == "Read and follow @.agents/instructions/tasker.md" { found = 1; exit }
    $0 ~ /^[ \t]*$/ { next }
    $0 ~ /^<!--/ && $0 ~ /-->$/ && index(substr($0, 5), "<!--") == 0 && index($0, "-->") == length($0) - 2 { next }
    $0 ~ /^Read and follow @\.agents\/instructions\/[A-Za-z0-9_-]+\.md$/ { next }
    { exit }
    END { exit !found }' "$1"
}
imported() {
  local claude="$project_root/CLAUDE.md" agents="$project_root/AGENTS.md" settings
  [ -f "$agents" ] && [ ! -L "$agents" ] && points "$agents" || return 1
  for settings in "$project_root/.claude/settings.json" "$project_root/.claude/settings.local.json" \
    "${CLAUDE_CONFIG_DIR:-${HOME:-/nonexistent}/.claude}/settings.json" \
    "/Library/Application Support/ClaudeCode/managed-settings.json" "/etc/claude-code/managed-settings.json"; do
    if [ -f "$settings" ] && grep -q claudeMdExcludes "$settings"; then return 1; fi
  done
  if [ -L "$claude" ]; then
    case "$(readlink "$claude")" in AGENTS.md | ./AGENTS.md) return 0 ;; esac
    return 1
  fi
  [ -f "$claude" ] && [ "$(tr -d '\r' < "$claude" | awk 'NF')" = '@AGENTS.md' ]
}
if [ -f "$rules" ] && ! imported; then
  # Claude Code and Codex show a long hook output only as a short preview and a file. So the first line, which is
  # always in the preview, asks for the whole file.
  CONTEXT="Read all of .agents/instructions/tasker.md before you start work. It holds the rules of this project.

$(cat "$rules")

$CONTEXT"
fi

escape_json() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/g' | tr -d '\n' | tr '\001-\037' ' '
}

printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}' \
  "$(escape_json "$CONTEXT")"
