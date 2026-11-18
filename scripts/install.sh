#!/bin/sh
# Install a release binary of jagt, with no Rust.
#
#   sh install.sh [--tag vX.Y.Z] [--dir DIR]
#   curl -fsSL https://raw.githubusercontent.com/rahuldave/jagt/main/scripts/install.sh | sh -s -- --tag vX.Y.Z
#
# It downloads jagt-<target>.tar.gz and its .sha256 from the GitHub release,
# checks the hash, and puts jagt in DIR, which is ~/.local/bin by default.
# With no --tag, it installs the latest release. It needs curl, tar, and
# sha256sum or shasum.
#
# The whole script is one function, called on the last line, so a download
# that stops early runs nothing.
set -eu

main() {
    repo=rahuldave/jagt
    bin=jagt
    tag=
    dir=

    while [ $# -gt 0 ]; do
        case $1 in
            --tag)
                [ $# -ge 2 ] || fail "--tag needs a value"
                tag=$2
                shift 2
                ;;
            --tag=*)
                tag=${1#--tag=}
                shift
                ;;
            --dir)
                [ $# -ge 2 ] || fail "--dir needs a value"
                dir=$2
                shift 2
                ;;
            --dir=*)
                dir=${1#--dir=}
                shift
                ;;
            -h | --help)
                echo "usage: sh install.sh [--tag vX.Y.Z] [--dir DIR]"
                exit 0
                ;;
            *)
                fail "unknown argument: $1"
                ;;
        esac
    done

    if [ -z "$dir" ]; then
        [ -n "${HOME:-}" ] || fail "HOME is not set; pass --dir DIR"
        dir=$HOME/.local/bin
    fi

    os=$(uname -s)
    arch=$(uname -m)
    case "$os/$arch" in
        Darwin/arm64 | Darwin/aarch64) target=aarch64-apple-darwin ;;
        Darwin/x86_64) target=x86_64-apple-darwin ;;
        Linux/x86_64 | Linux/amd64) target=x86_64-unknown-linux-musl ;;
        Linux/aarch64 | Linux/arm64) target=aarch64-unknown-linux-musl ;;
        *)
            fail "no release binary for $os $arch; build from source with: cargo install --git https://github.com/$repo --tag <tag> $bin"
            ;;
    esac

    if [ -z "$tag" ]; then
        tag=$(curl -fsSL "https://api.github.com/repos/$repo/releases/latest" |
            sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -n 1) ||
            fail "cannot read the latest release"
        [ -n "$tag" ] || fail "cannot read the latest release"
    fi
    case $tag in
        v[0-9]*) ;;
        [0-9]*) tag=v$tag ;;
        *) fail "a tag looks like v1.2.3, not $tag" ;;
    esac
    case $tag in
        *[!0-9A-Za-z.+-]*) fail "a tag looks like v1.2.3, not $tag" ;;
    esac

    if command -v sha256sum >/dev/null 2>&1; then
        sha() { sha256sum "$1" | awk '{ print $1 }'; }
    elif command -v shasum >/dev/null 2>&1; then
        sha() { shasum -a 256 "$1" | awk '{ print $1 }'; }
    else
        fail "needs sha256sum or shasum to check the download"
    fi

    asset=$bin-$target.tar.gz
    url=https://github.com/$repo/releases/download/$tag/$asset
    tmp=$(mktemp -d)
    new=
    trap 'rm -rf "$tmp"; [ -z "$new" ] || rm -f "$new"' EXIT
    trap 'exit 130' INT TERM

    curl -fsSL -o "$tmp/$asset" "$url" || fail "cannot download $url"
    curl -fsSL -o "$tmp/$asset.sha256" "$url.sha256" || fail "cannot download $url.sha256"

    expected=$(awk 'NR == 1 { print $1 }' "$tmp/$asset.sha256")
    case $expected in
        *[!0-9a-f]* | "") fail "the .sha256 file of $asset holds no hash" ;;
    esac
    [ "${#expected}" -eq 64 ] || fail "the .sha256 file of $asset holds no hash"
    [ "$expected" = "$(sha "$tmp/$asset")" ] ||
        fail "the hash of $asset does not match its .sha256 file"

    mkdir "$tmp/unpacked"
    tar -xzf "$tmp/$asset" -C "$tmp/unpacked" || fail "cannot unpack $asset"
    [ -f "$tmp/unpacked/$bin" ] || fail "$asset holds no $bin"

    mkdir -p "$dir"
    new=$dir/.$bin.new.$$
    cp "$tmp/unpacked/$bin" "$new"
    chmod 755 "$new"
    mv -f "$new" "$dir/$bin"
    new=
    "$dir/$bin" --version
}

fail() {
    echo "install.sh: $*" >&2
    exit 1
}

main "$@"
