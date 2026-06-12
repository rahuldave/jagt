#!/usr/bin/env bash
set -euo pipefail

if command -v but >/dev/null 2>&1 && but status >/dev/null 2>&1; then
  but status >/dev/null 2>&1 || true
elif git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git status --short --branch >/dev/null 2>&1 || true
fi

printf '{"continue":true}
'
