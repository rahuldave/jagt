# The toml tool of the rust profile: taplo and cargo-sort. just install toml adds it, and jnprofile-rust installs
# this file. It is not a default tool. just verify runs toml-check, and just check does not, because toml-check is
# not a step of the commit gates.

# Sort the tables of each Cargo.toml of the workspace with cargo-sort, then format the TOML files with taplo
toml-fmt:
    {{rust_py}} {{rust_steps}} toml

# Check the order of the tables of each Cargo.toml and the format of the TOML files, and change no file
toml-check:
    {{rust_py}} {{rust_steps}} toml --check
