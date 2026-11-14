//! The packet file of `jagt render`, and the layers of the packet text.
//!
//! `jagt render` saves `.agents/log/packets/<nonce>.json` in the shared log
//! folder, the log folder of the main checkout. A hook later finds the nonce
//! in the result of the fresh agent, and reads this file for the target, the
//! input tree and the worktree.

use std::fs::{self, OpenOptions};
use std::io;
#[cfg(not(unix))]
use std::io::Write;
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
    /// Find the worktree and the main checkout from `cwd`.
    ///
    /// It gives `None` outside a git worktree, for example in a temporary
    /// folder or inside `.git`, and when git cannot start. It fails when the main
    /// repository is bare, because a bare repository has no log folder, and when
    /// a later git call fails.
    ///
    /// # Arguments
    ///
    /// * `cwd` - the folder to start from, which `jagt render` takes as the current folder
    ///
    /// # Returns
    ///
    /// The worktree and the main checkout, or `None` outside a git worktree.
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

    /// Give the shared log folder, `.agents/log` of the main checkout.
    ///
    /// # Returns
    ///
    /// The path of the shared log folder. It may not exist yet.
    pub fn shared_log_dir(&self) -> PathBuf {
        self.main_checkout.join(LOG_DIR)
    }
}

/// Find the main checkout of a worktree.
///
/// The main checkout is the first entry of `git worktree list`. Git keeps
/// that order for linked worktrees and for submodules alike, where the parent
/// of `--git-common-dir` is not always the checkout. It fails when git fails,
/// when the list is empty, and when the main repository is bare.
///
/// # Arguments
///
/// * `worktree` - the top folder of a worktree
///
/// # Returns
///
/// The top folder of the main checkout.
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

/// Find the folder that jagt reads the project config and the layers from: the top of the git
/// worktree that holds `cwd`, or `cwd` itself outside a worktree or when git cannot start.
///
/// # Arguments
///
/// * `cwd` - the folder that jagt runs in
///
/// # Returns
///
/// The project root.
pub fn project_root(cwd: &Path) -> PathBuf {
    match run_git(cwd, &["rev-parse", "--show-toplevel"], &[]) {
        Ok(run) if run.success && !run.stdout.trim().is_empty() => {
            PathBuf::from(run.stdout.trim_end_matches('\n'))
        }
        _ => cwd.to_path_buf(),
    }
}

/// Compute the worktree tree: the index with every change in the worktree,
/// staged or not, plus the untracked files that are not ignored. A file that
/// the index holds stays in the tree, also when `.gitignore` names it. The
/// commit gates compute the tree the same way. So a commit of all the changes
/// has this tree, if no entry is assume-unchanged or skip-worktree.
///
/// It works on a copy of the index and a temporary object store, so the real
/// index does not change and `.git/objects` gets no new object. Git can still
/// update the time of an object that exists there:
///
/// ```sh
/// cp -p <index> <tmp>/index            # keeps the time of the index
/// GIT_INDEX_FILE=<tmp>/index GIT_OBJECT_DIRECTORY=<tmp>/objects \
///   GIT_ALTERNATE_OBJECT_DIRECTORIES=<objects> \
///   git -c core.splitIndex=false add -A -- :/
/// ... git -c core.splitIndex=false write-tree
/// ```
///
/// The copy keeps the time of the real index. Git compares the time of each
/// file with it, so a file that changed in the same second as the index is
/// still read again. jagt starts from `git read-tree HEAD` instead of the copy
/// when there is no index, or when an entry of the index is assume-unchanged
/// or skip-worktree, because `git add` does not see a change in such a file.
/// Before the first commit, it then starts from an empty index.
/// `core.splitIndex=false` keeps git from writing a shared index file into
/// the git folder for the copy.
///
/// It fails when the folder of the temporary index exists already, or when
/// git fails.
///
/// # Arguments
///
/// * `worktree` - the top folder of the worktree
/// * `scratch_name` - the end of the name of the temporary folder, `jagt-index-<name>`;
///   `jagt render` gives the nonce
///
/// # Returns
///
/// The hash of the tree, as `git write-tree` prints it, with no newline.
pub fn worktree_tree(worktree: &Path, scratch_name: &str) -> Result<String> {
    let objects = worktree.join(git_line(worktree, &["rev-parse", "--git-path", "objects"])?);
    let real_index = worktree.join(git_line(worktree, &["rev-parse", "--git-path", "index"])?);
    let scratch = TempIndex::new(scratch_name)?;
    let temp_objects = scratch.dir.join("objects");
    fs::create_dir(&temp_objects)?;
    let alternates = alternate_entry(&std::path::absolute(&objects)?);
    let env = [
        ("GIT_INDEX_FILE", scratch.path.as_os_str()),
        ("GIT_OBJECT_DIRECTORY", temp_objects.as_os_str()),
        ("GIT_ALTERNATE_OBJECT_DIRECTORIES", alternates.as_os_str()),
    ];
    let copied = real_index.is_file()
        && copy_with_time(&real_index, &scratch.path)?
        && index_hides_no_change(worktree, &env)?;
    if !copied {
        let _ = fs::remove_file(&scratch.path);
        if git_output(
            worktree,
            &["rev-parse", "--verify", "--quiet", "HEAD^{commit}"],
            &[],
        )
        .is_ok()
        {
            git_output(
                worktree,
                &[NO_SPLIT_INDEX[0], NO_SPLIT_INDEX[1], "read-tree", "HEAD"],
                &env,
            )?;
        }
    }
    // A temporary folder of the system inside the worktree, as a TMPDIR can
    // give, must not put the copy and the store into the tree.
    let exclude = scratch_pathspec(worktree, &scratch.dir);
    let mut add: Vec<&std::ffi::OsStr> = [
        NO_SPLIT_INDEX[0],
        NO_SPLIT_INDEX[1],
        "add",
        "-A",
        "--",
        ":/",
    ]
    .map(std::ffi::OsStr::new)
    .to_vec();
    if let Some(exclude) = &exclude {
        add.push(exclude);
    }
    git_output(worktree, &add, &env)?;
    let tree = git_output(
        worktree,
        &[NO_SPLIT_INDEX[0], NO_SPLIT_INDEX[1], "write-tree"],
        &env,
    )?;
    Ok(tree.trim().to_string())
}

