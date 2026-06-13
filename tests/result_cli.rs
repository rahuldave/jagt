use assert_cmd::Command;
use predicates::prelude::*;
use std::fs;
use tempfile::tempdir;

const SUCCESS_RESULT: &str = "\
<<<AGENT_RESULT v1>>>
target: eda-viz
task_ref: sha256:example
status: success
outputs:
  files:
    - path: reports/eda/index.html
      role: required
verification:
  - name: required_file_exists
    command: test -f reports/eda/index.html
    status: passed
notes: |
  Created the requested dashboard.
follow_up: []
<<<END_AGENT_RESULT>>>
";

#[test]
fn result_lint_accepts_valid_success_fixture_and_explain_summarizes() {
    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args([
            "result",
            "lint",
            "fixtures/agent_result/valid/success_file.agent-result.txt",
            "--expect-count",
            "1",
            "--expect-target",
            "eda-viz",
            "--expect-status",
            "success",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("validated 1 AGENT_RESULT block"));

    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args([
            "result",
            "explain",
            "fixtures/agent_result/valid/success_file.agent-result.txt",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("AGENT_RESULT v1"))
        .stdout(predicate::str::contains("target: eda-viz"))
        .stdout(predicate::str::contains("status: success"))
        .stdout(predicate::str::contains("outputs.files: 1 item(s)"))
        .stdout(predicate::str::contains("report_only: true"));
}

#[test]
fn result_lint_validates_partial_proposed_tasks() {
    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args([
            "result",
            "lint",
            "fixtures/agent_result/valid/proposed_tasks.agent-result.txt",
            "--expect-target",
            "count-chat-message-words",
            "--expect-status",
            "partial",
        ])
        .assert()
        .success();

    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args([
            "result",
            "explain",
            "fixtures/agent_result/valid/proposed_tasks.agent-result.txt",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "outputs.proposed_tasks: 1 item(s)",
        ));
}

#[test]
fn result_lint_expect_none_allows_ordinary_output_and_rejects_result_blocks() {
    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args(["result", "lint", "--expect-none", "-"])
        .write_stdin("ordinary command output\n")
        .assert()
        .success()
        .stdout(predicate::str::contains("no agent result blocks detected"));

    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args(["result", "lint", "--expect-none", "-"])
        .write_stdin(SUCCESS_RESULT)
        .assert()
        .failure()
        .stderr(predicate::str::contains("expected no AGENT_RESULT block"));
}

#[test]
fn result_lint_rejects_invalid_result_fixtures() {
    for (fixture, message) in [
        (
            "fixtures/agent_result/invalid/missing_status.agent-result.txt",
            "missing status",
        ),
        (
            "fixtures/agent_result/invalid/failed_missing_error.agent-result.txt",
            "missing error",
        ),
        (
            "fixtures/agent_result/invalid/report_authority.agent-result.txt",
            "report-only",
        ),
        (
            "fixtures/agent_result/invalid/success_failed_verification.agent-result.txt",
            "success result contains failed verification",
        ),
    ] {
        Command::cargo_bin("jagt")
            .expect("binary exists")
            .args(["result", "lint", fixture])
            .assert()
            .failure()
            .stderr(predicate::str::contains(message));
    }
}

#[test]
fn result_lint_rejects_expected_target_and_status_mismatch() {
    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args([
            "result",
            "lint",
            "fixtures/agent_result/valid/success_file.agent-result.txt",
            "--expect-target",
            "other-target",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("expected target other-target"));

    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args([
            "result",
            "lint",
            "fixtures/agent_result/valid/success_file.agent-result.txt",
            "--expect-status",
            "blocked",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("expected status blocked"));
}

#[test]
fn result_lint_check_files_uses_base_dir_and_rejects_missing_or_absolute_required_files() {
    let project = tempdir().expect("temp project");
    fs::create_dir_all(project.path().join("reports/eda")).expect("create reports");
    fs::write(
        project.path().join("reports/eda/index.html"),
        "<h1>EDA</h1>",
    )
    .expect("write required file");
    let result_path = project.path().join("success.agent-result.txt");
    fs::write(&result_path, SUCCESS_RESULT).expect("write result");

    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args([
            "result",
            "lint",
            result_path.to_str().expect("utf8 path"),
            "--check-files",
            "--base-dir",
            project.path().to_str().expect("utf8 path"),
        ])
        .assert()
        .success();

    fs::remove_file(project.path().join("reports/eda/index.html")).expect("remove required file");
    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args([
            "result",
            "lint",
            result_path.to_str().expect("utf8 path"),
            "--check-files",
            "--base-dir",
            project.path().to_str().expect("utf8 path"),
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("required output file missing"));

    let absolute_result = SUCCESS_RESULT.replace(
        "reports/eda/index.html",
        project
            .path()
            .join("reports/eda/index.html")
            .to_str()
            .expect("utf8 path"),
    );
    let absolute_path = project.path().join("absolute.agent-result.txt");
    fs::write(&absolute_path, absolute_result).expect("write absolute result");
    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args([
            "result",
            "lint",
            absolute_path.to_str().expect("utf8 path"),
            "--check-files",
            "--base-dir",
            project.path().to_str().expect("utf8 path"),
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("must be repo-relative"));
}
