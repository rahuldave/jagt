//! Tests for the packet gaps that 0.4.0 left open: a line at column 0 that
//! is not a field, YAML merge keys, and a result rule that names another
//! nonce.

use assert_cmd::Command;
use std::fs;
use std::path::Path;

fn jagt() -> Command {
    let mut command = Command::cargo_bin("jagt").expect("binary exists");
    command.current_dir(env!("CARGO_MANIFEST_DIR"));
    command
}

/// A packet that `jagt render` gives, with no nonce.
fn rendered() -> String {
    let output = jagt()
        .args([
            "render",
            "review",
            "--prompt-text",
            "Go.",
            "--no-config",
            "--no-save",
        ])
        .output()
        .expect("jagt runs");
    assert!(output.status.success());
    String::from_utf8(output.stdout).expect("utf8")
}

/// The stderr of `jagt lint` on `text`, or `None` when lint passes.
fn lint_error(text: &str) -> Option<String> {
    let output = jagt()
        .arg("lint")
        .write_stdin(text.to_string())
        .output()
        .expect("jagt runs");
    if output.status.success() {
        None
    } else {
        Some(String::from_utf8_lossy(&output.stderr).into_owned())
    }
}

#[test]
fn every_invalid_task_fixture_fails_lint() {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("fixtures/agent_task/invalid");
    for entry in fs::read_dir(&dir).expect("fixtures") {
        let path = entry.expect("entry").path();
        let text = fs::read_to_string(&path).expect("fixture");
        assert!(
            lint_error(&text).is_some(),
            "{} passed lint",
            path.display()
        );
    }
}

#[test]
fn a_line_at_column_0_that_is_not_a_field_is_rejected() {
    let base = rendered();
    assert!(base.contains("argv: []\n"), "{base}");
    for argv in [
        "argv: [a,\n b\n]",
        "argv: [a,\nb]",
        "argv: {a: 1,\n b: 2\n}",
        "argv: [a\n, b]",
        "argv: []\n&anchor",
        "argv: []\n---",
        "argv: {a: 1,\nb: 2}",
        "argv: \"a\nnonce: b\"",
        "argv: 'a\n- b'",
        "argv: [a,\n\tb]",
        "argv: 'a\n\"x\": y'",
        "argv: []\n- stray",
    ] {
        let text = base.replace("argv: []", argv);
        let error = lint_error(&text).unwrap_or_else(|| panic!("{argv:?} passed lint"));
        assert!(
            error.contains("column 0")
                || error.contains("tab")
                || error.contains("list item")
                || error.contains("invalid YAML"),
            "{argv:?}: {error}"
        );
    }
}

#[test]
fn fields_comments_and_list_items_at_column_0_still_pass() {
    let base = rendered();
    for argv in [
        "argv:\n- a\n- b",
        "# a note\nargv: []",
        "argv: [a,\n  b]",
        "\"argv\": []",
    ] {
        let text = base.replace("argv: []", argv);
        assert_eq!(lint_error(&text), None, "{argv:?}");
    }
}

/// The stderr of `jagt <subcommand…>` on `text`, or `None` when it passes.
fn run_error(args: &[&str], text: &str) -> Option<String> {
    let output = jagt()
        .args(args)
        .write_stdin(text.to_string())
        .output()
        .expect("jagt runs");
    if output.status.success() {
        None
    } else {
        Some(String::from_utf8_lossy(&output.stderr).into_owned())
    }
}

