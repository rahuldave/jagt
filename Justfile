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

# Every check of the repository: the release version, then verify. CI runs each of them
check: release-check verify

# The release tags. scripts/release_tag.py is a copy of .agents/skills/gpa/scripts/release_tag.py of
# agent_gest_git_skills at the commit 799a44b, the same file as in cx. The job release of ci.yml runs just release on
# each push to main. The script runs just <profile>::version for each name of the key profiles of .agents/stack.json,
# here rust, so the tag is v plus the version of Cargo.toml.
release_tag := "uv run --no-project --quiet --no-python-downloads --python '>=3.9' python scripts/release_tag.py"

# rust::version prints the version of Cargo.toml. The rust profile of jnterfaces gives the same recipe. When jagt
# installs that profile, take out this line and scripts/rust.just, because just stops on a module defined twice
mod rust 'scripts/rust.just'

# Tag HEAD with v plus the version of Cargo.toml, push the tag and check it. Takes --dry-run first
[positional-arguments]
release *args:
    @{{release_tag}} "$@"

# Fail when the version of Cargo.toml is below the last tag or the bump that the commits ask for. It needs no network
release-check:
    {{release_tag}} --check

# Build the release binary for TARGET, a Rust target triple, and pack it as dist/jagt-TARGET.tar.gz with jagt at its
# top level, plus dist/jagt-TARGET.tar.gz.sha256. The job binaries of ci.yml runs it, and scripts/install.sh installs it
dist target:
    rustup target add {{target}}
    cargo build --release --locked --target {{target}}
    mkdir -p dist
    COPYFILE_DISABLE=1 tar -czf dist/jagt-{{target}}.tar.gz -C "{{cargo_target_dir}}/{{target}}/release" jagt
    cd dist && shasum -a 256 jagt-{{target}}.tar.gz > jagt-{{target}}.tar.gz.sha256
