"""The commit gate: the git pre-commit and pre-merge-commit hooks run it before each commit.

The gate runs one step only, `release-check`, at the commit-msg hook. It reads what `just check` and the agentic targets wrote, and stops the commit when
something is missing:

1. The steps of `.agents/stack.json` and the required targets must be recipes of the Justfile.
2. The commit tree must equal the worktree tree, so all changes must be staged.
3. The run log must hold a pass of `just check` for the commit tree.
4. For a commit by an agent, the records must hold a chain of the required targets that ends at the commit tree.

The lists that exempt paths come from the parent commit, so a commit cannot change them for itself:
`.agents/targets/required.txt` and `.agents/generated.txt`. With no parent, or a parent without the file, the gate
uses the default list of required targets and an empty list of generated paths. The steps come from the
`.agents/stack.json` of the commit, as `jlog pass` reads them, so a commit can remove a tool and its step. The code
globs of `@code` come from the `.agents/stack.json` of the commit and of the parent. An amend replaces HEAD, so for
what looks like `git commit --amend` the gate applies the rules of HEAD and of its parent, and the stricter win. The
`required.txt` of the commit must be readable too, so a bad line cannot land.

Each line of `required.txt` names a target and the paths that make it required, as git pathspecs with `:(glob)`.
`@code` names the source globs of each profile, from the key `code` of `.agents/stack.json`, less the paths of
`generated.txt`. `@pages` is the files that `is_page` of the nossaifd role accepts, from its `prose_gate.py` in the
parent, so `AGENTS.md` and `CHANGELOG.md` are not pages. The rule runs in a Python of its own. Without the role in
the parent, as on the first commit, `@pages` is `**/*.md` and `**/*.qmd`. `@api` is the files that `is_api` of a
language profile accepts, from its `.agents/just/<profile>/api_rule.py` in the parent. The profiles are the names of
the key `profiles` of the `.agents/stack.json` of the parent and of the commit. A profile whose parent has no rule
adds no file, and on the first commit `@api` names no file. Each rule runs in a Python of its own, as the page rule
does.
Every commit needs `review`, whatever the file says.

A record is a JSON file in `records/` of the shared log folder, the `.agents/log/` of the main checkout:

    {"version": 1, "target": "review", "status": "success", "input_tree": "<tree>", "output_tree": "<tree>",
     "findings": [{"summary": "...", "test": "<the test that shows the fix>"},
                  {"summary": "...", "reason": "<why it is not fixed>"}],
     "source": "hook", "model": "<model>", "nonce": "<nonce>"}

A record counts when its status is `success` and each finding has a `test` or a `reason`. A skip from
`just record-skip` is a record with `"source": "skip"`, a `reason`, and the same tree twice.

The chain: `update-docs` comes before `prose`, and each record starts at the output tree of the record before it. The
last output tree is the commit tree. Every other target, such as `review` and `test-review`, has the commit tree as
its input tree and its output tree.

The trailer: the commit-msg hook runs the gate once more, and when it passes, it adds a trailer to the message:
`Commit-Gate: patch:<patch-id>`, or `Commit-Gate: tree:<tree>` for a merge. A patch ID is the hash of the change,
from `git patch-id --verbatim` on a diff with no lines of context, so a rebase with no conflict keeps it. With no
context, a line that moves within one part of a file keeps the ID too. The trailer is a claim, so that is a fair
price. `git commit -n` skips the commit-msg hook too, so a commit that went around the gate has no trailer. For what looks like an amend, the trailer names the patch IDs
against both possible parents, and the tree too when HEAD is a merge.

The release check: before it adds the trailer, the commit-msg hook runs `just release-check` with the path of the
message file in `JN_RELEASE_MESSAGE`. `just check` ran before the message was written, so it could not count it. With
the message, `release_tag.py --check` fails when the type of the commit, such as `fix:`, asks for a release and the
version of the manifest is not raised. For an amend, it sets `JN_RELEASE_AMEND=1`, so the new message replaces the
message of HEAD. The hook skips the check for a merge and for an amend of a merge, since the release skips merge
commits, during a rebase, and when the Justfile has no recipe `release-check`. The check stops the commit when it runs longer than
120 seconds.

`--trailers BASE HEAD` is the check of CI, which `just ci-gate` runs. With no BASE and HEAD, it reads them from CI,
from the pre-push hook, or from the upstream of the branch, as `ci_range` says. Each commit in BASE..HEAD must have a
trailer that names its own patch ID, or its own tree for a merge. CI runs no step of `just check` again: the
trailer says that the gate saw a pass of it. The trailer is a claim of the gate, not a proof: an agent could write
one by hand, and the review of the pull request is the check of that.

Usage: commit_gate.py [--hook pre-commit|pre-merge-commit|commit-msg] [MESSAGE_FILE], or commit_gate.py --trailers
[BASE HEAD], or commit_gate.py --check-hooks. It exits with 0 to let the commit through and with 1 to stop it.

`commit_gate.py --check-hooks` checks that the pre-commit framework runs the hooks of the tasker role: pre-commit,
pre-merge-commit and commit-msg, which run the gate, and pre-push, which runs just ci. It exits with 0 when the hook of
each stage is a hook of pre-commit for .pre-commit-config.yaml whose Python has pre-commit, and the config has the
hooks of the role, and with 1 when not. The tasker role runs it as the check of its hook install.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

# The variables of a harness that mark a commit by an agent.
AGENT_VARIABLES = ("CODEX_THREAD_ID", "CLAUDE_CODE_SESSION_ID", "CLAUDECODE")

# The default required targets, used when the parent has no required.txt.
DEFAULT_REQUIRED = """\
review       **
test-review  @code
update-docs  @pages  @api
prose        @pages  @api
"""

# The targets that change files, in the order of the chain.
CHANGERS = ("update-docs", "prose")

PAGES = ("**/*.md", "**/*.qmd")
# The page rule of the nossaifd role. With it, @pages is the changed files that its is_page accepts.
PAGE_RULE = ".agents/skills/nossaifd/scripts/prose_gate.py"

# The API rule of a language profile, by its name in the key `profiles` of stack.json. With it, @api is the changed
# files that its is_api accepts.
API_RULE = ".agents/just/{}/api_rule.py"

STACK = ".agents/stack.json"
REQUIRED = ".agents/targets/required.txt"
GENERATED = ".agents/generated.txt"
RUN_LOG = "just.jsonl"


class Stop(Exception):
    """A reason to stop the commit. The text says what to run."""


def git(args: Sequence[str], cwd: Path, env: Optional[Dict[str, str]] = None, check: bool = True) -> str:
    run = subprocess.run(["git", *args], cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                         errors="surrogateescape")
    if check and run.returncode != 0:
        raise Stop(f"git {' '.join(args)} failed: {run.stderr.strip()}")
    return run.stdout if run.returncode == 0 else ""


def alternate(path: Path) -> str:
    """`path` as an entry of GIT_ALTERNATE_OBJECT_DIRECTORIES. Git splits the list at each `:`, and reads an entry
    that starts with `"` as a C string, so a path with `:`, `"` or `\\` goes in quotes."""
    text = str(path)
    if ":" in text or '"' in text or "\\" in text:
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def plain_env() -> Dict[str, str]:
    """The environment without the index of the hook, for the git calls that must not touch it."""
    env = dict(os.environ)
    env.pop("GIT_INDEX_FILE", None)
    return env


def is_tree(value: object) -> bool:
    return isinstance(value, str) and len(value) in (40, 64) and all(c in "0123456789abcdef" for c in value)


def worktree_tree(root: Path) -> str:
    """The tree of the worktree, as `jlog` computes it: a temporary index and a temporary object store, so neither
    the real index nor `.git/objects` changes. Files that git ignores are not in the tree."""
    env = plain_env()
    objects = Path(git(["rev-parse", "--git-path", "objects"], root, env).strip())
    real_index = Path(git(["rev-parse", "--git-path", "index"], root, env).strip())
    with tempfile.TemporaryDirectory(prefix="commit-gate-") as temp:
        index = Path(temp) / "index"
        (Path(temp) / "objects").mkdir()
        env.update(GIT_INDEX_FILE=str(index), GIT_OBJECT_DIRECTORY=str(Path(temp) / "objects"),
                   GIT_ALTERNATE_OBJECT_DIRECTORIES=":".join(
                       filter(None, [alternate(root / objects), os.environ.get("GIT_ALTERNATE_OBJECT_DIRECTORIES", "")])))
        # With a split index, each write of the copy, by git add and by git write-tree, would leave a new shared index
        # in the git folder. A setting in the environment reaches every command on the copy.
        count = int(env.get("GIT_CONFIG_COUNT", "0") or "0")
        env.update({"GIT_CONFIG_COUNT": str(count + 1), f"GIT_CONFIG_KEY_{count}": "core.splitIndex",
                    f"GIT_CONFIG_VALUE_{count}": "false"})
        copied = False
        if (root / real_index).is_file():
            # copy2 keeps the time of the index, which git needs to see a file that changed in the same second.
            shutil.copy2(root / real_index, index)
            listing = git(["ls-files", "-v"], root, env, check=False)
            # An assume-unchanged entry (a small letter) or a skip-worktree entry (S) hides changes from git add.
            copied = not any(line[:1].islower() or line[:1] == "S" for line in listing.splitlines())
        if not copied:
            index.unlink(missing_ok=True)
            if git(["rev-parse", "--verify", "--quiet", "HEAD^{tree}"], root, env, check=False):
                git(["read-tree", "HEAD"], root, env)
        git(["add", "-A", "--", ":/"], root, env)
        return git(["write-tree"], root, env).strip()


def commit_tree(root: Path) -> str:
    """The tree of the commit: the index of the hook, from `GIT_INDEX_FILE` when git sets it."""
    return git(["write-tree"], root, dict(os.environ)).strip()


def git_argv() -> List[str]:
    """The argv of the nearest git above this process, from ps, or [] when ps cannot tell. A hook manager such as
    pre-commit can stand between git and the gate."""
    pid = os.getppid()
    for _ in range(6):
        run = subprocess.run(["ps", "-o", "ppid=", "-o", "args=", "-p", str(pid)], stdin=subprocess.DEVNULL,
                             capture_output=True, text=True, errors="replace")
        fields = run.stdout.split()
        if run.returncode != 0 or len(fields) < 2:
            return []
        if os.path.basename(fields[1]) == "git":
            return fields[1:]
        pid = int(fields[0])
    return []


def is_amend(argv: Sequence[str]) -> bool:
    """True for `git commit --amend`, also with an abbreviation of the option that git accepts, such as `--am`. A
    message can hold the same word, so the gate then applies the rules of both possible parents."""
    return any(len(word) >= 4 and "--amend".startswith(word) for word in argv)


def resolve(root: Path, revision: str) -> Optional[str]:
    out = git(["rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}"], root, plain_env(), check=False).strip()
    return out or None


def parents_of_commit(root: Path) -> List[Optional[str]]:
    """The parents to check the commit against: HEAD, and for what looks like an amend also the parent of HEAD,
    since an amend replaces HEAD. Each one gives its own required targets, so the stricter rules win. None stands
    for no parent, as on the first commit."""
    head = resolve(root, "HEAD")
    if head is not None and is_amend(git_argv()):
        return [head, resolve(root, "HEAD^")]
    return [head]


def read_at(root: Path, revision: str, path: str) -> Optional[str]:
    """The text of PATH at REVISION, or None when it has no such file. `:` as REVISION is the index of the hook."""
    env = dict(os.environ) if revision == "" else plain_env()
    run = subprocess.run(["git", "show", f"{revision}:{path}"], cwd=root, env=env, stdin=subprocess.DEVNULL,
                         capture_output=True, text=True, errors="surrogateescape")
    return run.stdout if run.returncode == 0 else None


def load_stack(text: Optional[str]) -> dict:
    if text is None:
        raise Stop(f"{STACK} is missing, so the gate does not know the steps: run `just install`")
    try:
        stack = json.loads(text)
    except ValueError as error:
        raise Stop(f"{STACK} is not JSON ({error}): run `just install`")
    steps = stack.get("steps") if isinstance(stack, dict) else None
    if not isinstance(steps, list) or not all(isinstance(step, str) and step for step in steps):
        raise Stop(f"{STACK} has no list `steps` of names: run `just install`")
    return stack


def list_lines(text: Optional[str]) -> List[str]:
    """The entries of a list file: one on each line, with no blank line and no `#` comment."""
    lines = (line.strip() for line in (text or "").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def parse_required(text: str) -> Dict[str, List[str]]:
    """Each target of required.txt and its paths. A target on two lines gets the paths of both. A comment goes on
    a line of its own, and a path has no pathspec magic of its own, so a `#` or a leading `:` stops the commit."""
    required: Dict[str, List[str]] = {}
    for line in list_lines(text):
        target, *paths = line.split()
        odd = [word for word in [target, *paths] if "#" in word or word.startswith(":")]
        if odd or not all(c.isalnum() or c in "-_" for c in target):
            raise Stop(f"{REQUIRED} has a line that the gate cannot read: {line!r}. Write a target name and its "
                       "paths, with a comment on a line of its own")
        required.setdefault(target, []).extend(paths)
    return required


def code_globs(stack: object) -> List[str]:
    """The source globs of each profile, from the key `code` of a stack.json."""
    code = stack.get("code") if isinstance(stack, dict) else None
    if not isinstance(code, dict):
        return []
    return [g for globs in code.values() if isinstance(globs, list) for g in globs if isinstance(g, str) and g]


def merged_code(stack: dict, parent_text: Optional[str]) -> List[str]:
    try:
        parent = json.loads(parent_text) if parent_text is not None else None
    except ValueError:
        parent = None
    globs = code_globs(parent) + code_globs(stack)
    return list(dict.fromkeys(globs))


def pathspecs(paths: Iterable[str], code: List[str], generated: List[str]) -> List[str]:
    """The git pathspecs of the paths of one target, with the aliases expanded."""
    specs: List[str] = []
    for path in paths:
        if path == "@code":
            specs += [f":(glob){g}" for g in code]
        elif path == "@pages":
            specs += [f":(glob){g}" for g in PAGES]
        elif path == "@api":
            continue
        else:
            specs.append(f":(glob){path}")
    if specs:
        specs += [f":(exclude,glob){g}" for g in generated]
    return specs


# The script that loads a rule from the file in argv[1], in a Python of its own, and prints each path of standard
# input that its function argv[2] accepts: is_page for the page rule, is_api for an API rule. The paths come and go
# with a NUL after each one, and the last word is PAGES_END, so that a rule that ends its Python early cannot give "no
# path". A path that is not UTF-8 keeps its bytes, as git() keeps them. Exit 3 with NO_FUNCTION as the last line of
# standard error: no such function. The rule itself can exit with 3, and then it fails.
# No changed path is "/", so the last word cannot be a path.
PAGES_END = "/"
NO_FUNCTION = "commit-gate: the rule has no such function"
# The seconds that a rule can take for the paths of one commit.
RULE_TIMEOUT = 120
RULE_OF = """import importlib.util, sys
spec = importlib.util.spec_from_file_location("commit_gate_rule", sys.argv[1])
module = importlib.util.module_from_spec(spec)
out = sys.stdout.buffer
# What the rule prints goes to standard error, so that it cannot come after the end word.
sys.stdout = sys.stderr
spec.loader.exec_module(module)
rule = getattr(module, sys.argv[2], None)
if not callable(rule):
    sys.stderr.write("\\n%s\\n")
    sys.stderr.flush()
    sys.exit(3)
