use std::collections::BTreeMap;
use std::env;
use std::ffi::OsString;
use std::fs;
use std::io::{self, Read};
use std::path::{Path, PathBuf};

use clap::{Args, Parser, Subcommand};
use serde::Deserialize;
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
    pub provenance: RenderProvenance,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct RenderProvenance {
    pub source_order: Vec<String>,
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
    if !options.provenance.source_order.is_empty() {
        push_nested_string_list(
            &mut output,
            "source_order",
            &options.provenance.source_order,
            2,
        );
    }
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

#[derive(Debug, Clone, Default, Deserialize)]
struct ProjectConfig {
    #[serde(default)]
    env: EnvConfig,
    #[serde(default)]
    defaults: RenderConfigSource,
    #[serde(default)]
    targets: BTreeMap<String, RenderConfigSource>,
}

#[derive(Debug, Clone, Default, Deserialize)]
struct EnvConfig {
    #[serde(default)]
    allow: Vec<String>,
    #[serde(default)]
    redact: Vec<String>,
}

#[derive(Debug, Clone, Default, Deserialize)]
struct RenderConfigSource {
    target: Option<String>,
    prompt: Option<String>,
    prompt_text: Option<String>,
    args: Option<Vec<String>>,
    inputs: Option<Vec<String>>,
    required_outputs: Option<Vec<String>>,
    allowed_actions: Option<Vec<String>>,
    verification: Option<Vec<String>>,
}

#[derive(Debug, Clone, Default)]
struct EffectiveRenderConfig {
    args: Vec<String>,
    inputs: Vec<String>,
    prompt_path: Option<String>,
    prompt_text: Option<String>,
    required_outputs: Vec<String>,
    allowed_actions: Vec<String>,
    verification: Vec<String>,
}

#[derive(Debug)]
struct LoadedConfig {
    path_label: String,
    config: ProjectConfig,
}

fn build_render_options(args: RenderArgs) -> Result<TaskRenderOptions> {
    let mut effective = EffectiveRenderConfig::default();
    let mut source_order = Vec::new();
    let loaded_config = load_project_config(args.config_path.as_deref(), args.no_config)?;
    let mut env_config = EnvConfig::default();

    if let Some(loaded) = &loaded_config {
        source_order.push("built-in defaults".to_string());
        source_order.push(format!("project config: {}", loaded.path_label));
        env_config = loaded.config.env.clone();

        let defaults = interpolate_source(&loaded.config.defaults, &env_config)?;
        merge_source(&mut effective, defaults);

        if let Some(target_config) = loaded.config.targets.get(&args.target) {
            source_order.push(format!("target config: {}", args.target));
            let target_config = interpolate_source(target_config, &env_config)?;
            merge_source(&mut effective, target_config);
        }
    }

    let prompt_path = args
        .prompt
        .clone()
        .or_else(|| effective.prompt_path.clone());
    if args.prompt_text.is_none()
        && let Some(path) = prompt_path
    {
        let prompt_file = read_prompt_file(Path::new(&path), &env_config)?;
        if prompt_file.frontmatter_seen {
            source_order.push(format!("prompt frontmatter: {path}"));
            merge_source(&mut effective, prompt_file.frontmatter);
        }
        effective.prompt_text = Some(prompt_file.body);
    }

    let cli_source = RenderConfigSource {
        prompt: args.prompt,
        prompt_text: args.prompt_text,
        args: non_empty(args.args),
        inputs: non_empty(args.inputs),
        required_outputs: non_empty(args.required_outputs),
        allowed_actions: non_empty(args.allowed_actions),
        verification: non_empty(args.verification),
        target: None,
    };
    let has_cli_source = source_has_render_values(&cli_source);
    merge_source(&mut effective, cli_source);
    if has_cli_source && !source_order.is_empty() {
        source_order.push("CLI flags".to_string());
    }

    Ok(TaskRenderOptions {
        target: args.target,
        args: effective.args,
        inputs: effective.inputs,
        prompt_text: effective.prompt_text,
        required_outputs: effective.required_outputs,
        allowed_actions: effective.allowed_actions,
        verification: effective.verification,
        provenance: RenderProvenance { source_order },
    })
}

fn non_empty(values: Vec<String>) -> Option<Vec<String>> {
    if values.is_empty() {
        None
    } else {
        Some(values)
    }
}

fn source_has_render_values(source: &RenderConfigSource) -> bool {
    source.prompt.is_some()
        || source.prompt_text.is_some()
        || source.args.is_some()
        || source.inputs.is_some()
        || source.required_outputs.is_some()
        || source.allowed_actions.is_some()
        || source.verification.is_some()
}

fn merge_source(effective: &mut EffectiveRenderConfig, source: RenderConfigSource) {
    let _ = source.target;
    if let Some(args) = source.args {
        effective.args = args;
    }
    if let Some(inputs) = source.inputs {
        effective.inputs = inputs;
    }
    if let Some(prompt) = source.prompt {
        effective.prompt_path = Some(prompt);
        effective.prompt_text = None;
    }
    if let Some(prompt_text) = source.prompt_text {
        effective.prompt_text = Some(prompt_text);
        effective.prompt_path = None;
    }
    if let Some(required_outputs) = source.required_outputs {
        effective.required_outputs = required_outputs;
    }
    if let Some(allowed_actions) = source.allowed_actions {
        effective.allowed_actions = allowed_actions;
    }
    if let Some(verification) = source.verification {
        effective.verification = verification;
    }
}

fn load_project_config(
    config_path: Option<&Path>,
    no_config: bool,
) -> Result<Option<LoadedConfig>> {
    if no_config {
        return Ok(None);
    }

    let (path, explicit) = match config_path {
        Some(path) => (path.to_path_buf(), true),
        None => (PathBuf::from(".jagt/config.toml"), false),
    };

    if !explicit && !path.exists() {
        return Ok(None);
    }

    let content = fs::read_to_string(&path)?;
    let config = toml::from_str(&content).map_err(|error| {
        JagtError::Render(format!(
            "invalid config {}: {error}",
            path.to_string_lossy()
        ))
    })?;

    Ok(Some(LoadedConfig {
        path_label: path.to_string_lossy().into_owned(),
        config,
    }))
}

#[derive(Debug)]
struct PromptFile {
    body: String,
    frontmatter: RenderConfigSource,
    frontmatter_seen: bool,
}

fn read_prompt_file(path: &Path, env_config: &EnvConfig) -> Result<PromptFile> {
    let content = fs::read_to_string(path)?;
    let parsed = parse_prompt_file(&content).map_err(|message| {
        JagtError::Render(format!(
            "invalid prompt {}: {message}",
            path.to_string_lossy()
        ))
    })?;
    Ok(PromptFile {
        body: parsed.body,
        frontmatter: interpolate_source(&parsed.frontmatter, env_config)?,
        frontmatter_seen: parsed.frontmatter_seen,
    })
}

fn parse_prompt_file(content: &str) -> std::result::Result<PromptFile, String> {
    let Some(rest) = content.strip_prefix("---\n") else {
        return Ok(PromptFile {
            body: content.to_string(),
            frontmatter: RenderConfigSource::default(),
            frontmatter_seen: false,
        });
    };
    let Some((frontmatter, body)) = rest.split_once("\n---") else {
        return Err("frontmatter start without closing delimiter".to_string());
    };
    let body = body.trim_start_matches(['\r', '\n']).to_string();
    let frontmatter = if frontmatter.trim().is_empty() {
        RenderConfigSource::default()
    } else {
        serde_yaml::from_str(frontmatter)
            .map_err(|error| format!("frontmatter contains invalid YAML: {error}"))?
    };

    Ok(PromptFile {
        body,
        frontmatter,
        frontmatter_seen: true,
    })
}

fn interpolate_source(
    source: &RenderConfigSource,
    env_config: &EnvConfig,
) -> Result<RenderConfigSource> {
    Ok(RenderConfigSource {
        target: interpolate_option(source.target.as_deref(), env_config)?,
        prompt: interpolate_option(source.prompt.as_deref(), env_config)?,
        prompt_text: interpolate_option(source.prompt_text.as_deref(), env_config)?,
        args: interpolate_list(source.args.as_deref(), env_config)?,
        inputs: interpolate_list(source.inputs.as_deref(), env_config)?,
        required_outputs: interpolate_list(source.required_outputs.as_deref(), env_config)?,
        allowed_actions: interpolate_list(source.allowed_actions.as_deref(), env_config)?,
        verification: interpolate_list(source.verification.as_deref(), env_config)?,
    })
}

fn interpolate_option(value: Option<&str>, env_config: &EnvConfig) -> Result<Option<String>> {
    value
        .map(|value| interpolate_env(value, env_config))
        .transpose()
}

fn interpolate_list(
    values: Option<&[String]>,
    env_config: &EnvConfig,
) -> Result<Option<Vec<String>>> {
    values
        .map(|values| {
            values
                .iter()
                .map(|value| interpolate_env(value, env_config))
                .collect()
        })
        .transpose()
}

fn interpolate_env(value: &str, env_config: &EnvConfig) -> Result<String> {
    let mut output = String::new();
    let mut rest = value;

    while let Some(start) = rest.find("${") {
        output.push_str(&rest[..start]);
        let after_start = &rest[start + 2..];
        let Some(end) = after_start.find('}') else {
            return Err(JagtError::Render(
                "unterminated environment interpolation".to_string(),
            ));
        };
        let name = &after_start[..end];
        validate_env_name(name, env_config)?;
        let replacement = env::var(name)
            .map_err(|_| JagtError::Render(format!("environment variable {name} is not set")))?;
        if looks_secret_value(&replacement) {
            return Err(JagtError::Render(format!(
                "environment variable {name} has a secret-like value"
            )));
        }
        output.push_str(&replacement);
        rest = &after_start[end + 1..];
    }

    output.push_str(rest);
    Ok(output)
}

fn validate_env_name(name: &str, env_config: &EnvConfig) -> Result<()> {
    if name.is_empty()
        || !name
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || ch == '_')
    {
        return Err(JagtError::Render(format!(
            "invalid environment variable reference {name:?}"
        )));
    }
    if !env_config.allow.iter().any(|allowed| allowed == name) {
        return Err(JagtError::Render(format!(
            "environment variable {name} is not allowlisted"
        )));
    }
    if env_config
        .redact
        .iter()
        .any(|pattern| wildcard_match_case_insensitive(pattern, name))
    {
        return Err(JagtError::Render(format!(
            "environment variable {name} matches redact rule"
        )));
    }
    if looks_secret_name(name) {
        return Err(JagtError::Render(format!(
            "environment variable {name} looks secret-like"
        )));
    }
    Ok(())
}

