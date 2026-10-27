# PROJECT: every task is a recipe here. `just` lists them.

# Each word after a recipe's name reaches its commands whole, as "$1", "$2" and so on; "$@" is all of them
set positional-arguments

[private]
default:
    @just --list --unsorted

# Install every dependency into .venv, exactly as the lockfile says
setup:
    uv sync --locked

# Format the code. Extra arguments go to ruff: just fmt --check
fmt *args:
    uv run ruff format "$@"

# Check the code against the lint rules. Extra arguments go to ruff: just lint --fix
lint *args:
    uv run ruff check "$@"

# Check the types. Extra arguments go to ty: just types src
types *args:
    uv run ty check "$@"

# Run the tests. Extra arguments go to pytest: just test tests/unit
test *args:
    uv run pytest "$@"

# Everything a commit must pass: the format, the lint, the types and the tests
check:
    just fmt --check
    just lint
    just types
    just test -q
