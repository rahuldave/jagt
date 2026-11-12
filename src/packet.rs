//! The packet file of `jagt render`, and the layers of the packet text.
//!
//! `jagt render` saves `.agents/log/packets/<nonce>.json` in the shared log
//! folder, the log folder of the main checkout. A hook later finds the nonce
//! in the result of the fresh agent, and reads this file for the target, the
//! input tree and the worktree.

use std::fs::{self, OpenOptions};
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::{JagtError, Result};

/// The log folder of a checkout, relative to its top folder.
pub const LOG_DIR: &str = ".agents/log";
/// The folder of the packet files, inside the log folder.
pub const PACKETS_DIR: &str = "packets";
/// The number of random bytes in a nonce. The nonce is their hex form.
pub const NONCE_BYTES: usize = 16;
/// The version of the form of the packet file.
pub const PACKET_FILE_VERSION: u32 = 1;

/// The saved facts of one packet, as `packets/<nonce>.json` holds them.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PacketRecord {
    /// The version of this form, now 1.
    pub version: u32,
    /// The random value that the packet text and the result both hold.
    pub nonce: String,
    /// The target of the packet, for example `review`.
    pub target: String,
    /// The worktree tree when the packet was made, as a git tree hash.
    pub input_tree: String,
    /// The absolute path of the worktree in which `jagt render` ran.
    pub worktree: String,
    /// The SHA-256 of the packet text, the exact bytes on stdout, in hex.
    pub packet_sha256: String,
}

/// The git facts that `jagt render` needs, found from the current folder.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitContext {
    /// The top folder of the current worktree.
    pub worktree: PathBuf,
    /// The top folder of the main checkout. Its log folder is the shared one.
    pub main_checkout: PathBuf,
}

impl GitContext {
    /// Finds the worktree and the main checkout from `cwd`.
    ///
    /// It gives `None` outside a git worktree, for example in a temporary
    /// folder or inside `.git`, and when git cannot start. It fails when the main
    /// repository is bare, because a bare repository has no log folder.
    pub fn discover(cwd: &Path) -> Result<Option<Self>> {
        // A git that cannot start counts as no worktree, so render warns and
        // prints the text, as it does outside a worktree.
        let Ok(inside) = run_git(cwd, &["rev-parse", "--is-inside-work-tree"], &[]) else {
            return Ok(None);
        };
        if !inside.success || inside.stdout.trim() != "true" {
            return Ok(None);
        }
        let worktree = git_line(cwd, &["rev-parse", "--show-toplevel"])?;
        let worktree = PathBuf::from(worktree);
        let main_checkout = main_checkout(&worktree)?;
        Ok(Some(Self {
            worktree,
            main_checkout,
        }))
    }

    /// The shared log folder, `.agents/log` of the main checkout.
    pub fn shared_log_dir(&self) -> PathBuf {
        self.main_checkout.join(LOG_DIR)
    }
}

/// The main checkout is the first entry of `git worktree list`. Git keeps
/// that order for linked worktrees and for submodules alike, where the parent
/// of `--git-common-dir` is not always the checkout.
fn main_checkout(worktree: &Path) -> Result<PathBuf> {
    let output = git_output(worktree, &["worktree", "list", "--porcelain", "-z"], &[])?;
    let mut fields = output.split('\0');
    let first = fields
        .next()
        .and_then(|field| field.strip_prefix("worktree "))
        .ok_or_else(|| render_error("git worktree list gave no main worktree"))?;
    for field in fields {
        if field.is_empty() {
            break;
        }
        if field == "bare" {
            return Err(render_error(
                "the main repository is bare, so it has no shared log folder",
            ));
        }
    }
    Ok(PathBuf::from(first))
}

/// Computes the worktree tree: the tree of all files in the worktree, staged
/// or not, with ignored files left out. It uses a temporary index, so the
/// real index does not change:
///
/// ```sh
/// GIT_INDEX_FILE=<tmp> git read-tree HEAD   # skipped before the first commit
/// GIT_INDEX_FILE=<tmp> git add -A
/// GIT_INDEX_FILE=<tmp> git write-tree
/// ```
pub fn worktree_tree(worktree: &Path, scratch_name: &str) -> Result<String> {
    let index = TempIndex::new(scratch_name)?;
    let env = [("GIT_INDEX_FILE", index.path.as_os_str())];
    if git_output(
        worktree,
        &["rev-parse", "--verify", "--quiet", "HEAD^{commit}"],
        &[],
    )
    .is_ok()
    {
        git_output(worktree, &["read-tree", "HEAD"], &env)?;
    }
    git_output(worktree, &["add", "-A"], &env)?;
    let tree = git_output(worktree, &["write-tree"], &env)?;
    Ok(tree.trim().to_string())
}

