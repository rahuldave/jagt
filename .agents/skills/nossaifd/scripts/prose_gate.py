"""The gate of the nossaifd flow: each page that a turn changed must pass the checker and have a recorded pass.

Claude Code and Codex run two hooks of this script.

- `prose_gate.py start` runs when a person sends a message (the UserPromptSubmit hook). It keeps a snapshot of
  the pages: the commit HEAD, and the git blob id of each page that git reports as changed.
- `prose_gate.py hook` runs when the agent tries to end its turn (the Stop hook). It compares the pages with
  the snapshot. A page counts when its content differs from the snapshot, either in the working tree or in a
  commit that the turn made: a commit by the same author, made since the turn started. A pull or a checkout
  brings commits made before the turn, so they do not count, and neither does a merge commit. For each page
  that counts, it runs the checker of the page, check.py unless the map of checkers names another, and it
  looks up the page in the record of passes. A page passes when its checker finds no hard problem and the
  record holds the page as it is now, passed by that checker. Otherwise the hook blocks the stop once and tells the agent which steps of the nossaifd skill remain.

After step 8 of the nossaifd skill, the agent records each page:

    uv run --no-project --quiet python .agents/skills/nossaifd/scripts/prose_gate.py record page.md

`record` refuses a page that has a hard problem. The record lives in .agents/log/nossaifd of the main checkout,
so every worktree of the repository shares it. The snapshots live in .agents/log/nossaifd of each worktree.
Nothing goes in the folder of git. The gate gives .agents/log a .gitignore with the line *, as the commit gate
does, so the folder never shows in git status. The record is a
promise of the agent, not a proof: the hook cannot see whether the declaude pass ran.

With the commit gates of agent_gest_git_skills, this turn gate stays and asks early, and the gate of the commit
decides. The gates are installed when .agents/stack.json turns on the tasker role. Then the block message says
"run `just prose`". That target gives the pages to a fresh agent, which records each page that it passed. The
steps by hand give a page pass, but not the `prose` record that a commit needs.

`prose_gate.py pages [-z] [PATH...]` prints each path that is a page. is_page is the one rule for pages: the
`@pages` of the commit gate uses it through this command, and check-changed, the step prose-check, calls it.

The map of checkers, the file .agents/nossaifd-checkers.json in the root of the project, can name another
checker for some pages, for example the talk checker for a deck. `pages` decides what is a page, and the map
decides how a page is checked. Every command that checks a page uses the map: hook, status, record,
check-diff, `prose_gate.py check [-v] PAGE...` and `prose_gate.py check-changed [-v] [--base REF] [PAGE...]`.
check-changed checks the pages that changed since HEAD, for the step prose-check of `just check`. In CI, or with
--base, it checks the pages that HEAD changed since a base, as check-diff does. A missing or failing checker,
or a broken map, is a hard problem of the page. Each message names the checker of each page. See map_rules for the format.

The hook fails open: an error never blocks. Claude Code and Codex set stop_hook_active when the agent tries
to stop again after a block, and the hook then lets it stop, so it cannot loop. The environment variable
NOSSAIFD_GATE=off, set before Claude Code or Codex starts, turns the gate off. Submodules are out of scope.
Python 3.11 or later, standard library only.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

sys.dont_write_bytecode = True        # keep __pycache__ out of the installed skill

HERE = Path(__file__).resolve().parent
PAGE = re.compile(r'\.(md|qmd)$')
# Instructions for agents, the copies of skills, the files that a build makes, and changelogs are not pages
SKIP = re.compile(r'(^|/)(AGENTS|CLAUDE|GEMINI)\.md$|^\.agents/|^\.claude/|^\.codex/'
                  r'|(^|/)(node_modules|_site|\.quarto)/|(^|/)CHANGELOG\.md$')
LISTED = 20                           # the most pages that a block message names
CREDIT = 'the declaude skill, by Oskar Austegard'
LOG = '.agents/log'                   # the log folder of a worktree, as the commit gate has it
MAP = '.agents/nossaifd-checkers.json'  # the map of checkers, read only from the root of the project
DEFAULT = 'check.py of the skill'     # the checker of a page that no glob of the map matches. No path of the map ends so
TIMEOUT = 30                          # the most seconds that a checker of the map may take for one page
BUDGET = 40                           # the most seconds of the Stop hook for all its checkers. The hook has 60
HARD_LINE = re.compile(r'^\s*HARD(?::|\s|$)[\s:]*(.*)$')   # a line of a checker that names a hard problem
INSTALL = "npx skills add rahuldave/nossaifd -a codex --skill '*' -y"   # the install line of the README
GRACE = 2                            # the seconds that the gate waits for the output after it stops a checker


def is_page(rel):
    """True when a path is a page for a person to read. The path is relative to the root of the repository, with
    `/` between folders, as git prints it. A leading `./` does not change the answer."""
    rel = re.sub(r'^(\./)+', '', rel)
    return bool(PAGE.search(rel)) and not SKIP.search(rel)


def problems(path, check):
    "The hard problems that check.py finds in one page. A page that cannot be read is one hard problem."
    try:
        return check.check(path)[0]
    except (OSError, UnicodeDecodeError) as error:
        return [f'the page cannot be read: {error.strerror if isinstance(error, OSError) else error}']


def glob_regex(pattern):
    """The regular expression of a glob of the map. The glob matches the whole path from the root. `*` matches
    any characters inside one folder name, and `?` matches one. A `**` that is a whole folder name matches any
    number of folders, also none. Every other character matches itself."""
    parts, out = pattern.split('/'), []
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        if part == '**':
            out.append('.*' if last else '(?:[^/]+/)*')
            continue
        seg = ''.join('[^/]*' if c == '*' else '[^/]' if c == '?' else re.escape(c) for c in part)
        out.append(seg + ('' if last else '/'))
    return re.compile(''.join(out))


def map_rules(root):
    """The rules of the map of checkers of a project, and the reason that the map is broken, or None.

    The map is the file .agents/nossaifd-checkers.json in the root of the project. It is JSON:

        {"version": 1,
         "checkers": [{"pages": ["**/slides.qmd", "**/plan.md"],
                       "checker": "tools/check_talk.py"}]}

    The first rule whose glob matches the path of a page from the root names its checker. A page that no rule
    matches gets check.py. The path of a checker is relative to the root, with `/`, and names a Python file
    inside the project: no absolute path and no `..`. A project without the file has no rules. A checker that
    is not there is a hard problem of each page that its rule matches."""
    path = root / MAP
    if not os.path.lexists(path):
        return [], None
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception as error:  # noqa: BLE001 - also RecursionError: a map that cannot be read is broken
        return [], f'it is not JSON that can be read: {type(error).__name__}: {str(error)[:200]}'
    if not isinstance(data, dict) or type(data.get('version')) is not int or data.get('version') != 1 \
            or not isinstance(data.get('checkers'), list):
        return [], 'it must be an object with "version": 1 and a list "checkers"'
    rules = []
    for n, rule in enumerate(data['checkers'], 1):
        globs = rule.get('pages') if isinstance(rule, dict) else None
        checker = rule.get('checker') if isinstance(rule, dict) else None
        if not isinstance(globs, list) or not globs or not all(isinstance(g, str) and g for g in globs):
            return [], f'rule {n} needs "pages", a list of globs'
        globs = [re.sub(r'^(\./)+', '', g) for g in globs]
        for g in globs:
            if g.startswith('/') or '\\' in g or g.endswith('/') or '//' in g or not g or g != g.strip() \
                    or {'.', '..'} & set(g.split('/')):
                return [], (f'rule {n} has the glob {g!r}. A glob is a path from the root, with / between '
                            'folders, and it ends with a file name or **')
        if not isinstance(checker, str) or not checker.endswith('.py'):
            return [], f'rule {n} needs "checker", the path of a Python file'
        if checker.startswith('/') or '\\' in checker or '..' in checker.split('/') or re.match(r'^[A-Za-z]:', checker):
            return [], f'rule {n} names the checker {checker}. Give a path inside the project, from its root, with no ..'
        checker = re.sub(r'^(\./)+', '', checker)
        rules += [(glob_regex(g), checker) for g in globs]
    return rules, None


class Checkers:
    "The checker of each page of one project, by its map of checkers."

    def __init__(self, root, budget=None):
        self.root = root
        self.rules, self.broken = map_rules(root) if root is not None else ([], None)
        self.check = None
        # the time by which every checker must end, for the Stop hook, which the harness kills after 60 seconds
        self.deadline = time.monotonic() + budget if budget else None

    def name(self, rel):
        "The name of the checker of a page, as the messages give it: check.py or the path of the map."
        if self.broken:
            return f'none, the map {MAP} is broken'
        rel = re.sub(r'^(\./)+', '', rel)
        return next((checker for regex, checker in self.rules if regex.fullmatch(rel)), DEFAULT)

    def problems(self, rel, verbose=False):
        """The hard problems of one page, from its checker, and the output of a checker of the map. A missing or
        failing checker and a broken map are hard problems."""
        name = self.name(rel)
        if self.broken:
            return [f'the map of checkers {MAP} is broken: {self.broken}'], ''
        if name == DEFAULT:
            try:
                self.check = self.check or checker()
            except MissingCheck as error:
                return [str(error)], ''
            return problems(self.root / rel if self.root else Path(rel), self.check), ''
        timeout = TIMEOUT
        if self.deadline is not None:
            timeout = min(TIMEOUT, self.deadline - time.monotonic() - GRACE)
            if timeout < 1:
                return [f'the hook had no time left to run its checker {name}. Run prose_gate.py check on '
                        'the page'], ''
        return run_checker(self.root, name, rel, verbose, timeout)


def run_checker(root, name, rel, verbose=False, timeout=TIMEOUT):
    """Run a checker of the map on one page: `python -B CHECKER [-v] PAGE`, with the Python of the gate, in the
    root of the project. The page is its path from the root. Exit 0 means no hard problem. Exit 1 means hard
    problems, and each line of the output that starts with HARD, after spaces, names one. Any other exit is a
    failure of the checker. Give back the hard problems and the output."""
    program = root / name
    if not program.is_file():
        return [f'its checker {name}, which the map {MAP} names, is missing. Install the skill that ships it '
                'again, or fix the map'], ''
    page = rel if not rel.startswith('-') else f'./{rel}'
    try:
        # its own session, so that a timeout kills the checker and every process that it started
        proc = subprocess.Popen([sys.executable, '-B', str(program), *(['-v'] if verbose else []), page], cwd=root,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                                start_new_session=True)
    except OSError as error:
        return [f'its checker {name} cannot run: {error.strerror}'], ''
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, 9)
        except OSError:
            proc.kill()
        try:
            proc.communicate(timeout=GRACE)
        except subprocess.TimeoutExpired:
            pass                                # a process that left the session holds the output: leave it
        return [f'its checker {name} did not end in {round(timeout)} seconds'], ''
    stdout = stdout.decode('utf-8', errors='replace')
    stderr = stderr.decode('utf-8', errors='replace')
    # a line that starts with the page is the summary of the checker, also for a page named HARD.qmd
    lines = [line for line in stdout.splitlines() if not line.startswith((f'{page}:', f'{page} '))]
    hard = [m.group(1).strip() or 'a hard problem' for m in map(HARD_LINE.match, lines) if m]
    if proc.returncode not in (0, 1) or (proc.returncode == 1 and not hard):
        # exit 1 with no HARD line is a crash of Python, or a checker that does not keep the contract
        why = (stderr.strip() or stdout.strip() or 'no output').splitlines()[-1][:300]
        return [f'its checker {name} failed with exit {proc.returncode}: {why}'], stdout + stderr
    if proc.returncode == 0 and hard:
        hard.append(f'its checker {name} printed HARD problems but exited 0')
    return hard, stdout + stderr


def pass_id(blob_id, name):
    """The value of the record for a pass. A page that check.py passed keeps the blob id alone, as before the map.
    A page that another checker passed adds its name, so that a change of checker asks again."""
    return blob_id if name == DEFAULT else f'{blob_id} {name}'


def gates_installed(root):
    "True when .agents/stack.json of the project turns on the tasker role, which brings the commit gates."
    try:
        choices = json.loads((root / '.agents/stack.json').read_text()).get('choices')
    except (OSError, ValueError, AttributeError):
        return False
    return isinstance(choices, dict) and choices.get('tasker') is True


class MissingCheck(Exception):
    "check.py of the skill is missing. The message gives the install line."


def missing_check():
    "The message for a missing check.py of the skill, with the install line of the README."
    return (f'check.py of the nossaifd skill is missing from {HERE}. Install the skill again: {INSTALL}, '
            'or run `just install prose` in a project that jnterfaces set up')


def checker():
    "The check module next to this script. MissingCheck, with the install line, when check.py is missing."
    if not (HERE / 'check.py').is_file():
        raise MissingCheck(missing_check())
    spec = importlib.util.spec_from_file_location('nossaifd_check', HERE / 'check.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(root, *args, stdin=None):
    return subprocess.run(['git', '--no-optional-locks', '--literal-pathspecs', '-C', str(root), *args],
                          capture_output=True, text=True, input=stdin)


def blob(path):
    "The git blob id of a file, or None when it is missing."
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def git_root(cwd):
    out = git(cwd, 'rev-parse', '--show-toplevel')
    return Path(out.stdout.strip()) if out.returncode == 0 else None


def state(root, shared=False):
    """The folder of the gate in the log folder .agents/log, never in the folder of git: the log folder of this
    worktree, or with shared the log folder of the main checkout, which every worktree shares. The main checkout
    is the folder that holds the common folder of git when that folder is named .git. Otherwise, as in a bare
    repository or a submodule, the shared folder is the log folder of this worktree."""
    folder = root / LOG
    if shared:
        out = git(root, 'rev-parse', '--git-common-dir')
        if out.returncode == 0 and out.stdout.strip():
            common = (root / out.stdout.strip()).resolve()
            if common.name == '.git':
                folder = common.parent / LOG
    return folder / 'nossaifd'


def head(root):
    out = git(root, 'rev-parse', '--verify', '-q', 'HEAD')
    return out.stdout.strip() or None


def git_changed(root):
    "Pages that git reports as changed or new, relative to the root."
    entries, found, i = git(root, 'status', '--porcelain', '-z', '--untracked-files=all').stdout.split('\0'), set(), 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        if 'R' in code or 'C' in code:
            i += 1                              # the old name of a renamed file follows
        if 'D' not in code and is_page(path):
            found.add(path)
    return found


def snapshot(root):
    return {'head': head(root), 'time': int(time.time()),
            'pages': {p: blob(root / p) for p in sorted(git_changed(root))}}


def snapshot_file(root, session):
    name = re.sub(r'[^A-Za-z0-9_.-]', '_', str(session or 'default'))[:100]
    return state(root) / 'turns' / f'{name}.json'


def save(path, value):
    "Write a file of the gate. The log folder above it gets a .gitignore with the line *, unless it has one."
    path.parent.mkdir(parents=True, exist_ok=True)
    for folder in path.parents:
        if folder.name == 'log' and folder.parent.name == '.agents':
            try:
                with open(folder / '.gitignore', 'x') as out:
                    out.write('*\n')
            except OSError:     # it exists, also as a link to nowhere: the file of the commit gate or of a person
                pass
            break
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def committed(root, old, new, since):
    """Pages in the commits that the turn made: commits by the same author, made since the turn started, that
    the start HEAD does not hold. A pull brings commits that were made before, so they do not count. After an
    amend or a rebase, the commits since the fork point count."""
    if not new or new == old:
        return set()
    if old and git(root, 'merge-base', '--is-ancestor', old, new).returncode:
        old = git(root, 'merge-base', old, new).stdout.strip() or None
    email = git(root, 'config', 'user.email').stdout.strip()
    args = ['log', '--no-merges', '--format=%H %ct'] + (['-F', f'--author=<{email}>'] if email else [])
    out = git(root, *args, new, *([f'^{old}'] if old else [])).stdout.split()
    commits = [h for h, t in zip(out[::2], out[1::2]) if since is None or int(t) >= since - 1]
    if not commits:
        return set()
    names = git(root, 'diff-tree', '--stdin', '--root', '-r', '-z', '--name-only', '--no-commit-id',
                stdin='\n'.join(commits) + '\n').stdout
    return {p for p in names.split('\0') if is_page(p)}


def tree_blobs(root, commit, paths):
    "The blob id of each path in a commit. One call for the whole tree, so no list of paths is too long."
    if not commit or not paths:
        return {}
    found = {}
    for entry in filter(None, git(root, 'ls-tree', '-r', '-z', '--full-tree', commit).stdout.split('\0')):
        meta, _, path = entry.partition('\t')
        if path in paths:
            found[path] = meta.split()[2]
    return found


def turn_pages(root, before):
    "The pages whose content differs from the snapshot at the start of the turn."
    now = head(root)
    candidates = git_changed(root) | set(before['pages']) | committed(root, before['head'], now, before.get('time'))
    at_head = tree_blobs(root, before['head'], candidates)
    changed = []
    for rel in sorted(candidates):
        current = blob(root / rel)
        # a stash, a checkout or a reset that gives back the committed page is not a change of the turn
        if current is not None and current != before['pages'].get(rel, at_head.get(rel)) and current != at_head.get(rel):
            changed.append(rel)
    return changed


def load_record(root):
    return read(state(root, shared=True) / 'passes.json') or {}


def gate(root, rels, checkers=None):
    "The block message for the pages that need work, or None when every page passed."
    saved, hard_pages, unrecorded = load_record(root), [], []
    checkers = checkers or Checkers(root)
    passed = set(saved.values())                # a renamed page keeps its pass
    for rel in rels:
        name = checkers.name(rel)
        if pass_id(blob(root / rel), name) in passed:
            continue
        hard = checkers.problems(rel)[0]
        if hard:
            hard_pages.append(f'{rel} (checked by {name}): ' + '; '.join(hard[:3]) + (' ...' if len(hard) > 3 else ''))
        else:
            unrecorded.append(f'{rel} (checked by {name})')
    if not hard_pages and not unrecorded:
        return None

    def listed(items):
        more = len(items) - LISTED
        return [f'- {p}' for p in items[:LISTED]] + ([f'- and {more} more'] if more > 0 else [])
    lines = ['nossaifd: this turn changed pages that have not passed the flow of the nossaifd skill.']
    gates = gates_installed(root)
    if hard_pages:
        lines += ['', 'Hard problems of the checker of each page:' if gates
                  else 'Hard problems of the checker of each page, which steps 4 and 7 fix:']
        lines += listed(hard_pages)
    if unrecorded:
        lines += ['', 'No recorded pass since the last change:'] + listed(unrecorded)
    if gates:
        lines += ['', 'This project has the commit gates, so run `just prose`. It gives the changed pages to a fresh '
                  f'agent, for the plain-writing pass and the pass of {CREDIT}. That agent fixes each hard problem '
                  'and records each page that it passed. Keep each bad example that a page shows on purpose. The '
                  'steps of the skill by hand record a page too, but a commit also needs the `prose` record, and '
                  'only `just prose` gives it.', '',
                  'If this project has no recipe `just prose` yet, do steps 6 to 8 of the nossaifd skill, and '
                  'record each page:', '',
                  f'    uv run --no-project --quiet python "{HERE / "prose_gate.py"}" record PAGE', '',
                  'If a page is not prose for a person to read, do not record it. Tell the user so in one line.',
                  'This hook asks once. It asks about a page again only when the page changes again.']
        return '\n'.join(lines)
    lines += ['', f'For each page, run the steps of the nossaifd skill that remain: the pass of {CREDIT}, in a '
              'subagent that did not write the page (step 6), the checker of the page again (step 7) and the '
              'linter once more (step 8). Keep each bad example that a page shows on purpose. Then record each page:', '',
              f'    uv run --no-project --quiet python "{HERE / "prose_gate.py"}" record PAGE', '',
              'If a page is not prose for a person to read, do not record it. Tell the user so in one line.',
              'This hook asks once. It asks about a page again only when the page changes again.']
    return '\n'.join(lines)


def hook_input(project=None):
    """The input of the hook, and the root of the project. The setting passes the folder of the project, so a cd
    of the agent into another repository does not move the gate there."""
    if os.environ.get('NOSSAIFD_GATE') == 'off':
        return None, None
    data = json.load(sys.stdin)
    return data, git_root(project or data.get('cwd') or os.getcwd())


def start(project=None):
    "UserPromptSubmit hook. Keep the snapshot of the pages at the start of the turn. Prints nothing."
    try:
        data, root = hook_input(project)
        if root is not None:
            save(snapshot_file(root, data.get('session_id')), snapshot(root))
            old = time.time() - 30 * 86400
            for path in (state(root) / 'turns').glob('*.json'):
                if path.stat().st_mtime < old:
                    path.unlink()
    except Exception:  # noqa: BLE001 - a hook fails open
        pass
    return 0


def hook(project=None):
    "Stop hook. Prints a block decision or an empty object, and always exits 0."
    try:
        message = None
        data, root = hook_input(project)
        if root is not None and not (HERE / 'check.py').is_file():
            # a broken install is no fault of the turn: say how to install, and let the stop go through
            print(f'nossaifd: {missing_check()}', file=sys.stderr)
            root = None
        if root is not None:
            path = snapshot_file(root, data.get('session_id'))
            before = read(path)
            if before is not None and not data.get('stop_hook_active'):
                message = gate(root, turn_pages(root, before), Checkers(root, BUDGET))
            if message is None:
                # the next turn starts here, also when the start hook did not run, so a page is asked about once
                save(path, snapshot(root))
        # Codex needs JSON on every exit 0, and an empty object lets the stop go through
        print(json.dumps({'decision': 'block', 'reason': message} if message else {}))
    except Exception:  # noqa: BLE001 - a hook fails open
        print('{}')
    return 0


def resolve(name, root):
    "A page named relative to the folder of the call or to the root of the repository."
    path = Path(name)
    if not path.exists() and not path.is_absolute() and (root / path).exists():
        path = root / path
    return path.resolve()


def record(names):
    "Record each page after its pass. Refuse a page with a hard problem, a missing page or a file outside the repo."
    root = git_root(Path.cwd())
    if root is None:
        print('prose_gate.py record: run it inside the git repository of the pages', file=sys.stderr)
        return 1
    checkers, saved, status = Checkers(root), load_record(root), 0
    for name in names:
        path = resolve(name, root)
        try:
            rel = path.relative_to(root.resolve()).as_posix()
        except ValueError:
            print(f'{name}: not recorded, it is outside the repository {root}', file=sys.stderr)
            status = 1
            continue
        if not path.is_file():
            print(f'{name}: not recorded, there is no such file', file=sys.stderr)
            status = 1
            continue
        by = checkers.name(rel)
        hard = checkers.problems(rel)[0]
        if hard:
            print(f'{rel}: not recorded, {len(hard)} hard problem(s) of {by}. The first: {hard[0]}', file=sys.stderr)
            status = 1
            continue
        saved[rel] = pass_id(blob(path), by)
        print(f'{rel}: recorded, checked by {by}')
    where = state(root, shared=True) / 'passes.json'
    try:
        save(where, dict(sorted(saved.items())))
    except OSError as exc:
        print(f'prose_gate.py record: no page recorded, cannot write {where}: {exc.strerror or exc}', file=sys.stderr)
        return 1
    return status


def status():
    """Print each page that git reports as changed and that still needs work, and the checker of each changed
    page. Exit 1 when a page needs work."""
    root = git_root(Path.cwd())
    rels = sorted(git_changed(root)) if root else []
    checkers = Checkers(root) if root else None
    message = gate(root, rels, checkers) if root else None
    print(message or 'nossaifd: every changed page passed.')
    if rels:
        print('\nThe checker of each changed page:')
        print('\n'.join(f'- {rel}: {checkers.name(rel)}' for rel in rels))
    return 1 if message else 0


def diff_pages(root, *revs):
    """The pages that git diff names between revs as added, changed or of a changed type, with no rename, relative
    to the root: the one listing of check-diff and of check-changed with a base. A deleted page is not listed.
    The pair (pages, None), or (None, the message of git) when git fails."""
    out = git(root, 'diff', '-z', '--name-only', '--no-renames', '--diff-filter=AMT', *revs, '--')
    if out.returncode:
        return None, out.stderr.strip()
    return [p for p in filter(None, out.stdout.split('\0')) if is_page(p)], None


def check_diff(base):
    """For a workflow: run the checker of each page that HEAD adds or changes since base. Exit 1 on a hard
    problem. A branch or a commit counts from its merge base with HEAD. A tree, such as the empty tree for the
    first push, has no merge base, so it is compared with HEAD directly."""
    root = git_root(Path.cwd())
    if root is None or base.startswith('-'):
        print('prose_gate.py check-diff: run it in a git repository, with a base that does not start with -',
              file=sys.stderr)
        return 2
    tree = git(root, 'cat-file', '-t', base).stdout.strip() == 'tree'
    rels, error = diff_pages(root, *((base, 'HEAD') if tree else (f'{base}...HEAD',)))
    if rels is None:
        print(error, file=sys.stderr)
        return 2
    checkers, status = Checkers(root), 0
    for rel in rels:
        by = checkers.name(rel)
        hard = checkers.problems(rel)[0]
        print(f'{rel}: checked by {by}, {len(hard)} hard problem(s)')
        for problem in hard:
            print(f'{rel}: {problem}')
        status |= bool(hard)
    print(f'nossaifd: checked {len(rels)} page(s), {"a hard problem" if status else "no hard problem"}.')
    return int(status)


def check_pages(args):
    """Check each page with its checker, by the map of checkers, and print what the checker found. With -v, also
    the soft notes. A name is relative to the folder of the call or to the root, as for record. Exit 0 when no
    page has a hard problem, 1 when one has, and 2 for a missing page or an unknown option."""
    verbose = False
    while args and args[0].startswith('-'):
        option, args = args[0], args[1:]
        if option == '--':
            break
        if option != '-v':
            print(f'prose_gate.py check: unknown option {option}', file=sys.stderr)
            return 2
        verbose = True
    if not args:
        print('prose_gate.py check: name at least one page', file=sys.stderr)
        return 2
    return check_named(git_root(Path.cwd()), args, verbose)


def check_named(root, names, verbose, changed=False):
    """The loop of check and check-changed. With changed, each name is the path of a page from the root, as git
    prints it; otherwise a name is relative to the folder of the call or to the root."""
    checkers, status = Checkers(root), 0
    for name in names:
        if changed:
            path, rel, inside = root / name, name, True
        else:
            path = resolve(name, root) if root else Path(name).resolve()
            rel, inside = name, False
            if root:
                try:
                    rel, inside = path.relative_to(root.resolve()).as_posix(), True
                except ValueError:
                    pass
        if not path.is_file():
            print(f'{name}: not checked, there is no such file', file=sys.stderr)
            status = 2
            continue
        # the map is of the pages of the project, so a file outside it, such as a draft in /tmp, gets check.py
        by = checkers.name(rel) if inside else DEFAULT
        if by == DEFAULT:
            try:
                checkers.check = checkers.check or checker()
                hard, soft = checkers.check.check(path)
            except MissingCheck as error:
                hard, soft = [str(error)], []
            except (OSError, UnicodeDecodeError) as error:
                hard, soft = [f'the page cannot be read: {error}'], []
            print(f'{rel}: checked by {by}, {len(hard)} hard, {len(soft)} soft')
            print(''.join(f'  HARD {p}\n' for p in hard) + ''.join(f'  soft {n}\n' for n in soft if verbose), end='')
        else:
            hard, output = checkers.problems(rel, verbose)
            print(f'{rel}: checked by {by}, {len(hard)} hard problem(s)')
            print(''.join(f'  {line}\n' for line in output.splitlines()), end='')
            # the problems that the gate found about the checker or the map, which its output does not hold
            print(''.join(f'  HARD {p}\n' for p in hard if p not in output), end='')
        if hard and status == 0:
            status = 1
    return status


def empty_tree(root):
    "The id of the empty tree, in the hash format of this repository, or None when git fails. It writes nothing."
    out = git(root, 'hash-object', '-t', 'tree', '--stdin', stdin='')
    if out.returncode:
        print(out.stderr.strip(), file=sys.stderr)
        return None
    return out.stdout.strip()


# jnprofile-python imports this function. Keep its name, arguments and result, or tell the jnterfaces agent first.
def ci_set():
    """Whether the environment variable CI is set. GitHub sets it to true. Empty, false and 0, in any case and with
    spaces around, count as not set, so CI=false turns the CI mode off."""
    return os.environ.get('CI', '').strip().lower() not in ('', 'false', '0')


FETCH = ('Fetch the whole history: set fetch-depth: 0 on actions/checkout, or run git fetch --unshallow, '
         'and fetch the base branch.')
BRANCH = re.compile(r'[^-\s~^:?*\[\\][^\s~^:?*\[\\]*')   # a name of a branch that git can take as origin/NAME


def default_branch(root):
    """The default branch of the repository, for CI: the key repository.default_branch of the event file of
    GitHub at GITHUB_EVENT_PATH, or else the branch of origin/HEAD. None when neither gives a branch."""
    try:
        event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
        branch = event['repository']['default_branch']
        if isinstance(branch, str) and BRANCH.fullmatch(branch):
            return branch
    except (KeyError, OSError, ValueError, TypeError):
        pass
    out = git(root, 'symbolic-ref', '-q', 'refs/remotes/origin/HEAD')
    name = out.stdout.strip().removeprefix('refs/remotes/origin/')
    return name if out.returncode == 0 and name and BRANCH.fullmatch(name) else None


def pushed_before():
    """The commit before a push on GitHub, the key before of the event file at GITHUB_EVENT_PATH, and None. All
    zeros, as for the push that makes a branch, comes back as it is: base_commit compares the empty tree with
    HEAD then. Or None and the reason when there is no such commit: no file or key, or a value that is not the
    id of a commit."""
    try:
        before = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))['before']
    except (KeyError, OSError, ValueError, TypeError):
        return None, 'the event file at GITHUB_EVENT_PATH gives no commit before a push'
    if not isinstance(before, str) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', before):
        return None, 'the key before of the event file is not the id of a commit'
    return before, None


def parent_or_empty(root, why):
    "HEAD^ and its name, or the empty tree when HEAD is the first commit, or None and the message of the error."
    parents = git(root, 'rev-list', '--parents', '-n1', 'HEAD')
    if parents.returncode:
        return None, parents.stderr.strip() or 'git cannot read the parents of HEAD.'
    parents = parents.stdout.split()[1:]
    if parents:
        return parents[0], f'HEAD^, the parent commit, {why}'
    tree = empty_tree(root)
    if tree is None:
        return None, 'git cannot make the empty tree.'
    return tree, f'the empty tree, as HEAD is the first commit, {why}'


def merge_base(root, ref, name, hint=''):
    "The merge base of ref and HEAD, and the name of the base, or None and the message of the error."
    if ref.startswith('-'):
        return None, f'the base {name} cannot start with -.'
    found = git(root, 'rev-parse', '--verify', '-q', f'{ref}^{{commit}}')
    if found.returncode:
        return None, f'the base {name} does not resolve to a commit.{hint}'
    merge = git(root, 'merge-base', found.stdout.strip(), 'HEAD')
    if merge.returncode or not merge.stdout.strip():
        return None, (f'{name} and HEAD have no merge base, so there is no change of HEAD to compare. '
                      'Rebase on the base, or name the pages.')
    return merge.stdout.split()[0], f'the merge base of {name} and HEAD'


# jnprofile-python imports this function. Keep its name, arguments and result, or tell the jnterfaces agent first.
def base_commit(root, option):
    """The commit to compare HEAD with, for check-changed with a base, and the name of the base for the message.
    The pair (commit, name), or (None, the message of the error). The base is a merge base, so the check never
    takes in the pages of commits that only the other side has.

    Other tools import it from the installed file: root is a Path or a str, and option is --base or None.

    - The option --base REF gives the merge base of REF and HEAD. It wins over CI.
    - On a pull request, with a nonempty GITHUB_BASE_REF, it is the merge base of origin/GITHUB_BASE_REF and HEAD.
    - On a push to the default branch, GITHUB_REF=refs/heads/DEFAULT, it is the commit before the push, the key
      before of the event file (see pushed_before), so each commit of the push is checked. A commit can skip the
      commit gate with --no-verify. When before is all zeros, as when the push makes the branch, the base is
      the empty tree, so each page of HEAD is checked. When before is missing, not in the history or not an
      ancestor of HEAD, as after a force-push, the base is HEAD^. A line of the output names either fallback.
    - On another push, a merge queue or another CI system, it is the merge base of origin/DEFAULT and HEAD, so
      each commit of a branch is checked, also after a force-push. When that merge base is HEAD itself, HEAD is
      on the default branch, so the base is HEAD^, as for a push to the default branch.
    - The default branch DEFAULT comes from the event file of GitHub, or else from origin/HEAD (default_branch).
    - When the base would be HEAD^ and HEAD has no parent, the base is the empty tree.

    Each error gives exit 2, never a check of no page: the event pull_request_target, which checks out the base
    branch; a shallow clone, also with the option, because its history is cut off and a cut-off commit looks
    like a first commit; no default branch; a base that does not resolve to a commit; and no merge base."""
    if head(root) is None:
        return None, 'HEAD has no commit, so there is no history to compare with a base.'
    if option is None and os.environ.get('GITHUB_EVENT_NAME') == 'pull_request_target':
        return None, ('the event pull_request_target checks out the base branch, so there is no change to '
                      'check. Run the workflow on the event pull_request.')
    shallow = git(root, 'rev-parse', '--is-shallow-repository')
    if shallow.returncode or shallow.stdout.strip() != 'false':
        return None, f'this clone is shallow, so its history is cut off and the base cannot be trusted. {FETCH}'
    if option is not None:
        return merge_base(root, option, option)
    if os.environ.get('GITHUB_BASE_REF'):
        branch = os.environ['GITHUB_BASE_REF']
        return merge_base(root, f'refs/remotes/origin/{branch}', f'origin/{branch}', f' {FETCH}')
    branch = default_branch(root)
    if branch is None:
        return None, ('no default branch: the event file at GITHUB_EVENT_PATH has no repository.default_branch, '
                      'and origin/HEAD is not set. Run git remote set-head origin --auto, or give --base REF.')
    if os.environ.get('GITHUB_REF') == f'refs/heads/{branch}':
        before, why = pushed_before()
        if before and not before.strip('0'):
            tree = empty_tree(root)
            if tree is None:
                return None, 'git cannot make the empty tree.'
            print('nossaifd: the base is the empty tree, because the key before of the event file is all zeros, as '
                  'when the push makes the branch, so each page of HEAD is checked.')
            return tree, f'the empty tree, as the key before of the push to the default branch {branch} is all zeros'
        if before and git(root, 'merge-base', '--is-ancestor', before, 'HEAD').returncode == 0:
            return before, f'{before[:12]}, the commit before the push to the default branch {branch}'
        if before:
            why = f'the commit before the push, {before[:12]}, is not an ancestor of HEAD, as after a force-push'
        commit, name = parent_or_empty(root, f'for a push to the default branch {branch}')
        if commit is not None:
            # the line names the base that parent_or_empty chose: HEAD^, or the empty tree for a first commit
            print(f'nossaifd: the base is {"HEAD^" if name.startswith("HEAD^") else "the empty tree"}, because '
                  f'{why}.')
        return commit, name
    commit, name = merge_base(root, f'refs/remotes/origin/{branch}', f'origin/{branch}', f' {FETCH}')
    if commit is not None and commit == head(root):
        return parent_or_empty(root, f'as HEAD has no commit of its own beside the default branch origin/{branch}')
    return commit, name




def changed_pages(root):
    """The pages that changed since HEAD and are on disk, relative to the root: each page that git diff reports as
    added, changed or of a changed type, such as a link that became a file, with no rename, and each new file that
    git does not ignore. Before the first commit, every
    page of the index counts as added. None when git fails."""
    base = head(root)
    if base is None:
        base = empty_tree(root)         # no commit yet
        if base is None:
            return None
    diff = git(root, 'diff', '-z', '--name-only', '--no-renames', '--diff-filter=AMT', base, '--')
    new = git(root, 'ls-files', '-z', '--others', '--exclude-standard')
    if diff.returncode or new.returncode:
        print((diff.stderr or new.stderr).strip(), file=sys.stderr)
        return None
    paths = set(filter(None, diff.stdout.split('\0'))) | set(filter(None, new.stdout.split('\0')))
    # a file that git reports, but that is gone, a folder or a link to nowhere, is not a page to check
    return sorted(p for p in paths if is_page(p) and (root / p).is_file())


def check_changed(args):
    """The step prose-check of `just check`. With names of pages, check those pages only, as check does. With none,
    check each page that changed since HEAD, by the map of checkers. -v adds the soft notes. Exit 0 when no page
    has a hard problem, also when no page changed, 1 when one has, and 2 outside a git repository, on a git
    error, on a missing named page or on an unknown option. -v may come before or after a page, as for check.py.
    A page whose name starts with - comes after --. It writes nothing: no record and no snapshot.

    With a base, it checks the pages as check-diff does: each page that HEAD adds or changes since the base, by
    the map of checkers, as the file is on disk, and also each page that changed since HEAD (see check_since). A
    base comes from the option --base REF, or --base=REF, or from the environment variable CI (see ci_set and
    base_commit). GitHub sets CI=true, and GITHUB_BASE_REF on a pull request. So in CI the step checks the pages
    of the pull request, of the branch or of the push. The option wins over CI, and runs the same check outside
    CI. With names of pages, CI changes nothing, and the option is an error. The last line names the base, for
    example "compared with the merge base of origin/main and HEAD". An error of the base gives exit 2, never a
    pass with no page checked."""
    options, names, base, i = [], [], None, 0
    while i < len(args):
        arg = args[i]
        i += 1
        if arg == '--':
            names += args[i:]
            break
        if arg == '-v':
            options = ['-v']
        elif arg == '--base' or arg.startswith('--base='):
            if arg == '--base':
                if i == len(args):
                    print('prose_gate.py check-changed: --base needs a branch or a commit', file=sys.stderr)
                    return 2
                arg, i = args[i], i + 1
            else:
                arg = arg.removeprefix('--base=')
            if not arg:
                print('prose_gate.py check-changed: --base needs a branch or a commit', file=sys.stderr)
                return 2
            base = arg
        elif arg.startswith('-'):
            print(f'prose_gate.py check-changed: unknown option {arg}. Put a page whose name starts with - '
                  'after --', file=sys.stderr)
            return 2
        else:
            names.append(arg)
    if names and base is not None:
        print('prose_gate.py check-changed: --base checks the pages of the diff, so name no page with it',
              file=sys.stderr)
        return 2
    if names:
        return check_pages([*options, '--', *names])
    root = git_root(Path.cwd())
    if root is None:
        print('prose_gate.py check-changed: this folder is not in a git repository, so name the pages: '
              'just prose-check README.md', file=sys.stderr)
        return 2
    if base is not None or ci_set():
        return check_since(root, base, bool(options))
    rels = changed_pages(root)
    if rels is None:
        print('prose_gate.py check-changed: git cannot list the changed files', file=sys.stderr)
        return 2
    if not rels:
        print('nossaifd: no page changed since HEAD, so there is no page to check.')
        return 0
    status = check_named(root, rels, bool(options), changed=True)
    result = {0: 'no hard problem', 1: 'a hard problem'}.get(status, 'a page that is gone')
    print(f'nossaifd: checked {len(rels)} changed page(s), {result}.')
    return status


def check_since(root, option, verbose):
    """check-changed with a base: check each page that HEAD adds or changes since the base, with the listing of
    check-diff, and each page that changed since HEAD, untracked pages too, with the loop of check. Each page
    counts once. In a clean checkout the second set is empty. A page of the commits that the working tree
    deleted is named and not checked. Any other page of the commits that is not a file on disk, as in a sparse
    checkout or for a link to nowhere, gives exit 2, so that a page is never skipped in silence. Without a base,
    changed_pages drops such a page, because there it is a change of the working tree, not of a commit."""
    commit, name = base_commit(root, option)
    if commit is None:
        print(f'prose_gate.py check-changed: {name}', file=sys.stderr)
        return 2
    rels, error = diff_pages(root, commit, 'HEAD')
    deleted = git(root, 'diff', '-z', '--name-only', '--no-renames', '--diff-filter=D', 'HEAD', '--')
    local = changed_pages(root)
    if rels is None or deleted.returncode or local is None:
        print(f'prose_gate.py check-changed: git cannot list the changed files: {error or deleted.stderr.strip()}',
              file=sys.stderr)
        return 2
    deleted = set(filter(None, deleted.stdout.split('\0'))) - set(local)   # git rm --cached leaves the file
    for rel in rels:
        if rel in deleted:
            print(f'{rel}: not checked, it is deleted since HEAD')
    missing = [rel for rel in rels if rel not in deleted and not (root / rel).is_file()]
    if missing:
        print(f'prose_gate.py check-changed: {len(missing)} changed page(s) are not files on disk, so they cannot '
              'be checked: ' + ', '.join(missing) + '. A sparse checkout, a skip-worktree flag or a link to '
              'nowhere leaves a page off the disk. Check out the whole tree, or fix or remove the link.',
              file=sys.stderr)
        return 2
    # each page once: the pages of the commits since the base, and the pages of the next commit
    rels = sorted({rel for rel in rels if rel not in deleted} | set(local))
    if not rels:
        print(f'nossaifd: no page changed, compared with {name}, so there is no page to check.')
        return 0
    status = check_named(root, rels, verbose, changed=True)
    result = {0: 'no hard problem', 1: 'a hard problem'}.get(status, 'a page that is gone')
    print(f'nossaifd: checked {len(rels)} changed page(s), compared with {name}, {result}.')
    return status


def pages(args, stdin=None):
    """Print each path that is_page accepts, in the order given, for prose-check and the `@pages` of the commit
    gate. The paths come from the arguments, or from standard input when no path follows the options. With -z,
    standard input and the output put NUL after each path; without it, a newline. A path is relative to the
    root of the repository, as git prints it. An absolute path counts by its path from the root of its
    repository (see relative). The names alone count: a deleted file can be a page. Exit 0, also when no path is a page, and 2 on an unknown option."""
    nul = False
    while args and args[0].startswith('-'):
        option, args = args[0], args[1:]
        if option == '--':
            break
        if option != '-z':
            print(f'prose_gate.py pages: unknown option {option}', file=sys.stderr)
            return 2
        nul = True
    sep = '\0' if nul else '\n'
    if not args:
        source = stdin or sys.stdin
        text = source.read() if source is not None else ''
        args = [p.removesuffix('\r') if not nul else p for p in text.split(sep)]
        args = [p for p in args if p]
    roots = {}
    for name in args:
        if is_page(relative(name, roots)):
            sys.stdout.write(name + sep)
    return 0


def relative(name, roots):
    """A path as the rule of pages reads it. An absolute path becomes its path from the root of its repository,
    with no symlink followed below that root. A path outside any repository stays as written."""
    if not os.path.isabs(name):
        return name
    path = os.path.abspath(name)
    folder = Path(path).parent
    while not folder.is_dir() and folder != folder.parent:
        folder = folder.parent                  # a deleted page: start from a folder that exists
    for start in (Path.cwd(), folder):
        if start not in roots:
            roots[start] = git_root(start)
        root = roots[start]
        if root is None:
            continue
        real_root = os.path.realpath(root)
        # the folder above the path that is the root, maybe through a symlink above the repository
        for above in Path(path).parents:
            if os.path.realpath(above) == real_root:
                return Path(path).relative_to(above).as_posix()
    return name


def main(argv):
    command = argv[1:2]
    if command == ['hook'] and len(argv) <= 3:
        return hook(argv[2] if len(argv) == 3 else None)
    if command == ['start'] and len(argv) <= 3:
        return start(argv[2] if len(argv) == 3 else None)
    if command == ['record'] and len(argv) > 2:
        return record(argv[2:])
    if command == ['status']:
        return status()
    if command == ['check-diff'] and len(argv) == 3:
        return check_diff(argv[2])
    if command == ['pages']:
        return pages(argv[2:])
    if command == ['check']:
        return check_pages(argv[2:])
    if command == ['check-changed']:
        return check_changed(argv[2:])
    print(__doc__)
    print('Usage: prose_gate.py hook [ROOT] | start [ROOT] | record PAGE... | status | check-diff BASE'
          ' | pages [-z] [PATH...] | check [-v] PAGE... | check-changed [-v] [--base REF] [PAGE...]', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
