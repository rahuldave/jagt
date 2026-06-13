use assert_cmd::Command;
use predicates::prelude::*;

#[test]
fn draft_lint_accepts_valid_result_pair_and_expect_none_rejects_drafts() {
    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args([
            "draft",
            "lint",
            "fixtures/agent_task_draft/valid/result_pair.agent-task-draft.txt",
            "--expect-count",
            "1",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "validated 1 AGENT_TASK_DRAFT block",
        ));

    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args(["draft", "lint", "--expect-none", "-"])
        .write_stdin("ordinary output\n")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "no agent task draft blocks detected",
        ));

    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args(["draft", "lint", "--expect-none", "-"])
        .write_stdin(include_str!(
            "../fixtures/agent_task_draft/valid/result_pair.agent-task-draft.txt"
        ))
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "expected no AGENT_TASK_DRAFT block",
        ));
}

#[test]
fn draft_lint_rejects_invalid_draft_fixtures() {
    for (fixture, message) in [
        (
            "fixtures/agent_task_draft/invalid/malformed.agent-task-draft.txt",
            "malformed top-level YAML-like field",
        ),
        (
            "fixtures/agent_task_draft/invalid/missing_approval.agent-task-draft.txt",
            "missing approval",
        ),
        (
            "fixtures/agent_task_draft/invalid/missing_safety_language.agent-task-draft.txt",
            "missing no-authority-expansion safety text",
        ),
        (
            "fixtures/agent_task_draft/invalid/mode_agentic.agent-task-draft.txt",
            "must use mode: draft",
        ),
        (
            "fixtures/agent_task_draft/invalid/overbroad_allowed_actions.agent-task-draft.txt",
            "overbroad allowed actions",
        ),
        (
            "fixtures/agent_task_draft/invalid/direct_execution.agent-task-draft.txt",
            "attempts direct draft execution",
        ),
    ] {
        Command::cargo_bin("jagt")
            .expect("binary exists")
            .args(["draft", "lint", fixture])
            .assert()
            .failure()
            .stderr(predicate::str::contains(message));
    }
}