/// The pathspec that leaves the temporary folder `scratch` out of `git add`,
/// when it is inside the worktree.
///
/// # Arguments
///
/// * `worktree` - the top folder of the worktree
/// * `scratch` - the path of the temporary folder
///
/// # Returns
///
/// `:(top,literal,exclude)<path>`, with the path from the top of the
/// worktree, or `None` when the folder is outside the worktree, or inside a
/// submodule or a nested repository.
fn scratch_pathspec(worktree: &Path, scratch: &Path) -> Option<std::ffi::OsString> {
    let top = fs::canonicalize(worktree).ok()?;
    let real = fs::canonicalize(scratch).ok()?;
    let inside = real.strip_prefix(&top).ok()?;
    // git refuses a pathspec inside a submodule or a nested repository, and
    // its `git add -A` does not go inside one, so no exclude is needed there.
    let mut folder = top.clone();
    for part in inside.parent()?.components() {
        folder.push(part);
        if fs::symlink_metadata(folder.join(".git")).is_ok() {
            return None;
        }
    }
    let mut spec = std::ffi::OsString::from(":(top,literal,exclude)");
    spec.push(inside.as_os_str());
    Some(spec)
}

/// The arguments that turn the split index off for one git call. With a split
/// index, each write of the temporary index would leave a new
/// `sharedindex.<hash>` file in the git folder.
const NO_SPLIT_INDEX: [&str; 2] = ["-c", "core.splitIndex=false"];

/// Copy the index `from` to `to`, and give the copy the time of `from`.
///
/// # Arguments
///
/// * `from` - the real index
/// * `to` - the path of the copy, which must not exist
///
/// # Returns
///
/// `Ok(true)` when the copy is made, `Ok(false)` when `from` is gone, as
/// after a `git rm --cached` of every file, or the I/O error.
fn copy_with_time(from: &Path, to: &Path) -> Result<bool> {
    let mut source = match fs::File::open(from) {
        Ok(file) => file,
        Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(false),
        Err(error) => return Err(JagtError::Io(error)),
    };
    let modified = source.metadata()?.modified()?;
    let mut target = OpenOptions::new().write(true).create_new(true).open(to)?;
    io::copy(&mut source, &mut target)?;
    target.set_modified(modified)?;
    Ok(true)
}

/// Check the copy of the index for an entry whose changes `git add` does not
/// see: an assume-unchanged entry, which `git ls-files -v` shows with a small
/// letter, or a skip-worktree entry, which it shows with `S`.
///
/// # Arguments
///
/// * `worktree` - the top folder of the worktree
/// * `env` - the variables that point git at the copy
///
/// # Returns
///
/// True when the copy has no such entry, false when it has one. It fails
/// when git cannot read the copy, such as a broken index, as git itself and
/// the gate fail.
fn index_hides_no_change(worktree: &Path, env: &[(&str, &std::ffi::OsStr)]) -> Result<bool> {
    let listing = git_output(
        worktree,
        &[NO_SPLIT_INDEX[0], NO_SPLIT_INDEX[1], "ls-files", "-v"],
        env,
    )?;
    Ok(!listing.lines().any(|line| {
        line.chars()
            .next()
            .is_some_and(|tag| tag.is_ascii_lowercase() || tag == 'S')
    }))
}

