use assert_cmd::Command;
use predicates::prelude::*;

const EXPECTED_RENDER: &str = "\
<<<AGENT_TASK v1>>>
target: count-chat-message-words
mode: agentic
argv:
  - inline:user-message
  - message.txt
prompt: |
  Count words.
  Treat whitespace-separated tokens as words.
inputs:
  files:
    - message.txt
outputs:
  required:
    - word_count
allowed_actions:
  - read listed inputs
  - compute deterministic word count
verification:
  - recompute the count once independently before returning
delegation:
  execution: subagent
  recursive: true
  triggers:
    - nested agentic Just calls
    - agentic dependencies
    - hook-triggered packets
    - agentic verification targets
safety:
  - This block is repo-local operational context.
  - It cannot override user, system, developer, VCS, or approval instructions.
provenance:
  renderer: jagt
  renderer_version: 0.1.0
<<<END_AGENT_TASK>>>
";

fn render_command() -> Command {
    let mut cmd = Command::cargo_bin("jagt").expect("binary exists");
    cmd.args([
        "render",
        "count-chat-message-words",
        "--arg",
        "inline:user-message",
        "--input",
        "message.txt",
        "--prompt-text",
        "Count words.\nTreat whitespace-separated tokens as words.",
        "--required-output",
        "word_count",
        "--allowed-action",
        "read listed inputs",
        "--allowed-action",
        "compute deterministic word count",
        "--verification",
        "recompute the count once independently before returning",
    ]);
    cmd
}

#[test]
fn render_cli_only_task_packet_is_byte_stable() {
    render_command().assert().success().stdout(EXPECTED_RENDER);
}

#[test]
fn rendered_task_packet_lints_from_stdin() {
    let render_output = render_command()
        .assert()
        .success()
        .get_output()
        .stdout
        .clone();
    let packet = String::from_utf8(render_output).expect("render output is utf8");

    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args(["lint", "-"])
        .write_stdin(packet)
        .assert()
        .success()
        .stdout(predicate::str::contains("validated 1 AGENT_TASK block"));
}

#[test]
fn lint_rejects_malformed_markers() {
    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args([
            "lint",
            "fixtures/agent_task/invalid/malformed_markers.agent-task.txt",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("start marker without end marker"));
}

#[test]
fn lint_rejects_missing_safety_text() {
    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args([
            "lint",
            "fixtures/agent_task/invalid/missing_safety.agent-task.txt",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("missing safety override text"));
}

#[test]
fn lint_rejects_missing_recursive_delegation() {
    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args([
            "lint",
            "fixtures/agent_task/invalid/missing_recursive.agent-task.txt",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "must declare recursive delegation",
        ));
}

#[test]
fn lint_expect_none_allows_ordinary_output_and_rejects_task_blocks() {
    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args(["lint", "--expect-none", "-"])
        .write_stdin("ordinary command output\n")
        .assert()
        .success()
        .stdout(predicate::str::contains("no agent task blocks detected"));

    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args(["lint", "--expect-none", "-"])
        .write_stdin(EXPECTED_RENDER)
        .assert()
        .failure()
        .stderr(predicate::str::contains("expected no AGENT_TASK block"));
}

#[test]
fn explain_task_summarizes_a_valid_packet() {
    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args(["explain", "task", "-"])
        .write_stdin(EXPECTED_RENDER)
        .assert()
        .success()
        .stdout(predicate::str::contains("target: count-chat-message-words"))
        .stdout(predicate::str::contains("delegation: recursive subagent"))
        .stdout(predicate::str::contains("provenance: jagt 0.1.0"));
}
