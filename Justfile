set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
cargo_target_dir := env_var_or_default("CARGO_TARGET_DIR", "target")

# The recipes of jnterfaces, and through it of the tasker role, from just install.
import? '.agents/install.just'

default: verify

setup:
    cargo fetch

fmt path="":
    cargo fmt --all

fmt-check:
    cargo fmt --all --check

lint:
    cargo clippy --all-targets --all-features -- -D warnings

typecheck:
    cargo check --all-targets --all-features

static: typecheck

build:
    cargo build --all-targets --all-features

test target="":
    cargo test --all-targets --all-features {{target}}

smoke:
    cargo run -- --help

# Run the protocol demo. The script renders with --no-save in a temporary folder of its own
protocol-demo:
    bash "{{justfile_directory()}}/.agents/skills/jagt-protocol/scripts/run_protocol_demo.sh" "{{absolute_path(cargo_target_dir)}}/debug/jagt"

# Check that git tracks the files that import the installed recipes, and that the recipes load.
# The imports use import?, so a missing file would drop the recipes without an error
installed-recipes:
    git ls-files --error-unmatch .agents/install.just .agents/just/index.just .agents/just/roles/agent_gest_git_skills.just > /dev/null
    summary="$(just --justfile "{{justfile()}}" --summary)"; \
    for recipe in install uninstall tasker-mode worktree-new worktree-sync worktrees worktrees-prune; do \
        [[ " $summary " == *" $recipe "* ]] || { echo "the recipe $recipe does not load" >&2; exit 1; }; \
    done

docs:
    cargo doc --no-deps

diff-check:
    git diff --check

verify: fmt-check lint typecheck build test smoke protocol-demo installed-recipes diff-check
