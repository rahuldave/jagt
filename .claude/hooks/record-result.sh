#!/usr/bin/env sh
# The record hook: when a fresh agent stops, write the record of its AGENT_RESULT v1 for the commit gate. It never
# stops the fresh agent. The script is in the gcm skill: .agents/skills/gcm/scripts/record_result.py.
root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
script="$root/.agents/skills/gcm/scripts/record_result.py"
# Without the gcm skill or uv, the hook cannot run. The commit gate then finds no record and says what is missing.
[ -f "$script" ] && command -v uv >/dev/null 2>&1 || exit 0
uv run --no-project --quiet --no-python-downloads --python '>=3.9' --with pyyaml python "$script" hook
exit 0
