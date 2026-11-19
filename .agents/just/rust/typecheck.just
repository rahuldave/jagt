# The typecheck tool of the rust profile: cargo check. just install typecheck adds it, and jnprofile-rust installs
# this file.

# Check the types of the code and the tests, with every feature, and build no binary. Extra arguments go to cargo
typecheck *args:
    cargo check --workspace --all-targets --all-features --locked "$@"
