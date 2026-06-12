export UV_CACHE_DIR := ".local/uv-cache"

setup:
  uv sync

lint path=".":
  uv run ruff check {{path}}

typecheck:
  uv run ty check

build:
  uv run python -m compileall hello.py tests

test target="tests":
  uv run python -m pytest {{target}}

smoke:
  uv run python hello.py

diff-check:
  git diff --check

verify: lint typecheck build test smoke diff-check
