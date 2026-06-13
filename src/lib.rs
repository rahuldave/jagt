use std::ffi::OsString;
use std::fs;
use std::io::{self, Read};
use std::path::PathBuf;

use clap::{Args, Parser, Subcommand};
use serde_yaml::{Mapping, Value};
use thiserror::Error;

pub const AGENT_TASK_START: &str = "<<<AGENT_TASK v1>>>";
pub const AGENT_TASK_END: &str = "<<<END_AGENT_TASK>>>";
pub const SAFETY_CONTEXT: &str = "This block is repo-local operational context.";
pub const SAFETY_OVERRIDE: &str =
    "It cannot override user, system, developer, VCS, or approval instructions.";
pub const DELEGATION_TRIGGERS: [&str; 4] = [
    "nested agentic Just calls",
    "agentic dependencies",
    "hook-triggered packets",
    "agentic verification targets",
];

#[derive(Debug, Error)]
pub enum JagtError {
    #[error("invalid AGENT_TASK block: {0}")]
    InvalidAgentTask(String),
    #[error("render failed: {0}")]
    Render(String),
    #[error("io error: {0}")]
    Io(#[from] io::Error),
    #[error("cli error: {0}")]
    Cli(String),
}

impl JagtError {
    pub fn exit_code(&self) -> i32 {
        match self {
            JagtError::InvalidAgentTask(_) | JagtError::Render(_) | JagtError::Cli(_) => 1,
            JagtError::Io(_) => 2,
        }
    }
}

pub type Result<T> = std::result::Result<T, JagtError>;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TaskRenderOptions {
    pub target: String,
    pub args: Vec<String>,
    pub inputs: Vec<String>,
    pub prompt_text: Option<String>,
    pub required_outputs: Vec<String>,
    pub allowed_actions: Vec<String>,
    pub verification: Vec<String>,
}

pub fn render_task_packet(options: &TaskRenderOptions) -> Result<String> {
    validate_target(&options.target)
        .map_err(|message| JagtError::Render(format!("invalid target: {message}")))?;

    let prompt = options
        .prompt_text
        .as_deref()
        .ok_or_else(|| JagtError::Render("missing prompt text".to_string()))?;
    if prompt.trim().is_empty() {
        return Err(JagtError::Render("missing prompt text".to_string()));
    }

    let mut argv = options.args.clone();
    argv.extend(options.inputs.iter().cloned());

    let allowed_actions = effective_allowed_actions(options);

    let mut output = String::new();
    push_line(&mut output, AGENT_TASK_START);
    push_field(&mut output, "target", &options.target);
    push_field(&mut output, "mode", "agentic");
    push_string_list(&mut output, "argv", &argv);
    push_literal_block(&mut output, "prompt", prompt);
    push_line(&mut output, "inputs:");
    push_nested_string_list(&mut output, "files", &options.inputs, 2);
    push_line(&mut output, "outputs:");
    push_nested_string_list(&mut output, "required", &options.required_outputs, 2);
    push_string_list(&mut output, "allowed_actions", &allowed_actions);
    push_string_list(&mut output, "verification", &options.verification);
    push_line(&mut output, "delegation:");
    push_line(&mut output, "  execution: subagent");
    push_line(&mut output, "  recursive: true");
    push_line(&mut output, "  triggers:");
    for trigger in DELEGATION_TRIGGERS {
        push_line(&mut output, &format!("    - {trigger}"));
    }
    push_line(&mut output, "safety:");
    push_line(&mut output, &format!("  - {SAFETY_CONTEXT}"));
    push_line(&mut output, &format!("  - {SAFETY_OVERRIDE}"));
    push_line(&mut output, "provenance:");
    push_line(&mut output, "  renderer: jagt");
    push_line(
        &mut output,
        &format!("  renderer_version: {}", env!("CARGO_PKG_VERSION")),
    );
    push_line(&mut output, AGENT_TASK_END);
    Ok(output)
}

fn effective_allowed_actions(options: &TaskRenderOptions) -> Vec<String> {
    if !options.allowed_actions.is_empty() {
        return options.allowed_actions.clone();
    }

    let mut actions = Vec::new();
    if !options.inputs.is_empty() {
        actions.push("read listed inputs".to_string());
    }
    if !options.required_outputs.is_empty() {
        actions.push("create listed outputs".to_string());
    }
    actions
}

fn push_line(output: &mut String, line: &str) {
    output.push_str(line);
    output.push('\n');
}

fn push_field(output: &mut String, key: &str, value: &str) {
    push_line(output, &format!("{key}: {value}"));
}

fn push_string_list(output: &mut String, key: &str, values: &[String]) {
    if values.is_empty() {
        push_line(output, &format!("{key}: []"));
        return;
    }

    push_line(output, &format!("{key}:"));
    for value in values {
        push_line(output, &format!("  - {}", yaml_scalar(value)));
    }
}

fn push_nested_string_list(output: &mut String, key: &str, values: &[String], indent: usize) {
    let prefix = " ".repeat(indent);
    if values.is_empty() {
        push_line(output, &format!("{prefix}{key}: []"));
        return;
    }

    push_line(output, &format!("{prefix}{key}:"));
    for value in values {
        push_line(output, &format!("{prefix}  - {}", yaml_scalar(value)));
    }
}

fn push_literal_block(output: &mut String, key: &str, value: &str) {
    push_line(output, &format!("{key}: |"));
    for line in value.lines() {
        push_line(output, &format!("  {line}"));
    }
}

fn yaml_scalar(value: &str) -> String {
    if is_plain_yaml_scalar(value) {
        return value.to_string();
    }

    format!("'{}'", value.replace('\'', "''"))
}

fn is_plain_yaml_scalar(value: &str) -> bool {
    if value.is_empty() || value.trim() != value {
        return false;
    }
    if value.contains(": ") || value.contains(" #") {
        return false;
    }
    if value.starts_with([
        '-', '?', ':', ',', '[', ']', '{', '}', '#', '&', '*', '!', '|', '>', '\'', '"', '%', '@',
        '`',
    ]) {
        return false;
    }
    true
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LintOptions {
    pub expect_none: bool,
    pub expect_count: Option<usize>,
}

pub fn lint_agent_task(input: &str, options: LintOptions) -> Result<usize> {
    if options.expect_none {
        if input
            .lines()
            .any(|line| line == AGENT_TASK_START || line == AGENT_TASK_END)
        {
            return Err(JagtError::InvalidAgentTask(
                "expected no AGENT_TASK block".to_string(),
            ));
        }
        return Ok(0);
    }

    let blocks = extract_agent_task_blocks(input)?;
    if blocks.is_empty() {
        return Err(JagtError::InvalidAgentTask(
            "no AGENT_TASK block found".to_string(),
        ));
    }

    if let Some(expected) = options.expect_count
        && blocks.len() != expected
    {
        return Err(JagtError::InvalidAgentTask(format!(
            "expected {expected} block(s), found {}",
            blocks.len()
        )));
    }

    for (index, body) in blocks.iter().enumerate() {
        validate_task_block(body, index + 1)?;
    }

    Ok(blocks.len())
}

fn extract_agent_task_blocks(input: &str) -> Result<Vec<String>> {
    let mut blocks = Vec::new();
    let mut in_block = false;
    let mut body = String::new();

    for line in input.lines() {
        if line == AGENT_TASK_START {
            if in_block {
                return Err(JagtError::InvalidAgentTask(
                    "nested start marker".to_string(),
                ));
            }
            in_block = true;
            body.clear();
            continue;
        }

        if line == AGENT_TASK_END {
            if !in_block {
                return Err(JagtError::InvalidAgentTask(
                    "end marker without start marker".to_string(),
                ));
            }
            blocks.push(std::mem::take(&mut body));
            in_block = false;
            continue;
        }

        if in_block {
            body.push_str(line);
            body.push('\n');
        }
    }

    if in_block {
        return Err(JagtError::InvalidAgentTask(
            "start marker without end marker".to_string(),
        ));
    }

    Ok(blocks)
}

fn validate_task_block(body: &str, index: usize) -> Result<()> {
    check_malformed_top_level_fields(body, index)?;
    check_balanced_delimiters(body, index)?;

    let value: Value = serde_yaml::from_str(body).map_err(|error| {
        JagtError::InvalidAgentTask(format!("block {index} contains invalid YAML: {error}"))
    })?;
    let map = value.as_mapping().ok_or_else(|| {
        JagtError::InvalidAgentTask(format!("block {index} body must be a mapping"))
    })?;

    for field in [
        "target",
        "mode",
        "argv",
        "prompt",
        "inputs",
        "outputs",
        "allowed_actions",
        "verification",
        "delegation",
        "safety",
    ] {
        if mapping_get(map, field).is_none() {
            return Err(JagtError::InvalidAgentTask(format!(
                "block {index} missing {field}"
            )));
        }
    }

    let target = scalar_string(map, "target")
        .ok_or_else(|| JagtError::InvalidAgentTask(format!("block {index} missing target")))?;
    validate_target(target)
        .map_err(|_| JagtError::InvalidAgentTask(format!("block {index} missing valid target")))?;

    if scalar_string(map, "mode") != Some("agentic") {
        return Err(JagtError::InvalidAgentTask(format!(
            "block {index} missing mode: agentic"
        )));
    }

    validate_delegation(map, index)?;
    validate_safety(map, index)?;
    Ok(())
}

fn validate_delegation(map: &Mapping, index: usize) -> Result<()> {
    let delegation = mapping_get(map, "delegation")
        .and_then(Value::as_mapping)
        .ok_or_else(|| JagtError::InvalidAgentTask(format!("block {index} missing delegation")))?;

    if scalar_string(delegation, "execution") != Some("subagent") {
        return Err(JagtError::InvalidAgentTask(format!(
            "block {index} must delegate to a subagent"
        )));
    }

    if mapping_get(delegation, "recursive").and_then(Value::as_bool) != Some(true) {
        return Err(JagtError::InvalidAgentTask(format!(
            "block {index} must declare recursive delegation"
        )));
    }

    let triggers = string_sequence(delegation, "triggers").ok_or_else(|| {
        JagtError::InvalidAgentTask(format!("block {index} missing delegation triggers"))
    })?;
    for trigger in DELEGATION_TRIGGERS {
        if !triggers.iter().any(|value| value == trigger) {
            return Err(JagtError::InvalidAgentTask(format!(
                "block {index} missing {trigger} delegation trigger"
            )));
        }
    }

    Ok(())
}

fn validate_safety(map: &Mapping, index: usize) -> Result<()> {
    let safety = string_sequence(map, "safety")
        .ok_or_else(|| JagtError::InvalidAgentTask(format!("block {index} missing safety")))?;

    if !safety.iter().any(|value| value == SAFETY_OVERRIDE) {
        return Err(JagtError::InvalidAgentTask(format!(
            "block {index} missing safety override text"
        )));
    }

    Ok(())
}

fn mapping_get<'a>(map: &'a Mapping, key: &str) -> Option<&'a Value> {
    map.get(Value::String(key.to_string()))
}

