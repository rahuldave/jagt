# A Python project with uv. `just` lists the recipes. `just install lint` adds a tool; `just install` adds the rest.
import? '.agents/install.just'

# Each word after a recipe's name reaches its commands whole, as "$1", "$2" and so on; "$@" is all of them
set positional-arguments

export UV_CACHE_DIR := ".local/uv-cache"

[private]
default:
    @just --list --unsorted

# Install Python and every dependency into .venv, as the lockfile says
setup:
    uv sync

# Install the git hook: the checks of .pre-commit-config.yaml before every commit. Once per clone
hook:
    uv run pre-commit install

# Format the code. Extra arguments go to ruff: just fmt --check
fmt *args:
    uv run ruff format "$@"

# Check the code against the rules in ruff.toml. Extra arguments go to ruff: just lint --fix
lint *args:
    uv run ruff check "$@"

# Check the types. Needs just install typecheck
typecheck *args:
    uv run ty check "$@"

# Run the tests. Extra arguments go to pytest: just test tests/unit. Alone, a project with no tests yet passes
test *args:
    #!/usr/bin/env sh
    # pytest exits 5 when no test runs. With arguments that is a miss, and it fails. With none, it passes only when
    # pytest finds no test file at all: with addopts and PYTEST_ADDOPTS off, and with its summary saying so, because a
    # conftest hook that removes every test also exits 5. A coverage gate such as fail_under still fails it.
    uv run pytest "$@" && exit 0 || code=$?
    if [ "$code" -eq 5 ] && [ "$#" -eq 0 ]; then
        out=$(PYTEST_ADDOPTS= uv run pytest --collect-only -q -o addopts= 2>&1) || all=$?
        if [ "${all:-0}" -eq 5 ] && printf '%s\n' "$out" | grep -q '^no tests collected in '; then
            echo "just test: no tests yet"; exit 0
        fi
    fi
    exit "$code"

# Run the tests, and show which lines they ran. Alone, a project with no tests yet passes, as for just test
cov *args:
    #!/usr/bin/env sh
    uv run pytest --cov --cov-report=term-missing "$@" && exit 0 || code=$?
    if [ "$code" -eq 5 ] && [ "$#" -eq 0 ]; then
        out=$(PYTEST_ADDOPTS= uv run pytest --collect-only -q -o addopts= 2>&1) || all=$?
        if [ "${all:-0}" -eq 5 ] && printf '%s\n' "$out" | grep -q '^no tests collected in '; then
            echo "just cov: no tests yet"; exit 0
        fi
    fi
    exit "$code"

# Find whitespace errors in the changes
diff-check:
    git diff --check

# Everything a commit must pass: the format, the lint, the tests and the diff check
verify:
    just fmt --check
    just lint
    just test
    just diff-check
