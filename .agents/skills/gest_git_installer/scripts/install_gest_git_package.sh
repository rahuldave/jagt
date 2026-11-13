#!/usr/bin/env bash
# Install the Gest skills, hooks, hook settings and AGENTS.md starter into a repository with the jnterfaces installer.
# Usage: install_gest_git_package.sh [TARGET]
# The machine needs just, uv and git. The packages are Git clones in $SKILL_PACKAGES_DIR, by default
# ~/.local/share/skill-packages, and a missing clone is cloned from GitHub. JNTERFACES_DIR names one jnterfaces
# clone, and AGENT_GEST_GIT_SKILLS_SOURCE names one clone of this package.
set -euo pipefail

target="${1:-$PWD}"
packages="${SKILL_PACKAGES_DIR:-$HOME/.local/share/skill-packages}"
jnterfaces="${JNTERFACES_DIR:-$packages/jnterfaces}"

missing_required=()
for exe in git uv just gest; do # git --version, uv --version, just --version and gest --version name the versions
  if ! command -v "$exe" >/dev/null 2>&1; then
    missing_required+=("$exe")
  fi
done
if [ "${#missing_required[@]}" -gt 0 ]; then
  printf 'Missing required workflow executable(s): %s\n' "${missing_required[*]}" >&2
  printf 'Install these before relying on the Git Gest workflow.\n' >&2
fi
for exe in git uv; do
  command -v "$exe" >/dev/null 2>&1 || { printf 'The installer needs %s.\n' "$exe" >&2; exit 1; }
done

optional_missing=()
for exe in rsync gh ast-grep direnv cx; do # rsync --version, gh --version and the others are optional
  if ! command -v "$exe" >/dev/null 2>&1; then
    optional_missing+=("$exe")
  fi
done
if [ "${#optional_missing[@]}" -gt 0 ]; then
  printf 'Optional executable(s) not found: %s\n' "${optional_missing[*]}" >&2
fi

if [ ! -f "$jnterfaces/scripts/install_stack.py" ]; then
  mkdir -p "$(dirname "$jnterfaces")"
  git clone --quiet https://github.com/rahuldave/jnterfaces "$jnterfaces"
fi

options=(--target "$target" tasker)
if [ -n "${AGENT_GEST_GIT_SKILLS_SOURCE:-}" ]; then
  options+=(--clone "agent_gest_git_skills=$AGENT_GEST_GIT_SKILLS_SOURCE")
fi
exec uv run --quiet --script "$jnterfaces/scripts/install_stack.py" "${options[@]}"