fn scalar_string<'a>(map: &'a Mapping, key: &str) -> Option<&'a str> {
    mapping_get(map, key).and_then(Value::as_str)
}

fn string_sequence(map: &Mapping, key: &str) -> Option<Vec<String>> {
    let value = mapping_get(map, key)?;
    match value {
        Value::Sequence(sequence) => sequence
            .iter()
            .map(|value| value.as_str().map(ToOwned::to_owned))
            .collect(),
        _ => None,
    }
}

fn check_malformed_top_level_fields(body: &str, index: usize) -> Result<()> {
    for line in body.lines() {
        if line.is_empty() || line.starts_with(char::is_whitespace) {
            continue;
        }
        let Some((first, rest)) = split_first_char(line) else {
            continue;
        };
        if !is_field_start(first) {
            continue;
        }
        let token = line.split_whitespace().next().unwrap_or_default();
        if rest.contains(' ') && !token.contains(':') && token.chars().all(is_field_char) {
            return Err(JagtError::InvalidAgentTask(format!(
                "block {index} contains malformed top-level YAML-like field"
            )));
        }
    }
    Ok(())
}

fn split_first_char(value: &str) -> Option<(char, &str)> {
    let mut chars = value.chars();
    let first = chars.next()?;
    Some((first, chars.as_str()))
}

