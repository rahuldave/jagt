#!/usr/bin/env bash
set -euo pipefail

jagt_bin="${JAGT_BIN:-jagt}"
if ! command -v "$jagt_bin" >/dev/null 2>&1; then
  echo "$jagt_bin is required for AGENT_TASK_DRAFT v1 linting" >&2
  exit 127
fi

exec "$jagt_bin" draft lint "$@"
