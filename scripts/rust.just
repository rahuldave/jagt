# The module rust of the Justfile. release_tag.py runs just rust::version, because .agents/stack.json names the
# profile rust. It reads only Cargo.toml, so it needs no network and no cargo.

# Print the version of Cargo.toml, X.Y.Z, for the release tag. A Cargo.toml that cannot be read exits 2
version:
    @uv run --no-project --quiet --no-python-downloads --python '>=3.11' python -I {{quote(source_directory() / "cargo_version.py")}} {{quote(justfile_directory() / "Cargo.toml")}}
