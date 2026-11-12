set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
cargo_target_dir := env_var_or_default("CARGO_TARGET_DIR", "target")

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

# The demo runs from a temporary folder, outside any git worktree, so that
# jagt render saves no packet file in this repository.
protocol-demo:
    cd "$(mktemp -d)" && bash "{{justfile_directory()}}/.agents/skills/jagt-protocol/scripts/run_protocol_demo.sh" "{{absolute_path(cargo_target_dir)}}/debug/jagt"

docs:
    cargo doc --no-deps

diff-check:
    git diff --check

verify: fmt-check lint typecheck build test smoke protocol-demo diff-check