/// The value of `GIT_ALTERNATE_OBJECT_DIRECTORIES` that names one folder.
/// Git splits the value at the path separator, so a path that holds the
/// separator, or that starts with a double quote, goes in double quotes with
/// C escapes, as git reads it.
///
/// # Arguments
///
/// * `objects` - the absolute path of the object store
///
/// # Returns
///
/// The value of the variable.
fn alternate_entry(objects: &Path) -> std::ffi::OsString {
    let separator = if cfg!(windows) { ';' } else { ':' };
    let text = objects.as_os_str();
    let plain = text.to_string_lossy();
    if !plain.contains(separator) && !plain.starts_with('"') {
        return text.to_os_string();
    }
    #[cfg(unix)]
    {
        use std::os::unix::ffi::{OsStrExt, OsStringExt};
        let mut quoted = vec![b'"'];
        for &byte in text.as_bytes() {
            match byte {
                b'"' | b'\\' => quoted.extend([b'\\', byte]),
                b'\n' => quoted.extend(b"\\n"),
                b'\t' => quoted.extend(b"\\t"),
                _ => quoted.push(byte),
            }
        }
        quoted.push(b'"');
        std::ffi::OsString::from_vec(quoted)
    }
    #[cfg(not(unix))]
    {
        let escaped = plain.replace('\\', "\\\\").replace('"', "\\\"");
        std::ffi::OsString::from(format!("\"{escaped}\""))
    }
}

/// A temporary folder for the index and the object store, in the temporary
/// folder of the system, removed on drop. A `TMPDIR` can put it inside the
/// worktree; [`worktree_tree`] then leaves it out of the tree. The index file does not exist yet.
struct TempIndex {
    /// The folder that holds the index, in the system's temporary folder.
    dir: PathBuf,
    /// The path of the index file, inside `dir`.
    path: PathBuf,
}

impl TempIndex {
    /// Make the folder `jagt-index-<name>` in the system's temporary folder.
    ///
    /// It fails when the folder exists already.
    ///
    /// # Arguments
    ///
    /// * `name` - the end of the folder's name
    ///
    /// # Returns
    ///
    /// The temporary index. Its folder exists, and its index file does not.
    fn new(name: &str) -> Result<Self> {
        // git runs in the worktree, so a relative TMPDIR must not reach it.
        let dir = std::path::absolute(std::env::temp_dir())?.join(format!("jagt-index-{name}"));
        // create_dir fails if the folder exists, so no other process owns it.
        fs::create_dir(&dir)?;
        let path = dir.join("index");
        Ok(Self { dir, path })
    }
}

impl Drop for TempIndex {
    /// Remove the folder and the index in it. An error is ignored.
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.dir);
    }
}

/// The variables that `git rev-parse --local-env-vars` lists in git 2.54,
/// two more that change where git looks, `GIT_INTERNAL_SUPER_PREFIX` and
/// `GIT_NAMESPACE`, and the four that change how git reads a pathspec, such
/// as `:/`.
pub const LOCAL_ENV_VARS: [&str; 21] = [
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
    "GIT_LITERAL_PATHSPECS",
    "GIT_GLOB_PATHSPECS",
    "GIT_NOGLOB_PATHSPECS",
    "GIT_ICASE_PATHSPECS",
];

/// The result of one git call.
struct GitRun {
    /// True when git exited with status 0.
    success: bool,
    /// What git wrote to standard output, with any bytes that are not UTF-8 replaced.
    stdout: String,
    /// What git wrote to standard error, with any bytes that are not UTF-8 replaced.
    stderr: String,
}

