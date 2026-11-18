//! Tests of `scripts/install.sh` against a fake release, with no network.
//!
//! Stub `uname` and `curl` commands come first on `PATH`. The stub curl serves
//! files from a folder that the test fills, and logs each URL it is asked for.
#![cfg(unix)]

use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use sha2::{Digest, Sha256};
use tempfile::{TempDir, tempdir};

const TAG: &str = "v9.9.9";

const CURL: &str = r#"#!/bin/sh
out=
url=
while [ $# -gt 0 ]; do
    case $1 in
        -o) out=$2; shift 2 ;;
        -*) shift ;;
        *) url=$1; shift ;;
    esac
done
echo "$url" >> "$FAKE_LOG"
case $url in
    https://api.github.com/repos/rahuldave/jagt/releases/latest)
        printf '{\n  "url": "x",\n  "tag_name": "%s",\n  "name": "y"\n}\n' "$FAKE_LATEST"
        exit 0 ;;
    https://github.com/rahuldave/jagt/releases/download/*)
        file=$FAKE_RELEASES/${url#https://github.com/rahuldave/jagt/releases/download/} ;;
    *) exit 6 ;;
esac
[ -f "$file" ] || exit 22
if [ -n "$out" ]; then cp "$file" "$out"; else cat "$file"; fi
"#;

const UNAME: &str = r#"#!/bin/sh
case $1 in
    -s) echo "$FAKE_OS" ;;
    -m) echo "$FAKE_ARCH" ;;
    *) exit 1 ;;
esac
"#;

struct Fake {
    dir: TempDir,
}

impl Fake {
    /// A fake release of TAG with an asset for each target, and stub commands.
    fn new() -> Self {
        let fake = Self {
            dir: tempdir().expect("tempdir"),
        };
        let stubs = fake.path("stubs");
        fs::create_dir(&stubs).expect("stubs");
        executable(&stubs.join("curl"), CURL);
        executable(&stubs.join("uname"), UNAME);
        for target in [
            "aarch64-apple-darwin",
            "x86_64-apple-darwin",
            "x86_64-unknown-linux-musl",
            "aarch64-unknown-linux-musl",
        ] {
            fake.publish(target, None);
        }
        fake
    }

    fn path(&self, name: &str) -> PathBuf {
        self.dir.path().join(name)
    }

    /// Put `jagt-<target>.tar.gz` and its `.sha256` in the release. A given
    /// hash replaces the true one.
    fn publish(&self, target: &str, hash: Option<&str>) {
        let release = self.path("releases").join(TAG);
        fs::create_dir_all(&release).expect("release");
        let build = self.path(&format!("build-{target}"));
        fs::create_dir_all(&build).expect("build");
        executable(
            &build.join("jagt"),
            &format!("#!/bin/sh\necho \"jagt 9.9.9 {target}\"\n"),
        );
        let asset = format!("jagt-{target}.tar.gz");
        let status = Command::new("tar")
            .arg("-czf")
            .arg(release.join(&asset))
            .arg("-C")
            .arg(&build)
            .arg("jagt")
            .status()
            .expect("tar");
        assert!(status.success());
        let bytes = fs::read(release.join(&asset)).expect("asset");
        let hash = hash.map_or_else(|| format!("{:x}", Sha256::digest(&bytes)), str::to_string);
        fs::write(
            release.join(format!("{asset}.sha256")),
            format!("{hash}  {asset}\n"),
        )
        .expect("sha256");
    }

    /// Run install.sh as `os` and `arch` with these arguments.
    fn install(&self, os: &str, arch: &str, args: &[&str]) -> Output {
        let path = std::env::var_os("PATH").unwrap_or_default();
        let mut paths = vec![self.path("stubs")];
        paths.extend(std::env::split_paths(&path));
        let mut command = self.command(os, arch, args);
        command
            .env("PATH", std::env::join_paths(paths).expect("PATH"))
            .env("HOME", self.path("home"));
        command.output().expect("run install.sh")
    }

    /// The command that runs install.sh, with the fake release but no PATH or HOME.
    fn command(&self, os: &str, arch: &str, args: &[&str]) -> Command {
        let script = Path::new(env!("CARGO_MANIFEST_DIR")).join("scripts/install.sh");
        let mut command = Command::new("/bin/sh");
        command
            .arg(script)
            .args(args)
            .env("FAKE_OS", os)
            .env("FAKE_ARCH", arch)
            .env("FAKE_LOG", self.path("curl.log"))
            .env("FAKE_RELEASES", self.path("releases"))
            .env("FAKE_LATEST", TAG);
        command
    }

