#!/usr/bin/env bash
set -euo pipefail

cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"This repository uses GitButler mode-strict for GitButler branch/stack series. Use but for VCS writes, use physical git worktrees for concurrent write agents, and apply the g* Gest workflow including tag classification and ast-grep dependency-impact checks."}}
JSON
