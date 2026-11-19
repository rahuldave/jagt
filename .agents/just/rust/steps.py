"""The helper of the steps of the rust profile: test, integration, coverage-check, docstring-check, test-paths and
api-check.

The recipes in this folder run it with uv: python steps.py run STEP ARG..., fresh STEP, coverage, docs, test-paths
PATH... and toml. STEP is test or integration. test runs the unit tests, those of the library and the binaries, and
integration runs the test targets, such as the files of the folder tests. Each writes its own coverage report. The
run ID JLOG_RUN of the root Justfile and the worktree tree tie each report to its run, so that coverage-check reads a
report only in the same run. It needs Python 3.11 or later and no package. The step coverage-check also needs
diff-cover, which it runs with uv.

The lists .agents/generated.txt and .agents/coverage-exclude.txt come from the parent commit, through git show
HEAD:./PATH, so a commit cannot exempt its own code. With no parent, or a parent without the file, the list is empty.
git matches their patterns, as pathspecs with the magic word glob. Every path is relative to the current folder, the top
of the project, which can be a subfolder of the git repository.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import threading
import tomllib
import urllib.parse

DIFF_COVER = 'diff-cover==11.0.1'
# The other place of the config of cargo-sort, which reads tomlfmt.toml from the current folder.
SORT_CONFIG = '.config/tomlfmt.toml'
# The exit codes of test-paths, the same for each profile: the tests passed, a test failed or did not build,
# the runner itself failed, and no test ran, as pytest gives when it collects none.
PASSED, FAILED, RUNNER, NO_TEST = 0, 1, 2, 5
# What cargo prints when a test fails or a test does not build.
BROKE = re.compile(r'^error: (?:test failed|could not compile|failed to run custom build command)', re.M)
# What cargo prints when no test target matches the name or the pattern.
NO_TARGET = re.compile(r'^error: no test target matches pattern', re.M)
# The line of cargo for each test binary that it starts, in its exact form, so a line that a test leaks, such as
# that of a cargo run inside a test, does not match. A binary with harness = false prints no test result. The binary is
# in target/debug/deps, or, with the build-dir layout of newer cargo, in target/debug/build/<package>/<hash>/out. The
# folder deps or out is a whole part of the path, and the path may hold a space, as a build-dir under a home folder can.
RUNNING = re.compile(r'^     Running (?:unittests )?[^`\s].* \((?:[^()\n]*[/\\])?(?:deps|out)[/\\][^/\\()\n]+\)$', re.M)
# The line of libtest that announces how many tests a binary will run.
ANNOUNCED = re.compile(r'^running (\d+) tests?$', re.M)
# The escape codes of terminal colors, which a test may still print.
ANSI = re.compile(r'\x1b\[[0-9;]*m')
# The seconds with no new line, once the command ends, after which the copy of its output stops.
LINGER = 2
# The line of libtest for a test that failed, also a #[should_panic] test, whose name ends in - should panic.
FAILED_TEST = re.compile(r'^test .+ \.\.\. FAILED$', re.M)
# The summary line of each test binary: the numbers of the passed and of the failed tests.
TEST_RESULT = re.compile(r'^test result: \w+\. (\d+) passed; (\d+) failed;', re.M)
GENERATED = '.agents/generated.txt'
COVERAGE_EXCLUDE = '.agents/coverage-exclude.txt'
REPORTS = Path('target/llvm-cov')
# The steps that write a coverage report.
COVERED = ('test', 'integration')
# The kinds of target of cargo metadata that --lib selects.
LIBRARY = {'lib', 'rlib', 'dylib', 'cdylib', 'staticlib', 'proc-macro'}
# The tests with coverage, with every feature. run adds the targets of the step and the path of its report.
COVERAGE = ['cargo', 'llvm-cov', 'test', '--all-features', '--locked', '--include-build-script']
# The file of jnterfaces whose steps list says whether integration runs in just check.
STACK = Path('.agents/stack.json')
DOC_LINTS = ('missing_docs', 'clippy::missing_docs_in_private_items')
WORK = Path('target/jnprofile-rust')
# The folder of the run of api-prose-check, as .jnprofile-python and .jnprofile-typescript of the other profiles. The
# tool api adds it to .gitignore and .worktreedisposable.
API_WORK = Path('.jnprofile-rust')
SMALLDOCS = 'smalldocs==0.5.12'
# The start of each uv run of the steps. smalldocs needs Python 3.11 or later, and uv may pick an older Python when
# none is named, as on a machine whose python3 is 3.9 or with UV_PYTHON set. The recipes name the same version.
UV_RUN = ['uv', 'run', '--no-project', '--quiet', '--python', '>=3.11']
DOCS_CONFIG = Path('docs/_smalldocs.yml')
# The nightly toolchain that runs rustdoc for smalldocs, which needs -Z unstable-options. smalldocs 0.5.12 reads
# only the formats 57 and 61 of the JSON of rustdoc, so the date is fixed. The program nightly of profile.json
# installs the same toolchain.
NIGHTLY = 'nightly-2026-11-12'
# The checker of nossaifd, which the prose role installs. api prose checks the API pages with it.
PROSE_CHECKER = Path('.agents/skills/nossaifd/scripts/check.py')
# The gate of nossaifd, which the prose role installs too. Its base_commit gives the base of api-prose-check in CI or
# with --base, as for check-changed of nossaifd.
PROSE_GATE = Path('.agents/skills/nossaifd/scripts/prose_gate.py')
# The variables of CI that the base of api-prose-check can come from, so a run with others runs again.
BASE_VARIABLES = ('CI', 'GITHUB_BASE_REF', 'GITHUB_REF', 'GITHUB_EVENT_NAME', 'GITHUB_EVENT_PATH')
# The start of each source link of the API pages that api prose builds, so that it finds the file of each item.
MARK = 'https://jnprofile-rust.invalid/'


def git(*args):
    """Run git with ARGS in the current folder, and return the finished process, with its output as text."""
    return subprocess.run(['git', *args], capture_output=True, text=True)


def has_parent():
    """True when HEAD names a commit, so that the next commit has a parent."""
    return git('rev-parse', '--verify', '--quiet', 'HEAD^{commit}').returncode == 0


def top():
    """The real path of the current folder, the top of the project. Every path of the steps is relative to it."""
    return Path(os.path.realpath('.'))


def parent_list(path):
    """The patterns of the list file PATH in the parent commit: one for each line that is not blank or a comment.

    A missing parent or a file that the parent does not have gives no patterns.
    """
    if not has_parent():
        return []
    run = git('show', f'HEAD:./{path}')
    if run.returncode:
        return []
    return [line.strip() for line in run.stdout.splitlines() if line.strip() and not line.strip().startswith('#')]


def matcher(patterns):
    """A function that is true for a path, relative to the current folder, that one of PATTERNS matches.

    git matches the patterns, as pathspecs with the magic word glob, against the tracked and the untracked files
    that it does not ignore. So the steps and the gate read a list in the same way. A * does not match a /, ** matches
    any number of folders, and a folder names all that it holds. A leading / is the top of the project.
    """
    if not patterns:
        return lambda path: False
    specs = [':(glob)' + pattern.lstrip('/') for pattern in patterns]
    run = git('ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', *specs)
    if run.returncode:
        raise SystemExit(f'steps.py: git cannot read the patterns {patterns}: {run.stderr.strip()}')
    found = set(filter(None, run.stdout.split('\0')))
    return lambda path: path in found


def relative(path, root):
    """PATH relative to ROOT, with / between its parts, or None for a path outside ROOT."""
    full = Path(os.path.realpath(root / path))
    try:
        return full.relative_to(root).as_posix()
    except ValueError:
        return None


def filter_lcov(text, root, excluded):
    """The LCOV report TEXT without the record of each source file that EXCLUDED is true for.

    A record runs from its SF: line to its end_of_record line. A path outside ROOT stays.
    """
    out, keep = [], True
    for line in text.splitlines(keepends=True):
        if line.startswith('SF:'):
            path = relative(line[3:].strip(), root)
            keep = path is None or not excluded(path)
        if keep:
            out.append(line)
        if line.strip() == 'end_of_record':
            keep = True
    return ''.join(out)


def ignored(path):
    """True for a path outside the project, or one that git ignores, such as a file that build.rs writes in target/."""
    if path.startswith('/') or path.startswith('../'):
        return True
    return git('check-ignore', '--quiet', '--', path).returncode == 0


def worktree_tree():
    """The tree hash of every file of the worktree, staged or not, that git does not ignore, or None on an error.

    It starts from HEAD in a temporary index of its own, so neither the real index nor a second run at the same time
    changes. The tree only ties a report to its run: steps.py compares it with its own trees, never with the tree of
    jlog or jagt, which start from a copy of the index. The folders target and .jnprofile-rust of the project never
    count. A file that git cannot index, such as a nested repository with no commit, gives None, and git's message goes
    to the error output.
    """
    WORK.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(dir=WORK, suffix='.index')
    os.close(handle)
    index = Path(name).resolve()
    index.unlink()
    env = dict(os.environ, GIT_INDEX_FILE=str(index))
    try:
        if has_parent():
            subprocess.run(['git', 'read-tree', 'HEAD'], env=env, check=True, capture_output=True)
        # git refuses to name an ignored path, even to exclude it, so the exclude is only for a folder that git sees.
        specs = [':/'] + [f':(exclude){folder}' for folder in ('target', str(API_WORK)) if not ignored(folder)]
        subprocess.run(['git', 'add', '-A', '--', *specs], env=env, check=True, capture_output=True)
        return subprocess.run(['git', 'write-tree'], env=env, check=True, capture_output=True,
                              text=True).stdout.strip()
    except subprocess.CalledProcessError as exc:
        print(f'steps.py: git cannot compute the worktree tree: {(exc.stderr or b"").decode(errors="replace").strip()}',
              file=sys.stderr)
        return None
    finally:
        index.unlink(missing_ok=True)
        Path(str(index) + '.lock').unlink(missing_ok=True)


def report(step):
    """The coverage report of STEP, test or integration: target/llvm-cov/STEP.lcov."""
    return REPORTS / f'{step}.lcov'


def run_folder(step):
    """The folder of the files of the run of STEP: target/llvm-cov for test and integration, .jnprofile-rust for
    prose."""
    return REPORTS if step in COVERED else API_WORK


def saved_run(step):
    """The file that ties the run of STEP, and its report, to the run of just: STEP.run.json in run_folder."""
    return run_folder(step) / f'{step}.run.json'


def pending_run(step):
    """The file that holds the run of STEP while it goes on: STEP.run.pending in run_folder."""
    return run_folder(step) / f'{step}.run.pending'


def run_key(step, args):
    """What else a run of STEP with ARGS depends on, beside the run ID and the tree, or None when such a run is not
    saved. A run of test or integration with ARGS runs only some tests, so it is not saved. api-prose-check, the
    run prose, takes --base REF, and in CI its base comes from the variables of CI, so these go into the key: a run
    with another base runs again. The commit of HEAD goes in too: a base resolves against HEAD, so a run on another
    HEAD with the same tree runs again."""
    if step == 'prose':
        head = git('rev-parse', '-q', '--verify', 'HEAD').stdout.strip()
        return {'args': list(args), 'env': {key: os.environ.get(key, '') for key in BASE_VARIABLES}, 'head': head}
    return None if args else {}


def begin(step, args):
    """Save the run ID and the worktree tree before a run of STEP, test, integration or prose, in its pending file.

    Only a run inside a run of just that has JLOG_RUN, and with a key of run_key, saves them. Any other run saves
    nothing, so the next step that needs the run runs it again. Returns the exit code, always 0.
    """
    saved_run(step).unlink(missing_ok=True)
    pending_run(step).unlink(missing_ok=True)
    run, key = os.environ.get('JLOG_RUN', ''), run_key(step, args)
    tree = worktree_tree() if key is not None and run else None
    if tree:
        run_folder(step).mkdir(parents=True, exist_ok=True)
        pending_run(step).write_text(json.dumps({'run': run, 'tree': tree, 'key': key}) + '\n')
    return 0


def stamp(step):
    """After the tests of STEP passed, keep the saved run as target/llvm-cov/STEP.run.json when the tree did not change.

    A change to a file while the tests ran means that the report may come from the old code, so the run is dropped.
    Returns the exit code, always 0.
    """
    try:
        saved = json.loads(pending_run(step).read_text())
    except (OSError, ValueError):
        return 0
    finally:
        pending_run(step).unlink(missing_ok=True)
    if isinstance(saved, dict) and saved.get('tree') and saved['tree'] == worktree_tree():
        saved_run(step).write_text(json.dumps(saved) + '\n')
    else:
        print(f'{recipe_of(step)}: a file changed during the run, so the next step that needs it runs it again',
              file=sys.stderr)
    return 0


def recipe_of(step):
    """The recipe of the run STEP, for a message: prose is the run of api-prose-check."""
    return 'api-prose-check' if step == 'prose' else step


def ran(step, args):
    """True when STEP passed before in this run of just, on this tree and with the same key of run_key for ARGS. So
    a check that two steps of just check can need, such as api-prose-check, runs once."""
    run, key = os.environ.get('JLOG_RUN', ''), run_key(step, args)
    try:
        saved = json.loads(saved_run(step).read_text())
    except (OSError, ValueError):
        saved = None
    if (run and key is not None and isinstance(saved, dict) and saved.get('run') == run
            and saved.get('key', {}) == key and saved.get('tree') and saved['tree'] == worktree_tree()):
        print(f'{recipe_of(step)}: it passed before in this run, {run}, on this tree, so it does not run again')
        return True
    return False


def counts(step):
    """True when the report of STEP counts for coverage-check.

    The report of test always counts. That of integration counts when integration is in the steps of just check,
    the key steps of .agents/stack.json, and an installed tool provides it, the key provided_steps. The setup
    answer of jnterfaces that runs integration only in just verify takes it out of steps. With no stack.json or no
    list of steps, the default of the spec holds: integration runs in just check, so it counts.
    """
    if step == 'test':
        return True
    try:
        stack = json.loads(STACK.read_text())
    except (OSError, ValueError):
        return True
    listed = stack.get('steps') if isinstance(stack, dict) else None
    if not isinstance(listed, list):
        return True
    provided = stack.get('provided_steps')
    return step in listed and (not isinstance(provided, list) or step in provided)


def fresh(step):
    """True when the report of STEP comes from this run of just, JLOG_RUN, and from the current worktree tree.

    A person can set JLOG_RUN by hand, so the tree must match too. An old run of the same tree is a valid run.
    A report that does not count for coverage-check needs no run, so it is fresh too.
    """
    if not counts(step):
        print(f'coverage-check: {step} is not in the steps of just check, so its report does not count')
        return True
    run = os.environ.get('JLOG_RUN', '')
    try:
        saved = json.loads(saved_run(step).read_text())
    except (OSError, ValueError):
        saved = None
    if (run and isinstance(saved, dict) and saved.get('run') == run and report(step).is_file()
            and saved.get('tree') and saved['tree'] == worktree_tree()):
        print(f'coverage-check: the tests of {step} in this run, {run}, wrote the report, so they do not run again')
        return True
    print(f'coverage-check: no report of {step} for this run and this tree, so the tests run now', flush=True)
    return False


def selections(step):
    """The selections of targets of STEP, from cargo metadata: one list of cargo options for each run of cargo.

    Only a target whose key test is true counts, as for a plain cargo test, so a [[test]] with test = false does
    not run. test takes the libraries and the binaries. integration takes the test targets, such as the files of
    the folder tests, and the examples and the benches that set test = true. Each such target is named, with --bin,
    --test, --example or --bench. cargo looks for a name in each selected package, and a library has no name of
    its own, only --lib. So one run with --workspace takes them all only when each library is tested and no
    package has an untested target of a tested name. Otherwise each package gets a run of its own, with
    --package and the id of the package, since a dependency can have the same name. A step with no target gives
    no selection.
    """
    done = subprocess.run(['cargo', 'metadata', '--no-deps', '--format-version', '1'], capture_output=True, text=True)
    if done.returncode:
        sys.stderr.write(done.stderr)
        raise SystemExit(f'{step}: cargo metadata failed')
    kinds = (('bin', '--bin'),) if step == 'test' else (('test', '--test'), ('example', '--example'),
                                                         ('bench', '--bench'))
    chosen, named, skipped, untested_library = [], [], set(), False
    for package in json.loads(done.stdout)['packages']:
        library, pairs = False, []
        for target in package['targets']:
            tested = target.get('test', True)
            if step == 'test' and set(target['kind']) & LIBRARY:
                library = library or tested
                untested_library = untested_library or not tested
            for kind, option in kinds:
                if kind in target['kind']:
                    if tested:
                        pairs.append((option, target['name']))
                    else:
                        skipped.add((option, target['name']))
        named += pairs
        if library or pairs:
            chosen.append((package['id'], library, pairs))
    if untested_library or skipped & set(named):
        return [['--package', name, *(['--lib'] if library else []), *[arg for pair in pairs for arg in pair]]
                for name, library, pairs in chosen]
    if not chosen:
        return []
    library = any(library for _, library, _ in chosen)
    return [['--workspace', *(['--lib'] if library else []), *[arg for pair in dict.fromkeys(named) for arg in pair]]]


# The options of cargo that select targets, and those that select packages. With one of them in the extra
# arguments, the arguments choose. The step adds --workspace only when they choose no package.
TARGETS = ('--lib', '--bin', '--bins', '--test', '--tests', '--example', '--examples', '--bench', '--benches',
           '--all-targets', '--doc')
PACKAGES = ('-p', '--package', '--workspace', '--all')


def chosen_by(args):
    """What ARGS, before a --, choose: 'packages' when they name packages, 'targets' for targets only, else None.

    --exclude alone chooses targets: cargo takes it only with --workspace, which the step then adds.
    """
    found = None
    for arg in args:
        if arg == '--':
            break
        name = arg.split('=', 1)[0]
        if name in PACKAGES or (arg.startswith('-p') and not arg.startswith('--')):
            return 'packages'
        if name in TARGETS or name == '--exclude':
            found = 'targets'
    return found


def merge_lcov(texts):
    """One LCOV report from the reports TEXTS: a line runs when one report runs it.

    For each source file, a line is in the report when one of TEXTS measures it, and its count is the highest of
    their counts. diff-cover takes only the lines that each report fails, so it cannot merge reports itself.
    """
    counts, path = {}, None
    for text in texts:
        for line in text.splitlines():
            if line.startswith('SF:'):
                path = line[3:].strip()
                counts.setdefault(path, {})
            elif line.startswith('DA:') and path is not None:
                number, count = line[3:].split(',')[:2]
                lines = counts[path]
                lines[int(number)] = max(lines.get(int(number), 0), int(count))
            elif line.strip() == 'end_of_record':
                path = None
    return ''.join(f'SF:{path}\n' + ''.join(f'DA:{number},{count}\n' for number, count in sorted(lines.items()))
                   + 'end_of_record\n' for path, lines in sorted(counts.items()))


def run_tests(step, args):
    """Run the tests of STEP with coverage into target/llvm-cov/STEP.lcov, with ARGS for cargo llvm-cov test.

    Each selection of targets runs in its own cargo llvm-cov, with a report of its own, and the step merges them.
    When ARGS select targets or packages, such as --test api or -p core, they take the place of the selections. With no
    target for STEP, no test runs and the report is empty. Returns the exit code of the first cargo that fails.
    """
    out = report(step)
    out.unlink(missing_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    for old in REPORTS.glob(f'{step}.part*.lcov'):
        old.unlink()
    begin(step, args)
    try:
        chosen = chosen_by(args)
        runs = [[]] if chosen == 'packages' else [['--workspace']] if chosen else selections(step)
    except SystemExit as error:
        pending_run(step).unlink(missing_ok=True)
        print(error, file=sys.stderr, flush=True)
        return 1
    if not runs:
        what = 'test target' if step == 'integration' else 'library or binary'
        print(f'{step}: the workspace has no {what}, so no test runs and the report is empty', flush=True)
        out.write_text('')
        return stamp(step)
    parts = []
    for number, selection in enumerate(runs):
        parts.append(REPORTS / f'{step}.part{number}.lcov')
        command = [*COVERAGE, *selection, '--lcov', '--output-path', parts[-1].as_posix(), *args]
        print(shlex.join(command), flush=True)
        code = subprocess.run(command).returncode
        if code:
            pending_run(step).unlink(missing_ok=True)
            return code
    out.write_text(merge_lcov([part.read_text() for part in parts]))
    return stamp(step)


def changed_code():
    """The changed Rust files against HEAD, staged, unstaged or untracked, without the deleted ones."""
    tracked = git('diff', '-z', '--name-only', '--relative', '--diff-filter=d', 'HEAD', '--', '*.rs')
    untracked = git('ls-files', '-z', '--others', '--exclude-standard', '--', '*.rs')
    return sorted(set(filter(None, (tracked.stdout + '\0' + untracked.stdout).split('\0'))))


def reported(text, root):
    """The paths of the source files of the LCOV report TEXT, relative to ROOT."""
    return {relative(line[3:].strip(), root) for line in text.splitlines() if line.startswith('SF:')}


def test_file(path):
    """True for a file in the folder tests or benches of a Cargo package, which holds tests and no code to cover."""
    try:
        _, folder = package_of(path)
    except SystemExit:
        return False
    parts = Path(os.path.realpath(path)).relative_to(folder).parts
    return len(parts) > 1 and parts[0] in ('tests', 'benches')


def unreported(changed, lines, excluded):
    """The files of CHANGED that are not in the report, not excluded and not test files: no test can cover them.

    cargo llvm-cov leaves out a file that no test target compiles, such as a file that no mod names or a file in
    examples. It also leaves out each file in a folder named tests, examples or benches, at any depth.
    """
    return [path for path in changed if path not in lines and not excluded(path) and not test_file(path)]


def missed_lines(text, root):
    """Each line that the LCOV report TEXT gives a count of 0, as PATH:LINE relative to ROOT, in order."""
    missed, path = [], None
    for line in text.splitlines():
        if line.startswith('SF:'):
            path = relative(line[3:].strip(), root) or line[3:].strip()
        elif line.startswith('DA:') and path is not None:
            number, count = line[3:].split(',')[:2]
            if int(count) == 0:
                missed.append((path, int(number)))
    return [f'{path}:{number}' for path, number in sorted(missed)]


def coverage():
    """Fail on each changed line of code that the tests do not run, as diff-cover against HEAD finds it.

    It reads the report of test, and that of integration when it counts. A line that one of them runs passes.
    The files of generated.txt and coverage-exclude.txt of the parent commit do not count. On the first commit,
    every line of the reports must run instead. Returns the exit code.
    """
    reports = [report(step) for step in COVERED if counts(step)]
    for path in reports:
        if not path.is_file():
            print(f'coverage-check: there is no coverage report {path}, so write tests and run just test',
                  file=sys.stderr)
            return 1
    texts = [path.read_text() for path in reports]
    root = top()
    if not has_parent():
        print('coverage-check: the first commit, so every line of code must run in the tests', flush=True)
        missed = missed_lines(merge_lcov(texts), root)
        for line in missed:
            print(f'{line}: no test runs this line')
        if missed:
            print('coverage-check: write tests for the lines that no test runs', file=sys.stderr)
            return 1
        return 0
    excluded = matcher(parent_list(GENERATED) + parent_list(COVERAGE_EXCLUDE))
    WORK.mkdir(parents=True, exist_ok=True)
    kept = WORK / 'lcov.info'
    kept.write_text(filter_lcov(merge_lcov(texts), root, excluded))
    code = subprocess.run([*UV_RUN, '--with', DIFF_COVER, 'diff-cover', str(kept),
                           '--compare-branch', 'HEAD', '--include-untracked', '--fail-under', '100']).returncode
    lines = set().union(*(reported(text, root) for text in texts))
    missing = unreported(changed_code(), lines, excluded)
    for path in missing:
        print(f'{path}: a changed file that is not in the coverage report, so no test runs it')
    if missing:
        print('coverage-check: no test target compiles these files, or cargo llvm-cov leaves out their folder. Call '
              'the code from a test, move it out of a folder named tests or examples, or exclude the file',
              file=sys.stderr)
        code = code or 1
    if code:
        print('coverage-check: write tests for the missing lines. A file that no test can run goes in '
              f'{COVERAGE_EXCLUDE}, in a commit of its own before this one', file=sys.stderr)
    return code


def doc_findings(messages, root, excluded):
    """The items with no doc in the JSON MESSAGES of cargo clippy, as lines FILE:LINE:COLUMN: TEXT.

    Each message of a doc lint counts, warning or error, except one in a file that EXCLUDED is true for. Also
    returns the rendered errors that are not doc lints, for example a type error, which stop the check.
    """
    findings, errors = set(), []
    for raw in messages.splitlines():
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if entry.get('reason') != 'compiler-message':
            continue
        message = entry.get('message', {})
        code = (message.get('code') or {}).get('code')
        if code in DOC_LINTS:
            span = next((s for s in message.get('spans', []) if s.get('is_primary')), None)
            if span is None:
                continue
            path = relative(span['file_name'], root) or span['file_name']
            if not excluded(path):
                findings.add((path, span['line_start'], span['column_start'], f'{message["message"]} ({code})'))
        elif message.get('level') == 'error':
            errors.append(message.get('rendered') or message.get('message', ''))
    return [f'{path}:{line}:{column}: {text}' for path, line, column, text in sorted(findings)], errors


def docs():
    """Fail on each item with no doc comment, public or private, outside the files of generated.txt.

    It runs cargo clippy on the code of every package, without the tests, with the two doc lints as warnings, and
    reads its JSON messages. It turns on every feature, so code behind a feature counts. --cap-lints warn keeps
    each lint a warning, also under #![deny(missing_docs)], so clippy checks every crate. An item in a file that
    git ignores, such as code that build.rs writes into target/, counts as generated. Returns the exit code.
    """
    run = subprocess.run(['cargo', 'clippy', '--workspace', '--all-features', '--locked', '--quiet',
                          '--message-format=json', '--', '--cap-lints', 'warn',
                          '-W', 'missing_docs', '-W', 'clippy::missing_docs_in_private_items'],
                         stdout=subprocess.PIPE, text=True)
    generated = matcher(parent_list(GENERATED))
    findings, errors = doc_findings(run.stdout, top(), lambda path: generated(path) or ignored(path))
    for error in errors:
        print(error, file=sys.stderr)
    for finding in findings:
        print(finding)
    if findings:
        print(f'docstring-check: {len(findings)} items have no doc comment. Write a doc comment for each one',
              file=sys.stderr)
    # --cap-lints warn keeps a #![deny(missing_docs)] of the crate a warning, so clippy fails only on a real error.
    if run.returncode:
        print(f'docstring-check: cargo clippy exited with {run.returncode}', file=sys.stderr)
        return run.returncode
    return 1 if findings else 0


def package_of(path):
    """The name of the Cargo package that holds PATH, and its folder: the nearest Cargo.toml with a [package].

    The search stops at the top of the project, so a Cargo.toml outside the project never counts.
    """
    folder, root = Path(os.path.realpath(path)).parent, top()
    for candidate in [folder, *folder.parents]:
        if candidate != root and root not in candidate.parents:
            break
        manifest = candidate / 'Cargo.toml'
        if manifest.is_file():
            data = tomllib.loads(manifest.read_text())
            if isinstance(data.get('package'), dict) and isinstance(data['package'].get('name'), str):
                return data['package']['name'], candidate
    raise SystemExit(f'test-paths: no Cargo package holds {path}')


def target_names():
    """Map the real path of the file of each test target of the workspace to the name of the target.

    A [[test]] in Cargo.toml can give a target a name that is not the name of its file, so the names come from
    cargo metadata.
    """
    done = subprocess.run(['cargo', 'metadata', '--no-deps', '--format-version', '1'], capture_output=True, text=True)
    if done.returncode:
        sys.stderr.write(done.stderr)
        raise SystemExit('test-paths: cargo metadata failed')
    return {os.path.realpath(target['src_path']): target['name']
            for package in json.loads(done.stdout)['packages'] for target in package['targets']
            if 'test' in target['kind']}


def test_commands(paths):
    """The cargo test commands for PATHS, one for each package, in the order of the paths, and the skipped paths.

    Only a file in the folder tests of a package counts. A file tests/NAME.rs runs as its test target, which
    cargo metadata names, and a file that is no test target, as with autotests = false, is skipped. Any
    other file there, for example tests/common/mod.rs, runs every test target of that folder, with --test '*'. A
    unit test lives in the file of its code, such as src/lib.rs. A copy of that file in the parent commit brings
    the new code too, so the test proves nothing there, and test-paths skips the file.
    """
    targets, skipped, names = {}, [], None
    for path in paths:
        if not Path(path).is_file():
            raise SystemExit(f'test-paths: {path} is not a file')
        name, folder = package_of(path)
        parts = Path(os.path.realpath(path)).relative_to(folder).parts
        if len(parts) < 2 or parts[0] != 'tests':
            skipped.append(path)
            continue
        if len(parts) == 2 and parts[1].endswith('.rs'):
            if names is None:
                names = target_names()
            target = names.get(os.path.realpath(path))
            if target is None:
                print(f'test-paths: skips {path}, which is no test target of its package', flush=True)
                continue
            targets.setdefault(name, []).append(['--test', target])
        else:
            targets.setdefault(name, []).append(['--test', '*'])
    commands = []
    for name, chosen in targets.items():
        every = ['--test', '*'] in chosen
        args = ['--test', '*'] if every else [arg for pair in dict.fromkeys(map(tuple, chosen)) for arg in pair]
        commands.append(['cargo', 'test', '--locked', '--all-features', '--package', name, *args])
    return commands, skipped


def test_paths(paths):
    """Run the tests of PATHS without coverage, and return the exit code that the spec gives every profile.

    PASSED (0) when the tests ran and passed, FAILED (1) when a test failed or did not build, NO_TEST (5) when no
    test ran, and RUNNER (2) when cargo itself failed, for example on a stale Cargo.lock or a path it cannot run.
    A test binary that announced its tests and stopped with no result, as on std::process::exit in a test, ended
    the run, and gives RUNNER too. Each command runs, one for each package, and a failed test in any of them wins
    over a run that ended or a cargo that failed.
    """
    try:
        commands, skipped = test_commands(paths)
    except SystemExit as error:
        print(error, file=sys.stderr, flush=True)
        return RUNNER
    for path in skipped:
        print(f'test-paths: skips {path}, which is not in the folder tests of a package', flush=True)
    if not commands:
        print('test-paths: no file in the folder tests of a package, so no test ran', flush=True)
        return NO_TEST
    ran, codes = 0, set()
    for command in commands:
        print(shlex.join(command), flush=True)
        code, out = run_streamed(command)
        if code and NO_TARGET.search(out) and not RUNNING.search(out) and not BROKE.search(out):
            print('test-paths: no test target in the folder tests, so no test ran', flush=True)
            continue
        stopped = False
        for binary in RUNNING.split(out)[1:]:
            results = TEST_RESULT.findall(binary)
            if results:
                ran += sum(int(a) + int(b) for a, b in results)
            elif FAILED_TEST.search(binary):
                # libtest named a failed test, and then the binary stopped: the failure counts.
                codes.add(FAILED)
            elif any(int(n) for n in ANNOUNCED.findall(binary)):
                # The run ended, as on std::process::exit in a test, and no test result says why. The spec gives
                # that the code of a runner that failed, so test-review does not read it as a failed test.
                print('test-paths: a test binary stopped before it gave its result, so the run ended early',
                      flush=True)
                stopped = True
                codes.add(RUNNER)
            else:
                ran += 1
        if code and not stopped:
            codes.add(outcome(code, out))
    for result in (FAILED, RUNNER):
        if result in codes:
            return result
    if not ran:
        print('test-paths: the test targets hold no test that is not ignored, so no test ran', flush=True)
        return NO_TEST
    return PASSED


def outcome(code, out):
    """The exit code of test-paths for a cargo command that exited with CODE, not 0, and printed OUT.

    cargo exits with 101 both when a test fails or does not build and when it fails itself, and it passes on the
    code of a test binary that exits by itself. Its output tells them apart: a failed test or a failed build is
    FAILED, and anything else is RUNNER.
    """
    if BROKE.search(out):
        return FAILED
    print(f'test-paths: cargo failed with {code} before a test could run', flush=True)
    return RUNNER


def run_streamed(command):
    """Run COMMAND with its stderr in its stdout, copy each line out as it comes, and return the code and the text.

    The output of cargo is plain, with no colors, no quiet and no verbose lines, so the patterns match it. Once
    COMMAND ends, the copy goes on while lines still come, so a slow reader of stdout loses none. A process that
    COMMAND left running and that holds the pipe open, but prints nothing, does not keep this one waiting.
    """
    env = dict(os.environ, CARGO_TERM_COLOR='never', CARGO_TERM_QUIET='false', CARGO_TERM_VERBOSE='false')
    lines = []

    def copy(pipe):
        """Copy each line of PIPE to stdout and keep its text."""
        for line in pipe:
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
            lines.append(line.decode('utf-8', 'replace'))

    child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    reader = threading.Thread(target=copy, args=(child.stdout,), daemon=True)
    reader.start()
    code = child.wait()
    seen = -1
    while reader.is_alive() and len(lines) != seen:
        seen = len(lines)
        reader.join(LINGER)
    if not reader.is_alive():
        child.stdout.close()
    return code, ANSI.sub('', ''.join(lines))


def toml(args):
    """Sort each Cargo.toml with cargo-sort, then format the TOML files with taplo, with ARGS such as --check.

    cargo-sort only sorts, with --no-format, because it would indent arrays other than taplo does, and the two
    would undo each other. taplo gets the TOML files that git tracks or does not ignore, so it never reads target/.
    cargo-sort reads tomlfmt.toml from the current folder. A project may keep the file in .config/ instead, and then
    it gets the option --config. Both run, so one run shows every problem; the exit code is 1 when either fails.
    """
    command = ['cargo', 'sort', '--workspace', '--no-format', *args]
    if not Path('tomlfmt.toml').is_file() and Path(SORT_CONFIG).is_file():
        command += ['--config', SORT_CONFIG]
    print(shlex.join(command), flush=True)
    failed = subprocess.run(command).returncode != 0
    listed = git('ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', '*.toml')
    if listed.returncode:
        print(f'git cannot list the TOML files: {listed.stderr.strip()}', file=sys.stderr, flush=True)
        return 1
    files = sorted({name for name in listed.stdout.split('\0') if name and Path(name).is_file()})
    if files:
        command = ['taplo', 'fmt', *args, '--', *files]
        print(shlex.join(command), flush=True)
        failed = subprocess.run(command).returncode != 0 or failed
    return 1 if failed else 0


def crates():
    """The Cargo packages of the workspace that have a library or a binary, as (name, manifest), in the order of
    cargo metadata, from the current folder. smalldocs documents a library, else the binary."""
    done = subprocess.run(['cargo', 'metadata', '--no-deps', '--format-version', '1'], capture_output=True, text=True)
    if done.returncode:
        sys.stderr.write(done.stderr)
        raise SystemExit('api-check: cargo metadata failed')
    return [(package['name'], package['manifest_path']) for package in json.loads(done.stdout)['packages']
            if any(set(target['kind']) & (LIBRARY | {'bin'}) for target in package['targets'])]


def api_settings(folder):
    """The folder of the smalldocs config that api-check uses, and a note, or None and a note, or None and an exit
    code on an error.

    When docs/_smalldocs.yml has the key api with a Rust section, a section with language: rust, the folder is
    FOLDER/rust, with a config of only those sections, which rust_config writes. Otherwise it is FOLDER, with a
    section for each crate of the workspace that has a library or a binary. With no such crate, it is None.
    """
    try:
        text = DOCS_CONFIG.read_text()
    except (OSError, UnicodeDecodeError):
        text = ''
    if re.search(r'^api\s*:', text, re.MULTILINE):
        own = folder / 'rust'
        code = subprocess.run(smalldocs('python', str(Path(__file__).resolve()), 'config', str(DOCS_CONFIG.parent),
                                        str(own))).returncode
        if code == 0:
            return own, f'the Rust sections of the api settings of {DOCS_CONFIG}'
        if code != 3:
            return None, code
    try:
        found = crates()
    except SystemExit as error:
        print(error, file=sys.stderr)
        return None, 2
    if not found:
        return None, f'no crate with a library or a binary. The key api of {DOCS_CONFIG} can name the crate'
    sections = [{'language': 'rust', 'manifest': manifest, 'toolchain': NIGHTLY, 'out': f'api/{name}'}
                for name, manifest in found]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / '_smalldocs.yml').write_text(json.dumps({'api': sections if len(sections) > 1 else sections[0]}) + '\n')
    about = f'the crate {found[0][0]}' if len(found) == 1 else f'the {len(found)} crates of the workspace'
    return folder, about


def smalldocs(*args):
    """The command that runs ARGS with smalldocs, with uv. smalldocs runs cargo +TOOLCHAIN rustdoc for the JSON."""
    return [*UV_RUN, '--with', SMALLDOCS, *args]


def ci_named():
    """True when the variable CI is set to a value other than empty, false and 0. Only for the error of a missing
    prose_gate.py: with prose_gate.py, its own ci_set decides."""
    return os.environ.get('CI', '').strip().lower() not in ('', 'false', '0')


def load_gate():
    """The module prose_gate.py of the prose role, from the project, or None when the project does not have it."""
    if not PROSE_GATE.is_file():
        return None
    # The import would write __pycache__ into the installed skill. The gate sets the flag itself, but too late.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('jnprofile_prose_gate', PROSE_GATE.resolve())
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prose_base(option):
    """The base of api-prose-check, as check-changed of nossaifd takes it, so that both check the same changes.

    It is (None, None) with no option and no CI, for the changes since HEAD. Otherwise it is (commit, name), from
    base_commit of prose_gate.py of the project: the merge base of the option --base REF and HEAD, or in CI the base
    of the pull request or the push. On an error, it prints the message and gives (None, 2), so that no API page is
    left out without a word. With no option and no CI, it does not load prose_gate.py, so a local run is as before.
    """
    if option is None and not ci_named():
        return None, None
    try:
        gate = load_gate()
    except Exception as exc:  # noqa: BLE001 - any failure of the import of another package is an error of the step
        print(f'api-prose-check: {PROSE_GATE} cannot be loaded: {exc}', file=sys.stderr)
        return None, 2
    if gate is None or not hasattr(gate, 'base_commit') or not hasattr(gate, 'ci_set'):
        print(f'api-prose-check: a base, from --base or from CI, needs base_commit of {PROSE_GATE}, and the project '
              f'does not have it. Run just install to update the prose role', file=sys.stderr)
        return None, 2
    if option is None and not gate.ci_set():
        return None, None
    found = git('rev-parse', '--show-toplevel')
    if found.returncode:
        print(f'api-prose-check: git cannot find the top of the repository: {found.stderr.strip()}', file=sys.stderr)
        return None, 2
    try:
        commit, name = gate.base_commit(Path(found.stdout.strip()), option)
    except Exception as exc:  # noqa: BLE001 - a failure of base_commit of another package is an error of the step
        print(f'api-prose-check: base_commit of {PROSE_GATE} failed: {exc!r}. Run just install to update the prose '
              f'role', file=sys.stderr)
        return None, 2
    if commit is None:
        print(f'api-prose-check: {name}', file=sys.stderr)
        return None, 2
    return commit, name


def changed_since(base):
    """The Rust files that changed since the commit or tree BASE, in the commits and in the working tree, and the
    untracked ones, relative to the current folder. Deleted files are left out. None on an error of git."""
    tracked = git('diff', '-z', '--name-only', '--relative', '--no-renames', '--diff-filter=d', base, '--', '*.rs')
    untracked = git('ls-files', '-z', '--others', '--exclude-standard', '--', '*.rs')
    if tracked.returncode or untracked.returncode:
        print(f'api-prose-check: git cannot list the changes since {base}: '
              f'{(tracked.stderr or untracked.stderr).strip()}', file=sys.stderr)
        return None
    return sorted(set(filter(None, tracked.stdout.split('\0'))) | set(filter(None, untracked.stdout.split('\0'))))


def api_files(paths):
    """The paths of PATHS, relative to the current folder, the top of the project, that are files of the API pages by
    in_api of api_rule.py, the rule that the commit gate reads, and that are not in generated.txt of the parent
    commit. in_api is is_api with no check of the api tool and the docs role, which api-prose-check does not need.
    It runs in the top of the project, where docs/_smalldocs.yml is, also when that is a subfolder of the repository.
    """
    # The import would write __pycache__ into the installed folder of the profile.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('jnprofile_rust_api_rule',
                                                  Path(__file__).resolve().parent / 'api_rule.py')
    rule = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rule)
    excluded = matcher(parent_list(GENERATED))
    try:
        return [path for path in paths if not excluded(path) and rule.in_api(path)]
    except Exception as exc:  # noqa: BLE001 - the rule raises on settings that it cannot read
        # The rule reads the key api only in the form of a block. The changed files of each crate count then, so no
        # page is left out.
        print(f'api-prose-check: api_rule.py cannot read the key api of {DOCS_CONFIG} or {GENERATED}: {exc}. So the '
              'changed files of each crate count', file=sys.stderr)
        found = []
        for path in paths:
            clean = rule.clean(path)
            # Not rule.excluded, which raises on a pattern of generated.txt that it cannot read: the matcher of git
            # above leaves out the generated files of the parent commit.
            crate = rule.crate_of(clean) if clean.endswith('.rs') and not clean.startswith(rule.TOOL_FOLDERS) else None
            if crate is not None and not excluded(path) and rule.in_crate(clean, crate):
                found.append(path)
        return found


def api(action, option=None):
    """Run the api check: smalldocs api check with the settings of api_settings, for ACTION check. For ACTION prose,
    check the API page of each changed file with the checker of nossaifd. A changed file changed since HEAD, or
    since the base of prose_base, from OPTION, the value of --base, or from CI. Returns the exit code."""
    if action == 'prose' and not PROSE_CHECKER.is_file():
        print(f'api-prose-check: no checker of nossaifd at {PROSE_CHECKER}, so the API pages are not checked. The '
              'prose role installs it')
        return 0
    base = about_base = None
    if action == 'prose':
        base, about_base = prose_base(option)
        if base is None and about_base is not None:
            return about_base
    with tempfile.TemporaryDirectory() as temp:
        folder, about = api_settings(Path(temp))
        if folder is None and isinstance(about, int):
            return about
        if folder is None:
            print(f'{"api-check" if action == "check" else "api-prose-check"}: {about}, so there is no API to check')
            return 0
        if action == 'check':
            print(f'api-check: smalldocs api check, with {about}', flush=True)
            code = subprocess.run(smalldocs('smalldocs', 'api', 'check', '--dir', str(folder))).returncode
            if code == 1:
                print('api-check: give each public item a doc comment, each parameter a comment after it on its line '
                      'or a line of an # Arguments section, and each return other than () a # Returns section',
                      file=sys.stderr)
            elif code:
                print(f'api-check: smalldocs or uv failed with the exit code {code}. smalldocs needs the toolchain '
                      f'{NIGHTLY}, which just install api installs. The key api of {DOCS_CONFIG} can name the crate',
                      file=sys.stderr)
            return code
        if base is not None:
            changed = changed_since(base)
            if changed is None:
                return 2
        elif has_parent():
            changed = changed_code()
        else:
            listed = git('ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', '*.rs')
            changed = sorted(filter(None, listed.stdout.split('\0')))
        changed = api_files(changed)
        since = f'since {about_base}' if base is not None else 'since HEAD'
        if not changed:
            print(f'api-prose-check: no code of the API changed {since}')
            return 0
        out = Path(temp) / 'pages'
        out.mkdir()
        sys.stdout.flush()
        code = subprocess.run(smalldocs('python', str(Path(__file__).resolve()), 'pages', str(folder), str(out),
                                        *changed)).returncode
        if code:
            return code
        # The API pages first, then the module comments.
        pages = sorted(out.rglob('*.md'), key=lambda page: (not page.is_relative_to(out / 'pages'), page))
        if not pages:
            print('api-prose-check: no changed file has an API page or a module comment')
            return 0
        names = [page.relative_to(out / 'pages').with_suffix('').as_posix() if page.is_relative_to(out / 'pages')
                 else f"the module comment of {page.relative_to(out / 'modules').with_suffix('').as_posix()}"
                 for page in pages]
        print(f'api-prose-check: the API pages {", ".join(names)}, of the files changed {since}', flush=True)
        code = subprocess.run([*UV_RUN, 'python', str(PROSE_CHECKER),
                               *map(str, pages)]).returncode
        if code:
            print('api-prose-check: fix each hard problem in the doc comment that it comes from', file=sys.stderr)
        return code


def absolute(value, folder):
    """VALUE, a path or a list of paths of a smalldocs config in FOLDER, with each path absolute."""
    if isinstance(value, list):
        return [absolute(item, folder) for item in value]
    return str((folder / value).resolve()) if isinstance(value, str) else value


def linked_files(text):
    """The files that the source links of the page TEXT name, as paths relative to the top of the project.

    smalldocs writes each link as MARK, the path relative to the root of the api settings, which pages() sets to the
    top of the project, and #L with the line. It percent-encodes a path with a space, a # or a letter outside ASCII.
    """
    return {urllib.parse.unquote(match.group(1)) for match in re.finditer(re.escape(MARK) + r'([^)\s#]+)', text)}


def block_end(source, at):
    """The end of the block comment that starts at AT of SOURCE, after its */, with the nested block comments that
    Rust allows, or None when it is not closed."""
    depth, at = 1, at + 2
    while depth:
        found = re.compile(r'/\*|\*/').search(source, at)
        if not found:
            return None
        depth += 1 if found.group() == '/*' else -1
        at = found.end()
    return at


def attribute_end(source, at):
    """The end of the inner attribute #![...] that starts at AT of SOURCE, with the brackets inside it and the
    brackets in its strings, or None when it is not closed."""
    depth, at = 0, at + 2
    while at < len(source):
        char = source[at]
        if char == '"':
            found = re.compile(r'"(?:\\.|[^"\\])*"', re.S).match(source, at)
            if not found:
                return None
            at = found.end()
            continue
        depth += {'[': 1, ']': -1}.get(char, 0)
        at += 1
        if depth == 0:
            return at
    return None


def module_comment(path):
    """The text of the module comment of the Rust file PATH, or None when the file has none: its //! lines and its
    /*! */ comments at the top of the file, before any item, as rustdoc reads them. Blank lines, plain comments and
    inner attributes, such as #![forbid(unsafe_code)], may come before and between them."""
    try:
        source = Path(path).read_text(errors='replace')
    except OSError:
        return None
    source, at, lines = source.lstrip('\ufeff'), 0, []
    while at < len(source):
        if source[at].isspace():
            at += 1
        elif source.startswith('//!', at):
            end = source.find('\n', at)
            end = len(source) if end < 0 else end
            text = source[at + 3:end]
            lines.append(text[1:] if text.startswith(' ') else text)
            at = end
        elif source.startswith('///', at) and not source.startswith('////', at):
            break
        elif source.startswith('//', at):
            end = source.find('\n', at)
            at = len(source) if end < 0 else end
        elif source.startswith('/*', at):
            end = block_end(source, at)
            if end is None:
                break
            if source.startswith('/*!', at):
                lines += [re.sub(r'^\s*\* ?', '', line) for line in source[at + 3:end - 2].splitlines()]
            elif source.startswith('/**', at) and not source.startswith('/**/', at) \
                    and not source.startswith('/***', at):
                break
            at = end
        elif source.startswith('#![', at):
            end = attribute_end(source, at)
            if end is None:
                break
            at = end
        else:
            break
    return '\n'.join(lines).strip() or None