/// A path for a temporary index outside the repository, removed on drop.
/// The file must not exist yet, because `git read-tree` makes it.
struct TempIndex {
    dir: PathBuf,
    path: PathBuf,
}

impl TempIndex {
    fn new(name: &str) -> Result<Self> {
        let dir = std::env::temp_dir().join(format!("jagt-index-{name}"));
        // create_dir fails if the folder exists, so no other process owns it.
        fs::create_dir(&dir)?;
        let path = dir.join("index");
        Ok(Self { dir, path })
    }
}

impl Drop for TempIndex {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.dir);
    }
}

/// The variables that `git rev-parse --local-env-vars` lists in git 2.54,
/// and two more that change where git looks, `GIT_INTERNAL_SUPER_PREFIX`
/// and `GIT_NAMESPACE`.
pub const LOCAL_ENV_VARS: [&str; 17] = [
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CONFIG",
    "GIT_CONFIG_PARAMETERS",
    "GIT_CONFIG_COUNT",
    "GIT_OBJECT_DIRECTORY",
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_IMPLICIT_WORK_TREE",
    "GIT_GRAFT_FILE",
    "GIT_INDEX_FILE",
    "GIT_NO_REPLACE_OBJECTS",
    "GIT_REPLACE_REF_BASE",
    "GIT_PREFIX",
    "GIT_INTERNAL_SUPER_PREFIX",
    "GIT_SHALLOW_FILE",
    "GIT_COMMON_DIR",
    "GIT_NAMESPACE",
];

/// The result of one git call.
struct GitRun {
    success: bool,
    stdout: String,
    stderr: String,
}

/// Runs git in `dir`. It fails only when git cannot start.
fn run_git(dir: &Path, args: &[&str], env: &[(&str, &std::ffi::OsStr)]) -> Result<GitRun> {
    let mut command = Command::new("git");
    command.arg("-C").arg(dir).args(args).stdin(Stdio::null());
    // A git hook or `git rebase --exec` sets variables such as GIT_DIR and
    // GIT_WORK_TREE. They would point git at another worktree or index, so
    // jagt removes them and finds the repository from `dir` alone.
    for name in LOCAL_ENV_VARS {
        command.env_remove(name);
    }
    for (key, value) in env {
        command.env(key, value);
    }
    let output = command
        .output()
        .map_err(|error| render_error(&format!("could not run git: {error}")))?;
    Ok(GitRun {
        success: output.status.success(),
        stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
        stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
    })
}

/// Runs git in `dir` and returns its stdout. A failure carries git's stderr.
fn git_output(dir: &Path, args: &[&str], env: &[(&str, &std::ffi::OsStr)]) -> Result<String> {
    let run = run_git(dir, args, env)?;
    if !run.success {
        return Err(render_error(&format!(
            "git {} failed: {}",
            args.join(" "),
            run.stderr.trim()
        )));
    }
    Ok(run.stdout)
}

fn git_line(dir: &Path, args: &[&str]) -> Result<String> {
    Ok(git_output(dir, args, &[])?
        .trim_end_matches('\n')
        .to_string())
}

/// A new random nonce: 16 bytes from the system, in lowercase hex.
///
/// The first digit is always a letter from `a` to `f`. A YAML reader then
/// always reads the nonce as a string, never as a number such as `123e45`.
/// jagt draws again until the first digit is a letter.
pub fn new_nonce() -> Result<String> {
    loop {
        let mut bytes = [0u8; NONCE_BYTES];
        getrandom::fill(&mut bytes)
            .map_err(|error| render_error(&format!("could not get random bytes: {error}")))?;
        let nonce = to_hex(&bytes);
        if is_nonce(&nonce) {
            return Ok(nonce);
        }
    }
}

