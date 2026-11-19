"""The gate guard: an agent hook that stops the plain commands that go around the commit gate.

The `PreToolUse` hooks of Claude Code and Codex run it before each tool call, with the hook input as JSON on stdin.
It exits with 2 and says why on stderr to stop the call, and with 0 to let it run. It never checks records: the
commit gate does that.

The guard is a guard against mistakes, not a lock. It reads the words of the line, and does not try to understand
what the shell makes of them. A command that hides git, such as a script or `python -c`, runs. The lock is the
trailer that the gate writes on each commit, which `just ci-gate` checks in CI. A commit that went around the
gate has no trailer, so CI stops it. The guard stops:

- `git commit` with `--no-verify` or `-n`, and `git merge` or `git pull` with `--no-verify`, also through a git
  alias, `sh -c`, `eval` or `git rebase --exec`;
- a setting of `core.hooksPath`, by `git -c`, `git config` or a `GIT_CONFIG_` variable, and `git commit-tree` and
  `git update-ref`;
- a commit while `core.hooksPath` is set, since git would then not run the gate;
- a write to a log folder, `.git/hooks`, `.git/config`, `.agents/targets/required.txt`, `.pre-commit-config.yaml` or
  the settings of the agent hooks, by a shell command, or by a file tool of Claude Code. Codex runs the guard for its
  shell only.

It asks the person before `just record-skip` or `record_result.py skip`, which let a tree through without a
record. Claude Code shows the question. Codex has no question for a hook, so there the guard stops the call and the
agent asks the person to run the command. It stops `record_result.py hook`, which only the harness runs, `just
record` in Claude Code, a record command that changes a variable of the harness, and a write to the sessions folder
of Codex.

When the guard itself fails, it lets the call run, since the gate and CI still check the commit. A line that names
git stops then, so that a fault does not open the way.

Usage: gate_guard.py, with the hook input on stdin.
"""

from __future__ import annotations

import functools
import json
import os
import posixpath
import re
import shlex
import subprocess
import sys
from typing import Dict, List, Optional, Sequence, Tuple

# The paths that only the installer, jlog and the record hooks write.
PROTECTED = (".agents/log", ".git/hooks", ".git/config", ".agents/targets/required.txt", ".pre-commit-config.yaml",
             ".claude/settings.json", ".claude/settings.local.json", ".codex/hooks.json", ".codex/config.toml")

# The programs that change each file that they name, and the programs that change only the last one.
WRITE_ALL = {"mv", "rm", "tee", "touch", "truncate", "chmod", "chown", "unlink", "mkdir", "rmdir", "shred"}
WRITE_LAST = {"cp", "ln", "install", "rsync", "scp"}
# The short options of sed, perl and ruby that take a value. In a cluster such as -ne, the rest is its value.
VALUE_FLAGS = {"sed": set("ef"), "perl": set("eEMmIlx0C"), "ruby": set("eEIrCx0")}

# The words in front of a program that run it, with their options that take a value.
PREFIXES: Dict[str, set] = {"env": {"-u", "-C", "--unset", "--chdir"}, "command": set(), "exec": {"-a"},
                            "nohup": set(), "builtin": set(), "time": {"-f", "-o"}, "nice": {"-n", "--adjustment"},
                            "sudo": {"-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-U", "-T"},
                            "timeout": {"-s", "-k", "--signal", "--kill-after"}, "doas": {"-u", "-C"},
                            "xargs": {"-I", "-L", "-n", "-P", "-s", "-d", "-E", "-a"}}
# The prefixes whose first word after the options is not the program, such as the time limit of timeout.
PREFIX_ARGUMENT = {"timeout"}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
# The words that start a part of a compound command, in front of a program.
KEYWORDS = {"if", "then", "else", "elif", "do", "while", "until", "!", "{", "}"}
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", "|&", ";;"}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\+?=")

# The options of git that come before the command and take a value.
GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
# The short options of git commit that take a value. In a cluster such as -am, the rest of the cluster after one of
# them is its value.
COMMIT_VALUE_FLAGS = set("mFCctSu")
# The git commands that make a commit, and so run the gate.
COMMITS = {"commit", "merge", "pull", "rebase", "cherry-pick", "revert", "am"}
# A line that sets one of these could give git a core.hooksPath.
CONFIG_VARIABLE = re.compile(r"\bGIT_CONFIG_[A-Z0-9_]+\b")
# How deep the guard follows sh -c, eval and git aliases.
DEPTH = 4