def rust_config(folder, target, links):
    """Write a smalldocs config into the folder TARGET with only the Rust sections of the key api of the config in
    FOLDER, and return those sections. It returns 3 when there is none, and 2 when PyYAML cannot read the config.

    The manifest and the root become absolute paths. A section with no toolchain gets NIGHTLY, which the profile
    installs. With LINKS, each section gets its own out, the top of the project as its root and the source link
    MARK, for pages(). It runs with smalldocs, whose PyYAML reads the config.
    """
    import yaml

    folder, target = Path(folder).resolve(), Path(target)
    try:
        data = yaml.safe_load((folder / '_smalldocs.yml').read_text())
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        print(f'api-check: {folder / "_smalldocs.yml"} cannot be read: {exc}', file=sys.stderr)
        return 2
    if data is not None and not isinstance(data, dict):
        print(f'api-check: {folder / "_smalldocs.yml"} is no map of settings', file=sys.stderr)
        return 2
    settings = (data or {}).get('api') or {}
    sections = [section for section in (settings if isinstance(settings, list) else [settings])
                if isinstance(section, dict) and section.get('language') == 'rust']
    own = []
    for number, section in enumerate(sections):
        section = dict(section)
        for key in ('manifest', 'root'):
            if key in section:
                section[key] = absolute(section[key], folder)
        # As smalldocs: the Cargo.toml of root. Its root is FOLDER, the folder of the site, when FOLDER holds a
        # Cargo.toml, a package.json or a .git, and the folder above it otherwise.
        at_site = any((folder / mark).exists() for mark in ('Cargo.toml', 'package.json', '.git'))
        root = section.get('root') or str(folder if at_site else folder.parent)
        section.setdefault('manifest', str(Path(root) / 'Cargo.toml'))
        section.setdefault('toolchain', NIGHTLY)
        if links:
            section.update(out=f'api{number}', source=MARK.rstrip('/'), root=str(top()))
        own.append(section)
    if not own:
        return 3
    target.mkdir(parents=True, exist_ok=True)
    (target / '_smalldocs.yml').write_text(yaml.safe_dump({'api': own if len(own) > 1 else own[0]}))
    return own


