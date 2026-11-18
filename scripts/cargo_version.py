"""Print the version of Cargo.toml, X.Y.Z, for the release tag. just rust::version runs it.

It prints nothing when [package] has no version. It exits 2 when it cannot read Cargo.toml. It reads the file with
tomllib only, so it needs Python 3.11 or later, no network and no cargo.
"""
import sys
import tomllib


def main(path="Cargo.toml"):
    try:
        with open(path, "rb") as file:
            data = tomllib.load(file)
    except (OSError, ValueError) as error:
        print(f"rust::version: cannot read {path}: {error}", file=sys.stderr)
        return 2
    package = data.get("package")
    version = package.get("version") if isinstance(package, dict) else None
    if version is None:
        return 0
    if not isinstance(version, str):
        print(f"rust::version: the version in {path} is not a string", file=sys.stderr)
        return 2
    print(version)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:2]))
