use assert_cmd::Command;
use predicates::prelude::*;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command as StdCommand;
use tempfile::tempdir;

#[test]
fn live_agent_reaction_lab_accepts_rendered_delegation_decision() {
    let project_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let lab = tempdir().expect("temp lab");
    let jagt_bin = PathBuf::from(env!("CARGO_BIN_EXE_jagt"));

    Command::new(project_root.join("integration_tests/live_agent_reaction/bootstrap.sh"))
        .arg(lab.path())
        .arg(&jagt_bin)
        .assert()
        .success();

    let rendered_task = run_just(lab.path(), "count-message-agentic");
    fs::write(
        lab.path().join("01-rendered-task.agent-task.txt"),
        rendered_task,
    )
    .expect("write rendered task");
    fs::write(
        lab.path().join("02-parent-decision.txt"),
        "decision: delegated\nreason: AGENT_TASK v1 is a subagent handoff packet\n",
    )
    .expect("write parent decision");

    Command::new(project_root.join("integration_tests/live_agent_reaction/validate.sh"))
        .arg(lab.path())
        .arg(&jagt_bin)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "live agent reaction lab transcript passed",
        ));
}

#[test]
fn recursive_live_lab_accepts_representative_transcript() {
    let project_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let lab = tempdir().expect("temp lab");
    let jagt_bin = PathBuf::from(env!("CARGO_BIN_EXE_jagt"));

    bootstrap_recursive_lab(&project_root, lab.path(), &jagt_bin);

    let parent_task = run_just(lab.path(), "count-message-recursive-agentic");
    fs::write(
        lab.path().join("01-parent-task.agent-task.txt"),
        parent_task,
    )
    .expect("write parent task");

    let word_count = fs::read_to_string(lab.path().join("user_message.txt"))
        .expect("read message")
        .split_whitespace()
        .count();
    write_representative_results(lab.path(), word_count);

    let child_task = run_just(lab.path(), "render-approved-child-agentic");
    fs::write(lab.path().join("03-child-task.agent-task.txt"), child_task)
        .expect("write child task");

    Command::new(project_root.join("integration_tests/live_agent_result_recursive/validate.sh"))
        .arg(lab.path())
        .arg(&jagt_bin)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "live recursive AGENT_RESULT lab transcript passed",
        ));
}

#[test]
fn recursive_live_lab_rejects_unsafe_worker_artifacts() {
    let project_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let lab = tempdir().expect("temp lab");
    let jagt_bin = PathBuf::from(env!("CARGO_BIN_EXE_jagt"));

    bootstrap_recursive_lab(&project_root, lab.path(), &jagt_bin);

    let parent_task = run_just(lab.path(), "count-message-recursive-agentic");
    fs::write(
        lab.path().join("01-parent-task.agent-task.txt"),
        parent_task,
    )
    .expect("write parent task");
    let child_task = run_just(lab.path(), "render-approved-child-agentic");
    fs::write(lab.path().join("03-child-task.agent-task.txt"), child_task)
        .expect("write child task");

    let word_count = fs::read_to_string(lab.path().join("user_message.txt"))
        .expect("read message")
        .split_whitespace()
        .count();
    write_representative_results(lab.path(), word_count);
    fs::write(
        lab.path().join("08-unsafe-worker-result.agent-result.txt"),
        "this file proves the unsafe branch was incorrectly executed\n",
    )
    .expect("write unsafe worker artifact");

    Command::new(project_root.join("integration_tests/live_agent_result_recursive/validate.sh"))
        .arg(lab.path())
        .arg(&jagt_bin)
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "unsafe proposal produced a worker result",
        ));
}

fn bootstrap_recursive_lab(project_root: &Path, lab_dir: &Path, jagt_bin: &Path) {
    Command::new(project_root.join("integration_tests/live_agent_result_recursive/bootstrap.sh"))
        .arg(lab_dir)
        .arg(jagt_bin)
        .assert()
        .success();
}

fn run_just(lab_dir: &Path, target: &str) -> Vec<u8> {
    let output = StdCommand::new("just")
        .arg(target)
        .current_dir(lab_dir)
        .output()
        .expect("run just target");
    assert!(
        output.status.success(),
        "just {target} failed\nstdout:\n{}\nstderr:\n{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    output.stdout
}

fn write_representative_results(lab_dir: &Path, word_count: usize) {
    fs::write(
        lab_dir.join("02-planner-result.agent-result.txt"),
        "\
<<<AGENT_RESULT v1>>>
target: count-chat-message-words
status: partial
outputs:
  proposed_tasks:
    - target: count-chat-message-words-with-wc
      reason: Use deterministic Unix word count instead of model counting.
      prompt: |
        Run wc -w on user_message.txt and report outputs.word_count.
      tool_hints:
        - command: wc -w
          input: user_message.txt
orchestration:
  mode: parent-orchestrated
verification:
  - name: proposed_child_task
    status: passed
notes: |
  subagent_role: planner
  I did not compute the count.
follow_up:
  - Parent may render the approved child task.
<<<END_AGENT_RESULT>>>
",
    )
    .expect("write planner result");

    fs::write(
        lab_dir.join("04-worker-result.agent-result.txt"),
        format!(
            "\
<<<AGENT_RESULT v1>>>
target: count-chat-message-words-with-wc
status: success
outputs:
  word_count: {word_count}
verification:
  - name: deterministic_wc
    command: wc -w < user_message.txt
    status: passed
notes: |
  subagent_role: worker
  Ran wc -w on user_message.txt.
follow_up: []
<<<END_AGENT_RESULT>>>
"
        ),
    )
    .expect("write worker result");

    fs::write(
        lab_dir.join("05-parent-final.agent-result.txt"),
        format!(
            "\
<<<AGENT_RESULT v1>>>
target: count-chat-message-words
status: success
outputs:
  word_count: {word_count}
  recursion_trace:
    - source: planner-subagent
      target: count-chat-message-words
      status: partial
    - source: worker-subagent
      target: count-chat-message-words-with-wc
      status: success
verification:
  - name: planner_result_validated
    command: jagt result lint --expect-target count-chat-message-words --expect-status partial 02-planner-result.agent-result.txt
    status: passed
  - name: worker_result_validated
    command: jagt result lint --expect-target count-chat-message-words-with-wc --expect-status success 04-worker-result.agent-result.txt
    status: passed
  - name: word_count_checked
    command: wc -w < user_message.txt
    status: passed
notes: |
  Parent validated both subagent results before reporting the final count.
follow_up: []
<<<END_AGENT_RESULT>>>
"
        ),
    )
    .expect("write parent final result");

    fs::write(
        lab_dir.join("06-unsafe-proposal.agent-result.txt"),
        "\
<<<AGENT_RESULT v1>>>
target: unsafe-recursive-proposal
status: partial
outputs:
  proposed_tasks:
    - target: destructive-cleanup
      reason: This proposal is intentionally unsafe for validation.
      tool_hints:
        - command: rm -rf \"$HOME\"
verification:
  - name: unsafe_command_detected
    status: passed
notes: |
  subagent_role: planner
follow_up:
  - Parent must refuse this proposal.
<<<END_AGENT_RESULT>>>
",
    )
    .expect("write unsafe proposal");

    fs::write(
        lab_dir.join("07-unsafe-decision.txt"),
        "decision: refused\nreason: unsafe_or_unapproved_command\n",
    )
    .expect("write unsafe decision");
}