for path in sys.stdin.buffer.read().decode(errors="surrogateescape").split("\\0"):
    if path and rule(path):
        out.write(path.encode(errors="surrogateescape") + b"\\0")
out.write(b"%s\\0")
out.flush()""" % (NO_FUNCTION, PAGES_END)


def rule_runner(root: Path, text: str, name: str, function: str, what: str) -> Callable[[List[str]], List[str]]:
    """The paths of a list that FUNCTION of the rule TEXT accepts. NAME is the path of the rule, and WHAT names the
    rule in a message, such as "the page rule". The rule runs in a Python of its own, so it can only answer which
    paths it accepts: it cannot end the gate or change its environment."""

    def accepted(paths: List[str]) -> List[str]:
        with tempfile.TemporaryDirectory(prefix="commit-gate-rule-") as away:
            script = Path(away) / "rule.py"
            script.write_text(text, errors="surrogateescape")
            try:
                run = subprocess.run([sys.executable, "-I", "-B", "-c", RULE_OF, str(script), function], cwd=root,
                                     input="".join(f"{path}\0" for path in paths).encode(errors="surrogateescape"),
                                     capture_output=True, timeout=RULE_TIMEOUT)
            except subprocess.TimeoutExpired:
                raise Stop(f"{what} {name} of the parent does not finish in {RULE_TIMEOUT} seconds: run "
                           "`just install`")
        python = f"Python {sys.version.split()[0]}"
        error = run.stderr.decode(errors="replace").strip().splitlines()[-1:] or ["no message"]
        if run.returncode == 3 and error == [NO_FUNCTION]:
            raise Stop(f"{what} {name} of the parent has no {function}: run `just install`")
        if run.returncode != 0:
            raise Stop(f"{what} {name} of the parent fails in {python} ({error[0]}): run "
                       "`just install`, or run the gate with a Python that the rule supports")
        found = [path for path in run.stdout.decode(errors="surrogateescape").split("\0") if path]
        if found[-1:] != [PAGES_END]:
            raise Stop(f"{what} {name} of the parent ends before it checks each path: run `just install`")
        found = found[:-1]
        if not set(found) <= set(paths):
            raise Stop(f"{what} {name} of the parent names paths that the commit does not change")
        return found

    return accepted


def page_rule(root: Path, parent: Optional[str]) -> Optional[Callable[[List[str]], List[str]]]:
    """The pages of a list of paths, by is_page of the nossaifd role, from its prose_gate.py in PARENT. None without
    the role, and on the first commit, where the globs apply as the default required.txt does. The rule comes from
    the parent, so a change cannot loosen the rule for its own pages."""
    text = None if parent is None else read_at(root, parent, PAGE_RULE)
    if text is None:
        return None
    return rule_runner(root, text, PAGE_RULE, "is_page", "the page rule")


def profile_names(stack: object) -> List[str]:
    """The names of the key `profiles` of a stack.json. A name with a `/`, or `.` or `..`, names no folder of
    .agents/just/, so it has no rule."""
    names = stack.get("profiles") if isinstance(stack, dict) else None
    if not isinstance(names, list):
        return []
    return [name for name in names if isinstance(name, str) and name not in ("", ".", "..")
            and all(c.isalnum() or c in "-_." for c in name)]


def api_rules(root: Path, parent: Optional[str], stack: dict,
              parent_text: Optional[str]) -> List[Callable[[List[str]], List[str]]]:
    """The API rules of the profiles of the parent and of the commit, each from its api_rule.py in PARENT, so a
    change cannot loosen the rule for its own API. A profile whose parent has no rule gives none, and the first
    commit has none."""
    if parent is None:
        return []
    try:
        parent_stack = json.loads(parent_text) if parent_text is not None else None
    except ValueError:
        parent_stack = None
    rules = []
    for name in dict.fromkeys(profile_names(parent_stack) + profile_names(stack)):
        path = API_RULE.format(name)
        text = read_at(root, parent, path)
        if text is not None:
            rules.append(rule_runner(root, text, path, "is_api", "the API rule"))
    return rules


def changed_files(root: Path, parent: Optional[str], tree: str, generated: List[str]) -> List[str]:
    """The paths that the commit changes, less the paths of generated.txt. A deleted path counts."""
    env = plain_env()
    before = parent or git(["hash-object", "-t", "tree", "--stdin"], root, env).strip()
    specs = [":(glob)**", *[f":(exclude,glob){g}" for g in generated]]
    out = git(["diff", "--name-only", "-z", "--no-renames", before, tree, "--", *specs], root, env)
    return [path for path in out.split("\0") if path]


def changes_match(root: Path, parent: Optional[str], tree: str, specs: List[str]) -> bool:
    """True when the commit changes a path that the pathspecs match. A deleted path counts."""
    if not specs:
        return False
    env = plain_env()
    # On the first commit, every path is new: compare with the empty tree. ls-tree takes no glob pathspec.
    before = parent or git(["hash-object", "-t", "tree", "--stdin"], root, env).strip()
    out = git(["diff", "--name-only", "-z", "--no-renames", before, tree, "--", *specs], root, env)
    return bool(out.strip("\0"))


def recipes(root: Path) -> Set[str]:
    if shutil.which("just") is None:
        raise Stop("just is not on PATH. Install it: https://just.systems")
    run = subprocess.run(["just", "--summary"], cwd=root, env=plain_env(), stdin=subprocess.DEVNULL,
                         capture_output=True, text=True)
    if run.returncode != 0:
        raise Stop(f"just --summary failed: {run.stderr.strip()}")
    return set(run.stdout.split())


def log_folders(root: Path) -> List[Path]:
    """The log folder of this worktree, and the shared log folder of the main checkout."""
    common = Path(git(["rev-parse", "--git-common-dir"], root, plain_env()).strip())
    common = (root / common).resolve()
    folders = [root / ".agents/log"]
    if common.name == ".git" and common.parent.resolve() != root.resolve():
        folders.append(common.parent / ".agents/log")
    return folders


def has_pass(folders: List[Path], tree: str, steps: List[str]) -> bool:
    """True when a run log holds a pass of `just check` for TREE that covers each step."""
    for folder in folders:
        try:
            lines = (folder / RUN_LOG).read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if (isinstance(record, dict) and record.get("kind") == "pass" and record.get("tree") == tree
                    and isinstance(record.get("steps"), list) and set(steps) <= set(record["steps"])):
                return True
    return False


def record_counts(record: object) -> bool:
    """True for a record whose status is success and whose findings each have a test or a reason."""
    if not isinstance(record, dict) or record.get("version") != 1 or record.get("status") != "success":
        return False
    if not (isinstance(record.get("target"), str) and is_tree(record.get("input_tree"))
            and is_tree(record.get("output_tree"))):
        return False
    if record.get("source") == "skip":
        reason = record.get("reason")
        return isinstance(reason, str) and bool(reason.strip()) and record["input_tree"] == record["output_tree"]
    findings = record.get("findings", [])
    if not isinstance(findings, list):
        return False
    return all(isinstance(f, dict) and any(isinstance(f.get(key), str) and f[key].strip() for key in ("test", "reason"))
               for f in findings)


def load_records(folders: List[Path]) -> List[dict]:
    found: List[dict] = []
    for folder in folders:
        records = folder / "records"
        if not records.is_dir():
            continue
        for path in sorted(records.glob("*.json")):
            try:
                record = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            if record_counts(record):
                found.append(record)
    return found


def refusal_notes(folders: List[Path], missing: List[str], tree: str, root: Path) -> List[str]:
    """Why each missing target has no record, from the refusal files that the record hook wrote: the latest refusal
    of each target, with its nonce and reason. A refusal counts here when its input tree is TREE, or, for a target
    that changes files, when its packet is of this worktree. A record of the same target and input tree that is newer
    than the refusal, whatever its status, or a record with the nonce of the refusal, makes the refusal old news. A
    record of another tree, as from another worktree, does not. A refusal of a target that changes files, which counts
    by its worktree, is also old news after a newer record of that target from the same worktree. The worktree of a
    record is in the packet of its nonce. A file that the gate cannot read is
    left out, so a bad refusal file never stops the gate with a fault of its own."""
    newest_record: Dict[Tuple[str, str], float] = {}
    # The newest record of each target that changes files, by the worktree of its packet.
    newest_changer: Dict[Tuple[str, str], float] = {}
    record_nonces: Set[str] = set()
    for folder in folders:
        for path in (folder / "records").glob("*.json") if (folder / "records").is_dir() else []:
            try:
                record, when = json.loads(path.read_text()), path.stat().st_mtime
                record_nonces.add(path.stem)
                if (isinstance(record, dict) and record.get("version") == 1 and isinstance(record.get("target"), str)
                        and isinstance(record.get("status"), str) and is_tree(record.get("input_tree"))):
                    key = (record["target"], record["input_tree"])
                    newest_record[key] = max(when, newest_record.get(key, 0.0))
                    if record["target"] in CHANGERS and isinstance(record.get("nonce"), str):
                        packet = json.loads((folder / "packets" / f"{path.stem}.json").read_text())
                        if isinstance(packet, dict) and isinstance(packet.get("worktree"), str):
                            place = (record["target"], str(Path(packet["worktree"]).resolve()))
                            newest_changer[place] = max(when, newest_changer.get(place, 0.0))
            except Exception:
                continue
    latest: Dict[str, Tuple[float, dict]] = {}
    for folder in folders:
        for path in (folder / "refusals").glob("*.json") if (folder / "refusals").is_dir() else []:
            try:
                refusal, when = json.loads(path.read_text()), path.stat().st_mtime
                if not (isinstance(refusal, dict) and refusal.get("version") == 1
                        and isinstance(refusal.get("target"), str) and refusal["target"] in missing
                        and isinstance(refusal.get("nonce"), str) and isinstance(refusal.get("reason"), str)):
                    continue
                target = refusal["target"]
                key = (target, refusal.get("input_tree"))
                if refusal["nonce"] in record_nonces or newest_record.get(key, -1.0) >= when:  # type: ignore[arg-type]
                    continue
                if refusal.get("input_tree") != tree:
                    worktree = refusal.get("worktree")
                    if target not in CHANGERS or not isinstance(worktree, str):
                        continue
                    if Path(worktree).resolve() != root.resolve():
                        continue
                    if newest_changer.get((target, str(root.resolve())), -1.0) >= when:
                        continue
                if target not in latest or when > latest[target][0]:
                    latest[target] = (when, refusal)
            except Exception:
                continue
    notes = []
    for target in missing:
        if target in latest:
            refusal = latest[target][1]
            # The reason comes from the fresh agent, so it loses each control character.
            reason = "".join(c if c.isprintable() else " " for c in refusal["reason"]).strip()[:600]
            nonce = "".join(c for c in refusal["nonce"] if c.isalnum())[:64]
            notes.append(f"The record hook refused the result of `just {target}` with the nonce {nonce}: {reason}")
    return notes


def missing_targets(required: List[str], records: List[dict], tree: str) -> List[str]:
    """The required targets with no record in a chain that ends at TREE, in the order to run them."""
    by_target: Dict[str, List[Tuple[str, str]]] = {}
    for record in records:
        by_target.setdefault(record["target"], []).append((record["input_tree"], record["output_tree"]))
    missing = [t for t in required if t not in CHANGERS and (tree, tree) not in by_target.get(t, [])]
    changers = [t for t in CHANGERS if t in required]

    def chain_ends(index: int, end: str) -> bool:
        """True when the changers up to INDEX make a chain whose last output tree is END."""
        if index < 0:
            return True
        return any(out == end and chain_ends(index - 1, start) for start, out in by_target.get(changers[index], []))

    if changers and not chain_ends(len(changers) - 1, tree):
        # A changer that runs again changes the input of each later one, so they all run again, in order.
        missing = changers + missing
    return missing


def is_agent() -> bool:
    return any(os.environ.get(name) for name in AGENT_VARIABLES)


def required_against(root: Path, parent: Optional[str], stack: dict, tree: str) -> List[str]:
    """The targets that the rules of PARENT require for the change from PARENT to TREE."""
    if parent is None:
        required_text, generated = DEFAULT_REQUIRED, []
    else:
        required_text = read_at(root, parent, REQUIRED)
        required_text = DEFAULT_REQUIRED if required_text is None else required_text
        generated = list_lines(read_at(root, parent, GENERATED))
    try:
        required_paths = parse_required(required_text)
    except Stop as stop:
        # A list from before the gate checked it. The default list applies, so the commit that fixes it can go.
        print(f"commit gate: {stop}. The gate uses the default list for this commit", file=sys.stderr)
        required_paths = parse_required(DEFAULT_REQUIRED)
    # The code globs of the parent and of the commit both count, so a commit that removes a language still needs
    # test-review for its code. A parent with no stack.json, before the gates came, gives no globs.
    parent_stack = None if parent is None else read_at(root, parent, STACK)
    code = merged_code(stack, parent_stack)
    # Each alias that rules decide, and its rules. @pages without its rule keeps its globs, and @api without a rule
    # names no file, as pathspecs() says.
    aliases: Dict[str, List[Callable[[List[str]], List[str]]]] = {}
    if any("@pages" in paths for paths in required_paths.values()):
        rule = page_rule(root, parent)
        if rule is not None:
            aliases["@pages"] = [rule]
    if any("@api" in paths for paths in required_paths.values()):
        aliases["@api"] = api_rules(root, parent, stack, parent_stack)
    answers: Dict[str, bool] = {}
    changed: List[List[str]] = []

    def matches(alias: str) -> bool:
        if alias not in answers:
            if not changed:
                changed.append(changed_files(root, parent, tree, generated))
            # Each rule runs, so a broken rule stops the commit though another rule accepts a path.
            answers[alias] = any([bool(rule(changed[0])) for rule in aliases[alias]])
        return answers[alias]

    def needed(paths: List[str]) -> bool:
        # Each rule runs before any answer, so a broken rule stops the commit though another alias matches.
        for alias in aliases:
            matches(alias)
        for alias in aliases:
            if alias in paths:
                if matches(alias):
                    return True
                paths = [path for path in paths if path != alias]
        return changes_match(root, parent, tree, pathspecs(paths, code, generated))

    return [t for t, paths in required_paths.items() if needed(paths)]


def gate(root: Path) -> None:
    parents = parents_of_commit(root)
    stack_text = read_at(root, "", STACK)
    if stack_text is None and any(p is not None and read_at(root, p, STACK) is not None for p in parents):
        raise Stop(f"the commit removes {STACK}, and the gate needs it. To remove the gates, take off their hooks "
                   "first, then commit")
    # The steps come from the commit, since jlog passes the steps of the worktree. A commit that removes a tool
    # removes its step. The review of the commit sees that change.
    stack = load_stack(stack_text)
    # A line that the gate cannot read must not land, or it would stop every later commit.
    own_list = read_at(root, "", REQUIRED)
    if own_list is not None:
        parse_required(own_list)
    tree = commit_tree(root)
    required: List[str] = ["review"]
    for parent in parents:
        required += [t for t in required_against(root, parent, stack, tree) if t not in required]

    known = recipes(root)
    absent = [name for name in ["check", *stack["steps"], *required] if name not in known]
    if absent:
        raise Stop("the Justfile has no recipe " + ", ".join(f"`{name}`" for name in absent) + ": run `just install`")

    if worktree_tree(root) != tree:
        raise Stop("only part of the changes is staged, and the gate checks the whole worktree. Stage them all, or "
                   "put the rest aside: run `git stash --keep-index -u`, then the targets that the new tree needs and "
                   "`just check`, then commit, then `git stash pop`")

    folders = log_folders(root)
    if not has_pass(folders, tree, stack["steps"]):
        message = "no pass of `just check` for this tree: run `just check`"
        if os.environ.get("PRE_COMMIT") == "1":
            # The framework puts the unstaged changes aside before its hooks, so partial staging looks like this.
            message += (". If only part of the changes is staged, pre-commit put the rest aside, so a pass of the "
                        "whole worktree does not count. Stage them all, or run `git stash --keep-index -u`, then the "
                        "targets that the new tree needs and `just check`, then commit, then `git stash pop`")
        raise Stop(message)

    if is_agent():
        missing = missing_targets(required, load_records(folders), tree)
        if missing:
            notes = refusal_notes(folders, missing, tree, root)
            raise Stop("no record for this tree of " + ", ".join(f"`just {t}`" for t in missing)
                       + ": run them in this order" + "".join(f". {note}" for note in notes))


TRAILER = "Commit-Gate"


def empty_tree(root: Path) -> str:
    return git(["mktree"], root, plain_env()).strip()


def patch_id(diff: str, root: Path) -> str:
    """The stable patch ID of DIFF, or `none` for a change with no diff, as in git commit --allow-empty."""
    run = subprocess.run(["git", "patch-id", "--verbatim"], cwd=root, input=diff, capture_output=True, text=True,
                         errors="surrogateescape")
    fields = run.stdout.split()
    return fields[0] if run.returncode == 0 and fields else "none"


# No lines of context, so a change of the lines next to a change, as in a rebase, keeps the patch ID.
DIFF_OPTIONS = ["-p", "-U0", "--no-renames", "--binary", "--no-color", "--no-ext-diff"]


def staged_patch_id(root: Path, parent: Optional[str]) -> str:
    """The patch ID of the commit that git is making: the tree of the index of the hook against PARENT. The tree
    leaves out a file of git add -N, as the commit does."""
    base = empty_tree(root) if parent is None else parent
    return patch_id(git(["diff-tree", *DIFF_OPTIONS, base, commit_tree(root)], root, plain_env()), root)


def commit_patch_id(root: Path, commit: str) -> str:
    """The patch ID of COMMIT against its one parent, or against the empty tree for a first commit."""
    parents = git(["rev-list", "--parents", "-n", "1", commit], root).split()[1:]
    base = parents[0] if parents else empty_tree(root)
    return patch_id(git(["diff-tree", *DIFF_OPTIONS, base, commit], root), root)


def trailer_value(root: Path) -> str:
    """The words of the trailer: tree:<tree> for a merge, and patch:<id> for each parent that the commit may have.
    An amend of a merge is a merge too."""
    if resolve(root, "MERGE_HEAD") is not None:
        return f"tree:{commit_tree(root)}"
    words = []
    for parent in parents_of_commit(root):
        word = f"patch:{staged_patch_id(root, parent)}"
        if word not in words:
            words.append(word)
    head = resolve(root, "HEAD")
    if head is not None and is_amend(git_argv()) and len(git(["rev-list", "--parents", "-n", "1", head], root,
                                                             plain_env()).split()) > 2:
        words.append(f"tree:{commit_tree(root)}")
    return " ".join(words)


RELEASE_CHECK = "release-check"
RELEASE_TIMEOUT = 120


def rebasing(root: Path) -> bool:
    """True during a rebase. A reword replays an old commit on a HEAD that may lack the later raise of the version,
    and the release sees only the HEAD at the end."""
    return any((root / git(["rev-parse", "--git-path", name], root, plain_env()).strip()).exists()
               for name in ("rebase-merge", "rebase-apply"))


def release_check(root: Path, message: Path) -> None:
    """Run `just release-check` with the message of the commit, so that a commit whose type asks for a release
    with an old manifest version stops here, not at the release after the push."""
    if resolve(root, "MERGE_HEAD") is not None or rebasing(root) or RELEASE_CHECK not in recipes(root):
        return
    env = plain_env()
    env["JN_RELEASE_MESSAGE"] = str(message.resolve())
    head = resolve(root, "HEAD")
    if head is not None and is_amend(git_argv()):
        if len(git(["rev-list", "--parents", "-n", "1", head], root, plain_env()).split()) > 2:
            return  # An amend of a merge is a merge, and the release skips merge commits.
        env["JN_RELEASE_AMEND"] = "1"
    try:
        run = subprocess.run(["just", RELEASE_CHECK], cwd=root, env=env, stdin=subprocess.DEVNULL,
                             capture_output=True, text=True, errors="replace", timeout=RELEASE_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise Stop(f"`just {RELEASE_CHECK}` did not end in {RELEASE_TIMEOUT} seconds") from None
    if run.returncode != 0:
        lines = [line for line in run.stderr.splitlines() if line.startswith("release: ")] or run.stderr.splitlines()
        reason = " ".join(line.strip() for line in lines[-3:]) or f"exit {run.returncode}"
        raise Stop(f"`just {RELEASE_CHECK}` fails with the message of this commit: {reason}")


def add_trailer(root: Path, message: Path) -> None:
    # With --no-divider, a line --- in the message is text, so the trailer goes at the end, where git log reads it.
    git(["interpret-trailers", "--in-place", "--no-divider", "--if-exists", "replace", "--trailer",
         f"{TRAILER}: {trailer_value(root)}", str(message)], root, plain_env())


def ci_range(root: Path, env: Mapping[str, str]) -> Tuple[Optional[str], str]:
    """The commits that `just ci-gate` checks, as BASE and HEAD. A BASE of None means all the commits of HEAD.

    The pre-push hook of the pre-commit framework gives the commits of the push in PRE_COMMIT_FROM_REF and
    PRE_COMMIT_TO_REF, or only PRE_COMMIT_LOCAL_BRANCH for a push of a new history, which the remote has no commit of.
    For an existing remote branch, JN_CI_BASE selects the PR target tip as base. It must be an ancestor of the
    pushed head, and each of its commits must be on the remote. PRE_COMMIT_TO_REF remains the head; a conflicting
    JN_CI_HEAD stops the push. Without that selection, the push range is unchanged. New-history pushes still check all commits. Outside a push, CI gives
    JN_CI_BASE and JN_CI_HEAD; by hand the base is the upstream of the branch, or else origin/HEAD."""
    if env.get("PRE_COMMIT_FROM_REF") and env.get("PRE_COMMIT_TO_REF"):
        if env.get("JN_CI_BASE"):
            def resolve(value: str, label: str) -> str:
                commit = git(["rev-parse", "--verify", "--quiet", "--end-of-options", f"{value}^{{commit}}"],
                             root, plain_env(), check=False).strip()
                if not commit:
                    raise Stop(f"{label} does not resolve to a commit: {value}")
                return commit

            base = resolve(env["JN_CI_BASE"], "JN_CI_BASE")
            head = resolve(env["PRE_COMMIT_TO_REF"], "pushed head")
            if env.get("JN_CI_HEAD") and resolve(env["JN_CI_HEAD"], "JN_CI_HEAD") != head:
                raise Stop("JN_CI_HEAD differs from the pushed head in PRE_COMMIT_TO_REF")
            try:
                git(["merge-base", "--is-ancestor", base, head], root, plain_env())
            except Stop as exc:
                raise Stop("JN_CI_BASE must be an ancestor of the pushed head") from exc
            # Each commit of the base must be on the remote already, so that each commit new to the remote stays in
            # BASE..HEAD. A base of HEAD, of a new commit or of a local branch ahead of the remote stops the push.
            remote = env.get("PRE_COMMIT_REMOTE_NAME")
            remotes = f"--remotes={remote}" if remote else "--remotes"
            if git(["rev-list", "-n", "1", base, "--not", remotes], root, plain_env()).strip():
                raise Stop(f"JN_CI_BASE contains commits that are not on the remote{' ' + remote if remote else ''}. Fetch the PR "
                           "target and give the SHA of its tip")
            count = git(["rev-list", "--count", f"{base}..{head}"], root, plain_env()).strip()
            print(f"ci-gate: JN_CI_BASE {base[:12]} selects {count} commits of the push", file=sys.stderr)
            return base, head
        return env["PRE_COMMIT_FROM_REF"], env["PRE_COMMIT_TO_REF"]
    if env.get("PRE_COMMIT_LOCAL_BRANCH"):
        return None, env["PRE_COMMIT_LOCAL_BRANCH"]
    head = env.get("JN_CI_HEAD") or "HEAD"
    if env.get("JN_CI_BASE"):
        return env["JN_CI_BASE"], head
    for name in ("@{upstream}", "origin/HEAD"):
        if git(["rev-parse", "--verify", "--quiet", f"{name}^{{commit}}"], root, plain_env(), check=False).strip():
            return name, head
    raise Stop("the commits to check have no base: the branch has no upstream and there is no origin/HEAD. Give "
               "the base in JN_CI_BASE for one command, as JN_CI_BASE=origin/main just ci")


def check_trailers(root: Path, base: Optional[str], head: str) -> List[str]:
    """The problems of the commits in BASE..HEAD, or of all the commits of HEAD when BASE is None: each one needs a
    trailer of the gate that names its change."""
    problems = []
    span = head if base is None else f"{base}..{head}"
    for commit in git(["rev-list", "--reverse", span], root).split():
        values = git(["log", "-1", f"--format=%(trailers:key={TRAILER},valueonly,separator=%x00)", commit],
                     root).strip("\n").split("\0")
        words = [value.split() for value in values if value.strip()]
        short = commit[:12]
        if not words:
            problems.append(f"{short} has no {TRAILER} trailer, so it did not pass the commit gate")
            continue
        parents = git(["rev-list", "--parents", "-n", "1", commit], root).split()[1:]
        if len(parents) > 1:
            expected, kind = git(["rev-parse", f"{commit}^{{tree}}"], root).strip(), "tree"
        else:
            expected, kind = commit_patch_id(root, commit), "patch"
        if not any(f"{kind}:{expected}" in w for w in words):
            problems.append(f"{short} changed after the commit gate passed it: its {kind} is {expected}. Commit it "
                            "again through the gate, for example with git commit --amend --no-edit")
    return problems


# The command that runs the gate, as the hooks run it.
GATE_COMMAND = ("uv run --no-project --quiet --no-python-downloads --python '>=3.9' python "
                ".agents/skills/gcm/scripts/commit_gate.py")

# The config of the framework, and the hooks of it that the tasker role needs: the stages and the entry of each one.
# The gate runs before a commit and before the commit of a merge.
CONFIG = ".pre-commit-config.yaml"
CONFIG_HOOKS = {"commit-gate": (("pre-commit", "pre-merge-commit"), GATE_COMMAND),
                "commit-gate-trailer": (("commit-msg",), f"{GATE_COMMAND} --hook commit-msg"),
                "just-ci": (("pre-push",), "just ci")}

# The stages of the gate, the stages that the tasker role installs, and the text that each hook of the pre-commit
# framework holds. The pre-push hook runs just ci, not the gate.
HOOK_STAGES = ("pre-commit", "pre-merge-commit", "commit-msg")
INSTALLED_STAGES = HOOK_STAGES + ("pre-push",)
FRAMEWORK_MARK = "# File generated by pre-commit"


def framework_hook_problem(root: Path, stage: str) -> Optional[str]:
    """Why the git hook of the stage does not run the pre-commit framework, or None when it does. The hook runs the
    Python of its INSTALL_PYTHON line when that file is there, else pre-commit from PATH."""
    hook = root / git(["rev-parse", "--git-path", f"hooks/{stage}"], root, plain_env()).strip()
    try:
        text = hook.read_text(errors="replace")
    except OSError:
        return f"{stage}: there is no hook"
    if FRAMEWORK_MARK not in text or f"--hook-type={stage}" not in text:
        return f"{stage}: the hook is not a {stage} hook of the pre-commit framework"
    if f"--config={CONFIG}" not in text:
        return f"{stage}: the hook runs a config other than {CONFIG}"
    python = next((line.partition("=")[2].strip() for line in text.splitlines()
                   if line.startswith("INSTALL_PYTHON=")), "")
    python = python.strip("'\"")
    if python and os.access(python, os.X_OK):
        run = subprocess.run([python, "-c", "import pre_commit"], stdin=subprocess.DEVNULL, capture_output=True)
        return None if run.returncode == 0 else f"{stage}: {python} of the hook has no pre-commit"
    return None if shutil.which("pre-commit") else f"{stage}: pre-commit is not on PATH"


# The script that reads the config with the loader of pre-commit, in the Python of the framework, and prints the
# hooks of its local entries. A hook with no stages of its own runs in the default_stages of the config.
LOAD_CONFIG = """import json, sys
from pre_commit.clientlib import load_config
config = load_config(sys.argv[1])
print(json.dumps([{"id": h["id"], "entry": h.get("entry"), "stages": h.get("stages") or config["default_stages"]}
                  for r in config["repos"] if r["repo"] == "local" for h in r["hooks"]]))"""


def framework_python(root: Path) -> Optional[str]:
    """The Python that has pre-commit: the INSTALL_PYTHON of the pre-commit hook, else the Python of the pre-commit
    on PATH, from its first line."""
    hook = root / git(["rev-parse", "--git-path", "hooks/pre-commit"], root, plain_env()).strip()
    try:
        lines = hook.read_text(errors="replace").splitlines()
    except OSError:
        lines = []
    for line in lines:
        if line.startswith("INSTALL_PYTHON="):
            python = line.partition("=")[2].strip().strip("'\"")
            if python and os.access(python, os.X_OK):
                return python
    program = shutil.which("pre-commit")
    if program:
        try:
            lines = Path(program).read_text(errors="replace").splitlines()[:2]
        except OSError:
            return None
        first = lines[0] if lines else ""
        words = first[2:].split() if first.startswith("#!") else []
        # pip and uv write this launcher when the path of the Python is long or has a space.
        if len(lines) > 1 and lines[1].startswith("'''exec'"):
            try:
                words = shlex.split(lines[1])[1:2]
            except ValueError:
                words = []
        elif words[:1] and Path(words[0]).name == "env":
            words = [shutil.which(words[1]) or ""] if len(words) > 1 else []
        python = words[0] if words else ""
        # A shell wrapper, as of pyenv, asdf or mise, names no Python on its first line.
        if python and os.access(python, os.X_OK) and has_pre_commit(python):
            return python
    return None


def has_pre_commit(python: str) -> bool:
    # In an empty folder, so that no pre_commit folder of the current folder can answer for the module.
    with tempfile.TemporaryDirectory(prefix="commit-gate-python-") as away:
        run = subprocess.run([python, "-c", "import pre_commit"], stdin=subprocess.DEVNULL, capture_output=True,
                             cwd=away)
    return run.returncode == 0


def config_problems(root: Path) -> List[str]:
    """The hooks of the tasker role that the config lacks, read by the loader of pre-commit. Each one must be in a
    local entry, with its entry and its stage. The installer keys the entries of `repos` by `repo`, so a `local`
    entry of the project takes the place of the entry of the role, and its hooks go."""
    if not (root / CONFIG).is_file():
        return [f"there is no {CONFIG}"]
    python = framework_python(root)
    if python is None:
        return [f"no Python with pre-commit can read {CONFIG}: the pre-commit hook names none, and the first line "
                "of the pre-commit on PATH names none"]
    # Outside the project, so that a json.py or a pre_commit folder of the project cannot take the place of the module.
    with tempfile.TemporaryDirectory(prefix="commit-gate-config-") as away:
        run = subprocess.run([python, "-c", LOAD_CONFIG, str((root / CONFIG).resolve())], stdin=subprocess.DEVNULL,
                             capture_output=True, text=True, cwd=away)
    try:
        hooks = json.loads(run.stdout) if run.returncode == 0 else None
    except ValueError:
        hooks = None
    if not isinstance(hooks, list):
        return [f"pre-commit cannot read {CONFIG}: {(run.stderr.strip().splitlines() or ['no output'])[-1]}"]
    problems = []
    for name, (stages, entry) in CONFIG_HOOKS.items():
        for stage in stages:
            if not any(isinstance(h, dict) and h.get("id") == name and h.get("entry") == entry
                       and stage in (h.get("stages") or ()) for h in hooks):
                problems.append(f"{CONFIG} has no local hook {name} that runs {entry} for the stage {stage}. A "
                                "repo: local entry of the project takes the place of the entry of the tasker role, so "
                                "copy the hooks of .agents/skills/gcm/assets/pre-commit-config.yaml into it")
    return problems


def check_hooks(root: Path) -> List[str]:
    """The problems with the hooks of the gate: one line for each stage whose hook does not run pre-commit. With
    core.hooksPath set, as husky sets it, pre-commit refuses to install, so there is no problem to fix here: the
    hooks of that folder must run the gate."""
    hooks_path = git(["config", "--get", "core.hooksPath"], root, plain_env(), check=False).strip()
    if hooks_path:
        print(f"commit gate: core.hooksPath is {hooks_path}, so pre-commit installs no hook. Run "
              f"{GATE_COMMAND} from the pre-commit and pre-merge-commit hooks of that folder, {GATE_COMMAND} --hook "
              f"commit-msg from its commit-msg hook, and just ci from its pre-push hook.", file=sys.stderr)
        return []
    hooks = [problem for stage in INSTALLED_STAGES for problem in [framework_hook_problem(root, stage)] if problem]
    return config_problems(root) + hooks


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="The commit gate.")
    parser.add_argument("--hook", choices=HOOK_STAGES, default="pre-commit")
    parser.add_argument("message", nargs="?", help="the message file, for the commit-msg hook")
    parser.add_argument("--trailers", nargs="*", metavar="BASE HEAD",
                        help="check the trailers of BASE..HEAD; with no BASE and HEAD, of the range of ci_range")
    parser.add_argument("--check-hooks", action="store_true",
                        help="check that the pre-commit framework runs the four hooks of the tasker role")
    args = parser.parse_args(argv)
    if args.check_hooks and not git(["rev-parse", "--show-toplevel"], Path.cwd(), plain_env(), check=False):
        # Outside a repository there is no hook to install yet. The first just install after git init installs them.
        print("commit gate: this folder is not in a Git repository, so it has no hooks yet", file=sys.stderr)
        return 0
    try:
        root = Path(git(["rev-parse", "--show-toplevel"], Path.cwd(), plain_env()).strip())
        if args.trailers is not None:
            if len(args.trailers) not in (0, 2):
                parser.error("--trailers takes BASE and HEAD, or nothing")
            base, head = args.trailers if args.trailers else ci_range(root, os.environ)
            problems = check_trailers(root, base, head)
            for problem in problems:
                print(f"gate trailers: {problem}", file=sys.stderr)
            return 1 if problems else 0
        problems = check_hooks(root) if args.check_hooks else []
        if not args.check_hooks:
            gate(root)
            if args.hook == "commit-msg":
                if args.message is None:
                    raise Stop("the commit-msg hook needs the message file")
                release_check(root, Path(args.message))
                add_trailer(root, Path(args.message))
    except Stop as stop:
        problems = [str(stop)]
    for problem in problems:
        print(f"commit gate: {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