fn check_balanced_delimiters(body: &str, index: usize) -> Result<()> {
    for (open, close, label) in [('[', ']', "square brackets"), ('{', '}', "curly braces")] {
        let open_count = body.chars().filter(|value| *value == open).count();
        let close_count = body.chars().filter(|value| *value == close).count();
        if open_count != close_count {
            return Err(JagtError::InvalidAgentTask(format!(
                "block {index} has unbalanced {label}"
            )));
        }
    }
    Ok(())
}

fn validate_target(target: &str) -> std::result::Result<(), &'static str> {
    if target.is_empty() {
        return Err("target must not be empty");
    }
    if target.chars().all(is_field_char) {
        Ok(())
    } else {
        Err("target may contain only ASCII letters, digits, underscores, dots, and dashes")
    }
}

fn is_field_start(value: char) -> bool {
    value.is_ascii_alphabetic() || value == '_'
}

fn is_field_char(value: char) -> bool {
    value.is_ascii_alphanumeric() || matches!(value, '_' | '.' | '-')
}

pub fn explain_agent_task(input: &str) -> Result<String> {
    let blocks = extract_agent_task_blocks(input)?;
    if blocks.is_empty() {
        return Err(JagtError::InvalidAgentTask(
            "no AGENT_TASK block found".to_string(),
        ));
    }

    validate_task_block(&blocks[0], 1)?;
    let value: Value = serde_yaml::from_str(&blocks[0]).map_err(|error| {
        JagtError::InvalidAgentTask(format!("block 1 contains invalid YAML: {error}"))
    })?;
    let map = value
        .as_mapping()
        .ok_or_else(|| JagtError::InvalidAgentTask("block 1 body must be a mapping".to_string()))?;

    let target = scalar_string(map, "target").unwrap_or("<unknown>");
    let mode = scalar_string(map, "mode").unwrap_or("<unknown>");
    let argv_count = sequence_len(map, "argv");
    let input_count = mapping_get(map, "inputs")
        .and_then(Value::as_mapping)
        .map(|inputs| sequence_len(inputs, "files"))
        .unwrap_or(0);
    let output_count = mapping_get(map, "outputs")
        .and_then(Value::as_mapping)
        .map(|outputs| sequence_len(outputs, "required"))
        .unwrap_or(0);
    let provenance = mapping_get(map, "provenance")
        .and_then(Value::as_mapping)
        .and_then(|provenance| {
            let renderer = scalar_string(provenance, "renderer")?;
            let version = scalar_string(provenance, "renderer_version")?;
            Some(format!("{renderer} {version}"))
        })
        .unwrap_or_else(|| "none".to_string());

    Ok(format!(
        "\
AGENT_TASK v1
target: {target}
mode: {mode}
argv: {argv_count} item(s)
inputs.files: {input_count} item(s)
outputs.required: {output_count} item(s)
delegation: recursive subagent
safety: present
provenance: {provenance}
"
    ))
}

