# The api tool of the rust profile: smalldocs api check, for the API pages of the docs site. just install api adds
# it, and jnprofile-rust installs this file. uv runs smalldocs, and smalldocs reads the API with rustdoc of the
# toolchain nightly-2026-11-12, which just install api installs.

# Fail on each public item with no doc comment, and on each parameter and return with no comment: the comment after
# a parameter or a line of an # Arguments section, and a # Returns section. The settings are the key api of
# docs/_smalldocs.yml, or else each crate of the workspace with a library or a binary. Then run api-prose-check. The
# step docs-check of the docs role runs this recipe. Without that role, no step runs it
api-check:
    {{rust_py}} {{rust_steps}} api check
    just --justfile {{quote(module_file())}} api-prose-check

# Check the API page of each changed file with the checker of nossaifd. The page goes into a temporary folder,
# outside the project. A changed file changed since HEAD. In CI, or with --base REF, it changed since the base that
# check-changed of nossaifd takes, in the commits or in the working tree. Without the prose role, which installs the
# checker, it passes. When it passed before in this run of just, on this tree and with the same base, it does not
# run again, so api-check and prose-check can both call it
[positional-arguments]
api-prose-check *args:
    {{rust_py}} {{rust_steps}} ran prose "$@" || just --justfile {{quote(module_file())}} _api-prose-check "$@"

# The run of api-prose-check: the run ID, the tree and the base go into .jnprofile-rust, so that it runs once in a
# run
[positional-arguments]
_api-prose-check *args:
    {{rust_py}} {{rust_steps}} begin prose "$@"
    {{rust_py}} {{rust_steps}} api prose "$@"
    {{rust_py}} {{rust_steps}} stamp prose
