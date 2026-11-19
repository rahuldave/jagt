"""test-parent: run the added and changed test files on the parent commit, before `just test-review` writes its packet.

A new test that passes on the parent commit tests nothing new. So the recipe `test-review` runs this script first, and
the packet of the fresh agent holds its result:

1. It finds the test files of the change: the added and changed files of the worktree that match the globs of the
   key `tests` of `.agents/stack.json`, for each language. The installer copies them from the `profile.json` of each
   profile.
2. It makes a worktree of HEAD in a temporary folder outside the repository, with `git worktree add --detach`.
3. It copies only those test files in, so no new code reaches the parent. It runs the recipe
   `<language>::test-paths` of the parent on each test file alone, so a file that fails cannot hide a file that
   passes.
4. It removes the worktree, and writes the result to `test-parent/<tree>.json` in the shared log folder, where
   `<tree>` is the worktree tree, as the gate computes it.

The exit code of `test-paths` gives the case of each file: 0 is "passed on the parent", 1 is "failed on the parent", the
expected case, and 5 is "no test ran on the parent". Any other code is "the runner failed". A language whose test
files match no glob, as Rust unit tests, gets "no test ran on the parent" with no run. On the first commit, the
result is a skip.

The script exits with 0 in each case above. It exits with 1 only when it fails itself: a worktree that git cannot
make, a copy that fails, or a result that it cannot write. On SIGTERM, SIGHUP or Ctrl-C it stops the tests and
removes the worktree first. A test that leaves its process group, as with setsid, can outlive the run.

Usage: test_parent.py, in the repository.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agentic_target import Stop, git, plain_env, prepare_log, worktree_diff  # noqa: E402

STACK = ".agents/stack.json"
CASES = {0: "passed on the parent", 1: "failed on the parent", 5: "no test ran on the parent"}
# The output of a run that the result keeps, from its end, so that a long log stays readable.
OUTPUT_LIMIT = 20000
# The signals that stop the script. The first one removes the worktree first, and the script ignores the ones after it.
STOP_SIGNALS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)


def glob_pattern(glob: str) -> re.Pattern:
    """A glob as git reads it with :(glob): `**/` matches any folders, `*` and `?` do not match `/`."""
    out, index = "", 0
    while index < len(glob):
        if glob.startswith("**/", index):
            out, index = out + "(?:.*/)?", index + 3
        elif glob.startswith("**", index):
            out, index = out + ".*", index + 2
        elif glob[index] == "*":
            out, index = out + "[^/]*", index + 1
        elif glob[index] == "?":
            out, index = out + "[^/]", index + 1
        else:
            out, index = out + re.escape(glob[index]), index + 1
    return re.compile(out + r"\Z")


def test_globs(root: Path) -> Dict[str, List[str]]:
    """The globs of the test files of each language, from the key `tests` of `.agents/stack.json`."""
    try:
        tests = json.loads((root / STACK).read_text()).get("tests", {})
    except (OSError, ValueError, AttributeError):
        return {}
    if not isinstance(tests, dict):
        return {}
    return {name: [g for g in globs if isinstance(g, str)] for name, globs in tests.items() if isinstance(globs, list)}


def changed_files(root: Path, head: str) -> List[str]:
    """The added and changed files of the worktree against HEAD, with the new files that git does not ignore."""
    env = plain_env()
    tracked = git(["diff", "--name-only", "--no-renames", "--diff-filter=AMT", "-z", head], root, env).split("\0")
    new = git(["ls-files", "-z", "--others", "--exclude-standard"], root, env).split("\0")
    return sorted({path for path in tracked + new if path and (root / path).is_file()})


def run_tests(folder: Path, recipe: str, path: str) -> subprocess.CompletedProcess:
    """Run the recipe on one test file in its own process group, with the output in a file. When the recipe ends, or
    on an exception, as the SystemExit of a signal, the whole group stops. So no process of a test runs on in a
    worktree that is gone, and a process that keeps the output open cannot hold up the run."""
    with tempfile.TemporaryFile() as out:
        process = subprocess.Popen(["just", recipe, path], cwd=folder, stdin=subprocess.DEVNULL, stdout=out,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            process.wait()
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                pass
            process.wait()
        out.seek(0)
        output = out.read().decode(errors="replace")
    return subprocess.CompletedProcess(process.args, process.returncode, output)


def remove_worktree(root: Path, folder: Path) -> None:
    """Remove the worktree FOLDER. The git calls run in their own session, so a Ctrl-C of the terminal does not reach
    them."""
    for args in (["worktree", "remove", "--force", str(folder)], ["worktree", "prune"]):
        subprocess.run(["git", *args], cwd=root, env=plain_env(), stdin=subprocess.DEVNULL, capture_output=True,
                       start_new_session=True)


def run_on_parent(root: Path, head: str, language: str, files: List[str]) -> List[dict]:
    """Run each test file of FILES of LANGUAGE alone on the commit HEAD, in a worktree outside the repository."""
    with tempfile.TemporaryDirectory(prefix="test-parent-") as temp:
        folder = Path(temp) / "parent"
        # The try starts before the add: a signal during the checkout leaves a worktree to remove too.
        try:
            made = subprocess.run(["git", "worktree", "add", "--detach", "--quiet", str(folder), head], cwd=root,
                                  env=plain_env(), stdin=subprocess.DEVNULL, capture_output=True, text=True)
            if made.returncode != 0:
                raise Stop(f"git cannot make a worktree of the parent: {made.stderr.strip()}")
            for path in files:
                target = folder / path
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(root / path, target, follow_symlinks=False)
                except OSError as exc:
                    raise Stop(f"cannot copy {path} into the worktree of the parent: {exc.strerror}")
            recipe = f"{language}::test-paths"
            listed = subprocess.run(["just", "--summary"], cwd=folder, stdin=subprocess.DEVNULL, capture_output=True,
                                    text=True)
            if recipe not in listed.stdout.split():
                return [{"language": language, "files": files, "exit": None, "case": "the runner failed",
                         "output": f"the parent has no recipe {recipe}"}]
            runs = []
            for path in files:
                run = run_tests(folder, recipe, path)
                runs.append({"language": language, "files": [path], "exit": run.returncode,
                             "case": CASES.get(run.returncode, "the runner failed"),
                             "output": run.stdout[-OUTPUT_LIMIT:]})
            return runs
        finally:
            remove_worktree(root, folder)


def result_of(root: Path) -> dict:
    head, tree, _ = worktree_diff(root)
    if head == "none":
        return {"version": 1, "tree": tree, "parent": None, "skip": "the first commit has no parent", "runs": []}
    files = changed_files(root, head)
    runs = []
    for language, globs in sorted(test_globs(root).items()):
        patterns = [glob_pattern(glob) for glob in globs]
        mine = [path for path in files if any(p.match(path) for p in patterns)]
        if mine:
            runs.extend(run_on_parent(root, head, language, mine))
        else:
            runs.append({"language": language, "files": [], "exit": None, "case": "no test ran on the parent",
                         "output": "no changed file matches the test globs of the language"})
    return {"version": 1, "tree": tree, "parent": head, "runs": runs}


def write_result(root: Path, result: dict) -> Path:
    log, fd = prepare_log(root, "test-parent")
    name = f"{result['tree']}.json"
    try:
        try:
            os.unlink(name, dir_fd=fd)
        except FileNotFoundError:
            pass
        try:
            out = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=fd)
        except OSError as exc:
            raise Stop(f"cannot write {log / 'test-parent' / name}: {exc.strerror}")
    finally:
        os.close(fd)
    with os.fdopen(out, "w") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    return log / "test-parent" / name


def stop_on_signal(number: int, _frame) -> None:
    """Turn the first stop signal into an exit, so that the finally of run_on_parent removes the worktree. The stop
    signals after it are ignored, so a second Ctrl-C cannot stop the cleanup. Python keeps an ignored signal ignored
    through its shutdown, and a handler of its own does not, so a late signal cannot change the exit code."""
    for each in STOP_SIGNALS:
        signal.signal(each, signal.SIG_IGN)
    sys.exit(128 + number)


def main() -> int:
    for number in STOP_SIGNALS:
        signal.signal(number, stop_on_signal)
    try:
        root = Path(git(["rev-parse", "--show-toplevel"], Path.cwd(), plain_env()).strip())
        result = result_of(root)
        path = write_result(root, result)
    except Stop as stop:
        print(f"test-parent: {stop}", file=sys.stderr)
        return 1
    cases = ", ".join(f"{', '.join(run['files']) or run['language']}: {run['case']}" for run in result["runs"])
    cases = cases or result.get("skip", "no language")
    print(f"test-parent: {cases}. The result is in {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
