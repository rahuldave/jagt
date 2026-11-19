# The lint tool of the rust profile: rustfmt and clippy. just install lint adds it, and jnprofile-rust installs this
# file.

# Format the code of every package of the workspace. Extra arguments go to cargo fmt: just fmt -- --check
fmt *args:
    cargo fmt --all "$@"

# Check the format of the code, and change no file
fmt-check:
    cargo fmt --all --check

# Check the code with clippy, with every feature, and fail on each warning. Extra arguments go to cargo: just lint -p app
lint *args:
    cargo clippy --workspace --all-targets --all-features --locked "$@" -- -D warnings