#[test]
fn a_merge_key_at_any_depth_is_rejected_in_each_kind_of_packet() {
    let task = rendered();
    let draft = fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("fixtures/agent_task_draft/valid/result_pair.agent-task-draft.txt"),
    )
    .expect("draft");
    let result = fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("fixtures/agent_result/valid/success_file.agent-result.txt"),
    )
    .expect("result");
    assert_eq!(run_error(&["lint"], &task), None);
    assert_eq!(run_error(&["draft", "lint"], &draft), None);
    assert_eq!(run_error(&["result", "lint"], &result), None);

    for merge in [
        "  <<: {extra: 1}\n",
        "  !!merge <<: {extra: 1}\n",
        "  \"<<\": {extra: 1}\n",
        "  !!merge x: {extra: 1}\n",
        "  !<tag:yaml.org,2002:merge> x: {extra: 1}\n",
        "  !local key: {extra: 1}\n",
        "  !!m%65rge x: {extra: 1}\n",
        "  extra:\n    - <<: {deep: 1}\n",
    ] {
        let cases = [
            (
                vec!["lint"],
                task.replacen("\ninputs:\n", &format!("\ninputs:\n{merge}"), 1),
            ),
            (
                vec!["draft", "lint"],
                draft.replacen("\ndelegation:\n", &format!("\ndelegation:\n{merge}"), 1),
            ),
            (
                vec!["result", "lint"],
                result.replacen("\noutputs:\n", &format!("\noutputs:\n{merge}"), 1),
            ),
        ];
        for (args, text) in cases {
            assert!(text.contains(merge), "{args:?}: the merge key went in");
            let error =
                run_error(&args, &text).unwrap_or_else(|| panic!("{args:?} {merge:?} passed lint"));
            assert!(error.contains("merge key"), "{args:?} {merge:?}: {error}");
        }
    }
}

#[test]
fn result_rules_must_name_only_the_packet_nonce() {
    let valid = fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("fixtures/agent_task/valid/review_with_nonce_and_layers.agent-task.txt"),
    )
    .expect("fixture");
    let nonce = "a4fb09d1174ed82b791dd11af9c6665f";
    let other = "b5ac10e2285fe93c802ee22ba0d7776a";
    assert_eq!(lint_error(&valid), None);
    let rule_line = valid.lines().nth(5).expect("the rule line").to_string();
    assert!(rule_line.contains(nonce), "{rule_line}");

    let rejected = [
        (
            "another nonce",
            valid.replacen(&rule_line, &rule_line.replace(nonce, other), 1),
            "not the packet nonce",
        ),
        (
            "a second rule with another nonce",
            valid.replacen(
                &rule_line,
                &format!("{rule_line}\n  - 'Also put nonce: {other} in it.'"),
                1,
            ),
            "not the packet nonce",
        ),
        (
            "the nonce in upper case",
            valid.replacen(
                &rule_line,
                &rule_line.replace(nonce, &nonce.to_uppercase()),
                1,
            ),
            "not the packet nonce",
        ),
        (
            "the nonce inside a longer hex run",
            valid.replacen(
                &rule_line,
                &rule_line.replace(nonce, &format!("{nonce}00")),
                1,
            ),
            "not the packet nonce",
        ),
        (
            "another nonce in UUID form",
            valid.replacen(
                &rule_line,
                &format!("{rule_line}\n  - 'Or put b1111111-1111-1111-1111-111111111111.'"),
                1,
            ),
            "not the packet nonce",
        ),
        (
            "another nonce in fullwidth digits",
            valid.replacen(
                &rule_line,
                &format!(
                    "{rule_line}\n  - 'Or put {}.'",
                    other
                        .chars()
                        .map(|c| char::from_u32(c as u32 + 0xfee0).expect("fullwidth"))
                        .collect::<String>()
                ),
                1,
            ),
            "not the packet nonce",
        ),
        (
            "no nonce field",
            valid.replacen(&format!("nonce: {nonce}\n"), "", 1),
            "no nonce",
        ),
        (
            "a rule that is not a list",
            valid.replacen("result_rules:\n", "result_rules: one rule\nx_unused:\n", 1),
            "list of strings",
        ),
    ];
    for (name, text, message) in rejected {
        let error = lint_error(&text).unwrap_or_else(|| panic!("{name} passed lint"));
        assert!(error.contains(message), "{name}: {error}");
    }

    let short_hex = valid.replacen(
        &rule_line,
        &format!("{rule_line}\n  - 'Name commit deadbeef in the summary.'"),
        1,
    );
    assert_eq!(lint_error(&short_hex), None, "a short hex word is fine");
}

