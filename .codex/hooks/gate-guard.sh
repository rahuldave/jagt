#!/usr/bin/env sh
# The gate guard: stop the commands that go around the commit gate, such as git commit --no-verify. It exits with 2
# to stop a tool call. The script is in the gcm skill: .agents/skills/gcm/scripts/gate_guard.py.
root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
script="$root/.agents/skills/gcm/scripts/gate_guard.py"
# Without the gcm skill or uv, the guard cannot run, and the tool call goes on. The commit gate still checks.
[ -f "$script" ] && command -v uv >/dev/null 2>&1 || exit 0
# Codex has no question for a hook, so the guard stops a call that needs the person.
JN_HOOK_HARNESS=codex exec uv run --no-project --quiet --no-python-downloads --python '>=3.9' python "$script"