fn sequence_len(map: &Mapping, key: &str) -> usize {
    match mapping_get(map, key) {
        Some(Value::Sequence(values)) => values.len(),
        Some(Value::Null) | None => 0,
        _ => 0,
    }
}

#[derive(Debug, Parser)]
#[command(
    name = "jagt",
    version,
    about = "Deterministic renderer and validator for agentic Just envelopes"
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    Render(RenderArgs),
    Lint(LintArgs),
    Explain(ExplainArgs),
}

#[derive(Debug, Args)]
struct RenderArgs {
    target: String,
    #[arg(long = "arg")]
    args: Vec<String>,
    #[arg(long = "input")]
    inputs: Vec<String>,
    #[arg(long = "prompt-text")]
    prompt_text: Option<String>,
    #[arg(long = "required-output")]
    required_outputs: Vec<String>,
    #[arg(long = "allowed-action")]
    allowed_actions: Vec<String>,
    #[arg(long = "verification")]
    verification: Vec<String>,
}

#[derive(Debug, Args)]
struct LintArgs {
    #[arg(default_value = "-")]
    path: String,
    #[arg(long)]
    expect_count: Option<usize>,
    #[arg(long)]
    expect_none: bool,
}

#[derive(Debug, Args)]
struct ExplainArgs {
    #[command(subcommand)]
    command: ExplainCommand,
}