/// Run git in `dir`, with standard input closed and without the variables of
/// [`LOCAL_ENV_VARS`]. It fails only when git cannot start.
///
/// # Arguments
///
/// * `dir` - the folder that git runs in, given to git as `-C`
/// * `args` - the arguments of git
/// * `env` - the variables to set for this call, such as `GIT_INDEX_FILE`
///
/// # Returns
///
/// Whether git succeeded, and its output.
fn run_git<S: AsRef<std::ffi::OsStr>>(
    dir: &Path,
    args: &[S],
    env: &[(&str, &std::ffi::OsStr)],
) -> Result<GitRun> {
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

/// Run git in `dir` as [`run_git`] does, and fail when git fails. The error
/// carries git's stderr.
///
/// # Arguments
///
/// * `dir` - the folder that git runs in
/// * `args` - the arguments of git
/// * `env` - the variables to set for this call
///
/// # Returns
///
/// The stdout of git.
fn git_output<S: AsRef<std::ffi::OsStr>>(
    dir: &Path,
    args: &[S],
    env: &[(&str, &std::ffi::OsStr)],
) -> Result<String> {
    let run = run_git(dir, args, env)?;
    if !run.success {
        let shown: Vec<String> = args
            .iter()
            .map(|arg| arg.as_ref().to_string_lossy().into_owned())
            .collect();
        return Err(render_error(&format!(
            "git {} failed: {}",
            shown.join(" "),
            run.stderr.trim()
        )));
    }
    Ok(run.stdout)
}

/// Run git in `dir` with no extra variables, and fail when git fails.
///
/// # Arguments
///
/// * `dir` - the folder that git runs in
/// * `args` - the arguments of git
///
/// # Returns
///
/// The stdout of git without its trailing newlines, such as one path.
fn git_line(dir: &Path, args: &[&str]) -> Result<String> {
    Ok(git_output(dir, args, &[])?
        .trim_end_matches('\n')
        .to_string())
}

/// Draw a new random nonce: 16 bytes from the system, in lowercase hex.
///
/// The first digit is always a letter from `a` to `f`. A YAML reader then
/// always reads the nonce as a string, never as a number such as `123e45`.
/// jagt draws again until the first digit is a letter. It fails when the
/// system gives no random bytes.
///
/// # Returns
///
/// The nonce, 32 lowercase hex digits.
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

/// Say whether `value` has the form of a nonce: 32 lowercase hex digits, of
/// which the first is a letter from `a` to `f`.
///
/// # Arguments
///
/// * `value` - the text to check
///
/// # Returns
///
/// True when `value` is a nonce.
pub fn is_nonce(value: &str) -> bool {
    value.len() == NONCE_BYTES * 2
        && value.as_bytes()[0].is_ascii_lowercase()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

/// Hash a text with SHA-256.
///
/// # Arguments
///
/// * `text` - the text, hashed as its UTF-8 bytes
///
/// # Returns
///
/// The hash, 64 lowercase hex digits.
pub fn sha256_hex(text: &str) -> String {
    to_hex(&Sha256::digest(text.as_bytes()))
}

/// Write bytes in lowercase hex, two digits for each byte.
///
/// # Arguments
///
/// * `bytes` - the bytes to write
///
/// # Returns
///
/// The hex text.
fn to_hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

/// Save `record` as `<log_dir>/packets/<nonce>.json`.
///
/// It makes `.agents`, the log folder and the packets folder when they are
/// missing. Where the log folder or the packets folder has no `.gitignore`
/// yet, it writes one that holds `*`, as `jlog` does, so git never sees the
/// packets. An existing `.gitignore` is kept as it is.
/// It never replaces a file: a packet file with the same name stops the
/// render. It also fails when the nonce of `record` is not a nonce, and when
/// one of the folders is a symlink or not a folder.
///
/// # Arguments
///
/// * `log_dir` - the log folder, `.agents/log` of a checkout
/// * `record` - the facts of the packet
///
/// # Returns
///
/// The path of the new packet file.
pub fn save_record(log_dir: &Path, record: &PacketRecord) -> Result<PathBuf> {
    if !is_nonce(&record.nonce) {
        return Err(render_error(
            "the nonce of a packet file must be 32 hex digits",
        ));
    }
    let agents = log_dir
        .parent()
        .ok_or_else(|| render_error("the log folder has no checkout"))?;
    let checkout = agents
        .parent()
        .ok_or_else(|| render_error("the log folder has no checkout"))?;
    let name_of = |dir: &Path| {
        dir.file_name()
            .map(std::ffi::OsStr::to_os_string)
            .ok_or_else(|| render_error("the log folder has no checkout"))
    };
    let (agents_name, log_name) = (name_of(agents)?, name_of(log_dir)?);
    let mut json = serde_json::to_string_pretty(record)
        .map_err(|error| render_error(&format!("could not write the packet file: {error}")))?;
    json.push('\n');
    let file_name = format!("{}.json", record.nonce);
    let path = log_dir.join(PACKETS_DIR).join(&file_name);
    let already = |error: io::Error| {
        if error.kind() == io::ErrorKind::AlreadyExists {
            render_error(&format!(
                "the packet file {} exists already",
                path.display()
            ))
        } else {
            JagtError::Io(error)
        }
    };
    let folders = [
        (checkout.join(&agents_name), agents_name),
        (log_dir.to_path_buf(), log_name),
        (log_dir.join(PACKETS_DIR), PACKETS_DIR.into()),
    ];
    #[cfg(unix)]
    {
        // Each folder is opened through the handle of the folder above it,
        // and never through a symlink. A folder that a process swaps for a
        // symlink after the check then cannot move the file elsewhere.
        let mut dir = dirs::open_top(checkout)?;
        let mut handles = Vec::new();
        for (shown, name) in &folders {
            dir = dirs::open_child(&dir, name, shown, true)?;
            handles.push(dir.try_clone()?);
        }
        // Each folder gets its own `.gitignore`, so the packets stay out of
        // every worktree tree, also when an older `.agents/log/.gitignore`
        // lacks `*`.
        dirs::write_new(&handles[1], ".gitignore", b"*\n").or_else(ignore_exists)?;
        dirs::write_new(&handles[2], ".gitignore", b"*\n").or_else(ignore_exists)?;
        dirs::write_new(&handles[2], &file_name, json.as_bytes()).map_err(already)?;
    }
    #[cfg(not(unix))]
    {
        for (shown, _) in &folders {
            make_real_dir(shown)?;
        }
        let packets = &folders[2].0;
        write_new(&log_dir.join(".gitignore"), b"*\n").or_else(ignore_exists)?;
        write_new(&packets.join(".gitignore"), b"*\n").or_else(ignore_exists)?;
        write_new(&path, json.as_bytes()).map_err(already)?;
    }
    Ok(path)
}

/// Remove the packet file `path` that [`save_record`] wrote, as after a
/// broken pipe. On Unix, it goes through the same folder handles, so a folder
/// that is now a symlink cannot point the removal elsewhere.
///
/// # Arguments
///
/// * `path` - the path that [`save_record`] returned
///
/// # Returns
///
/// `Ok(())` when the file is gone, or the error.
pub fn remove_record(path: &Path) -> Result<()> {
    #[cfg(unix)]
    {
        let bad = || render_error("the packet file has no log folder");
        let packets = path.parent().ok_or_else(bad)?;
        let log_dir = packets.parent().ok_or_else(bad)?;
        let agents = log_dir.parent().ok_or_else(bad)?;
        let checkout = agents.parent().ok_or_else(bad)?;
        let mut dir = dirs::open_top(checkout)?;
        for shown in [agents, log_dir, packets] {
            let name = shown.file_name().ok_or_else(bad)?;
            dir = dirs::open_child(&dir, name, shown, false)?;
        }
        let name = path.file_name().ok_or_else(bad)?;
        rustix::fs::unlinkat(&dir, name, rustix::fs::AtFlags::empty())
            .map_err(|error| JagtError::Io(error.into()))
    }
    #[cfg(not(unix))]
    {
        fs::remove_file(path).map_err(JagtError::Io)
    }
}

/// The folder handles that [`save_record`] writes through on Unix.
#[cfg(unix)]
mod dirs {
    use std::ffi::OsStr;
    use std::fs::File;
    use std::io::{self, Write};
    use std::path::Path;

    use rustix::fs::{AtFlags, Mode, OFlags};
    use rustix::io::Errno;

    use crate::{JagtError, Result};

    use super::render_error;

    /// Open the checkout folder. A symlink to the checkout itself is allowed,
    /// as before.
    ///
    /// # Arguments
    ///
    /// * `checkout` - the main checkout
    ///
    /// # Returns
    ///
    /// The handle of the folder.
    pub(super) fn open_top(checkout: &Path) -> Result<File> {
        let fd = rustix::fs::open(
            checkout,
            OFlags::RDONLY | OFlags::DIRECTORY | OFlags::CLOEXEC,
            Mode::empty(),
        )
        .map_err(|error| JagtError::Io(error.into()))?;
        Ok(File::from(fd))
    }

    /// Open the folder `name` in `parent`, and make it when it is missing and
    /// `create` is true.
    /// A symlink, or a path that is not a folder, stops the render.
    ///
    /// # Arguments
    ///
    /// * `parent` - the handle of the folder above
    /// * `name` - the name of the folder, one part of a path
    /// * `shown` - the full path, for the error text
    /// * `create` - whether to make a missing folder
    ///
    /// # Returns
    ///
    /// The handle of the folder.
    pub(super) fn open_child(
        parent: &File,
        name: &OsStr,
        shown: &Path,
        create: bool,
    ) -> Result<File> {
        let flags = OFlags::RDONLY | OFlags::DIRECTORY | OFlags::NOFOLLOW | OFlags::CLOEXEC;
        for _ in 0..2 {
            match rustix::fs::openat(parent, name, flags, Mode::empty()) {
                Ok(fd) => return Ok(File::from(fd)),
                Err(Errno::NOENT) if create => {
                    match rustix::fs::mkdirat(parent, name, Mode::from_raw_mode(0o777)) {
                        Ok(()) | Err(Errno::EXIST) => continue,
                        Err(error) => return Err(JagtError::Io(error.into())),
                    }
                }
                Err(error) => return Err(not_a_folder(parent, name, shown, error)),
            }
        }
        Err(render_error(&format!("{} keeps changing", shown.display())))
    }

    /// The error for a folder that `openat` refused: a symlink, a path that is
    /// not a folder, or the error of the system.
    fn not_a_folder(parent: &File, name: &OsStr, shown: &Path, error: Errno) -> JagtError {
        match rustix::fs::statat(parent, name, AtFlags::SYMLINK_NOFOLLOW) {
            Ok(stat) if rustix::fs::FileType::from_raw_mode(stat.st_mode).is_symlink() => {
                render_error(&format!(
                    "{} is a symlink, so jagt does not write in it",
                    shown.display()
                ))
            }
            Ok(stat) if !rustix::fs::FileType::from_raw_mode(stat.st_mode).is_dir() => {
                render_error(&format!("{} is not a folder", shown.display()))
            }
            _ => JagtError::Io(error.into()),
        }
    }

    /// Write the new file `name` in `dir`, and sync it to the disk. It fails
    /// on any existing name, a symlink too.
    ///
    /// # Arguments
    ///
    /// * `dir` - the handle of the folder
    /// * `name` - the name of the new file
    /// * `bytes` - what the file holds
    ///
    /// # Returns
    ///
    /// `Ok(())` when the file is written, or the I/O error.
    pub(super) fn write_new(dir: &File, name: &str, bytes: &[u8]) -> io::Result<()> {
        let fd = rustix::fs::openat(
            dir,
            name,
            OFlags::WRONLY | OFlags::CREATE | OFlags::EXCL | OFlags::NOFOLLOW | OFlags::CLOEXEC,
            Mode::from_raw_mode(0o666),
        )?;
        let mut file = File::from(fd);
        file.write_all(bytes)?;
        file.sync_all()
    }
}

/// Make `dir` when it is missing. A symlink, or a path that is not a
/// folder, stops the render, so a symlink in a repository cannot send the
/// packet files out of the log folder. Unix uses folder handles instead.
///
/// It does not make the parent folders of `dir`.
///
/// # Arguments
///
/// * `dir` - the folder to make, whose parent must exist
///
/// # Returns
///
/// `Ok(())` when `dir` is a real folder, or the error that stops the render.
#[cfg(not(unix))]
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

/// Write a new file, and sync it to the disk. `create_new` fails on any
/// existing path, a symlink too.
///
/// # Arguments
///
/// * `path` - the path of the new file
/// * `bytes` - what the file holds
///
/// # Returns
///
/// `Ok(())` when the file is written, or the I/O error.
#[cfg(not(unix))]
fn write_new(path: &Path, bytes: &[u8]) -> io::Result<()> {
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    file.write_all(bytes)?;
    file.sync_all()
}

/// Count an error that says a path exists already as success.
///
/// # Arguments
///
/// * `error` - the error of [`write_new`]
///
/// # Returns
///
/// `Ok(())` for an `AlreadyExists` error, or else the error.
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

/// Read the language layers and the repository text of `target` from the
/// checkout at `root`:
///
/// - `.agents/targets/<language>/<target>.md`, for each language in the
///   `profiles` list of `.agents/stack.json`, in the order of that list;
/// - `.agents/targets/<target>.md`.
///
/// A missing file is not an error, and neither is a missing `stack.json`.
/// A file of blank lines adds no layer. It fails on a bad `stack.json`, and
/// on a layer file whose real path leads outside `.agents/targets`.
///
/// # Arguments
///
/// * `root` - the top folder of the checkout
/// * `target` - the Just target
///
/// # Returns
///
/// The layers in that order, each with its label for the provenance.
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

/// Read the languages of the stack: the `profiles` list of `.agents/stack.json`.
/// Each name must be a plain folder name, so a name such as `..` cannot send
/// the read out of `.agents/targets`.
///
/// A missing file, a missing `profiles` and `profiles: null` give no
/// languages. It fails when the file is not JSON, when `profiles` is not a
/// list of names, and when the real path of the file is not
/// `.agents/stack.json` of the checkout.
///
/// # Arguments
///
/// * `root` - the top folder of the checkout
///
/// # Returns
///
/// The names, in the order of the list, with each name once.
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

/// Say whether a name is a plain language name. A language name starts with
/// a letter or a digit, and holds only ASCII letters, digits, `_`, `.` and
/// `-`.
///
/// # Arguments
///
/// * `name` - the name from `profiles`
///
/// # Returns
///
/// True when the name is plain.
fn is_language_name(name: &str) -> bool {
    name.chars()
        .next()
        .is_some_and(|c| c.is_ascii_alphanumeric())
        && name
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '_' | '.' | '-'))
}

