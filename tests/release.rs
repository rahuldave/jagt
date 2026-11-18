//! The release tags of jagt, as in cx: just check runs release-check, the tag is v plus the version of Cargo.toml, and only the jobs
//! release and publish of CI can write to the repository. The tests need git, just and uv on the PATH.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use serde_json::Value;
use tempfile::TempDir;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

/// Run a program in DIR with no git config of the user, such as a signing key, and a fixed author.
fn run(dir: &Path, program: &str, args: &[&str]) -> Output {
    Command::new(program)
        .args(args)
        .current_dir(dir)
        // A git hook sets these for the repository of the hook, and the scratch repository must not use them.
        .env_remove("GIT_DIR")
        .env_remove("GIT_INDEX_FILE")
        .env_remove("GIT_WORK_TREE")
        .env("GIT_CONFIG_GLOBAL", "/dev/null")
        .env("GIT_CONFIG_NOSYSTEM", "1")
        .env("GIT_AUTHOR_NAME", "t")
        .env("GIT_AUTHOR_EMAIL", "t@example.com")
        .env("GIT_COMMITTER_NAME", "t")
        .env("GIT_COMMITTER_EMAIL", "t@example.com")
        .output()
        .unwrap_or_else(|error| panic!("run {program}: {error}"))
}

fn ok(dir: &Path, program: &str, args: &[&str]) -> String {
    let output = run(dir, program, args);
    assert!(
        output.status.success(),
        "{program} {args:?} failed: {}{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    String::from_utf8_lossy(&output.stdout).into_owned()
}

/// A scratch repository with the release files of jagt, Cargo.toml at VERSION, a bare remote, and the tag v0.1.0.
fn scratch(version: &str) -> TempDir {
    let temp = TempDir::new().expect("tempdir");
    let repo = temp.path().join("repo");
    for dir in ["repo/scripts", "repo/.agents"] {
        fs::create_dir_all(temp.path().join(dir)).expect("mkdir");
    }
    for file in [
        "Justfile",
        "scripts/release_tag.py",
        "scripts/rust.just",
        "scripts/cargo_version.py",
        ".agents/stack.json",
    ] {
        fs::copy(root().join(file), repo.join(file)).expect("copy");
    }
    set_version(&repo, version);
    ok(temp.path(), "git", &["init", "-q", "--bare", "remote.git"]);
    ok(&repo, "git", &["init", "-q", "-b", "main"]);
    ok(&repo, "git", &["remote", "add", "origin", "../remote.git"]);
    commit(&repo, "feat: start");
    ok(&repo, "git", &["tag", "-a", "v0.1.0", "-m", "v0.1.0"]);
    ok(&repo, "git", &["push", "-q", "origin", "main", "v0.1.0"]);
    temp
}

fn set_version(repo: &Path, version: &str) {
    let manifest =
        format!("[package]\nname = \"x\"\nversion = \"{version}\"\nedition = \"2024\"\n");
    fs::write(repo.join("Cargo.toml"), manifest).expect("write Cargo.toml");
}

fn commit(repo: &Path, message: &str) {
    ok(repo, "git", &["add", "-A"]);
    ok(
        repo,
        "git",
        &["commit", "-q", "--allow-empty", "-m", message],
    );
}

/// The commit of agent_gest_git_skills that scripts/release_tag.py copies. The Justfile names it too.
const UPSTREAM_COMMIT: &str = "799a44b";
/// The Git blob of .agents/skills/gpa/scripts/release_tag.py at UPSTREAM_COMMIT of agent_gest_git_skills. To update the
/// copy, copy that file of the new commit, set UPSTREAM_COMMIT and the comment of the Justfile, and set this blob to
/// the output of `git -C AGENT_GEST_GIT_SKILLS rev-parse COMMIT:.agents/skills/gpa/scripts/release_tag.py`.
const UPSTREAM_BLOB: &str = "f014570e60c3ef9a7d2828cdd3e87f7d5e1f7047";

#[test]
fn the_script_is_the_copy_of_upstream() {
    let blob = ok(&root(), "git", &["hash-object", "scripts/release_tag.py"]);
    assert_eq!(
        blob.trim(),
        UPSTREAM_BLOB,
        "scripts/release_tag.py differs from agent_gest_git_skills {UPSTREAM_COMMIT}"
    );
}

#[test]
fn check_runs_release_check() {
    let dump: Value =
        serde_json::from_str(&ok(&root(), "just", &["--dump", "--dump-format", "json"]))
            .expect("json");
    let dependencies: Vec<&str> = dump["recipes"]["check"]["dependencies"]
        .as_array()
        .expect("dependencies")
        .iter()
        .map(|dependency| dependency["recipe"].as_str().expect("name"))
        .collect();
    assert!(dependencies.contains(&"release-check"), "{dependencies:?}");
    assert!(dependencies.contains(&"verify"), "{dependencies:?}");
}

#[test]
fn rust_version_prints_the_version_of_cargo_toml() {
    let version = ok(&root(), "just", &["rust::version"]);
    assert_eq!(version.trim(), env!("CARGO_PKG_VERSION"));
}

#[test]
fn release_check_fails_when_cargo_toml_is_below_the_bump() {
    let temp = scratch("0.1.0");
    let repo = temp.path().join("repo");
    commit(&repo, "fix: a bug");
    let output = run(&repo, "just", &["release-check"]);
    assert!(
        !output.status.success(),
        "release-check passed with 0.1.0 after a fix"
    );
    assert!(String::from_utf8_lossy(&output.stderr).contains("the version must be at least 0.1.1"));
    set_version(&repo, "0.1.1");
    commit(&repo, "chore: release 0.1.1");
    assert!(ok(&repo, "just", &["release-check"]).contains("the next tag is v0.1.1"));
}

#[test]
fn release_tags_the_version_of_cargo_toml() {
    let temp = scratch("0.1.0");
    let repo = temp.path().join("repo");
    set_version(&repo, "0.3.0");
    commit(&repo, "fix: a bug");
    assert!(ok(&repo, "just", &["release", "--dry-run"]).contains("next tag: v0.3.0"));
    assert!(ok(&repo, "just", &["release"]).contains("tagged v0.3.0"));
    let tags = ok(&repo, "git", &["ls-remote", "--tags", "origin"]);
    assert!(tags.contains("refs/tags/v0.3.0"), "{tags}");
    assert!(ok(&repo, "just", &["release"]).contains("no release"));
}

#[test]
fn only_the_jobs_release_and_publish_can_write() {
    let workflow = root().join(".github/workflows/ci.yml");
    let text = fs::read_to_string(workflow).expect("read ci.yml");
    let flow: Value = serde_yaml::from_str(&text).expect("yaml");
    assert_eq!(flow["permissions"], serde_json::json!({"contents": "read"}));
    for (name, job) in flow["jobs"].as_object().expect("jobs") {
        let write = job["permissions"]["contents"] == "write";
        assert_eq!(
            write,
            name == "release" || name == "publish",
            "the job {name}"
        );
    }
    let release = &flow["jobs"]["release"];
    assert_eq!(release["needs"], "verify");
    let condition = release["if"].as_str().expect("if");
    assert!(
        condition.contains("github.event_name == 'push'") && condition.contains("refs/heads/main")
    );
    let steps = release["steps"].as_array().expect("steps");
    assert_eq!(steps[0]["with"]["fetch-depth"], 0);
    assert_eq!(steps.last().expect("step")["run"], "just release");
    // The jobs binaries and publish run after the job release, on a push to main, and find the tag of HEAD.
    let binaries = &flow["jobs"]["binaries"];
    let publish = &flow["jobs"]["publish"];
    assert_eq!(binaries["needs"], "release");
    assert_eq!(publish["needs"], "binaries");
    for job in [binaries, publish] {
        assert_eq!(job["if"], release["if"]);
        let steps = job["steps"].as_array().expect("steps");
        assert_eq!(steps[0]["with"]["fetch-depth"], 0);
        assert_eq!(steps[0]["with"]["fetch-tags"], true);
        assert!(
            steps[1]["run"]
                .as_str()
                .expect("run")
                .contains("git tag --points-at HEAD")
        );
        // With no tag, each step after the checkout and the tag step is skipped.
        for step in &steps[2..] {
            assert_eq!(
                step["if"]
                    .as_str()
                    .map(|s| s.starts_with("steps.tag.outputs.tag != ''")),
                Some(true),
                "{step}"
            );
        }
    }
    let targets: Vec<(&str, &str)> = binaries["strategy"]["matrix"]["include"]
        .as_array()
        .expect("include")
        .iter()
        .map(|leg| {
            (
                leg["runner"].as_str().expect("runner"),
                leg["target"].as_str().expect("target"),
            )
        })
        .collect();
    assert_eq!(
        targets,
        [
            ("macos-15", "aarch64-apple-darwin"),
            ("macos-15", "x86_64-apple-darwin"),
            ("ubuntu-24.04", "x86_64-unknown-linux-musl"),
            ("ubuntu-24.04-arm", "aarch64-unknown-linux-musl"),
        ]
    );
    let steps = binaries["steps"].as_array().expect("steps");
    assert!(
        steps
            .iter()
            .any(|step| step["run"] == "just dist ${{ matrix.target }}")
    );
    // Each binary is checked before it is published: run, or its architecture, or that it is static.
    let runs: Vec<&str> = steps
        .iter()
        .filter_map(|step| step["run"].as_str())
        .collect();
    // The x86_64 musl build is a static PIE, which file names "static-pie linked", so the check takes both forms.
    for check in [
        "release/jagt --version",
        "lipo -archs",
        "grep -Eq 'statically linked|static-pie linked'",
    ] {
        assert!(runs.iter().any(|run| run.contains(check)), "{check}");
    }
    let upload = publish["steps"]
        .as_array()
        .expect("steps")
        .last()
        .expect("step")["run"]
        .as_str()
        .expect("run")
        .to_owned();
    // A new release gets its notes from the CHANGELOG, and its assets in the same call.
    assert!(upload.contains("gh release create \"$TAG\" dist/* --verify-tag"));
    assert!(upload.contains("CHANGELOG.md"));
    let verify = flow["jobs"]["verify"]["steps"].as_array().expect("steps");
    assert_eq!(verify[0]["with"]["fetch-depth"], 0);
    assert!(
        verify
            .iter()
            .any(|step| step["run"] == "just release-check")
    );
}

#[test]
fn the_installer_of_jnterfaces_can_read_the_stack_record() {
    // install_stack.py reads the keys version, choices and profiles of .agents/stack.json, and stops without choices.
    let text = fs::read_to_string(root().join(".agents/stack.json")).expect("read");
    let record: Value = serde_json::from_str(&text).expect("json");
    assert_eq!(record["version"], 2);
    assert!(record["choices"].is_object());
    assert_eq!(record["profiles"], serde_json::json!(["rust"]));
}

#[test]
fn the_tests_ignore_the_git_repository_of_a_hook() {
    // A pre-commit hook sets GIT_INDEX_FILE. The scratch repository must still use its own index.
    let temp = TempDir::new().expect("tempdir");
    ok(temp.path(), "git", &["init", "-q", "-b", "main"]);
    let bogus = temp.path().join("bogus-index");
    // Each test spawns its programs through run(), which removes the variable, so setting it here changes no other
    // test.
    unsafe { std::env::set_var("GIT_INDEX_FILE", &bogus) };
    fs::write(temp.path().join("a"), "a").expect("write");
    ok(temp.path(), "git", &["add", "a"]);
    unsafe { std::env::remove_var("GIT_INDEX_FILE") };
    assert!(!bogus.exists(), "git add used GIT_INDEX_FILE");
    assert!(temp.path().join(".git/index").exists());
}