def pages(folder, out, files):
    """Write the API page of each changed file of FILES under OUT, as a Markdown file, from the Rust sections of the
    key api of the smalldocs config in FOLDER, and its module comment as a page of its own.

    It runs with smalldocs. rust_config writes the config, and smalldocs builds the pages there. A page is a page of
    a changed file when the source link of one of its items names that file. A page holds the first paragraph of the
    module comment in its front matter, which the checker of nossaifd does not read as prose. So the module comment
    of each changed file goes into a page of its own. Returns the exit code.
    """
    out = Path(out)
    config = out / 'config'
    own = rust_config(folder, config, True)
    if own == 3:
        print('api-prose-check: the api settings have no section with language: rust')
        return 0
    if isinstance(own, int):
        return own
    sys.stdout.flush()
    build = subprocess.run(['smalldocs', 'api', 'build', '--dir', str(config)], capture_output=True, text=True)
    if build.returncode:
        print(build.stdout + build.stderr, end='')
        print('api-prose-check: smalldocs cannot build the API pages', file=sys.stderr)
        return build.returncode
    wanted = {Path(name).as_posix() for name in files}
    for number in range(len(own)):
        built = config / f'api{number}'
        for page in sorted(built.rglob('*.qmd')):
            text = page.read_text()
            if linked_files(text) & wanted:
                # The pages keep their folders, so that a/b.qmd and a.b.qmd stay two pages.
                target = out / 'pages' / (f'{number}' if len(own) > 1 else '') / page.relative_to(built)
                target = target.with_suffix('.md')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
    for name in sorted(wanted):
        comment = module_comment(name)
        if comment:
            target = out / 'modules' / (name + '.md')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f'---\ntitle: "{Path(name).name}"\n---\n\n{comment}\n')
    return 0


