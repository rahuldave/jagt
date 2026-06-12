#!/usr/bin/env bash
set -euo pipefail

project_root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$project_root"

if command -v but >/dev/null 2>&1 && but status >/dev/null 2>&1; then
  but status >/dev/null 2>&1 || true
elif git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git status --short --branch >/dev/null 2>&1 || true
fi