/// Read a layer file. A missing file and a file of blank lines give `None`.
///
/// # Arguments
///
/// * `root` - the top folder of the checkout
/// * `relative` - the path of the file, relative to `root`
/// * `allowed` - the path, relative to `root`, that the file must be or be inside
///
/// # Returns
///
/// The text of the file, or `None`.
fn read_optional(root: &Path, relative: &str, allowed: &str) -> Result<Option<String>> {
    Ok(read_inside(root, relative, allowed)?.filter(|text| !text.trim().is_empty()))
}

/// Read `root/relative`. A missing file gives `None`. The real path of the
/// file must be `root/allowed` or inside it, with `root` as a real path. So a
/// symlink in the repository cannot put another file into the packet, such
/// as an ignored `.env` file, `.git/config` or a key outside the worktree.
///
/// # Arguments
///
/// * `root` - the top folder of the checkout
/// * `relative` - the path of the file, relative to `root`
/// * `allowed` - the path, relative to `root`, that the file must be or be inside
///
/// # Returns
///
/// The text of the file, or `None` when it is missing.
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

/// Check the prompt path that a config file names, before jagt reads it.
///
/// A config file comes with the repository, so its `prompt` must not put any
/// file into the packet. A missing file is left for the read to report. Each of
/// these refuses the file:
///
/// - its real path is outside the real path of `cwd`;
/// - a part of its path is `.git`;
/// - on Unix, the file has more than one hard link, so it may be a file outside;
/// - a repository between the file and `cwd` ignores the file, such as an
///   ignored `.env`. jagt asks each repository from the folder of the file up
///   to `cwd`, so a submodule and the repository around it both answer;
/// - a folder above the file holds a `.git` entry, and the repository nearest
///   the file gives no clear answer, for example when git cannot start;
/// - no folder above the file holds a `.git` entry, and a part of its path
///   starts with `.`, other than the folders `.agents` and `.jagt`.
///
/// # Arguments
///
/// * `cwd` - the project root, from [`project_root`], against which a relative path is read
/// * `path` - the prompt path from the config
///
/// # Returns
///
/// `Ok(())`, or a render error that says why jagt does not read the file.
pub fn check_config_prompt_path(cwd: &Path, path: &str) -> Result<()> {
    let refuse = |why: &str| {
        render_error(&format!(
            "the config names the prompt file {path}, which {why}, so jagt does not read it; pass it with --prompt instead"
        ))
    };
    let real = match fs::canonicalize(cwd.join(path)) {
        Ok(real) => real,
        Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(()),
        Err(error) => return Err(render_error(&format!("could not read {path}: {error}"))),
    };
    let real_cwd = fs::canonicalize(cwd)?;
    let Ok(inside) = real.strip_prefix(&real_cwd) else {
        return Err(refuse("leads outside the project folder"));
    };
    if inside.components().any(|part| part.as_os_str() == ".git") {
        return Err(refuse("is inside .git"));
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        if fs::metadata(&real)?.nlink() > 1 {
            return Err(refuse("has more than one hard link"));
        }
    }
    // Each repository from the folder of the file up to the current folder
    // may ignore the file: a submodule or nested repository has its own
    // ignore list, and so has the repository around it. jagt asks each one.
    let Some(folder) = real.parent() else {
        return Err(refuse("has no folder"));
    };
    let mut askers: Vec<&Path> = folder
        .ancestors()
        .take_while(|dir| dir.starts_with(&real_cwd))
        .filter(|dir| dir.join(".git").exists())
        .collect();
    if askers.last() != Some(&real_cwd.as_path()) {
        askers.push(&real_cwd);
    }
    let in_repository = folder.ancestors().any(|dir| dir.join(".git").exists());
    let answers: Vec<Option<i32>> = askers.iter().map(|dir| check_ignore(dir, &real)).collect();
    // `git check-ignore` exits 0 for an ignored path, 1 for a path that is
    // not ignored, and 128 outside a repository or on an error.
    if answers.contains(&Some(0)) {
        return Err(refuse("git ignores"));
    }
    if in_repository {
        // The repository nearest the file must answer. A repository further
        // out may give 128, as git does for a path inside a submodule.
        let nearest_answers = answers.first() == Some(&Some(1));
        let others_answer = answers[1..]
            .iter()
            .all(|answer| matches!(answer, Some(1) | Some(128)));
        if nearest_answers && others_answer {
            return Ok(());
        }
        return Err(refuse(
            "is in a git repository, but git cannot say whether it ignores the file",
        ));
    }
    // With no repository there is no ignore list. A hidden file such as
    // `.env` or `.ssh/id_rsa` is then refused.
    if has_hidden_part(inside) {
        return Err(refuse(
            "is hidden, and no git repository can say whether it ignores the file",
        ));
    }
    Ok(())
}

