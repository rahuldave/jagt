//! These tests check the release tags of jagt, as in cx. They check these facts:
//!
//! - `just check` runs `release-check`.
//! - The tag is `v` and the version of `Cargo.toml`.
//! - Only the jobs `release` and `publish` of CI can write to the repository.
//!
//! The recipes `release` and `release-check` come from the tasker role of `agent_gest_git_skills`. The recipe
//! `rust::version` comes from the rust profile. `just install` puts the recipes of both in `.agents`. The tests need
//! `git`, `just`, `uv` and `jlog` on the `PATH`.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use serde_json::Value;
use sha2::{Digest, Sha256};
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
        // The scratch repository logs its own run of jlog, not the run of the just check that runs the tests.
        .env_remove("JLOG_RUN")
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

/// `RELEASE_FILES` names the files that `just release` and `just release-check` read, apart from the recipes in
/// `.agents/just`, which `scratch` copies with `copy_tree`.
const RELEASE_FILES: [&str; 5] = [
    "Justfile",
    ".gitignore",
    ".agents/install.just",
    ".agents/stack.json",
    ".agents/skills/gpa/scripts/release_tag.py",
];

/// Copy the folder `from`, with each file and folder in it, to the folder `to`.
fn copy_tree(from: &Path, to: &Path) {
    fs::create_dir_all(to).expect("mkdir");
    for entry in fs::read_dir(from).expect("read_dir") {
        let entry = entry.expect("entry");
        let target = to.join(entry.file_name());
        if entry.file_type().expect("file type").is_dir() {
            copy_tree(&entry.path(), &target);
        } else {
            fs::copy(entry.path(), target).expect("copy");
        }
    }
}

/// Make a scratch repository with the release files of jagt, `Cargo.toml` at `version`, a bare remote and the tag
/// `v0.1.0`.
fn scratch(version: &str) -> TempDir {
    let temp = TempDir::new().expect("tempdir");
    let repo = temp.path().join("repo");
    for file in RELEASE_FILES {
        let target = repo.join(file);
        fs::create_dir_all(target.parent().expect("parent")).expect("mkdir");
        fs::copy(root().join(file), target).expect("copy");
    }
    copy_tree(&root().join(".agents/just"), &repo.join(".agents/just"));
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

/// Return the JSON of `just --dump`, which holds each recipe of the `Justfile` and of the files that it imports.
fn dump() -> Value {
    serde_json::from_str(&ok(&root(), "just", &["--dump", "--dump-format", "json"])).expect("json")
}

/// Return the names of the dependencies of the recipe `recipe` in `dump`, in order.
fn dependencies<'a>(dump: &'a Value, recipe: &str) -> Vec<&'a str> {
    dump["recipes"][recipe]["dependencies"]
        .as_array()
        .unwrap_or_else(|| panic!("no recipe {recipe}"))
        .iter()
        .map(|dependency| dependency["recipe"].as_str().expect("name"))
        .collect()
}

/// Return the text of the body of the recipe `recipe` in `dump`.
///
/// The text joins the parts of each line that are text, and drops the other parts.
fn body(dump: &Value, recipe: &str) -> String {
    dump["recipes"][recipe]["body"]
        .as_array()
        .unwrap_or_else(|| panic!("no recipe {recipe}"))
        .iter()
        .flat_map(|line| line.as_array().expect("line").iter())
        .filter_map(|part| part.as_str())
        .collect()
}

#[test]
fn release_comes_from_the_tasker_role() {
    // jagt keeps no copy of the script or of the module rust. A copy would clash with the files of just install.
    for file in [
        "scripts/release_tag.py",
        "scripts/rust.just",
        "scripts/cargo_version.py",
    ] {
        assert!(!root().join(file).exists(), "{file} is back");
    }
    let justfile = fs::read_to_string(root().join("Justfile")).expect("read");
    for line in justfile.lines() {
        let name = line.split([' ', ':']).next().unwrap_or("");
        assert!(
            !["release", "release-check", "check", "mod", "set"].contains(&name),
            "the Justfile has {line:?}, which the tasker role, the rust profile or the index gives"
        );
    }
    let dump = dump();
    for recipe in ["release", "release-check"] {
        assert!(
            body(&dump, recipe).contains(".agents/skills/gpa/scripts/release_tag.py"),
            "{recipe} does not run the script of the tasker role"
        );
    }
    // The script is the file that the install of the tasker role recorded, with no edit.
    let record: Value = serde_json::from_str(
        &fs::read_to_string(root().join(".agents/gest-git-install.json")).expect("read"),
    )
    .expect("json");
    let recorded = record["managed_files"][".agents/skills/gpa/scripts/release_tag.py"]
        .as_str()
        .expect("the record of the tasker role has no release_tag.py");
    let script = fs::read(root().join(".agents/skills/gpa/scripts/release_tag.py")).expect("read");
    let actual: String = Sha256::digest(&script)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect();
    assert_eq!(actual, recorded);
}