class Blocked(Exception):
    pass


# The commands of the current call that need the person: a skip lets a tree through without a record.
ASKS: List[str] = []
RECORD_SCRIPT = "record_result.py"
# The variables that tell the record script which harness runs it, and where the transcripts of Codex are.
HARNESS_VARIABLES = ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID", "CODEX_HOME")


def name_of(word: str) -> str:
    return posixpath.basename(word.lstrip("`"))


# The start of a here-doc, as in cat <<'EOF', but not the here-string <<<.
HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def without_heredocs(command: str) -> str:
    """COMMAND without the bodies of its here-docs, which are text such as a commit message."""
    kept, end = [], None
    for line in command.split("\n"):
        if end is not None:
            if line.strip() == end:
                end = None
            continue
        kept.append(line)
        for match in HEREDOC.finditer(line):
            before = line[:match.start()]
            # Not inside quotes, as in -m "use <<EOF", and not a shift, as in $((x << y)).
            if before.count("'") % 2 == 0 and before.count('"') % 2 == 0 and "((" not in before:
                end = match.group(2)
    return "\n".join(kept)


def words_of(text: str) -> List[str]:
    lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|()<>")
    lexer.whitespace_split = True
    return list(lexer)


def segments(command: str) -> List[List[str]]:
    """The simple commands of COMMAND, as lists of words. A new line ends a command, and $( and ( start one, so a
    substitution is a command of its own. A redirection such as > stays a word. The body of a here-doc is left out."""
    # A backslash at the end of a line goes on to the next one, as in git commit \ -n.
    # An even run of backslashes before it is literal text, so only an odd run goes on.
    lines = re.sub(r"(?<!\\)((?:\\\\)*)\\\n", r"\1 ", without_heredocs(command)).split("\n")
    try:
        # Each line on its own, so that a comment ends at the end of its line.
        words = [word for line in lines for word in words_of(line) + [";"]]
    except ValueError:
        # A quote that goes on to the next line, or that does not close.
        text = " ; ".join(lines)
        try:
            words = words_of(text)
        except ValueError:
            words = words_of(text.replace("'", " ").replace('"', " "))
    found: List[List[str]] = [[]]
    for word in words:
        if word in SEPARATORS:
            found.append([])
        elif word.endswith("$") and len(word) > 1:
            # The $ of $( sticks to the word before the (.
            found[-1].append(word[:-1])
        elif word != "$":
            found[-1].append(word)
    return [words for words in found if words]


def program_of(words: List[str]) -> List[str]:
    """The words from the program on: without the assignments such as A=1, the keywords and the prefixes."""
    rest = list(words)
    while rest:
        word, name = rest[0], name_of(rest[0])
        if ASSIGNMENT.match(word) or word in KEYWORDS:
            rest.pop(0)
        elif name in PREFIXES:
            rest.pop(0)
            while rest and rest[0].startswith("-"):
                option = rest.pop(0)
                if option in PREFIXES[name] and rest:
                    rest.pop(0)
            if name in PREFIX_ARGUMENT and rest:
                rest.pop(0)
        else:
            break
    return rest


def has_abbreviation(words: Sequence[str], option: str, shortest: str) -> bool:
    """True when a word is OPTION or an abbreviation of it that git takes, at least as long as SHORTEST."""
    return any(len(word) >= len(shortest) and option.startswith(word) for word in words)


def commit_skips_hooks(args: Sequence[str]) -> bool:
    for word in args:
        if word == "--":
            return False
        if word.startswith("-") and not word.startswith("--"):
            for flag in word[1:]:
                if flag == "n":
                    return True
                if flag in COMMIT_VALUE_FLAGS:
                    break
    # --no-verify and the abbreviations that git takes. --no-ver is also --no-verbose.
    return has_abbreviation(args, "--no-verify", "--no-veri")


def sets_hooks_path(setting: str) -> bool:
    return setting.lower().startswith("core.hookspath")