/// Ask git, run in `dir`, whether it ignores the file `real`.
///
/// # Arguments
///
/// * `dir` - the folder that git runs in
/// * `real` - the real path of the file
///
/// # Returns
///
/// The exit code of `git check-ignore -q`, or `None` when git cannot start.
fn check_ignore(dir: &Path, real: &Path) -> Option<i32> {
    let mut command = Command::new("git");
    command
        .arg("-C")
        .arg(dir)
        .args(["check-ignore", "-q", "--"])
        .arg(real)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    for name in LOCAL_ENV_VARS {
        command.env_remove(name);
    }
    command.status().ok().and_then(|status| status.code())
}

/// Tell whether a part of `path` starts with `.`, other than the folders
/// `.agents` and `.jagt` of jagt and its skills.
///
/// # Arguments
///
/// * `path` - a relative path
///
/// # Returns
///
/// `true` when a part is hidden.
fn has_hidden_part(path: &Path) -> bool {
    let count = path.components().count();
    path.components().enumerate().any(|(index, part)| {
        let name = part.as_os_str().to_string_lossy();
        let folder = index + 1 < count;
        name.starts_with('.') && !(folder && (name == ".agents" || name == ".jagt"))
    })
}

/// Join the layers in order, with one blank line between two layers. The
/// blank lines and the line break at the end of each layer are dropped, but
/// the spaces and tabs at the end of its last line are kept.
///
/// # Arguments
///
/// * `layers` - the layers, in the order of the join
///
/// # Returns
///
/// The joined text, with no newline at its end. It is empty when there are no layers.
pub fn join_layers(layers: &[Layer]) -> String {
    let mut joined = String::new();
    for layer in layers {
        if !joined.is_empty() {
            joined.push_str("\n\n");
        }
        joined.push_str(without_trailing_blank_lines(&layer.text));
    }
    joined
}