def base_option(args):
    """The REF of the arguments ARGS of api-prose-check, --base REF or --base=REF, or '' with no base. As in
    check-changed of nossaifd, -v is taken and does nothing here, and the last --base counts. On an error, it prints
    the message and gives the exit code 2."""
    ref = ''
    rest = list(args)
    while rest:
        arg = rest.pop(0)
        if arg == '-v':
            continue
        if arg == '--base' and rest:
            ref = rest.pop(0)
        elif arg.startswith('--base='):
            ref = arg[len('--base='):]
        else:
            print(f'api-prose-check: unknown arguments {" ".join(args)}. It takes only --base REF and -v',
                  file=sys.stderr)
            return 2
        if not ref:
            print('api-prose-check: --base needs a branch or a commit', file=sys.stderr)
            return 2
    return ref


# A semver 2.0 version, as cargo takes it: X.Y.Z with no leading zeros, then an optional prerelease and build.
SEMVER = re.compile(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)'
                    r'(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?')


def version(manifest=Path('Cargo.toml')):
    """Print the version of the project from the root MANIFEST, for the release tag vX.Y.Z, and return the exit code.

    The version is [package] version, or [workspace.package] version when the package inherits it or the root has
    no package. No manifest, or no version in it, prints nothing and gives 0. A manifest that cannot be read or
    parsed, or a version that is not a string, gives 2. It reads the file with tomllib only, so it runs no cargo,
    starts no download and writes nothing. The version must be semver, as cargo asks, so the tag is v plus the text
    of the manifest.
    """
    try:
        # cargo reads a manifest that starts with a byte order mark, so this does too.
        data = tomllib.loads(manifest.read_text(encoding='utf-8-sig'))
    except FileNotFoundError:
        if manifest.is_symlink():
            print(f'version: {manifest} is a symlink to a missing file', file=sys.stderr)
            return 2
        return 0
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        print(f'version: cannot read {manifest}: {error}', file=sys.stderr)
        return 2
    workspace = data.get('workspace')
    shared = workspace.get('package') if isinstance(workspace, dict) else None
    shared = shared.get('version') if isinstance(shared, dict) else None
    package = data.get('package')
    if isinstance(package, dict):
        found = package.get('version')
        if isinstance(found, dict) and found.get('workspace') is True:
            if shared is None:
                print(f'version: {manifest} inherits the version, but [workspace.package] has none', file=sys.stderr)
                return 2
            found = shared
    else:
        found = shared
    if found is None:
        return 0
    if not isinstance(found, str) or not SEMVER.fullmatch(found):
        print(f'version: the version in {manifest} is not a semver version such as 1.2.3', file=sys.stderr)
        return 2
    print(found)
    return 0