#[test]
fn check_runs_release_check_and_the_steps_of_the_profile() {
    // just check is the check of the index of jnterfaces. It runs the steps of the rust profile and of the roles.
    let dump = dump();
    let check = dependencies(&dump, "check");
    for step in [
        "release-check",
        "fmt-check",
        "lint",
        "typecheck",
        "test",
        "integration",
        "prose-check",
        "diff-check",
    ] {
        assert!(check.contains(&step), "{step}: {check:?}");
    }
}

#[test]
fn verify_runs_the_quick_checks_the_tests_and_the_demo() {
    // CI runs just verify, so verify runs the tests in tests/ through the step integration of the rust profile, and
    // the protocol demo against the binary that build makes.
    let dump = dump();
    assert_eq!(
        dependencies(&dump, "verify"),
        [
            "fmt-check",
            "lint",
            "typecheck",
            "build",
            "test",
            "integration",
            "smoke",
            "protocol-demo",
            "installed-recipes",
            "diff-check"
        ]
    );
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
    // ci.yml has the only job that tags. The tasker role writes a starter release.yml once, and its job would tag each
    // release a second time.
    assert!(!root().join(".github/workflows/release.yml").exists());
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

#[test]
fn each_job_that_runs_just_installs_jlog_first() {
    // The index of jnterfaces sets jlog as the shell of each recipe, also of the recipes of the Justfile. So each job
    // of each workflow installs jlog before its first step that runs just.
    let mut paths: Vec<PathBuf> = fs::read_dir(root().join(".github/workflows"))
        .expect("read_dir")
        .map(|entry| entry.expect("entry").path())
        .filter(|path| {
            path.extension()
                .is_some_and(|ext| ext == "yml" || ext == "yaml")
        })
        .collect();
    paths.sort();
    let mut checked = 0;
    for path in &paths {
        let flow: Value =
            serde_yaml::from_str(&fs::read_to_string(path).expect("read")).expect("yaml");
        for (name, job) in flow["jobs"].as_object().expect("jobs") {
            let runs: Vec<&str> = job["steps"]
                .as_array()
                .map(|steps| {
                    steps
                        .iter()
                        .map(|step| step["run"].as_str().unwrap_or(""))
                        .collect()
                })
                .unwrap_or_default();
            let Some(just) = runs.iter().position(|run| {
                run.lines()
                    .any(|line| line.trim_start().starts_with("just "))
            }) else {
                continue;
            };
            let jlog = runs
                .iter()
                .position(|run| run.contains("rahuldave/jlog/v0.3.0/scripts/install.sh"));
            assert!(
                jlog.is_some_and(|jlog| jlog < just),
                "the job {name} of {} runs just before it installs jlog",
                path.display()
            );
            checked += 1;
        }
    }
    // The jobs verify, release and binaries of ci.yml, and ci of check.yml.
    assert_eq!(checked, 4);
}

#[test]
fn git_ignores_the_python_caches_of_the_stack() {
    // The record hook imports agentic_target, and Python writes a cache next to it. The commit gate compares the
    // commit tree with the worktree tree, so an untracked cache would stop every commit.
    for path in [
        ".agents/skills/gcm/scripts/__pycache__/agentic_target.cpython-312.pyc",
        ".agents/just/rust/__pycache__/steps.cpython-312.pyc",
    ] {
        ok(&root(), "git", &["check-ignore", "-q", "--no-index", path]);
    }
}

#[test]
fn installed_recipes_checks_each_file_and_module_of_the_profile() {
    // rust.just loads the files of .agents/just/rust with import?, so a missing one drops its recipes with no error.
    // installed-recipes checks that git tracks each one, and that each recipe of the module loads.
    let dump = dump();
    let text = body(&dump, "installed-recipes");
    let tracked = ok(&root(), "git", &["ls-files", ".agents/just"]);
    for file in tracked
        .lines()
        .filter(|file| file.ends_with(".just") || file.ends_with("steps.py"))
        .filter(|file| {
            !file.contains("/rust/api") && !file.contains("docstring") && !file.contains("toml")
        })
    {
        assert!(
            text.contains(file),
            "installed-recipes does not check {file}"
        );
    }
    for recipe in [
        "rust::version",
        "rust::fmt-check",
        "rust::lint",
        "rust::typecheck",
        "rust::test",
        "rust::integration",
        "prose-check",
    ] {
        assert!(
            text.contains(recipe),
            "installed-recipes does not check {recipe}"
        );
    }
}
