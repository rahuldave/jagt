#!/usr/bin/env bash
set -euo pipefail

target="${1:-$PWD}"
repo_url="${AGENT_GEST_GIT_SKILLS_REPO:-https://github.com/rahuldave/agent_gest_git_skills.git}"
source_dir="${AGENT_GEST_GIT_SKILLS_SOURCE:-}"

missing_required=()
for exe in git gest just uv; do
  if ! command -v "$exe" >/dev/null 2>&1; then
    missing_required+=("$exe")
  fi
done

if [ "${#missing_required[@]}" -gt 0 ]; then
  printf 'Missing required workflow executable(s): %s\n' "${missing_required[*]}" >&2
  printf 'The package skills may already be installed, but install these before relying on the Git/GitButler Gest workflow.\n' >&2
fi

optional_missing=()
for exe in rsync gh but ast-grep direnv cx; do
  if ! command -v "$exe" >/dev/null 2>&1; then
    optional_missing+=("$exe")
  fi
done

if [ "${#optional_missing[@]}" -gt 0 ]; then
  printf 'Optional executable(s) not found: %s\n' "${optional_missing[*]}" >&2
fi

tmp_dir=""
if [ -z "$source_dir" ]; then
  if ! command -v git >/dev/null 2>&1; then
    printf 'Cannot fetch %s because git is not installed. Clone the repo manually and rerun with AGENT_GEST_GIT_SKILLS_SOURCE=/path/to/clone.\n' "$repo_url" >&2
    exit 1
  fi
  tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/agent-gest-git-skills.XXXXXX")"
  trap 'if [ -n "$tmp_dir" ]; then rm -rf "$tmp_dir"; fi' EXIT
  git clone --depth 1 "$repo_url" "$tmp_dir/repo" >/dev/null
  source_dir="$tmp_dir/repo"
fi

if [ ! -x "$source_dir/scripts/install.sh" ] && [ ! -f "$source_dir/scripts/install.sh" ]; then
  printf 'Installer not found at %s/scripts/install.sh\n' "$source_dir" >&2
  exit 1
fi

bash "$source_dir/scripts/install.sh" "$target"
