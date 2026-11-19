# A Rust project that does not use just install. The rust profile gives the steps of just check, with
# coverage-check and docstring-check. Prefer it. Install it with:
#   uv run "${SKILL_PACKAGES_DIR:-$HOME/.local/share/skill-packages}/jnterfaces/scripts/install_stack.py" --profile rust

fmt:
  cargo fmt --all

lint:
  cargo clippy --all-targets --all-features -- -D warnings

typecheck:
  cargo check --all-targets --all-features

build:
  cargo build --all-targets --all-features

test target="":
  cargo test --all-features {{target}}

docs:
  cargo doc --no-deps

smoke:
  cargo run --quiet

diff-check:
  git diff --check

verify: fmt lint typecheck build test smoke diff-check