#[derive(Debug, Subcommand)]
enum ExplainCommand {
    Task(InputPath),
}

#[derive(Debug, Args)]
struct InputPath {
    #[arg(default_value = "-")]
    path: String,
}

pub fn run_cli() -> Result<()> {
    run_with_args(std::env::args_os())
}

fn run_with_args<I, T>(args: I) -> Result<()>
where
    I: IntoIterator<Item = T>,
    T: Into<OsString> + Clone,
{
    let cli = Cli::parse_from(args);
    match cli.command {
        Command::Render(args) => {
            let packet = render_task_packet(&TaskRenderOptions {
                target: args.target,
                args: args.args,
                inputs: args.inputs,
                prompt_text: args.prompt_text,
                required_outputs: args.required_outputs,
                allowed_actions: args.allowed_actions,
                verification: args.verification,
            })?;
            print!("{packet}");
        }
        Command::Lint(args) => {
            let input = read_input(&args.path)?;
            let count = lint_agent_task(
                &input,
                LintOptions {
                    expect_none: args.expect_none,
                    expect_count: args.expect_count,
                },
            )?;
            if args.expect_none {
                println!("no agent task blocks detected");
            } else {
                println!("validated {count} AGENT_TASK block(s)");
            }
        }
        Command::Explain(args) => match args.command {
            ExplainCommand::Task(path) => {
                let input = read_input(&path.path)?;
                print!("{}", explain_agent_task(&input)?);
            }
        },
    }
    Ok(())
}

fn read_input(path: &str) -> Result<String> {
    if path == "-" {
        let mut input = String::new();
        io::stdin().read_to_string(&mut input)?;
        return Ok(input);
    }

    Ok(fs::read_to_string(PathBuf::from(path))?)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn minimal_options() -> TaskRenderOptions {
        TaskRenderOptions {
            target: "count-chat-message-words".to_string(),
            args: vec!["inline:user-message".to_string()],
            inputs: vec!["message.txt".to_string()],
            prompt_text: Some("Count words.".to_string()),
            required_outputs: vec!["word_count".to_string()],
            allowed_actions: Vec::new(),
            verification: vec!["recompute once".to_string()],
        }
    }

    #[test]
    fn renderer_adds_conservative_allowed_actions_when_omitted() {
        let packet = render_task_packet(&minimal_options()).expect("packet renders");

        assert!(
            packet
                .contains("allowed_actions:\n  - read listed inputs\n  - create listed outputs\n")
        );
    }

    #[test]
    fn renderer_rejects_invalid_targets() {
        let mut options = minimal_options();
        options.target = "not valid".to_string();

        let error = render_task_packet(&options).expect_err("invalid target fails");

        assert!(error.to_string().contains("invalid target"));
    }

    #[test]
    fn lint_accepts_rendered_packet() {
        let packet = render_task_packet(&minimal_options()).expect("packet renders");

        let count = lint_agent_task(
            &packet,
            LintOptions {
                expect_none: false,
                expect_count: Some(1),
            },
        )
        .expect("rendered packet lints");

        assert_eq!(count, 1);
    }

    #[test]
    fn renderer_quotes_yaml_sensitive_list_values() {
        let mut options = minimal_options();
        options.allowed_actions = vec!["run command: wc -w".to_string()];

        let packet = render_task_packet(&options).expect("packet renders");

        assert!(packet.contains("  - 'run command: wc -w'\n"));
        lint_agent_task(
            &packet,
            LintOptions {
                expect_none: false,
                expect_count: Some(1),
            },
        )
        .expect("quoted packet lints");
    }

    #[test]
    fn marker_extraction_rejects_nested_start_marker() {
        let input = format!("{AGENT_TASK_START}\n{AGENT_TASK_START}\n{AGENT_TASK_END}\n");

        let error = lint_agent_task(
            &input,
            LintOptions {
                expect_none: false,
                expect_count: None,
            },
        )
        .expect_err("nested marker fails");

        assert!(error.to_string().contains("nested start marker"));
    }
}