def git_output(args: Sequence[str], cwd: str) -> Optional[str]:
    """The output of git ARGS in CWD, or None when git fails or does not run."""
    try:
        run = subprocess.run(["git", *args], cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                             timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return run.stdout.strip() if run.returncode == 0 else None


def check_hooks_path(cwd: str) -> None:
    """Stop a commit when git has a core.hooksPath for CWD, since git would then not run the gate."""
    folder = cwd if os.path.isdir(cwd) else None
    if folder is None:
        return
    origin = git_output(["config", "--show-origin", "--get", "core.hooksPath"], folder)
    if origin:
        raise Blocked(f"core.hooksPath is set ({origin}), so git would not run the commit gate. Ask the person to "
                      "remove it. A hooks folder of their own can call the pre-commit hook of the gate")


def check_git(args: List[str], cwd: str, depth: int) -> None:
    """Check the words of a git command after the word git."""
    index, aliases = 0, {}
    while index < len(args) and args[index].startswith("-"):
        option = args[index]
        value = None
        if option in GIT_VALUE_OPTIONS and index + 1 < len(args):
            value, index = args[index + 1], index + 2
        else:
            index += 1
            if option.startswith("-c") and len(option) > 2:
                value, option = option[2:], "-c"
            elif "=" in option:
                option, value = option.split("=", 1)
        if option == "-C" and value is not None:
            cwd = os.path.join(cwd, os.path.expanduser(value))
        if option in ("-c", "--config-env") and value is not None:
            setting = value.lower()
            if sets_hooks_path(value) or setting.startswith("include.") or setting.startswith("includeif."):
                raise Blocked("core.hooksPath moves the git hooks, and the commit gate with them. Leave it alone")
            if value.lower().startswith("alias.") and "=" in value:
                name, text = value[6:].split("=", 1)
                aliases[name.lower()] = text
    if index >= len(args):
        return
    sub, rest = args[index], args[index + 1:]
    alias = aliases.get(sub.lower())
    if alias is None and sub not in COMMITS and sub not in ("config", "commit-tree", "update-ref"):
        alias = git_output(["config", "--get", f"alias.{sub}"], cwd) if os.path.isdir(cwd) else None
    if alias is not None and depth < DEPTH:
        if alias.startswith("!"):
            check_command(alias[1:] + " " + shlex.join(rest), cwd, depth + 1)
        else:
            check_git(shlex.split(alias) + rest, cwd, depth + 1)
        return
    if sub == "commit" and commit_skips_hooks(rest):
        raise Blocked("git commit -n and --no-verify skip the commit gate. Commit through the gate")
    if sub in ("merge", "pull") and has_abbreviation(rest, "--no-verify", "--no-veri"):
        raise Blocked(f"git {sub} --no-verify skips the commit gate. Merge through the gate")
    if sub in ("commit-tree", "update-ref"):
        raise Blocked(f"git {sub} makes a commit or moves a branch without the commit gate")
    if sub == "config":
        values, skip = [], False
        for word in rest:
            if skip:
                skip = False
            elif word in ("-f", "--file", "--blob", "--type", "--default", "--comment", "--value"):
                skip = True
            elif not word.startswith("-"):
                values.append(word)
        if values and values[0] in ("set", "unset", "get"):
            values = values[1:] if values[0] == "set" else []
        if any(sets_hooks_path(w) for w in values[:1]) and len(values) > 1:
            raise Blocked("core.hooksPath moves the git hooks, and the commit gate with them. Leave it alone")
    if sub == "rebase":
        for position, word in enumerate(rest):
            text = None
            if word in ("-x", "--exec") and position + 1 < len(rest):
                text = rest[position + 1]
            elif word.startswith("--exec="):
                text = word.split("=", 1)[1]
            if text is not None and depth < DEPTH:
                check_command(text, cwd, depth + 1)
    if sub in COMMITS:
        check_hooks_path(cwd)


@functools.lru_cache(maxsize=None)
def places(cwd: str) -> Tuple[Tuple[str, str], ...]:
    """Each protected path of the repository of CWD, with its real place. The hooks and the shared log folder are
    in the main checkout, also for a worktree. Outside a repository, the paths are under CWD."""
    root, common = os.path.realpath(cwd), None
    # Inside .git, git has no work tree, but it still knows the git folder.
    found_common = git_output(["rev-parse", "--path-format=absolute", "--git-common-dir"], cwd)
    if found_common:
        common = os.path.realpath(found_common)
        top = git_output(["rev-parse", "--path-format=absolute", "--show-toplevel"], cwd)
        root = os.path.realpath(top) if top else root
    found = [(path, os.path.join(root, path)) for path in PROTECTED]
    # The transcripts of Codex are the proof of a `just record` in Codex.
    codex = os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex")
    found.append(("the Codex sessions folder", os.path.join(os.path.realpath(codex), "sessions")))
    if common:
        found.append((".git/hooks", os.path.join(common, "hooks")))
        found.append((".git/config", os.path.join(common, "config")))
        if os.path.basename(common) == ".git":
            # The main checkout holds the shared log, and its settings decide whether the records come from a hook.
            found += [(path, os.path.join(os.path.dirname(common), path)) for path in PROTECTED]
    return tuple(found)


def protected_path(word: str, cwd: str, above: bool = False) -> Optional[str]:
    """The protected path that WORD names, in the repository of CWD, or None. With ABOVE, a folder that holds a
    protected path counts too, as for rm -rf .agents. A word that the shell changes, such as one with a variable,
    could be any path, so the guard lets it run."""
    text = word.replace("\\", "/")
    if "=" in text and not text.startswith("/"):
        text = text.split("=", 1)[1]
    # $PWD and $HOME have known values. Any other variable could be any path.
    known = {"PWD": cwd, "HOME": os.path.expanduser("~")}
    text = re.sub(r"\$\{(PWD|HOME)\}|\$(PWD|HOME)\b", lambda m: known[m.group(1) or m.group(2)], text)
    if not text or "$" in text or "`" in text:
        return None
    full = os.path.realpath(os.path.join(cwd, os.path.expanduser(text)))
    # A folder that the line makes, as in mkdir sub && cd sub, is not there yet. Its repository is that of the
    # nearest folder that is.
    base = os.path.realpath(cwd)
    while not os.path.isdir(base) and os.path.dirname(base) != base:
        base = os.path.dirname(base)
    for path, place in places(base):
        if full == place or full.startswith(place + os.sep) or above and place.startswith(full + os.sep):
            return path
    return None


def raise_write(path: str) -> None:
    raise Blocked(f"{path} is written only by the installer, jlog and the record hooks, so the commit gate can "
                  "trust it. Ask the person to change it")


def in_cluster(word: str, value_flags: set) -> bool:
    """True when a short option cluster such as -pi has -i before any option that takes a value."""
    if not word.startswith("-") or word.startswith("--"):
        return False
    for flag in word[1:]:
        if flag == "i":
            return True
        if flag in value_flags:
            return False
    return False


def check_writes(words: List[str], rest: List[str], cwd: str) -> None:
    # A redirection writes to the word after it, whatever the program.
    for index, word in enumerate(words[:-1]):
        if ">" in word and set(word) <= set("<>&|0123456789"):
            path = protected_path(words[index + 1], cwd)
            if path:
                raise_write(path)
    if not rest:
        return
    program = name_of(rest[0])
    # The word after a redirection is no argument: < reads it, and > is checked above.
    args, skip = [], False
    words_after = rest[1:]
    for index, word in enumerate(words_after):
        if skip:
            skip = False
        elif set(word) <= set("<>&|0123456789") and ("<" in word or ">" in word):
            skip = True
        elif word.isdigit() and index + 1 < len(words_after) and set(words_after[index + 1]) <= set("<>&|") and \
                words_after[index + 1]:
            # The number of 2> is the descriptor of the redirection, not an argument.
            continue
        elif not word.startswith("-"):
            args.append(word)
    if program in VALUE_FLAGS:
        in_place = any(w.startswith("--in-place") or in_cluster(w, VALUE_FLAGS[program]) for w in rest[1:])
        targets = args if in_place else []
    elif program == "dd":
        targets = [w for w in rest[1:] if w.startswith("of=")]
    elif program in WRITE_ALL:
        targets = args
    elif program in WRITE_LAST:
        targets = args[-1:]
    else:
        targets = []
    # Removing or moving a folder takes the protected paths in it too. A move into a folder leaves the folder.
    sources = targets[:-1] if program == "mv" else targets
    above = program in ("rm", "rmdir", "mv", "unlink", "shred")
    for word in targets:
        path = protected_path(word, cwd, above and word in sources)
        if path:
            raise_write(path)


def recipe_is(word: str, name: str) -> bool:
    return word == name or word.endswith("::" + name)


# An option of `just --help` with its values, such as `  -f, --justfile <JUSTFILE>` or `--set <VARIABLE> <VALUE>`.
JUST_OPTION = re.compile(r"^\s+(?:-(\w), )?(--[\w-]+)((?: <[^>]+>(?:\.\.\.)?)+)", re.M)


@functools.lru_cache(maxsize=None)
def just_options() -> Optional[Dict[str, int]]:
    """The options of the installed just that take values, with the number of values, from `just --help`. A list
    of values, such as `--command <COMMAND>...`, gives -1: the line runs no recipe. None when just does not run."""
    try:
        run = subprocess.run(["just", "--help"], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    found: Dict[str, int] = {}
    for short, long, values in JUST_OPTION.findall(run.stdout):
        count = -1 if values.endswith("...") else values.count("<")
        found[long] = count
        if short:
            found["-" + short] = count
    # An option of the section Commands, such as --list or --dump, runs no recipe of the line.
    commands = run.stdout.split("Commands:", 1)[1] if "Commands:" in run.stdout else ""
    commands = re.split(r"\n\S", commands, maxsplit=1)[0]
    for short, long in re.findall(r"^\s+(?:-(\w), )?(--[\w-]+)", commands, re.M):
        found[long] = -1
        if short:
            found["-" + short] = -1
    return found or None


def first_recipe(args: List[str], options: Dict[str, int]) -> Optional[str]:
    """The first recipe of a just command line, after its options and its NAME=VALUE overrides, or None."""
    index = 0
    while index < len(args):
        word = args[index]
        index += 1
        if word.startswith("--"):
            count = 0 if "=" in word else options.get(word, 0)
        elif word.startswith("-") and len(word) > 1:
            # A group of short options, such as -vf FILE or -fFILE: the first one that takes a value ends it.
            count = 0
            for position, letter in enumerate(word[1:], start=1):
                if "-" + letter in options:
                    count = options["-" + letter] if position == len(word) - 1 else 0
                    break
        elif "=" in word:
            continue
        else:
            return word
        if count < 0:
            return None
        index += count
    return None


def runs_record(args: List[str]) -> bool:
    """True when a just command line runs the recipe `record`. Without the options of just, any word `record`
    counts, so that no option hides it."""
    options = just_options()
    if options is None:
        return any(recipe_is(word, "record") for word in args)
    first = first_recipe(args, options)
    return bool(first) and recipe_is(first, "record")


def record_calls(rest: List[str]) -> List[str]:
    """The record commands that REST runs: `hook`, `record` or `skip`, from just or from the script. A skip counts in
    any place on the line, so that no spelling of the options hides it."""
    calls = []
    if name_of(rest[0]) == "just":
        calls += ["skip" for word in rest[1:] if recipe_is(word, "record-skip")]
        if runs_record(rest[1:]):
            calls.append("record")
    for index, word in enumerate(rest):
        if posixpath.basename(word) == RECORD_SCRIPT and index + 1 < len(rest):
            calls.append(rest[index + 1])
    return calls


def clears_variables(words: List[str], rest: List[str], command: str) -> bool:
    """True when the line can clear the variables of the harness without their names: the record command runs
    under env or exec, or a part of the line runs unset or export -n."""
    if any(name_of(word) in ("env", "exec") for word in words[:len(words) - len(rest)]):
        return True
    for segment in segments(command):
        program = program_of(segment)
        if program and (name_of(program[0]) == "unset"
                        or name_of(program[0]) == "export" and any(w.startswith("-") and "n" in w for w in program)):
            return True
    return False


def check_records(words: List[str], rest: List[str], command: str) -> None:
    """Stop the record commands that would let an agent write its own record, and note a skip for a question."""
    calls = record_calls(rest)
    if not calls:
        return
    if "hook" in calls:
        raise Blocked("only the SubagentStop hook of the harness runs record_result.py hook")
    # env and exec -c can clear the variables without naming them, and unset can name them through a pattern.
    if any(name in command for name in HARNESS_VARIABLES) or clears_variables(words, rest, command):
        raise Blocked("a record command with env, exec, unset or a change of " + ", ".join(HARNESS_VARIABLES) +
                      " could write a record that no fresh agent gave")
    if "record" in calls and os.environ.get("JN_HOOK_HARNESS") == "claude":
        raise Blocked("in Claude Code the SubagentStop hook writes the records; give the packet to a fresh agent")
    if "skip" in calls:
        ASKS.append(" ".join(rest))


def shell_text(rest: List[str]) -> Optional[str]:
    """The text of `sh -c TEXT`, with any options before -c, as in bash -lc TEXT. None for any other shell line."""
    for index, word in enumerate(rest[1:], start=1):
        if not word.startswith("-"):
            return None
        if not word.startswith("--") and "c" in word[1:]:
            return rest[index + 1] if index + 1 < len(rest) else None
    return None


def check_command(command: str, cwd: str, depth: int = 0) -> None:
    """Check each simple command of COMMAND, run in CWD."""
    if CONFIG_VARIABLE.search(command) and re.search(r"\bgit\b", command):
        raise Blocked("a GIT_CONFIG_ variable can give git a core.hooksPath, and the commit gate would not run")
    here: Optional[str] = cwd
    before: Optional[str] = cwd
    for words in segments(command):
        rest = program_of(words)
        # A cd in a subshell, as in (cd sub && ls), ends with it. The guard does not follow subshells, so a write
        # is checked against the folder of the call too.
        for folder in {here, cwd} if here is not None else ():
            check_writes(words, rest, folder)
        if not rest:
            continue
        program = name_of(rest[0])
        check_records(words, rest, command)
        if program == "cd":
            target = rest[1] if len(rest) > 1 else os.path.expanduser("~")
            # After a cd to a folder that the guard cannot know, a relative path could be any path.
            if target == "-":
                here, before = before, here
            elif "$" in target or "`" in target:
                here, before = None, here
            elif here is not None:
                here, before = os.path.join(here, os.path.expanduser(target)), here
            continue
        folder = cwd if here is None else here
        if program == "git":
            check_git(rest[1:], folder, depth)
        elif program == "eval" and depth < DEPTH:
            check_command(" ".join(rest[1:]), folder, depth + 1)
        elif program in SHELLS and depth < DEPTH:
            text = shell_text(rest)
            if text is not None:
                check_command(text, folder, depth + 1)


def command_of(tool_input: dict) -> Optional[str]:
    """The shell line of a tool call: `command` in Claude Code, `command` or `cmd` in Codex. A list such as
    ["bash", "-lc", LINE] gives LINE."""
    value = tool_input.get("command", tool_input.get("cmd"))
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return shlex.join(value)
    return value if isinstance(value, str) else None


def check(payload: dict, cwd: str) -> None:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return
    command = command_of(tool_input)
    if command is not None:
        check_command(command, cwd)
    for key in ("file_path", "notebook_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str) and protected_path(value, cwd):
            raise_write(protected_path(value, cwd))


def main() -> int:
    payload = None
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            return 0
        cwd = payload.get("cwd")
        cwd = cwd if isinstance(cwd, str) and os.path.isdir(cwd) else os.getcwd()
        check(payload, cwd)
        if ASKS:
            reason = (f"{ASKS[0]} lets the worktree tree through without the record of a fresh agent, and the gate "
                      f"then lets the commit through. Only the person decides that")
            if os.environ.get("JN_HOOK_HARNESS") == "codex":
                raise Blocked(reason + ". Ask the person to run the command")
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                     "permissionDecisionReason": reason}}))
            return 0
    except Blocked as blocked:
        print(f"gate guard: {blocked}.", file=sys.stderr)
        return 2
    except Exception as error:
        tool_input = payload.get("tool_input") if isinstance(payload, dict) else None
        command = command_of(tool_input) if isinstance(tool_input, dict) else None
        if command is not None and re.search(r"\bgit\b", command):
            print(f"gate guard: could not read the git call ({error!r}), so it stops. Write it more plainly",
                  file=sys.stderr)
            return 2
        print(f"gate guard: could not check the call ({error!r}), so it runs", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
