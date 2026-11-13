//! Tests for the findings of the final review: packets that `jagt render`
//! printed but `jagt lint` rejected, prompt files that a config could name
//! outside the repository, and `..` paths in `result lint --check-files`.

use assert_cmd::Command;
use predicates::prelude::*;
use serde_yaml::Value;
use std::fs;
use std::path::Path;
use std::process::Command as StdCommand;
use tempfile::tempdir;

fn jagt(cwd: &Path) -> Command {
    let mut command = Command::cargo_bin("jagt").expect("binary exists");
    command.current_dir(cwd);
    command
}

/// The body of the first AGENT_TASK block, read as YAML.
fn packet_yaml(text: &str) -> Value {
    let body = text
        .split("<<<AGENT_TASK v1>>>\n")
        .nth(1)
        .and_then(|rest| rest.split("<<<END_AGENT_TASK>>>").next())
        .expect("one block");
    serde_yaml::from_str(body).expect("the packet is valid YAML")
}

/// Render with `--no-save` and no config, and return the packet text.
fn render_prompt(cwd: &Path, prompt: &str) -> String {
    let output = jagt(cwd)
        .args(["render", "t", "--no-save", "--no-config"])
        .arg(format!("--prompt-text={prompt}"))
        .output()
        .expect("jagt runs");
    assert!(
        output.status.success(),
        "render of {prompt:?} failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    String::from_utf8(output.stdout).expect("utf8")
}

fn assert_lints(cwd: &Path, text: &str) {
    jagt(cwd)
        .arg("lint")
        .write_stdin(text.to_string())
        .assert()
        .success();
}

fn git(cwd: &Path, args: &[&str]) {
    let output = StdCommand::new("git")
        .current_dir(cwd)
        .args(args)
        .env_remove("GIT_DIR")
        .env_remove("GIT_WORK_TREE")
        .env_remove("GIT_INDEX_FILE")
        .output()
        .expect("git runs");
    assert!(
        output.status.success(),
        "git {args:?} failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}

#[test]
fn prompts_with_unbalanced_brackets_render_and_lint() {
    let dir = tempdir().expect("tempdir");
    for prompt in ["Fix arr[i", "fn main() {", "close ] and }", "[[[", "{a: [b"] {
        let text = render_prompt(dir.path(), prompt);
        assert_lints(dir.path(), &text);
        assert_eq!(
            packet_yaml(&text)["prompt"].as_str(),
            Some(&*format!("{prompt}\n"))
        );
    }
}

#[test]
fn a_saved_render_accepts_a_prompt_with_an_open_bracket() {
    let dir = tempdir().expect("tempdir");
    git(dir.path(), &["init", "-q"]);
    let output = jagt(dir.path())
        .args(["render", "t", "--no-config", "--prompt-text", "Fix arr[i"])
        .output()
        .expect("jagt runs");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert_lints(dir.path(), &String::from_utf8(output.stdout).expect("utf8"));
}

#[test]
fn lint_still_rejects_a_flow_list_that_is_not_closed() {
    let dir = tempdir().expect("tempdir");
    let text = render_prompt(dir.path(), "Go.");
    let broken = text.replacen("argv: []", "argv: [a", 1);
    assert_ne!(broken, text, "the packet has an empty argv to break");
    jagt(dir.path())
        .arg("lint")
        .write_stdin(broken)
        .assert()
        .failure()
        .stderr(predicate::str::contains("invalid YAML"));
}

#[test]
fn prompts_with_line_breaks_or_controls_that_a_block_cannot_hold_read_back_unchanged() {
    let dir = tempdir().expect("tempdir");
    for prompt in [
        "a\rb",
        "a\u{85}b",
        "a\u{2028}b",
        "a\u{2029}b",
        "a\u{1}b",
        "a\u{7f}b",
        "a\u{feff}b",
        "first\nsecond\rthird",
    ] {
        let text = render_prompt(dir.path(), prompt);
        assert_lints(dir.path(), &text);
        assert!(text.contains("prompt: \""), "{prompt:?}: {text}");
        assert_eq!(
            packet_yaml(&text)["prompt"].as_str(),
            Some(prompt),
            "{prompt:?}"
        );
    }
}

#[test]
fn a_prompt_with_crlf_line_ends_keeps_the_literal_block() {
    let dir = tempdir().expect("tempdir");
    let text = render_prompt(dir.path(), "one\r\ntwo\r\n");
    assert_lints(dir.path(), &text);
    assert!(text.contains("prompt: |\n  one\n  two\n"), "{text}");
}

#[test]
fn a_prompt_with_a_bad_character_and_crlf_ends_reads_back_with_lf_ends() {
    let dir = tempdir().expect("tempdir");
    let text = render_prompt(dir.path(), "one\r\ntwo\u{2028}three");
    assert_lints(dir.path(), &text);
    assert_eq!(
        packet_yaml(&text)["prompt"].as_str(),
        Some("one\ntwo\u{2028}three")
    );
}

/// A git repository with a config whose `[defaults] prompt` is `prompt`.
fn repo_with_config_prompt(prompt: &str) -> tempfile::TempDir {
    let dir = tempdir().expect("tempdir");
    git(dir.path(), &["init", "-q"]);
    fs::create_dir_all(dir.path().join(".jagt")).expect("config folder");
    fs::create_dir_all(dir.path().join("prompts")).expect("prompts folder");
    fs::write(dir.path().join("prompts/ok.md"), "From the repo.\n").expect("prompt");
    fs::write(dir.path().join(".env"), "NOT_A_PROMPT=1\n").expect("env file");
    fs::write(dir.path().join(".gitignore"), ".env\n").expect("ignore");
    fs::write(
        dir.path().join(".jagt/config.toml"),
        format!("[defaults]\nprompt = {prompt:?}\n"),
    )
    .expect("config");
    dir
}

#[test]
fn a_config_prompt_inside_the_repository_is_read() {
    let dir = repo_with_config_prompt("prompts/ok.md");
    jagt(dir.path())
        .args(["render", "t", "--no-save"])
        .assert()
        .success()
        .stdout(predicate::str::contains("From the repo."));
}

#[test]
fn a_config_prompt_outside_the_folder_is_refused() {
    let outside = tempdir().expect("tempdir");
    let secret = outside.path().join("secret.md");
    fs::write(&secret, "NOT_A_PROMPT\n").expect("outside file");
    let dir = repo_with_config_prompt(secret.to_str().expect("utf8"));
    jagt(dir.path())
        .args(["render", "t", "--no-save"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("leads outside the current folder"))
        .stdout(predicate::str::contains("NOT_A_PROMPT").not());

    let dir = repo_with_config_prompt("../secret.md");
    fs::write(dir.path().join("../secret.md"), "NOT_A_PROMPT\n").expect("parent file");
    jagt(dir.path())
        .args(["render", "t", "--no-save"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("leads outside the current folder"));
    fs::remove_file(dir.path().join("../secret.md")).expect("clean up");
}

#[cfg(unix)]
#[test]
fn a_config_prompt_symlink_that_leads_outside_is_refused() {
    let outside = tempdir().expect("tempdir");
    let secret = outside.path().join("secret.md");
    fs::write(&secret, "NOT_A_PROMPT\n").expect("outside file");
    let dir = repo_with_config_prompt("prompts/link.md");
    std::os::unix::fs::symlink(&secret, dir.path().join("prompts/link.md")).expect("symlink");
    jagt(dir.path())
        .args(["render", "t", "--no-save"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("leads outside the current folder"));
}

#[test]
fn a_config_prompt_that_git_ignores_or_that_is_in_git_is_refused() {
    let dir = repo_with_config_prompt(".env");
    jagt(dir.path())
        .args(["render", "t", "--no-save"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("git ignores"))
        .stdout(predicate::str::contains("NOT_A_PROMPT").not());

    let dir = repo_with_config_prompt(".git/config");
    jagt(dir.path())
        .args(["render", "t", "--no-save"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("is inside .git"));
}

#[test]
fn a_target_config_prompt_gets_the_same_check() {
    let dir = repo_with_config_prompt("prompts/ok.md");
    fs::write(
        dir.path().join(".jagt/config.toml"),
        "[targets.t]\nprompt = \".env\"\n",
    )
    .expect("config");
    jagt(dir.path())
        .args(["render", "t", "--no-save"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("git ignores"));
}

#[test]
fn a_cli_prompt_file_is_the_callers_choice_and_is_not_checked() {
    let outside = tempdir().expect("tempdir");
    let file = outside.path().join("mine.md");
    fs::write(&file, "My own prompt.\n").expect("prompt");
    let dir = repo_with_config_prompt(".env");
    jagt(dir.path())
        .args(["render", "t", "--no-save", "--prompt"])
        .arg(&file)
        .assert()
        .success()
        .stdout(predicate::str::contains("My own prompt."));
}

const RESULT_WITH_PARENT_PATH: &str = "<<<AGENT_RESULT v1>>>
target: eda
status: success
outputs:
  files:
    - path: ../outside.txt
      role: required
verification:
  - ran: just test
follow_up: []
<<<END_AGENT_RESULT>>>
";

#[test]
fn check_files_refuses_a_path_with_a_parent_part() {
    let root = tempdir().expect("tempdir");
    let project = root.path().join("project");
    fs::create_dir(&project).expect("project");
    fs::write(root.path().join("outside.txt"), "x").expect("outside file");
    for path in ["../outside.txt", "reports/../../outside.txt"] {
        jagt(&project)
            .args(["result", "lint", "--check-files", "--base-dir", "."])
            .write_stdin(RESULT_WITH_PARENT_PATH.replace("../outside.txt", path))
            .assert()
            .failure()
            .stderr(predicate::str::contains("must be repo-relative"));
    }
}

/// A folder that is not a git repository, with a config whose `[defaults]
/// prompt` is `prompt`, and the same files as [`repo_with_config_prompt`].
fn folder_with_config_prompt(prompt: &str) -> tempfile::TempDir {
    let dir = tempdir().expect("tempdir");
    for folder in [".jagt", "prompts", ".agents/targets"] {
        fs::create_dir_all(dir.path().join(folder)).expect("folder");
    }
    fs::write(dir.path().join("prompts/ok.md"), "From the folder.\n").expect("prompt");
    fs::write(dir.path().join(".agents/targets/t.md"), "From targets.\n").expect("prompt");
    fs::write(dir.path().join(".env"), "NOT_A_PROMPT=1\n").expect("env file");
    fs::write(
        dir.path().join(".jagt/config.toml"),
        format!("[defaults]\nprompt = {prompt:?}\n"),
    )
    .expect("config");
    dir
}

#[test]
fn outside_git_a_hidden_config_prompt_is_refused_and_others_are_read() {
    for hidden in [".env", "prompts/../.env"] {
        let dir = folder_with_config_prompt(hidden);
        jagt(dir.path())
            .args(["render", "t", "--no-save"])
            .assert()
            .failure()
            .stderr(predicate::str::contains("is hidden"))
            .stdout(predicate::str::contains("NOT_A_PROMPT").not());
    }
    for (prompt, text) in [
        ("prompts/ok.md", "From the folder."),
        (".agents/targets/t.md", "From targets."),
    ] {
        let dir = folder_with_config_prompt(prompt);
        jagt(dir.path())
            .args(["render", "t", "--no-save"])
            .assert()
            .success()
            .stdout(predicate::str::contains(text));
    }
}

#[test]
fn in_a_repository_a_config_prompt_is_refused_when_git_cannot_start() {
    let dir = repo_with_config_prompt(".env");
    fs::write(dir.path().join("ignored.md"), "NOT_A_PROMPT\n").expect("ignored file");
    fs::write(dir.path().join(".gitignore"), ".env\nignored.md\n").expect("ignore");
    for prompt in [".env", "ignored.md", "prompts/ok.md"] {
        fs::write(
            dir.path().join(".jagt/config.toml"),
            format!("[defaults]\nprompt = {prompt:?}\n"),
        )
        .expect("config");
        jagt(dir.path())
            .env("PATH", "/nonexistent")
            .args(["render", "t", "--no-save"])
            .assert()
            .failure()
            .stderr(predicate::str::contains("git cannot say"))
            .stdout(predicate::str::contains("NOT_A_PROMPT").not());
    }
}

#[test]
fn an_ignored_file_in_a_nested_repository_is_refused() {
    let dir = repo_with_config_prompt("smod/secret.json");
    let nested = dir.path().join("smod");
    fs::create_dir(&nested).expect("nested folder");
    git(&nested, &["init", "-q"]);
    fs::write(nested.join(".gitignore"), "secret.json\n").expect("ignore");
    fs::write(nested.join("secret.json"), "NOT_A_PROMPT\n").expect("secret");
    fs::write(nested.join("README.md"), "x\n").expect("readme");
    git(&nested, &["add", ".gitignore", "README.md"]);
    git(
        &nested,
        &[
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "commit",
            "-q",
            "-m",
            "x",
        ],
    );
    // The outer repository records the nested one as a gitlink, as a submodule.
    git(dir.path(), &["add", "smod"]);
    jagt(dir.path())
        .args(["render", "t", "--no-save"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("git ignores"))
        .stdout(predicate::str::contains("NOT_A_PROMPT").not());
}

#[test]
fn a_config_given_with_config_from_a_plain_folder_cannot_read_its_env_file() {
    let repo = repo_with_config_prompt(".env");
    let plain = tempdir().expect("tempdir");
    fs::write(plain.path().join(".env"), "NOT_A_PROMPT=1\n").expect("env file");
    jagt(plain.path())
        .args(["render", "t", "--no-save", "--config"])
        .arg(repo.path().join(".jagt/config.toml"))
        .assert()
        .failure()
        .stderr(predicate::str::contains("is hidden"));
}

#[cfg(unix)]
#[test]
fn a_config_prompt_with_a_second_hard_link_is_refused() {
    let outside = tempdir().expect("tempdir");
    let secret = outside.path().join("secret.md");
    fs::write(&secret, "NOT_A_PROMPT\n").expect("outside file");
    let dir = repo_with_config_prompt("prompts/hard.md");
    if fs::hard_link(&secret, dir.path().join("prompts/hard.md")).is_err() {
        // Two temporary folders on different file systems cannot share a link.
        return;
    }
    jagt(dir.path())
        .args(["render", "t", "--no-save"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("more than one hard link"))
        .stdout(predicate::str::contains("NOT_A_PROMPT").not());
}

#[test]
fn a_file_that_the_outer_repository_ignores_is_refused_from_a_nested_one() {
    let dir = repo_with_config_prompt("inner/creds.txt");
    let inner = dir.path().join("inner");
    fs::create_dir(&inner).expect("inner folder");
    git(&inner, &["init", "-q"]);
    fs::write(inner.join("creds.txt"), "NOT_A_PROMPT\n").expect("creds");
    fs::write(dir.path().join(".gitignore"), ".env\ninner/creds.txt\n").expect("ignore");
    jagt(dir.path())
        .args(["render", "t", "--no-save"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("git ignores"))
        .stdout(predicate::str::contains("NOT_A_PROMPT").not());
}

#[test]
fn a_file_in_a_nested_repository_that_no_repository_ignores_is_read() {
    let dir = repo_with_config_prompt("inner/p.md");
    let inner = dir.path().join("inner");
    fs::create_dir(&inner).expect("inner folder");
    git(&inner, &["init", "-q"]);
    fs::write(inner.join("p.md"), "From the nested repo.\n").expect("prompt");
    jagt(dir.path())
        .args(["render", "t", "--no-save"])
        .assert()
        .success()
        .stdout(predicate::str::contains("From the nested repo."));
}

#[test]
fn an_allowlisted_database_url_with_a_password_is_refused() {
    let dir = tempdir().expect("tempdir");
    fs::create_dir(dir.path().join(".jagt")).expect("config folder");
    fs::write(
        dir.path().join(".jagt/config.toml"),
        "[env]\nallow = [\"JAGT_TEST_DB_URL\"]\n\n[defaults]\nprompt_text = \"Go.\"\ninputs = [\"${JAGT_TEST_DB_URL}\"]\n",
    )
    .expect("config");
    jagt(dir.path())
        .env("JAGT_TEST_DB_URL", "postgres://user:fakepw@h/db")
        .args(["render", "t", "--no-save"])
        .assert()
        .failure()
        .stderr(predicate::str::contains("secret-like value"))
        .stdout(predicate::str::contains("fakepw").not());
}
