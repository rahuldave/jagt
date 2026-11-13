//! Tests for two render bugs: a prompt file from the CLI, and YAML scalars
//! that a reader read back as another type.

use assert_cmd::Command;
use predicates::prelude::*;
use serde_yaml::Value;
use std::fs;
use tempfile::tempdir;

fn jagt(cwd: &std::path::Path) -> Command {
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

fn render(cwd: &std::path::Path, args: &[&str]) -> String {
    let output = jagt(cwd)
        .arg("render")
        .args(args)
        .output()
        .expect("jagt runs");
    assert!(
        output.status.success(),
        "render failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    String::from_utf8(output.stdout).expect("utf8")
}

#[test]
fn a_cli_prompt_file_with_no_config_gives_its_body() {
    let dir = tempdir().expect("tempdir");
    fs::write(dir.path().join("p.md"), "Count the words.\n").expect("prompt");
    let text = render(dir.path(), &["t", "--prompt", "p.md", "--no-config"]);
    assert!(text.contains("prompt: |\n  Count the words.\n"), "{text}");
}

#[test]
fn a_cli_prompt_file_with_frontmatter_gives_its_body_and_fields() {
    let dir = tempdir().expect("tempdir");
    fs::write(
        dir.path().join("p.md"),
        "---\nrequired_outputs:\n  - word_count\n---\nCount the words.\n",
    )
    .expect("prompt");
    let text = render(dir.path(), &["t", "--prompt", "p.md", "--no-config"]);
    assert!(text.contains("Count the words."), "{text}");
    assert!(text.contains("    - word_count\n"), "{text}");
}

#[test]
fn a_cli_prompt_file_wins_over_the_config_prompt_and_is_named_in_the_provenance() {
    let dir = tempdir().expect("tempdir");
    fs::create_dir(dir.path().join(".jagt")).expect("config folder");
    fs::write(
        dir.path().join(".jagt/config.toml"),
        "[defaults]\nprompt_text = \"From the config.\"\n",
    )
    .expect("config");
    fs::write(dir.path().join("p.md"), "From the file.\n").expect("prompt");
    let text = render(dir.path(), &["t", "--prompt", "p.md"]);
    assert!(text.contains("From the file."), "{text}");
    assert!(!text.contains("From the config."), "{text}");
    assert!(text.contains("    - CLI flags\n"), "{text}");
}

#[test]
fn prompt_text_still_wins_over_a_cli_prompt_file() {
    let dir = tempdir().expect("tempdir");
    fs::write(dir.path().join("p.md"), "From the file.\n").expect("prompt");
    let text = render(
        dir.path(),
        &[
            "t",
            "--prompt",
            "p.md",
            "--prompt-text",
            "From the flag.",
            "--no-config",
        ],
    );
    assert!(text.contains("From the flag."), "{text}");
    assert!(!text.contains("From the file."), "{text}");
}

#[test]
fn list_values_that_look_like_other_types_read_back_as_the_same_strings() {
    let dir = tempdir().expect("tempdir");
    let values = [
        "123",
        "-5",
        "1.5",
        "1e3",
        "0x1F",
        "0o17",
        "true",
        "False",
        "null",
        "Null",
        "~",
        ".inf",
        ".nan",
        "foo:",
        "a: b",
        "a #b",
        "line one\nline two",
        "tab\there",
        "plain words",
    ];
    // `--input=<value>`, so that clap does not read `-5` as an option.
    let flags: Vec<String> = values
        .iter()
        .map(|value| format!("--input={value}"))
        .collect();
    let mut args = vec!["t", "--prompt-text", "Go.", "--no-config"];
    args.extend(flags.iter().map(String::as_str));
    let text = render(dir.path(), &args);

    jagt(dir.path())
        .arg("lint")
        .write_stdin(text.clone())
        .assert()
        .success();
    let yaml = packet_yaml(&text);
    let files: Vec<&str> = yaml["inputs"]["files"]
        .as_sequence()
        .expect("files")
        .iter()
        .map(|value| value.as_str().expect("each file is a string"))
        .collect();
    assert_eq!(files, values);
    assert!(
        text.contains("    - plain words\n"),
        "plain text stays plain"
    );
}

#[test]
fn a_target_that_looks_like_another_type_still_lints_and_explains() {
    let dir = tempdir().expect("tempdir");
    for target in ["123", "true", "null", ".inf", "1e3"] {
        let text = render(dir.path(), &[target, "--prompt-text", "Go.", "--no-config"]);
        assert_eq!(packet_yaml(&text)["target"].as_str(), Some(target));
        jagt(dir.path())
            .arg("lint")
            .write_stdin(text.clone())
            .assert()
            .success();
        jagt(dir.path())
            .args(["explain", "task"])
            .write_stdin(text)
            .assert()
            .success()
            .stdout(predicate::str::contains(format!("target: {target}\n")));
    }
}

#[test]
fn control_characters_and_unicode_line_breaks_read_back_unchanged() {
    let dir = tempdir().expect("tempdir");
    let values = [
        "a\u{7f}b",
        "a\u{80}b",
        "a\u{9f}b",
        "a\u{85}b",
        "a\u{2028}b",
        "a\u{2029}b",
        "a\u{feff}b",
        "a\u{fffe}b",
        "a\u{ffff}",
        "a\u{1}b",
        "back\\slash \"quoted\"\nnext",
        "cr\r\nlf",
    ];
    let flags: Vec<String> = values
        .iter()
        .map(|value| format!("--input={value}"))
        .collect();
    let mut args = vec!["t", "--prompt-text", "Go.", "--no-config"];
    args.extend(flags.iter().map(String::as_str));
    let text = render(dir.path(), &args);

    jagt(dir.path())
        .arg("lint")
        .write_stdin(text.clone())
        .assert()
        .success();
    let yaml = packet_yaml(&text);
    let files: Vec<&str> = yaml["inputs"]["files"]
        .as_sequence()
        .expect("files")
        .iter()
        .map(|value| value.as_str().expect("each file is a string"))
        .collect();
    assert_eq!(files, values);
    for raw in [
        '\u{7f}', '\u{80}', '\u{85}', '\u{2028}', '\u{2029}', '\u{feff}', '\u{fffe}', '\u{ffff}',
    ] {
        assert!(!text.contains(raw), "{raw:?} is escaped, not raw");
    }
}

#[test]
fn values_that_a_yaml_1_1_reader_reads_as_other_types_get_quotes() {
    let dir = tempdir().expect("tempdir");
    let quoted = [
        "yes",
        "No",
        "ON",
        "off",
        "y",
        "N",
        "012",
        "1_000",
        "2001-12-14",
        "1:20",
        "+1",
        ".5",
        "<<",
        "=",
    ];
    let plain = [
        ".agents/targets/review.md",
        "src/lib.rs",
        "yesterday",
        "one2three",
    ];
    let flags: Vec<String> = quoted
        .iter()
        .chain(plain.iter())
        .map(|value| format!("--input={value}"))
        .collect();
    let mut args = vec!["t", "--prompt-text", "Go.", "--no-config"];
    args.extend(flags.iter().map(String::as_str));
    let text = render(dir.path(), &args);

    for value in quoted {
        assert!(
            text.contains(&format!("    - '{value}'\n")),
            "{value}: {text}"
        );
    }
    for value in plain {
        assert!(
            text.contains(&format!("    - {value}\n")),
            "{value}: {text}"
        );
    }
    let yaml = packet_yaml(&text);
    let files: Vec<&str> = yaml["inputs"]["files"]
        .as_sequence()
        .expect("files")
        .iter()
        .map(|value| value.as_str().expect("string"))
        .collect();
    let expected: Vec<&str> = quoted.iter().chain(plain.iter()).copied().collect();
    assert_eq!(files, expected);
}

fn render_prompt_file(content: &str) -> std::process::Output {
    let dir = tempdir().expect("tempdir");
    fs::write(dir.path().join("p.md"), content).expect("prompt");
    jagt(dir.path())
        .args([
            "render",
            "t",
            "--prompt",
            "p.md",
            "--no-config",
            "--no-save",
        ])
        .output()
        .expect("jagt runs")
}

#[test]
fn an_empty_frontmatter_is_accepted() {
    let output = render_prompt_file("---\n---\nBody text.\n");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let text = String::from_utf8(output.stdout).expect("utf8");
    assert!(text.contains("prompt: |\n  Body text.\n"), "{text}");
}

#[test]
fn the_frontmatter_closes_only_at_a_line_of_exactly_three_dashes() {
    // `----` and `--- x` do not close the frontmatter; the first `---` does.
    let output = render_prompt_file(
        "---\nrequired_outputs:\n  - word_count\n---\nBody\n----\nmore\n--- x\nend\n",
    );
    assert!(output.status.success());
    let text = String::from_utf8(output.stdout).expect("utf8");
    assert!(
        text.contains("prompt: |\n  Body\n  ----\n  more\n  --- x\n  end\n"),
        "{text}"
    );
    assert!(text.contains("    - word_count\n"), "{text}");

    // A line that only starts with `---` inside the frontmatter is no close.
    let output = render_prompt_file("---\nrequired_outputs: []\n----\nBody\n");
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("closing delimiter"));
}

#[test]
fn a_frontmatter_with_crlf_line_ends_is_read() {
    let output = render_prompt_file("---\r\nrequired_outputs:\r\n  - count\r\n---\r\nBody\r\n");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let text = String::from_utf8(output.stdout).expect("utf8");
    assert!(text.contains("    - count\n"), "{text}");
    assert!(text.contains("Body"), "{text}");
}

#[test]
fn a_file_without_frontmatter_keeps_a_later_dash_line_in_the_body() {
    let output = render_prompt_file("Body\n---\nmore\n");
    assert!(output.status.success());
    let text = String::from_utf8(output.stdout).expect("utf8");
    assert!(
        text.contains("prompt: |\n  Body\n  ---\n  more\n"),
        "{text}"
    );
}

#[test]
fn a_byte_order_mark_does_not_hide_the_frontmatter() {
    let output = render_prompt_file("\u{feff}---\nargs:\n  - a\n---\nBody\n");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let text = String::from_utf8(output.stdout).expect("utf8");
    assert!(text.contains("argv:\n  - a\n"), "{text}");
    assert!(text.contains("prompt: |\n  Body\n"), "{text}");
    assert!(!text.contains('\u{feff}'), "{text}");
}

#[test]
fn a_file_of_only_an_opening_delimiter_is_an_error() {
    let output = render_prompt_file("---\n");
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("closing delimiter"));
}

#[test]
fn spaces_at_line_ends_and_lines_of_only_whitespace_read_back_unchanged() {
    // Each prompt reads back as written, with one newline at its end.
    let prompts = [
        ("x \n", "x \n"),
        ("a  \nb\n", "a  \nb\n"),
        ("a\n   \nb\n", "a\n   \nb\n"),
        ("a\n\t\nb\n", "a\n\t\nb\n"),
        ("   \nx\n", "   \nx\n"),
        ("\t\n  y\n", "\t\n  y\n"),
        ("x\t\n  \n\n", "x\t\n"),
        ("a  ", "a  \n"),
    ];
    for (written, expected) in prompts {
        let output = render_prompt_file(written);
        assert!(
            output.status.success(),
            "{written:?}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        let text = String::from_utf8(output.stdout).expect("utf8");
        assert_eq!(
            packet_yaml(&text)["prompt"].as_str(),
            Some(expected),
            "{written:?}: {text}"
        );
    }
}