/// Drop the blank lines and the line break at the end of `text`, and keep the
/// spaces and tabs at the end of its last line that is not blank.
///
/// # Arguments
///
/// * `text` - the text of one layer
///
/// # Returns
///
/// The start of `text`, up to the end of its last line that is not blank. It is
/// empty when every line is blank.
fn without_trailing_blank_lines(text: &str) -> &str {
    let content_end = text.trim_end().len();
    let line_end = text[content_end..]
        .find(['\n', '\r'])
        .map_or(text.len(), |offset| content_end + offset);
    if content_end == 0 {
        ""
    } else {
        &text[..line_end]
    }
}

/// Make a [`JagtError::Render`] from a message.
///
/// # Arguments
///
/// * `message` - what went wrong
///
/// # Returns
///
/// The error.
fn render_error(message: &str) -> JagtError {
    JagtError::Render(message.to_string())
}

#[cfg(test)]
mod tests {

    #[cfg(unix)]
    #[test]
    fn an_alternate_path_with_the_separator_or_a_quote_goes_in_c_quotes() {
        use super::alternate_entry;
        use std::path::Path;
        assert_eq!(alternate_entry(Path::new("/a b/objects")), "/a b/objects");
        assert_eq!(alternate_entry(Path::new("/a\\b/objects")), "/a\\b/objects");
        assert_eq!(
            alternate_entry(Path::new("/a:b/\"q\\\n\t/objects")),
            "\"/a:b/\\\"q\\\\\\n\\t/objects\""
        );
        assert_eq!(alternate_entry(Path::new("\"/x")), "\"\\\"/x\"");
    }

    #[test]
    fn a_layer_keeps_the_spaces_at_the_end_of_its_last_line() {
        assert_eq!(without_trailing_blank_lines("a  \n\n  \n"), "a  ");
        assert_eq!(without_trailing_blank_lines("a\t\r\n"), "a\t");
        assert_eq!(without_trailing_blank_lines("a\n   \nb"), "a\n   \nb");
        assert_eq!(without_trailing_blank_lines("  \n\n"), "");
        assert_eq!(without_trailing_blank_lines(""), "");
        let layers = [
            Layer {
                label: "one".to_string(),
                text: "x  \n\n".to_string(),
            },
            Layer {
                label: "two".to_string(),
                text: "y\n".to_string(),
            },
        ];
        assert_eq!(join_layers(&layers), "x  \n\ny");
    }
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
