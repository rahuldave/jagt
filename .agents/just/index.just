# Written by just install. Do not edit: the next just install writes it again.
# The recipes of the profiles and roles of this project. .agents/install.just imports this file.

# Each line of a recipe runs through jlog, which adds it to the run log in .agents/log
set shell := ["jlog", "sh", "-cu"]

mod rust 'rust.just'
import? 'roles/agent_gest_git_skills.just'
import? 'roles/nossaifd.just'

# just build for each language that has it: rust
[positional-arguments]
build *args:
    just --justfile {{quote(justfile())}} rust build "$@"

# just coverage-check for each language that has it: rust
coverage-check:
    just --justfile {{quote(justfile())}} rust coverage-check
    jlog step coverage-check

# just fmt for each language that has it: rust
[positional-arguments]
fmt *args:
    just --justfile {{quote(justfile())}} rust fmt "$@"

# just fmt-check for each language that has it: rust
fmt-check:
    just --justfile {{quote(justfile())}} rust fmt-check
    jlog step fmt-check

# just integration for each language that has it: rust
[positional-arguments]
integration *args:
    just --justfile {{quote(justfile())}} rust integration "$@"
    jlog step integration

# just lint for each language that has it: rust
[positional-arguments]
lint *args:
    just --justfile {{quote(justfile())}} rust lint "$@"
    jlog step lint

# just setup for each language that has it: rust
setup:
    just --justfile {{quote(justfile())}} rust setup

# just test for each language that has it: rust
[positional-arguments]
test *args:
    just --justfile {{quote(justfile())}} rust test "$@"
    jlog step test

# just test-paths for each language that has it: rust
[positional-arguments]
test-paths *args:
    just --justfile {{quote(justfile())}} rust test-paths "$@"

# just typecheck for each language that has it: rust
[positional-arguments]
typecheck *args:
    just --justfile {{quote(justfile())}} rust typecheck "$@"
    jlog step typecheck

# just version for each language that has it: rust
version:
    just --justfile {{quote(justfile())}} rust version

# Check each program that .agents/stack.json records: it is there, and at its version floor
tools-check:
    uv run --no-project --quiet --no-python-downloads --python '>=3.9' python .agents/tools_check.py
    jlog step tools-check

# Find whitespace errors in the changes against the last commit
diff-check:
    git diff --check "$(git rev-parse -q --verify HEAD || git hash-object -t tree /dev/null)"
    jlog step diff-check

# No profile or role of this repository has docstring-check, so the step logs a skip
docstring-check:
    jlog skip docstring-check "no docstring check in this repository"

# No profile or role of this repository has docs-check, so the step logs a skip
docs-check:
    jlog skip docs-check "no docs site in this repository"

# Everything a commit must pass: each step, then the pass of jlog for the worktree
check: tools-check release-check fmt-check lint typecheck test integration coverage-check docstring-check docs-check prose-check diff-check
    jlog pass

# What CI checks: the trailers of the commit gate, then the steps of the list ci of .agents/stack.json
ci: ci-gate
