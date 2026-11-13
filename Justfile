set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
cargo_target_dir := env_var_or_default("CARGO_TARGET_DIR", "target")

# The recipes of jnterfaces and of the tasker role, from just install.
import? '.agents/install.just'
import? '.agents/just/roles/agent_gest_git_skills.just'

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

# Run the protocol demo outside any git worktree, so jagt saves no packet file here
protocol-demo:
    cd "$(mktemp -d)" && bash "{{justfile_directory()}}/.agents/skills/jagt-protocol/scripts/run_protocol_demo.sh" "{{absolute_path(cargo_target_dir)}}/debug/jagt"

docs:
    cargo doc --no-deps

diff-check:
    git diff --check

verify: fmt-check lint typecheck build test smoke protocol-demo diff-check