def main(argv):
    """Run the command of ARGV and return its exit code, as the usage at the end lists the commands."""
    if len(argv) >= 2 and argv[0] == 'run' and argv[1] in COVERED:
        return run_tests(argv[1], argv[2:])
    if len(argv) == 2 and argv[0] == 'fresh' and argv[1] in COVERED:
        return 0 if fresh(argv[1]) else 1
    if argv == ['coverage']:
        return coverage()
    if argv == ['docs']:
        return docs()
    if argv[:1] == ['test-paths']:
        return test_paths(argv[1:])
    if argv in (['toml'], ['toml', '--check']):
        return toml(argv[1:])
    if argv[:2] == ['ran', 'prose']:
        return 0 if ran('prose', argv[2:]) else 1
    if argv[:2] == ['begin', 'prose']:
        return begin('prose', argv[2:])
    if argv == ['stamp', 'prose']:
        return stamp('prose')
    if argv == ['api', 'check']:
        return api('check')
    if argv[:2] == ['api', 'prose']:
        option = base_option(argv[2:])
        return option if isinstance(option, int) else api('prose', option or None)
    if argv == ['version']:
        return version()
    if argv[:1] == ['pages'] and len(argv) >= 3:
        return pages(argv[1], argv[2], argv[3:])
    if argv[:1] == ['config'] and len(argv) == 3:
        own = rust_config(argv[1], argv[2], False)
        return own if isinstance(own, int) else 0
    print('usage: steps.py run STEP [ARG...] | fresh STEP | coverage | docs | test-paths [PATH...] | toml [--check] | '
          'ran prose [ARG...] | begin prose [ARG...] | stamp prose | api check | api prose [--base REF] | '
          'version | pages DOCS OUT [FILE...] | config DOCS OUT, where STEP is test or integration', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
