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