/// True when `value` has the form of a nonce: 32 lowercase hex digits, of
/// which the first is a letter from `a` to `f`.
pub fn is_nonce(value: &str) -> bool {
    value.len() == NONCE_BYTES * 2
        && value.as_bytes()[0].is_ascii_lowercase()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

/// The SHA-256 of `text`, in lowercase hex.
pub fn sha256_hex(text: &str) -> String {
    to_hex(&Sha256::digest(text.as_bytes()))
}

fn to_hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

/// Saves `record` as `<log_dir>/packets/<nonce>.json` and returns the path.
///
/// It makes the log folder when it is missing, with a `.gitignore` that holds
/// `*`, as `jlog` does, so git never sees the packets. It never replaces a
/// file: a packet file with the same name stops the render.
pub fn save_record(log_dir: &Path, record: &PacketRecord) -> Result<PathBuf> {
    if !is_nonce(&record.nonce) {
        return Err(render_error(
            "the nonce of a packet file must be 32 hex digits",
        ));
    }
    let checkout = log_dir
        .parent()
        .and_then(Path::parent)
        .ok_or_else(|| render_error("the log folder has no checkout"))?;
    let packets = log_dir.join(PACKETS_DIR);
    for dir in [
        checkout.join(".agents"),
        log_dir.to_path_buf(),
        packets.clone(),
    ] {
        make_real_dir(&dir)?;
    }
    // Each folder gets its own `.gitignore`, so the packets stay out of every
    // worktree tree, also when an older `.agents/log/.gitignore` lacks `*`.
    write_new(&log_dir.join(".gitignore"), b"*\n").or_else(ignore_exists)?;
    write_new(&packets.join(".gitignore"), b"*\n").or_else(ignore_exists)?;

    let mut json = serde_json::to_string_pretty(record)
        .map_err(|error| render_error(&format!("could not write the packet file: {error}")))?;
    json.push('\n');
    let path = packets.join(format!("{}.json", record.nonce));
    write_new(&path, json.as_bytes()).map_err(|error| {
        if error.kind() == io::ErrorKind::AlreadyExists {
            render_error(&format!(
                "the packet file {} exists already",
                path.display()
            ))
        } else {
            JagtError::Io(error)
        }
    })?;
    Ok(path)
}

/// Makes `dir` when it is missing. A symlink, or a path that is not a
/// folder, stops the render, so a symlink in a repository cannot send the
/// packet files out of the log folder.
fn make_real_dir(dir: &Path) -> Result<()> {
    match fs::symlink_metadata(dir) {
        Ok(meta) if meta.file_type().is_symlink() => Err(render_error(&format!(
            "{} is a symlink, so jagt does not write in it",
            dir.display()
        ))),
        Ok(meta) if meta.is_dir() => Ok(()),
        Ok(_) => Err(render_error(&format!("{} is not a folder", dir.display()))),
        Err(error) if error.kind() == io::ErrorKind::NotFound => match fs::create_dir(dir) {
            Ok(()) => Ok(()),
            Err(error) if error.kind() == io::ErrorKind::AlreadyExists => make_real_dir(dir),
            Err(error) => Err(JagtError::Io(error)),
        },
        Err(error) => Err(JagtError::Io(error)),
    }
}

/// Writes a new file. `create_new` fails on any existing path, a symlink too.
fn write_new(path: &Path, bytes: &[u8]) -> io::Result<()> {
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    file.write_all(bytes)?;
    file.sync_all()
}

fn ignore_exists(error: io::Error) -> io::Result<()> {
    if error.kind() == io::ErrorKind::AlreadyExists {
        Ok(())
    } else {
        Err(error)
    }
}

/// One layer of the packet text: where it came from, and its text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Layer {
    /// A label for the provenance, for example `language layer: .agents/targets/python/docs.md`.
    pub label: String,
    /// The text of the layer.
    pub text: String,
}

/// Reads the language layers and the repository text of `target` from the
/// checkout at `root`:
///
/// - `.agents/targets/<language>/<target>.md`, for each language in the
///   `profiles` list of `.agents/stack.json`, in the order of that list;
/// - `.agents/targets/<target>.md`.
///
/// A missing file is not an error, and neither is a missing `stack.json`.
/// An empty file adds no layer.
pub fn read_layers(root: &Path, target: &str) -> Result<Vec<Layer>> {
    let mut layers = Vec::new();
    for language in stack_languages(root)? {
        let relative = format!(".agents/targets/{language}/{target}.md");
        if let Some(text) = read_optional(root, &relative, ".agents/targets")? {
            layers.push(Layer {
                label: format!("language layer: {relative}"),
                text,
            });
        }
    }
    let relative = format!(".agents/targets/{target}.md");
    if let Some(text) = read_optional(root, &relative, ".agents/targets")? {
        layers.push(Layer {
            label: format!("repository text: {relative}"),
            text,
        });
    }
    Ok(layers)
}

