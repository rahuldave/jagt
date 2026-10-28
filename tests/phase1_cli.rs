use assert_cmd::Command;
use predicates::prelude::*;
use std::fs;
use tempfile::tempdir;

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
  renderer_version: 0.2.0
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
        .stdout(predicate::str::contains("provenance: jagt 0.2.0"));
}

#[test]
fn render_uses_config_prompt_frontmatter_env_and_cli_precedence() {
    let project = tempdir().expect("temp project");
    fs::create_dir(project.path().join(".jagt")).expect("create .jagt");
    fs::create_dir(project.path().join("prompts")).expect("create prompts");
    fs::write(
        project.path().join(".jagt/config.toml"),
        r#"
[env]
allow = ["DATA_ROOT"]
redact = ["*_TOKEN", "*_SECRET", "PASSWORD"]

[defaults]
allowed_actions = ["default action"]
verification = ["default verify"]

[targets.eda-viz]
prompt = "prompts/eda.md"
inputs = ["${DATA_ROOT}/train.csv"]
required_outputs = ["reports/from-config.html"]
allowed_actions = ["config action"]
verification = ["config verify"]
"#,
    )
    .expect("write config");
    fs::write(
        project.path().join("prompts/eda.md"),
        r#"---
required_outputs:
  - reports/from-frontmatter.html
allowed_actions:
  - frontmatter action
verification:
  - frontmatter verify
---

Build the eda report from the configured dataset.
"#,
    )
    .expect("write prompt");

    let first = Command::cargo_bin("jagt")
        .expect("binary exists")
        .current_dir(project.path())
        .env("DATA_ROOT", "data")
        .args([
            "render",
            "eda-viz",
            "--required-output",
            "reports/from-cli.html",
            "--allowed-action",
            "cli action",
            "--verification",
            "cli verify",
        ])
        .assert()
        .success()
        .get_output()
        .stdout
        .clone();
    let second = Command::cargo_bin("jagt")
        .expect("binary exists")
        .current_dir(project.path())
        .env("DATA_ROOT", "data")
        .args([
            "render",
            "eda-viz",
            "--required-output",
            "reports/from-cli.html",
            "--allowed-action",
            "cli action",
            "--verification",
            "cli verify",
        ])
        .assert()
        .success()
        .get_output()
        .stdout
        .clone();
    assert_eq!(first, second, "config render output is byte stable");

    let packet = String::from_utf8(first).expect("render output is utf8");
    assert!(packet.contains("    - data/train.csv\n"));
    assert!(packet.contains("  Build the eda report from the configured dataset.\n"));
    assert!(packet.contains("  required:\n    - reports/from-cli.html\n"));
    assert!(packet.contains("allowed_actions:\n  - cli action\n"));
    assert!(packet.contains("verification:\n  - cli verify\n"));
    assert!(packet.contains("source_order:\n"));
    assert!(packet.contains("  - 'project config: .jagt/config.toml'\n"));
    assert!(packet.contains("  - 'target config: eda-viz'\n"));
    assert!(packet.contains("  - 'prompt frontmatter: prompts/eda.md'\n"));
    assert!(packet.contains("  - CLI flags\n"));

    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args(["lint", "-"])
        .write_stdin(packet.clone())
        .assert()
        .success();

    Command::cargo_bin("jagt")
        .expect("binary exists")
        .args(["explain", "task", "-"])
        .write_stdin(packet)
        .assert()
        .success()
        .stdout(predicate::str::contains("source_order:\n"))
        .stdout(predicate::str::contains(
            "- project config: .jagt/config.toml\n",
        ))
        .stdout(predicate::str::contains(
            "- prompt frontmatter: prompts/eda.md\n",
        ));
}

#[test]
fn render_supports_explicit_config_path_and_no_config() {
    let project = tempdir().expect("temp project");
    fs::write(
        project.path().join("custom-jagt.toml"),
        r#"
[targets.count-chat-message-words]
prompt_text = "Count words from custom config."
inputs = ["message.txt"]
required_outputs = ["word_count"]
"#,
    )
    .expect("write custom config");

    Command::cargo_bin("jagt")
        .expect("binary exists")
        .current_dir(project.path())
        .args([
            "render",
            "count-chat-message-words",
            "--config",
            "custom-jagt.toml",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("Count words from custom config."))
        .stdout(predicate::str::contains("source_order:\n"))
        .stdout(predicate::str::contains(
            "  - 'project config: custom-jagt.toml'\n",
        ));

    Command::cargo_bin("jagt")
        .expect("binary exists")
        .current_dir(project.path())
        .args([
            "render",
            "count-chat-message-words",
            "--config",
            "custom-jagt.toml",
            "--no-config",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("missing prompt text"));
}

#[test]
fn render_rejects_unallowlisted_and_redacted_env_interpolation() {
    let project = tempdir().expect("temp project");
    fs::write(
        project.path().join("unallowlisted.toml"),
        r#"
[targets.eda-viz]
prompt_text = "Inspect the dataset."
inputs = ["${DATA_ROOT}/train.csv"]
"#,
    )
    .expect("write unallowlisted config");
    fs::write(
        project.path().join("redacted.toml"),
        r#"
[env]
allow = ["API_TOKEN"]
redact = ["*_TOKEN"]

[targets.eda-viz]
prompt_text = "Inspect the dataset."
inputs = ["${API_TOKEN}/train.csv"]
"#,
    )
    .expect("write redacted config");

    Command::cargo_bin("jagt")
        .expect("binary exists")
        .current_dir(project.path())
        .env("DATA_ROOT", "data")
        .args(["render", "eda-viz", "--config", "unallowlisted.toml"])
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "environment variable DATA_ROOT is not allowlisted",
        ));

    Command::cargo_bin("jagt")
        .expect("binary exists")
        .current_dir(project.path())
        .env("API_TOKEN", "ghp_secret")
        .args(["render", "eda-viz", "--config", "redacted.toml"])
        .assert()
        .failure()
        .stderr(predicate::str::contains(
            "environment variable API_TOKEN matches redact rule",
        ));
}
