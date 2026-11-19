# begin lines of jnterfaces, the installer, from jnterfaces at a0cb68d.
# Last written to Justfile by `just install`. The record is parts."Justfile" in .agents/stack.json.
import? '.agents/install.just'
export JLOG_RUN := env("JLOG_RUN", uuid())
# end lines of jnterfaces. They stay while the project keeps .agents/stack.json.

cargo_target_dir := env_var_or_default("CARGO_TARGET_DIR", "target")

# The recipes of jagt. The block of jnterfaces above imports .agents/install.just, which gives just install, and the
# recipes of the rust profile and of the tasker role, for example setup, build, fmt, fmt-check, lint, typecheck, test,
# integration, coverage-check, diff-check, tools-check, check, ci, release, release-check and rust::version. The index
# sets the shell of the Justfile to jlog. Each name below is jagt's own, and the index leaves it out.

default: verify

# The static check of the code, as an alias of the step typecheck
static: typecheck

# Run the binary once, as a smoke test of the build
smoke:
    cargo run -- --help

# Run the protocol demo. The script renders with --no-save in a temporary folder of its own
protocol-demo:
    bash "{{justfile_directory()}}/.agents/skills/jagt-protocol/scripts/run_protocol_demo.sh" "{{absolute_path(cargo_target_dir)}}/debug/jagt"

# Check that git tracks the files that import the installed recipes, and that the recipes load.
# The imports use import? and mod, so a missing file would drop the recipes without an error
installed-recipes:
    git ls-files --error-unmatch .agents/install.just .agents/just/index.just .agents/just/rust.just \
        .agents/just/rust/base.just .agents/just/rust/lint.just .agents/just/rust/typecheck.just \
        .agents/just/rust/test.just .agents/just/rust/integration.just .agents/just/rust/steps.py \
        .agents/just/roles/agent_gest_git_skills.just .agents/just/roles/nossaifd.just > /dev/null
    summary="$(just --justfile "{{justfile()}}" --summary)"; \
    for recipe in install uninstall tasker-mode worktree-new worktrees check release release-check fmt-check lint test integration prose prose-check diff-check rust::version \
        rust::fmt-check rust::lint rust::typecheck rust::test rust::integration; do \
        case " $summary " in *" $recipe "*) ;; *) echo "the recipe $recipe does not load" >&2; exit 1 ;; esac; \
    done

# The API docs of the crate
docs:
    cargo doc --no-deps

# The quick local check: the format, the lint, the build, the tests, the smoke test, the protocol demo, the installed
# recipes and the whitespace of the diff. just check runs every step of the commit gate
verify: fmt-check lint typecheck build test integration smoke protocol-demo installed-recipes diff-check

# Build the release binary for TARGET, a Rust target triple, and pack it as dist/jagt-TARGET.tar.gz with jagt at its
# top level, plus dist/jagt-TARGET.tar.gz.sha256. The job binaries of ci.yml runs it, and scripts/install.sh installs it
dist target:
    rustup target add {{target}}
    cargo build --release --locked --target {{target}}
    mkdir -p dist
    COPYFILE_DISABLE=1 tar -czf dist/jagt-{{target}}.tar.gz -C "{{cargo_target_dir}}/{{target}}/release" jagt
    cd dist && shasum -a 256 jagt-{{target}}.tar.gz > jagt-{{target}}.tar.gz.sha256