/// The languages of the stack: the `profiles` list of `.agents/stack.json`.
/// Each name must be a plain folder name, so a name such as `..` cannot send
/// the read out of `.agents/targets`.
pub fn stack_languages(root: &Path) -> Result<Vec<String>> {
    let Some(content) = read_inside(root, ".agents/stack.json", ".agents/stack.json")? else {
        return Ok(Vec::new());
    };
    let invalid = |message: &str| render_error(&format!("invalid .agents/stack.json: {message}"));
    let value: serde_json::Value =
        serde_json::from_str(&content).map_err(|error| invalid(&error.to_string()))?;
    let profiles = match value.get("profiles") {
        None | Some(serde_json::Value::Null) => return Ok(Vec::new()),
        Some(serde_json::Value::Array(profiles)) => profiles,
        Some(_) => return Err(invalid("profiles must be a list of names")),
    };
    let mut languages: Vec<String> = Vec::new();
    for profile in profiles {
        let name = profile
            .as_str()
            .ok_or_else(|| invalid("profiles must be a list of names"))?;
        if !is_language_name(name) {
            return Err(invalid(&format!(
                "profile name {name:?} is not a plain name"
            )));
        }
        if !languages.iter().any(|seen| seen == name) {
            languages.push(name.to_string());
        }
    }
    Ok(languages)
}

/// A language name starts with a letter or a digit, and holds only ASCII
/// letters, digits, `_`, `.` and `-`.
fn is_language_name(name: &str) -> bool {
    name.chars()
        .next()
        .is_some_and(|c| c.is_ascii_alphanumeric())
        && name
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '_' | '.' | '-'))
}

/// Reads a layer file. A missing file and a file of blank lines give `None`.
fn read_optional(root: &Path, relative: &str, allowed: &str) -> Result<Option<String>> {
    Ok(read_inside(root, relative, allowed)?.filter(|text| !text.trim().is_empty()))
}

/// Reads `root/relative`. A missing file gives `None`. The real path of the
/// file must be `root/allowed` or inside it, with `root` as a real path. So a
/// symlink in the repository cannot put another file into the packet, such
/// as an ignored `.env` file, `.git/config` or a key outside the worktree.
fn read_inside(root: &Path, relative: &str, allowed: &str) -> Result<Option<String>> {
    let path = root.join(relative);
    let real = match fs::canonicalize(&path) {
        Ok(real) => real,
        Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(None),
        Err(error) => {
            return Err(render_error(&format!(
                "could not read {}: {error}",
                path.display()
            )));
        }
    };
    let real_allowed = fs::canonicalize(root)?.join(allowed);
    if !real.starts_with(&real_allowed) {
        return Err(render_error(&format!(
            "{relative} leads outside {allowed} of the worktree, so jagt does not read it"
        )));
    }
    match fs::read_to_string(&real) {
        Ok(text) => Ok(Some(text)),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(render_error(&format!(
            "could not read {}: {error}",
            path.display()
        ))),
    }
}

/// Joins the layers in order, with one blank line between two layers.
pub fn join_layers(layers: &[Layer]) -> String {
    let mut joined = String::new();
    for layer in layers {
        if !joined.is_empty() {
            joined.push_str("\n\n");
        }
        joined.push_str(layer.text.trim_end());
    }
    joined
}

fn render_error(message: &str) -> JagtError {
    JagtError::Render(message.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn nonce_is_32_hex_digits_and_new_each_time() {
        let first = new_nonce().expect("nonce");
        let second = new_nonce().expect("nonce");
        assert!(is_nonce(&first), "{first}");
        assert_ne!(first, second);
    }

    #[test]
    fn is_nonce_rejects_other_forms() {
        assert!(!is_nonce("ABCDEF0123456789abcdef0123456789"));
        // A nonce of digits, or a digit and an `e`, reads as a YAML number.
        assert!(!is_nonce("12345678901234567890123456789012"));
        assert!(!is_nonce("1234567890123456e890123456789012"));
        assert!(is_nonce("a2345678901234567890123456789012"));
        assert!(!is_nonce("abc"));
        assert!(!is_nonce("../../../../etc/passwd/xxxxxxxxxx"));
    }

    #[test]
    fn sha256_matches_a_known_value() {
        assert_eq!(
            sha256_hex("abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn join_layers_puts_one_blank_line_between_layers() {
        let layer = |text: &str| Layer {
            label: String::new(),
            text: text.to_string(),
        };
        assert_eq!(join_layers(&[layer("a\n"), layer("b\n\n")]), "a\n\nb");
        assert_eq!(join_layers(&[]), "");
    }

    #[test]
    fn language_names_must_be_plain() {
        assert!(is_language_name("python"));
        assert!(is_language_name("c-sharp"));
        assert!(!is_language_name(".."));
        assert!(!is_language_name("a/b"));
        assert!(!is_language_name(""));
    }
}