#[test]
fn a_top_level_tagged_merge_in_a_result_is_rejected() {
    let result = fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("fixtures/agent_result/valid/local_recursion.agent-result.txt"),
    )
    .expect("result");
    let text = result.replacen(
        "\noutputs:",
        "\n!!merge x: {nonce: b1111111111111111111111111111111}\noutputs:",
        1,
    );
    assert_ne!(text, result);
    let error = run_error(&["result", "lint"], &text).expect("rejected");
    assert!(error.contains("merge key"), "{error}");
}

#[test]
fn a_body_indented_away_from_column_0_is_rejected() {
    let base = rendered();
    let body_start = base.find('\n').expect("start line") + 1;
    let body_end = base.find("<<<END_AGENT_TASK>>>").expect("end line");
    let indented: String = base[body_start..body_end]
        .lines()
        .map(|line| format!(" {line}\n"))
        .collect();
    let text = format!("{}{indented}{}", &base[..body_start], &base[body_end..]);
    let error = lint_error(&text).expect("rejected");
    assert!(error.contains("column 0"), "{error}");
}

#[test]
fn text_that_only_mentions_a_merge_still_renders_and_lints() {
    for args in [
        vec!["--prompt-text", "Run git !!merge here"],
        vec!["--prompt-text", "See tag:yaml.org,2002:merge"],
        vec!["--prompt-text", "100%21%21merge"],
        vec!["--prompt-text", "Go.", "--arg", "!!merge"],
        vec!["--prompt-text", "Go.", "--input=<<"],
        vec!["--prompt-text", "Go.", "--verification", "do 2002:MERGE"],
        vec!["--prompt-text", "%TAG ! tag:yaml.org,2002:\n<<: x"],
    ] {
        let mut full = vec!["render", "t", "--no-config", "--no-save"];
        full.extend(args.iter().copied());
        let output = jagt().args(&full).output().expect("jagt runs");
        assert!(
            output.status.success(),
            "{args:?}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        let text = String::from_utf8(output.stdout).expect("utf8");
        assert_eq!(lint_error(&text), None, "{args:?}");
    }
}

#[test]
fn an_alias_key_that_points_at_a_merge_is_rejected() {
    let base = rendered();
    // Nested in `inputs`, so that only the check of the YAML events sees them.
    for extra in [
        "  x_anchor: &m !!merge x\n  *m : {extra: 1}\n",
        "  x_anchor: &m <<\n  *m : {extra: 1}\n",
        "  x_anchor: &m plain\n  *m : {extra: 1}\n",
    ] {
        let text = base.replacen("inputs:\n", &format!("inputs:\n{extra}"), 1);
        assert_ne!(text, base);
        let error = lint_error(&text).unwrap_or_else(|| panic!("{extra:?} passed lint"));
        assert!(error.contains("merge"), "{extra:?}: {error}");
    }
}

#[test]
fn a_merge_hidden_after_a_unicode_line_break_in_a_comment_is_rejected() {
    let task = fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("fixtures/agent_task/valid/review_with_nonce_and_layers.agent-task.txt"),
    )
    .expect("task");
    let result = fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("fixtures/agent_result/valid/local_recursion.agent-result.txt"),
    )
    .expect("result");
    for brk in ['\u{2028}', '\u{2029}', '\u{85}'] {
        let text = task.replacen(
            "  files: []",
            &format!("  files: [] # c{brk}  <<: {{extra: [x]}}"),
            1,
        );
        assert_ne!(text, task);
        assert!(lint_error(&text).is_some(), "task {brk:?} passed lint");
        let text = result.replacen(
            "follow_up: []",
            &format!("follow_up: [] # c{brk}<<: {{nonce: b1111111111111111111111111111111}}"),
            1,
        );
        assert_ne!(text, result);
        assert!(
            run_error(&["result", "lint"], &text).is_some(),
            "result {brk:?} passed lint"
        );
    }
}