    fn urls(&self) -> String {
        fs::read_to_string(self.path("curl.log")).unwrap_or_default()
    }
}

fn executable(path: &Path, text: &str) {
    fs::write(path, text).expect("write");
    fs::set_permissions(path, fs::Permissions::from_mode(0o755)).expect("chmod");
}

fn text(bytes: &[u8]) -> String {
    String::from_utf8_lossy(bytes).into_owned()
}

#[test]
fn each_platform_installs_the_asset_of_its_target() {
    for (os, arch, target) in [
        ("Darwin", "arm64", "aarch64-apple-darwin"),
        ("Darwin", "x86_64", "x86_64-apple-darwin"),
        ("Linux", "x86_64", "x86_64-unknown-linux-musl"),
        ("Linux", "amd64", "x86_64-unknown-linux-musl"),
        ("Linux", "aarch64", "aarch64-unknown-linux-musl"),
        ("Linux", "arm64", "aarch64-unknown-linux-musl"),
    ] {
        let fake = Fake::new();
        let dir = fake.path("bin");
        let out = fake.install(
            os,
            arch,
            &["--tag", TAG, "--dir", dir.to_str().expect("utf8")],
        );
        assert!(out.status.success(), "{os} {arch}: {}", text(&out.stderr));
        assert_eq!(text(&out.stdout), format!("jagt 9.9.9 {target}\n"));
        let url = format!(
            "https://github.com/rahuldave/jagt/releases/download/{TAG}/jagt-{target}.tar.gz"
        );
        assert!(
            fake.urls().lines().any(|line| line == url),
            "{}",
            fake.urls()
        );
        let mode = fs::metadata(dir.join("jagt"))
            .expect("jagt")
            .permissions()
            .mode();
        assert_eq!(mode & 0o777, 0o755);
        assert_eq!(
            fs::read_dir(&dir).expect("bin").count(),
            1,
            "no temporary file stays"
        );
    }
}

#[test]
fn the_default_folder_is_local_bin_and_no_tag_means_the_latest_release() {
    let fake = Fake::new();
    let out = fake.install("Darwin", "arm64", &[]);
    assert!(out.status.success(), "{}", text(&out.stderr));
    assert!(fake.path("home/.local/bin/jagt").is_file());
    assert!(
        fake.urls()
            .starts_with("https://api.github.com/repos/rahuldave/jagt/releases/latest\n")
    );
}

#[test]
fn a_hash_that_does_not_match_fails_and_installs_nothing() {
    let fake = Fake::new();
    fake.publish("aarch64-apple-darwin", Some(&"0".repeat(64)));
    let dir = fake.path("bin");
    let out = fake.install(
        "Darwin",
        "arm64",
        &["--tag", TAG, "--dir", dir.to_str().expect("utf8")],
    );
    assert!(!out.status.success());
    assert!(
        text(&out.stderr).contains("does not match"),
        "{}",
        text(&out.stderr)
    );
    assert!(!dir.join("jagt").exists());
}

#[test]
fn a_hash_file_without_a_hash_fails() {
    let fake = Fake::new();
    fake.publish("aarch64-apple-darwin", Some("not-a-hash"));
    let dir = fake.path("bin");
    let out = fake.install(
        "Darwin",
        "arm64",
        &["--tag", TAG, "--dir", dir.to_str().expect("utf8")],
    );
    assert!(!out.status.success());
    assert!(
        text(&out.stderr).contains("holds no hash"),
        "{}",
        text(&out.stderr)
    );
    assert!(!dir.join("jagt").exists());
}

#[test]
fn a_missing_release_fails() {
    let fake = Fake::new();
    let dir = fake.path("bin");
    let out = fake.install(
        "Darwin",
        "arm64",
        &["--tag", "v0.0.1", "--dir", dir.to_str().expect("utf8")],
    );
    assert!(!out.status.success());
    assert!(
        text(&out.stderr).contains("cannot download"),
        "{}",
        text(&out.stderr)
    );
    assert!(!dir.join("jagt").exists());
}

