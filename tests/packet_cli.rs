//! Labs for the packet file and the layers of `jagt render`.
//!
//! Each lab makes a temporary git repository, and some add a linked worktree.
//! git runs with no global or system config, so the config of this machine
//! cannot change a result.

use assert_cmd::Command;
use predicates::prelude::*;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command as StdCommand;
use tempfile::{TempDir, tempdir};

/// Sets the environment that keeps git away from the config of the machine.
fn isolate(command: &mut StdCommand) -> &mut StdCommand {
    command
        .env("GIT_CONFIG_GLOBAL", "/dev/null")
        .env("GIT_CONFIG_NOSYSTEM", "1")
        .env_remove("GIT_INDEX_FILE")
        .env_remove("GIT_DIR")
        .env_remove("GIT_WORK_TREE")
}

/// Runs git in `dir`, checks that it worked, and returns its stdout.
fn git(dir: &Path, args: &[&str]) -> String {
    git_env(dir, args, &[])
}

fn git_env(dir: &Path, args: &[&str], env: &[(&str, &Path)]) -> String {
    let mut command = StdCommand::new("git");
    isolate(&mut command).arg("-C").arg(dir).args(args);
    for (key, value) in env {
        command.env(key, value);
    }
    let output = command.output().expect("git runs");
    assert!(
        output.status.success(),
        "git {args:?} failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    String::from_utf8(output.stdout).expect("utf8")
}

/// A lab: a temporary folder that holds the main checkout, `main/`.
struct Lab {
    _dir: TempDir,
    root: PathBuf,
    main: PathBuf,
}

impl Lab {
    /// A repository with one commit, which holds `README.md` and a
    /// `.gitignore` that ignores `*.ignored`.
    fn new() -> Self {
        let lab = Self::unborn();
        write(&lab.main, "README.md", "hello\n");
        write(&lab.main, ".gitignore", "*.ignored\n");
        git(&lab.main, &["add", "-A"]);
        git(&lab.main, &["commit", "-q", "-m", "first"]);
        lab
    }

    /// A repository with no commit yet.
    fn unborn() -> Self {
        let dir = tempdir().expect("tempdir");
        let root = dir.path().canonicalize().expect("canonical");
        let main = root.join("main");
        fs::create_dir(&main).expect("main folder");
        git(&main, &["init", "-q", "-b", "main"]);
        git(&main, &["config", "user.name", "Lab"]);
        git(&main, &["config", "user.email", "lab@example.invalid"]);
        Self {
            _dir: dir,
            root,
            main,
        }
    }

    /// Adds a linked worktree at `<root>/<name>` on a new branch.
    fn add_worktree(&self, name: &str) -> PathBuf {
        let path = self.root.join(name);
        git(
            &self.main,
            &[
                "worktree",
                "add",
                "-q",
                "-b",
                name,
                path.to_str().expect("utf8 path"),
            ],
        );
        path
    }

    fn packets_dir(&self) -> PathBuf {
        self.main.join(".agents/log/packets")
    }

    fn packet_files(&self) -> Vec<PathBuf> {
        let Ok(entries) = fs::read_dir(self.packets_dir()) else {
            return Vec::new();
        };
        let mut files: Vec<PathBuf> = entries
            .map(|entry| entry.expect("entry").path())
            .filter(|path| path.extension().is_some_and(|ext| ext == "json"))
            .collect();
        files.sort();
        files
    }
}

fn write(dir: &Path, relative: &str, text: &str) {
    let path = dir.join(relative);
    fs::create_dir_all(path.parent().expect("parent")).expect("folders");
    fs::write(path, text).expect("write");
}

fn jagt(cwd: &Path) -> Command {
    let mut command = Command::cargo_bin("jagt").expect("binary exists");
    command
        .current_dir(cwd)
        .env("GIT_CONFIG_GLOBAL", "/dev/null")
        .env("GIT_CONFIG_NOSYSTEM", "1")
        .env_remove("GIT_INDEX_FILE")
        .env_remove("GIT_DIR")
        .env_remove("GIT_WORK_TREE");
    command
}

/// Runs `jagt render <target> --no-config --prompt-text <base>` and returns
/// its stdout.
fn render(cwd: &Path, target: &str, base: Option<&str>, extra: &[&str]) -> String {
    let mut command = jagt(cwd);
    command.args(["render", target, "--no-config"]);
    if let Some(base) = base {
        command.args(["--prompt-text", base]);
    }
    command.args(extra);
    let output = command.output().expect("jagt runs");
    assert!(
        output.status.success(),
        "render failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    String::from_utf8(output.stdout).expect("utf8")
}

/// The value of the top-level `nonce:` field of a packet, if any.
fn nonce_of(text: &str) -> Option<String> {
    text.lines()
        .find_map(|line| line.strip_prefix("nonce: "))
        .map(str::to_string)
}

fn read_json(path: &Path) -> Value {
    serde_json::from_str(&fs::read_to_string(path).expect("packet file")).expect("json")
}

fn sha256_hex(text: &str) -> String {
    Sha256::digest(text.as_bytes())
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

/// The worktree tree, computed the way the spec says, apart from jagt.
fn expected_tree(worktree: &Path) -> String {
    let scratch = tempdir().expect("tempdir");
    let index = scratch.path().join("index");
    let env = [("GIT_INDEX_FILE", index.as_path())];
    let has_head = {
        let mut command = StdCommand::new("git");
        isolate(&mut command).arg("-C").arg(worktree).args([
            "rev-parse",
            "--verify",
            "--quiet",
            "HEAD",
        ]);
        command.output().expect("git").status.success()
    };
    if has_head {
        git_env(worktree, &["read-tree", "HEAD"], &env);
    }
    git_env(worktree, &["add", "-A"], &env);
    git_env(worktree, &["write-tree"], &env).trim().to_string()
}

#[test]
fn render_saves_the_packet_file_with_the_nonce_target_tree_worktree_and_hash() {
    let lab = Lab::new();
    let text = render(&lab.main, "review", Some("Review the change."), &[]);

    let nonce = nonce_of(&text).expect("the packet text holds a nonce");
    assert_eq!(nonce.len(), 32);
    assert!(
        nonce
            .bytes()
            .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
    );

    let files = lab.packet_files();
    assert_eq!(files, vec![lab.packets_dir().join(format!("{nonce}.json"))]);
    let record = read_json(&files[0]);
    assert_eq!(record["version"], 1);
    assert_eq!(record["nonce"], nonce.as_str());
    assert_eq!(record["target"], "review");
    assert_eq!(record["worktree"], lab.main.to_str().expect("utf8"));
    assert_eq!(record["input_tree"], expected_tree(&lab.main).as_str());
    assert_eq!(record["packet_sha256"], sha256_hex(&text).as_str());
    let keys: Vec<&String> = record.as_object().expect("object").keys().collect();
    assert_eq!(
        keys.len(),
        6,
        "the packet file holds only its six fields: {keys:?}"
    );
}

#[test]
fn rendered_packet_with_a_nonce_lints_and_explain_shows_the_nonce() {
    let lab = Lab::new();
    let text = render(&lab.main, "review", Some("Review the change."), &[]);
    let nonce = nonce_of(&text).expect("nonce");

    jagt(&lab.main)
        .args(["lint", "--expect-count", "1"])
        .write_stdin(text.clone())
        .assert()
        .success();
    jagt(&lab.main)
        .args(["explain", "task"])
        .write_stdin(text)
        .assert()
        .success()
        .stdout(predicate::str::contains(format!("nonce: {nonce}\n")));
}

#[test]
fn lint_rejects_a_packet_whose_nonce_has_another_form() {
    let lab = Lab::new();
    let text = render(&lab.main, "review", Some("Review the change."), &[]);
    let nonce = nonce_of(&text).expect("nonce");
    for bad in ["not-a-nonce", &nonce.to_uppercase(), "[]"] {
        let broken = text.replace(&format!("nonce: {nonce}"), &format!("nonce: {bad}"));
        jagt(&lab.main)
            .arg("lint")
            .write_stdin(broken)
            .assert()
            .failure()
            .stderr(predicate::str::contains("nonce"));
    }
}

#[test]
fn each_render_draws_a_new_nonce_and_a_new_file() {
    let lab = Lab::new();
    let first = render(&lab.main, "review", Some("Review."), &[]);
    let second = render(&lab.main, "review", Some("Review."), &[]);
    assert_ne!(nonce_of(&first), nonce_of(&second));
    assert_eq!(lab.packet_files().len(), 2);
}

#[test]
fn the_input_tree_holds_unstaged_and_untracked_files_but_not_ignored_ones() {
    let lab = Lab::new();
    let clean_tree = expected_tree(&lab.main);
    write(&lab.main, "README.md", "changed, not staged\n");
    write(&lab.main, "new.txt", "untracked\n");
    write(&lab.main, "secret.ignored", "ignored\n");
    let index_before = fs::read(lab.main.join(".git/index")).expect("index");

    let text = render(&lab.main, "review", Some("Review."), &[]);
    let record = read_json(&lab.packet_files()[0]);
    let tree = record["input_tree"].as_str().expect("tree").to_string();

    assert_ne!(tree, clean_tree);
    assert_eq!(tree, expected_tree(&lab.main));
    let listing = git(&lab.main, &["ls-tree", "-r", "--name-only", &tree]);
    assert!(listing.contains("new.txt"), "{listing}");
    assert!(!listing.contains("secret.ignored"), "{listing}");
    assert!(
        !listing.contains(".agents/log"),
        "the log folder is not in the tree: {listing}"
    );
    assert_eq!(
        fs::read(lab.main.join(".git/index")).expect("index"),
        index_before,
        "the real index does not change"
    );
    assert!(nonce_of(&text).is_some());
}

#[test]
fn a_git_index_file_from_the_caller_does_not_change_the_tree() {
    let lab = Lab::new();
    write(&lab.main, "new.txt", "untracked\n");
    let stray = lab.root.join("stray-index");
    let output = jagt(&lab.main)
        .args([
            "render",
            "review",
            "--no-config",
            "--prompt-text",
            "Review.",
        ])
        .env("GIT_INDEX_FILE", &stray)
        .output()
        .expect("jagt runs");
    assert!(output.status.success());
    let record = read_json(&lab.packet_files()[0]);
    assert_eq!(record["input_tree"], expected_tree(&lab.main).as_str());
    assert!(!stray.exists(), "jagt does not write the caller's index");
}

#[test]
fn render_works_before_the_first_commit() {
    let lab = Lab::unborn();
    write(&lab.main, "a.txt", "a\n");
    render(&lab.main, "review", Some("Review."), &[]);
    let record = read_json(&lab.packet_files()[0]);
    assert_eq!(record["input_tree"], expected_tree(&lab.main).as_str());
}

#[test]
fn the_log_folder_has_a_gitignore_so_git_never_sees_the_packets() {
    let lab = Lab::new();
    render(&lab.main, "review", Some("Review."), &[]);
    assert_eq!(
        fs::read_to_string(lab.main.join(".agents/log/.gitignore")).expect("gitignore"),
        "*\n"
    );
    assert_eq!(git(&lab.main, &["status", "--porcelain"]), "");
}

#[test]
fn an_existing_log_gitignore_is_kept() {
    let lab = Lab::new();
    write(&lab.main, ".agents/log/.gitignore", "*\n# from jlog\n");
    render(&lab.main, "review", Some("Review."), &[]);
    assert_eq!(
        fs::read_to_string(lab.main.join(".agents/log/.gitignore")).expect("gitignore"),
        "*\n# from jlog\n"
    );
}

#[test]
fn a_linked_worktree_saves_its_packet_in_the_shared_log_folder() {
    let lab = Lab::new();
    let linked = lab.add_worktree("feature");
    write(&linked, "feature.txt", "work in the linked worktree\n");
    write(&linked, "sub/deeper/x.txt", "x\n");

    // From a subfolder too: jagt finds the top of the worktree.
    let text = render(&linked.join("sub/deeper"), "review", Some("Review."), &[]);
    let nonce = nonce_of(&text).expect("nonce");

    let files = lab.packet_files();
    assert_eq!(files, vec![lab.packets_dir().join(format!("{nonce}.json"))]);
    assert!(
        !linked.join(".agents/log").exists(),
        "the linked worktree has no log folder of its own"
    );
    let record = read_json(&files[0]);
    assert_eq!(record["worktree"], linked.to_str().expect("utf8"));
    assert_eq!(record["input_tree"], expected_tree(&linked).as_str());
    assert_ne!(record["input_tree"], expected_tree(&lab.main).as_str());
}

#[test]
fn a_worktree_of_a_bare_repository_is_an_error() {
    let lab = Lab::new();
    let bare = lab.root.join("bare.git");
    git(
        &lab.root,
        &[
            "clone",
            "-q",
            "--bare",
            lab.main.to_str().expect("utf8"),
            bare.to_str().expect("utf8"),
        ],
    );
    let linked = lab.root.join("from-bare");
    git(
        &bare,
        &[
            "worktree",
            "add",
            "-q",
            linked.to_str().expect("utf8"),
            "main",
        ],
    );
    jagt(&linked)
        .args([
            "render",
            "review",
            "--no-config",
            "--prompt-text",
            "Review.",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("bare"));
}

#[test]
fn no_save_renders_without_a_nonce_or_a_file() {
    let lab = Lab::new();
    let text = render(&lab.main, "review", Some("Review."), &["--no-save"]);
    assert_eq!(nonce_of(&text), None);
    assert!(lab.packet_files().is_empty());
    assert!(!lab.main.join(".agents/log").exists());
}

#[test]
fn outside_a_git_worktree_render_warns_and_saves_nothing() {
    let dir = tempdir().expect("tempdir");
    let output = jagt(dir.path())
        .args([
            "render",
            "review",
            "--no-config",
            "--prompt-text",
            "Review.",
        ])
        .output()
        .expect("jagt runs");
    assert!(output.status.success());
    let text = String::from_utf8(output.stdout).expect("utf8");
    assert_eq!(nonce_of(&text), None);
    assert!(String::from_utf8_lossy(&output.stderr).contains("not in a git worktree"));
    assert!(!dir.path().join(".agents").exists());
}

#[test]
fn the_docs_packet_of_a_python_project_holds_the_python_language_layer() {
    let lab = Lab::new();
    write(
        &lab.main,
        ".agents/stack.json",
        r#"{"version": 1, "profiles": ["python"]}"#,
    );
    write(
        &lab.main,
        ".agents/targets/python/docs.md",
        "Write docments for each argument.\n",
    );
    write(
        &lab.main,
        ".agents/targets/typescript/docs.md",
        "Write JSDoc for each function.\n",
    );
    write(
        &lab.main,
        ".agents/targets/docs.md",
        "This repository has user docs and a change log.\n",
    );

    let text = render(
        &lab.main,
        "docs",
        Some("Find the docs that the change affects."),
        &[],
    );

    let base = text.find("Find the docs").expect("base task");
    let python = text.find("Write docments").expect("Python language layer");
    let repo = text
        .find("user docs and a change log")
        .expect("repository text");
    assert!(
        base < python && python < repo,
        "the layers keep their order"
    );
    assert!(!text.contains("JSDoc"), "only the languages of the stack");
    assert!(text.contains(
        "  layers:\n    - base task\n    - 'language layer: .agents/targets/python/docs.md'\n    - 'repository text: .agents/targets/docs.md'\n"
    ), "{text}");
    jagt(&lab.main)
        .arg("lint")
        .write_stdin(text.clone())
        .assert()
        .success();

    // The hash covers the joined text.
    let record = read_json(&lab.packet_files()[0]);
    assert_eq!(record["packet_sha256"], sha256_hex(&text).as_str());
}

#[test]
fn language_layers_follow_the_order_of_the_profiles() {
    let lab = Lab::new();
    write(
        &lab.main,
        ".agents/stack.json",
        r#"{"profiles": ["typescript", "python", "typescript"]}"#,
    );
    write(&lab.main, ".agents/targets/python/review.md", "PY\n");
    write(&lab.main, ".agents/targets/typescript/review.md", "TS\n");
    let text = render(&lab.main, "review", Some("BASE"), &[]);
    let prompt = text
        .split("prompt: |\n")
        .nth(1)
        .and_then(|rest| rest.split("\ninputs:").next())
        .expect("prompt");
    assert_eq!(prompt, "  BASE\n\n  TS\n\n  PY");
}

#[test]
fn a_missing_layer_is_not_an_error() {
    let lab = Lab::new();
    // No stack.json, no language layer, no repository text.
    let text = render(&lab.main, "review", Some("Only the base."), &[]);
    assert!(
        text.contains("prompt: |\n  Only the base.\ninputs:"),
        "{text}"
    );

    // A profile with no file of its own, and an empty repository text.
    write(&lab.main, ".agents/stack.json", r#"{"profiles": ["rust"]}"#);
    write(&lab.main, ".agents/targets/review.md", "\n\n");
    let text = render(&lab.main, "review", Some("Only the base."), &[]);
    assert!(
        text.contains("prompt: |\n  Only the base.\ninputs:"),
        "{text}"
    );
}

#[test]
fn the_repository_text_alone_is_enough_without_a_base_task() {
    let lab = Lab::new();
    write(
        &lab.main,
        ".agents/targets/review.md",
        "Check each SQL migration.\n",
    );
    let text = render(&lab.main, "review", None, &[]);
    assert!(text.contains("Check each SQL migration."), "{text}");
}

#[test]
fn no_layer_at_all_is_an_error_and_saves_no_file() {
    let lab = Lab::new();
    jagt(&lab.main)
        .args(["render", "review", "--no-config"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("missing prompt text"));
    assert!(lab.packet_files().is_empty());
}

#[test]
fn a_profile_name_that_leaves_the_targets_folder_is_an_error() {
    let lab = Lab::new();
    write(&lab.main, ".agents/review.md", "OUTSIDE\n");
    for profiles in [r#"[".."]"#, r#"["a/b"]"#, r#"[1]"#, r#""python""#] {
        write(
            &lab.main,
            ".agents/stack.json",
            &format!(r#"{{"profiles": {profiles}}}"#),
        );
        jagt(&lab.main)
            .args([
                "render",
                "review",
                "--no-config",
                "--prompt-text",
                "Review.",
            ])
            .assert()
            .failure()
            .stderr(predicate::str::contains("stack.json"));
    }
    assert!(lab.packet_files().is_empty());
}

#[test]
fn a_linked_worktree_reads_its_own_layers() {
    let lab = Lab::new();
    write(&lab.main, ".agents/targets/review.md", "MAIN TEXT\n");
    git(&lab.main, &["add", "-A"]);
    git(&lab.main, &["commit", "-q", "-m", "targets"]);
    let linked = lab.add_worktree("feature");
    write(&linked, ".agents/targets/review.md", "LINKED TEXT\n");

    let text = render(&linked, "review", Some("Review."), &[]);
    assert!(text.contains("LINKED TEXT"));
    assert!(!text.contains("MAIN TEXT"));
}

const RESULT: &str = "\
<<<AGENT_RESULT v1>>>
target: review
NONCE_LINE
status: success
outputs: {}
verification:
  - name: checked
    status: passed
follow_up: []
<<<END_AGENT_RESULT>>>
";

fn result_with(nonce_line: &str) -> String {
    RESULT.replace("NONCE_LINE\n", nonce_line)
}

#[test]
fn result_lint_accepts_only_the_nonce_of_the_packet() {
    let lab = Lab::new();
    let text = render(&lab.main, "review", Some("Review."), &[]);
    let nonce = nonce_of(&text).expect("nonce");
    let other = "0".repeat(32);

    let lint = |result: String| {
        let mut command = jagt(&lab.main);
        command
            .args([
                "result",
                "lint",
                "--expect-target",
                "review",
                "--expect-nonce",
            ])
            .arg(&nonce)
            .write_stdin(result);
        command.assert()
    };

    lint(result_with(&format!("nonce: {nonce}\n"))).success();
    lint(result_with(&format!("nonce: {other}\n")))
        .failure()
        .stderr(predicate::str::contains("expected nonce"));
    lint(result_with(""))
        .failure()
        .stderr(predicate::str::contains("missing nonce"));
    lint(result_with(&format!("nonce: {nonce}\nnonce: {nonce}\n"))).failure();
}

// Tests for the findings of the adversarial review.

#[cfg(unix)]
fn symlink(target: &Path, link: &Path) {
    fs::create_dir_all(link.parent().expect("parent")).expect("folders");
    std::os::unix::fs::symlink(target, link).expect("symlink");
}

#[test]
fn a_symlinked_log_folder_stops_the_render_and_writes_nothing_outside() {
    for link in [".agents/log", ".agents", ".agents/log/packets"] {
        let lab = Lab::new();
        let victim = lab.root.join("victim");
        fs::create_dir(&victim).expect("victim");
        symlink(&victim, &lab.main.join(link));
        jagt(&lab.main)
            .args([
                "render",
                "review",
                "--no-config",
                "--prompt-text",
                "Review.",
            ])
            .assert()
            .failure()
            .stderr(predicate::str::contains("symlink"));
        assert_eq!(
            fs::read_dir(&victim).expect("victim").count(),
            0,
            "nothing is written through {link}"
        );
    }
}

#[test]
fn a_layer_symlink_that_leads_outside_the_worktree_is_an_error() {
    let lab = Lab::new();
    let secret = lab.root.join("creds");
    fs::write(&secret, "SECRET-TOKEN-xyz\n").expect("secret");
    symlink(&secret, &lab.main.join(".agents/targets/review.md"));
    let output = jagt(&lab.main)
        .args([
            "render",
            "review",
            "--no-config",
            "--prompt-text",
            "Review.",
        ])
        .output()
        .expect("jagt runs");
    assert!(!output.status.success());
    assert!(!String::from_utf8_lossy(&output.stdout).contains("SECRET"));
    assert!(String::from_utf8_lossy(&output.stderr).contains("leads outside"));
    assert!(lab.packet_files().is_empty());

    // The same for stack.json.
    let lab = Lab::new();
    let outside = lab.root.join("stack.json");
    fs::write(&outside, r#"{"profiles": []}"#).expect("outside");
    symlink(&outside, &lab.main.join(".agents/stack.json"));
    jagt(&lab.main)
        .args([
            "render",
            "review",
            "--no-config",
            "--prompt-text",
            "Review.",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("leads outside"));
}

#[test]
fn a_layer_symlink_inside_the_worktree_is_read() {
    let lab = Lab::new();
    write(
        &lab.main,
        ".agents/targets/shared/common.md",
        "SHARED TEXT\n",
    );
    symlink(
        Path::new("shared/common.md"),
        &lab.main.join(".agents/targets/review.md"),
    );
    let text = render(&lab.main, "review", Some("Review."), &[]);
    assert!(text.contains("SHARED TEXT"), "{text}");
}

#[test]
fn no_save_works_in_a_worktree_of_a_bare_repository_and_without_git() {
    let lab = Lab::new();
    let bare = lab.root.join("bare.git");
    git(
        &lab.root,
        &[
            "clone",
            "-q",
            "--bare",
            lab.main.to_str().expect("utf8"),
            bare.to_str().expect("utf8"),
        ],
    );
    let linked = lab.root.join("from-bare");
    git(
        &bare,
        &[
            "worktree",
            "add",
            "-q",
            linked.to_str().expect("utf8"),
            "main",
        ],
    );
    write(&linked, ".agents/targets/review.md", "LINKED TEXT\n");
    let text = render(&linked, "review", Some("Review."), &["--no-save"]);
    assert!(text.contains("LINKED TEXT"));
    assert_eq!(nonce_of(&text), None);

    // A PATH with no git in it.
    let empty = lab.root.join("empty-path");
    fs::create_dir(&empty).expect("empty");
    let dir = tempdir().expect("tempdir");
    jagt(dir.path())
        .env("PATH", &empty)
        .args([
            "render",
            "review",
            "--no-config",
            "--no-save",
            "--prompt-text",
            "Review.",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("Review."));
}

#[test]
fn an_inherited_git_dir_and_work_tree_do_not_change_the_worktree_or_the_tree() {
    let lab = Lab::new();
    write(&lab.main, "sub/file.txt", "in sub\n");
    write(&lab.main, ".agents/targets/review.md", "TOP TEXT\n");
    let sub = lab.main.join("sub");
    let output = jagt(&sub)
        .args([
            "render",
            "review",
            "--no-config",
            "--prompt-text",
            "Review.",
        ])
        .env("GIT_DIR", lab.main.join(".git"))
        .env("GIT_WORK_TREE", &sub)
        .output()
        .expect("jagt runs");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(String::from_utf8_lossy(&output.stdout).contains("TOP TEXT"));
    let record = read_json(&lab.packet_files()[0]);
    assert_eq!(record["worktree"], lab.main.to_str().expect("utf8"));
    assert_eq!(record["input_tree"], expected_tree(&lab.main).as_str());
}

#[test]
fn the_packet_tells_the_fresh_agent_to_return_the_nonce() {
    let lab = Lab::new();
    let text = render(&lab.main, "review", Some("Review."), &[]);
    let nonce = nonce_of(&text).expect("nonce");
    assert!(
        text.contains(&format!(
            "result_rules:\n  - 'Put the top-level field nonce: {nonce} in the AGENT_RESULT v1 block."
        )),
        "{text}"
    );
}

#[test]
fn a_layer_whose_first_line_is_indented_still_gives_a_valid_packet() {
    let lab = Lab::new();
    write(
        &lab.main,
        ".agents/targets/review.md",
        "    indented first line\nnext line\n",
    );
    let text = render(&lab.main, "review", None, &[]);
    assert!(
        text.contains("prompt: |2\n      indented first line\n  next line\n"),
        "{text}"
    );
    jagt(&lab.main)
        .arg("lint")
        .write_stdin(text)
        .assert()
        .success();
    assert_eq!(lab.packet_files().len(), 1);
}

#[test]
fn every_nonce_starts_with_a_letter() {
    let lab = Lab::new();
    for _ in 0..20 {
        let text = render(&lab.main, "review", Some("Review."), &[]);
        let nonce = nonce_of(&text).expect("nonce");
        assert!(matches!(nonce.as_bytes()[0], b'a'..=b'f'), "{nonce}");
    }
}

#[test]
fn expect_nonce_rejects_an_argument_that_is_not_a_nonce() {
    let lab = Lab::new();
    for bad in ["", "12345678901234567890123456789012", "xyz"] {
        jagt(&lab.main)
            .args(["result", "lint", "--expect-nonce", bad])
            .write_stdin(result_with(&format!("nonce: \"{bad}\"\n")))
            .assert()
            .failure()
            .stderr(predicate::str::contains("invalid expected nonce"));
    }
}

#[test]
fn a_broken_pipe_on_stdout_leaves_no_packet_file() {
    let lab = Lab::new();
    let jagt_bin = PathBuf::from(env!("CARGO_BIN_EXE_jagt"));
    // The reader `:` exits at once. jagt runs git before it writes, so the
    // pipe is closed when it writes the packet.
    let mut command = StdCommand::new("bash");
    isolate(&mut command)
        .current_dir(&lab.main)
        .arg("-c")
        .arg(r#""$0" render review --no-config --prompt-text Review. | :; exit "${PIPESTATUS[0]}""#)
        .arg(&jagt_bin);
    let output = command.output().expect("bash runs");
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("io error"));
    assert!(lab.packet_files().is_empty(), "{:?}", lab.packet_files());
}

#[test]
fn packets_stay_out_of_the_tree_when_the_log_gitignore_lacks_a_star() {
    let lab = Lab::new();
    write(&lab.main, ".agents/log/.gitignore", "just.jsonl\n");
    git(&lab.main, &["add", "-A"]);
    git(&lab.main, &["commit", "-q", "-m", "an old log gitignore"]);
    render(&lab.main, "review", Some("Review."), &[]);
    render(&lab.main, "review", Some("Review."), &[]);
    let records: Vec<Value> = lab
        .packet_files()
        .iter()
        .filter(|path| path.extension().is_some_and(|ext| ext == "json"))
        .map(|path| read_json(path))
        .collect();
    assert_eq!(records.len(), 2);
    assert_eq!(
        records[0]["input_tree"], records[1]["input_tree"],
        "the first packet file is not in the tree of the second"
    );
    assert_eq!(
        fs::read_to_string(lab.packets_dir().join(".gitignore")).expect("gitignore"),
        "*\n"
    );
}

#[test]
fn a_layer_symlink_to_a_secret_inside_the_worktree_is_an_error() {
    for target in ["../../.env", "../../.git/config", "../stack.json"] {
        let lab = Lab::new();
        write(&lab.main, ".env", "API_KEY=zzz\n");
        write(&lab.main, ".agents/stack.json", r#"{"profiles": []}"#);
        symlink(
            Path::new(target),
            &lab.main.join(".agents/targets/review.md"),
        );
        let output = jagt(&lab.main)
            .args([
                "render",
                "review",
                "--no-config",
                "--prompt-text",
                "Review.",
            ])
            .output()
            .expect("jagt runs");
        assert!(!output.status.success(), "{target}");
        assert!(!String::from_utf8_lossy(&output.stdout).contains("API_KEY"));
        assert!(String::from_utf8_lossy(&output.stderr).contains("leads outside"));
    }

    // stack.json must be the file itself.
    let lab = Lab::new();
    write(&lab.main, "other.json", r#"{"profiles": []}"#);
    symlink(
        Path::new("../other.json"),
        &lab.main.join(".agents/stack.json"),
    );
    jagt(&lab.main)
        .args([
            "render",
            "review",
            "--no-config",
            "--prompt-text",
            "Review.",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("leads outside"));
}

#[test]
fn leading_lines_of_spaces_still_give_a_valid_packet() {
    let dir = tempdir().expect("tempdir");
    for outside_git in [true, false] {
        let lab = Lab::new();
        let cwd = if outside_git {
            dir.path()
        } else {
            lab.main.as_path()
        };
        let output = jagt(cwd)
            .args([
                "render",
                "review",
                "--no-config",
                "--prompt-text",
                "        \nx\n  y",
            ])
            .output()
            .expect("jagt runs");
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        let text = String::from_utf8(output.stdout).expect("utf8");
        assert!(text.contains("prompt: |\n\n  x\n    y\n"), "{text}");
        jagt(cwd).arg("lint").write_stdin(text).assert().success();
    }
}

#[test]
fn without_git_on_the_path_render_warns_and_prints_the_text() {
    let dir = tempdir().expect("tempdir");
    let empty = dir.path().join("empty-path");
    fs::create_dir(&empty).expect("empty");
    let output = jagt(dir.path())
        .env("PATH", &empty)
        .args([
            "render",
            "review",
            "--no-config",
            "--prompt-text",
            "Review.",
        ])
        .output()
        .expect("jagt runs");
    assert!(output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("not in a git worktree"));
    assert!(String::from_utf8_lossy(&output.stdout).contains("Review."));
}