fn wildcard_match_case_insensitive(pattern: &str, value: &str) -> bool {
    wildcard_match(&pattern.to_ascii_uppercase(), &value.to_ascii_uppercase())
}

fn wildcard_match(pattern: &str, value: &str) -> bool {
    let (mut pattern_index, mut value_index) = (0, 0);
    let pattern_bytes = pattern.as_bytes();
    let value_bytes = value.as_bytes();
    let mut star_index = None;
    let mut match_index = 0;

    while value_index < value_bytes.len() {
        if pattern_index < pattern_bytes.len()
            && pattern_bytes[pattern_index] == value_bytes[value_index]
        {
            pattern_index += 1;
            value_index += 1;
        } else if pattern_index < pattern_bytes.len() && pattern_bytes[pattern_index] == b'*' {
            star_index = Some(pattern_index);
            match_index = value_index;
            pattern_index += 1;
        } else if let Some(star) = star_index {
            pattern_index = star + 1;
            match_index += 1;
            value_index = match_index;
        } else {
            return false;
        }
    }

    while pattern_index < pattern_bytes.len() && pattern_bytes[pattern_index] == b'*' {
        pattern_index += 1;
    }

    pattern_index == pattern_bytes.len()
}

fn looks_secret_name(name: &str) -> bool {
    let upper = name.to_ascii_uppercase();
    upper.contains("TOKEN")
        || upper.contains("SECRET")
        || upper.contains("PASSWORD")
        || upper.contains("PRIVATE_KEY")
        || upper.contains("API_KEY")
        || upper.contains("ACCESS_KEY")
        || upper.contains("CREDENTIAL")
        || upper.contains("AUTH")
}