#[test]
fn an_unknown_platform_fails_before_any_download() {
    for (os, arch) in [
        ("FreeBSD", "amd64"),
        ("Linux", "riscv64"),
        ("Darwin", "ppc"),
    ] {
        let fake = Fake::new();
        let out = fake.install(os, arch, &["--tag", TAG]);
        assert!(!out.status.success(), "{os} {arch}");
        assert!(
            text(&out.stderr).contains("no release binary"),
            "{}",
            text(&out.stderr)
        );
        assert!(fake.urls().is_empty());
    }
}

#[test]
fn a_tag_that_is_not_a_version_fails_before_any_download() {
    for tag in ["main", "v1/../../x", "v1?x=y"] {
        let fake = Fake::new();
        let out = fake.install("Darwin", "arm64", &["--tag", tag]);
        assert!(!out.status.success(), "{tag}");
        assert!(fake.urls().is_empty(), "{tag}: {}", fake.urls());
    }
}

#[test]
fn a_hash_file_that_is_empty_fails() {
    let fake = Fake::new();
    fake.publish("aarch64-apple-darwin", Some(""));
    let dir = fake.path("bin");
    let out = fake.install(
        "Darwin",
        "arm64",
        &["--tag", TAG, "--dir", dir.to_str().expect("utf8")],
    );
    assert!(!out.status.success());
    assert!(
        text(&out.stderr).contains("holds no hash"),
        "{}",
        text(&out.stderr)
    );
    assert!(!dir.join("jagt").exists());
}

#[test]
fn a_latest_release_without_a_tag_fails() {
    let fake = Fake::new();
    let path = std::env::var_os("PATH").unwrap_or_default();
    let mut paths = vec![fake.path("stubs")];
    paths.extend(std::env::split_paths(&path));
    let out = fake
        .command("Darwin", "arm64", &[])
        .env("PATH", std::env::join_paths(paths).expect("PATH"))
        .env("HOME", fake.path("home"))
        .env("FAKE_LATEST", "")
        .output()
        .expect("run install.sh");
    assert!(!out.status.success());
    assert!(
        text(&out.stderr).contains("cannot read the latest release"),
        "{}",
        text(&out.stderr)
    );
    assert!(!fake.path("home/.local/bin/jagt").exists());
}

#[test]
fn no_home_and_no_dir_fails_before_any_download() {
    let fake = Fake::new();
    let path = std::env::var_os("PATH").unwrap_or_default();
    let mut paths = vec![fake.path("stubs")];
    paths.extend(std::env::split_paths(&path));
    let out = fake
        .command("Darwin", "arm64", &["--tag", TAG])
        .env("PATH", std::env::join_paths(paths).expect("PATH"))
        .env_remove("HOME")
        .output()
        .expect("run install.sh");
    assert!(!out.status.success());
    assert!(
        text(&out.stderr).contains("HOME is not set"),
        "{}",
        text(&out.stderr)
    );
    assert!(fake.urls().is_empty());
}

#[test]
fn no_hash_tool_fails_before_any_download() {
    // A PATH of links to the tools the script needs, without sha256sum or shasum.
    let fake = Fake::new();
    let tools = fake.path("tools");
    fs::create_dir(&tools).expect("tools");
    for tool in [
        "awk", "sed", "head", "mktemp", "tar", "gzip", "mkdir", "cp", "chmod", "mv", "rm", "cat",
    ] {
        let found = Command::new("/bin/sh")
            .args(["-c", &format!("command -v {tool}")])
            .output()
            .expect("command -v");
        let found = text(&found.stdout).trim().to_string();
        if !found.is_empty() {
            std::os::unix::fs::symlink(found, tools.join(tool)).expect("link");
        }
    }
    let paths = [fake.path("stubs"), tools];
    let out = fake
        .command(
            "Darwin",
            "arm64",
            &[
                "--tag",
                TAG,
                "--dir",
                fake.path("bin").to_str().expect("utf8"),
            ],
        )
        .env("PATH", std::env::join_paths(paths).expect("PATH"))
        .env("HOME", fake.path("home"))
        .output()
        .expect("run install.sh");
    assert!(!out.status.success());
    assert!(
        text(&out.stderr).contains("needs sha256sum or shasum"),
        "{}",
        text(&out.stderr)
    );
    assert!(fake.urls().is_empty());
    assert!(!fake.path("bin/jagt").exists());
}