fn looks_secret_value(value: &str) -> bool {
    let lower = value.to_ascii_lowercase();
    lower.starts_with("ghp_")
        || lower.starts_with("gho_")
        || lower.starts_with("github_pat_")
        || lower.starts_with("sk-")
        || lower.contains("private key")
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
    let source_order = mapping_get(map, "provenance")
        .and_then(Value::as_mapping)
        .and_then(|provenance| string_sequence(provenance, "source_order"))
        .unwrap_or_default();

    let mut output = format!(
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
    );
    if !source_order.is_empty() {
        output.push_str("source_order:\n");
        for source in source_order {
            output.push_str(&format!("- {source}\n"));
        }
    }

    Ok(output)
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
    #[arg(long = "prompt")]
    prompt: Option<String>,
    #[arg(long = "prompt-text")]
    prompt_text: Option<String>,
    #[arg(long = "required-output")]
    required_outputs: Vec<String>,
    #[arg(long = "allowed-action")]
    allowed_actions: Vec<String>,
    #[arg(long = "verification")]
    verification: Vec<String>,
    #[arg(long = "config")]
    config_path: Option<PathBuf>,
    #[arg(long = "no-config")]
    no_config: bool,
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
            let options = build_render_options(args)?;
            let packet = render_task_packet(&options)?;
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
            provenance: RenderProvenance::default(),
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

    #[test]
    fn prompt_frontmatter_parser_returns_structured_fields_and_body() {
        let prompt = "\
---
required_outputs:
  - reports/eda/index.html
allowed_actions:
  - inspect dataset
---

Create the report.
";

        let parsed = parse_prompt_file(prompt).expect("prompt parses");

        assert!(parsed.frontmatter_seen);
        assert_eq!(
            parsed.frontmatter.required_outputs,
            Some(vec!["reports/eda/index.html".to_string()])
        );
        assert_eq!(
            parsed.frontmatter.allowed_actions,
            Some(vec!["inspect dataset".to_string()])
        );
        assert_eq!(parsed.body, "Create the report.\n");
    }

    #[test]
    fn redact_wildcard_matching_is_case_insensitive() {
        assert!(wildcard_match_case_insensitive("*_TOKEN", "API_TOKEN"));
        assert!(wildcard_match_case_insensitive("PASSWORD", "password"));
        assert!(!wildcard_match_case_insensitive("*_TOKEN", "DATA_ROOT"));
    }

    #[test]
    fn explain_reports_rendered_source_order_when_present() {
        let mut options = minimal_options();
        options.provenance.source_order = vec![
            "built-in defaults".to_string(),
            "project config: .jagt/config.toml".to_string(),
            "target config: count-chat-message-words".to_string(),
        ];
        let packet = render_task_packet(&options).expect("packet renders");

        let explanation = explain_agent_task(&packet).expect("packet explains");

        assert!(explanation.contains("source_order:\n"));
        assert!(explanation.contains("- project config: .jagt/config.toml\n"));
        assert!(explanation.contains("- target config: count-chat-message-words\n"));
    }
}
