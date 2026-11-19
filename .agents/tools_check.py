"""Check the programs that .agents/stack.json records: each one is there, and at its version floor.

just install writes this file, and the step tools-check of just check runs it. It reads only the record, so a clone
of the project, as in CI, can run it. It runs each check without a shell, and it never installs or downloads.

    python .agents/tools_check.py                          check the programs of .agents/stack.json
    python .agents/tools_check.py --manifest skill-package.json    check the required executables of a package

The record holds each program under the key programs: {"just": {"check": "just --version", "version": ">=1.50.0",
"owners": {"jnterfaces": ">=1.50.0"}}}. The key project_programs is the list of programs that the project itself
needs, with the keys name, check, version, expect and description. A version floor is >=X.Y or >=X.Y.Z. The version
of a program is the first X.Y.Z, or X.Y, anywhere in the output of its check. A program with "each_clone": true is a
setup of each clone, such as the git hooks of a role, which just install sets up. CI skips it, as CI needs no hooks.

This file runs with Python 3.9 or later, and it needs no package.
"""
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys

# A version floor: >= and two or three numbers.
FLOOR = re.compile(r'>=\s*(\d+)\.(\d+)(?:\.(\d+))?')
# A version in the output of a check: the first two or three numbers with dots, not inside a longer number.
FOUND = re.compile(r'(?<![\d.])(\d+)\.(\d+)(?:\.(\d+))?')
# The keys of a program of the project.
PROJECT_KEYS = {'name', 'check', 'version', 'expect', 'description'}
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.+-]*')
# The variables that stop a check from an install or a download: rustup installs a missing toolchain that the project
# pins, and uv downloads a missing Python.
NO_DOWNLOADS = {'RUSTUP_AUTO_INSTALL': '0', 'UV_PYTHON_DOWNLOADS': 'never'}
# The seconds that one check may take.
CHECK_SECONDS = 120


def parse_floor(text):
    """The numbers of a version floor, such as (1, 50, 0) for >=1.50.0. None when there is no floor. ValueError when
    the text is not a floor."""
    if text is None:
        return None
    match = FLOOR.fullmatch(text.strip()) if isinstance(text, str) else None
    if not match:
        raise ValueError(f'{text!r} is not a version floor: write >=X.Y or >=X.Y.Z, for example >=1.50.0')
    return tuple(int(part or 0) for part in match.groups())


def found_version(output):
    """The first version in the output of a check, as three numbers, or None."""
    match = FOUND.search(output or '')
    return tuple(int(part or 0) for part in match.groups()) if match else None


def text_of(numbers):
    return '.'.join(str(part) for part in numbers)


def higher(first, second):
    """The higher of two floors, as text. None counts as no floor."""
    if first is None or second is None:
        return first if second is None else second
    return first if parse_floor(first) >= parse_floor(second) else second


def merge(entries):
    """Merge programs by name. Each entry has name, check, and optional version, expect and owner. For the same name,
    the floor is the highest, and owners maps each owner to the floor that it asks for, or None for no floor. The
    first entry gives the check and expect. each_clone is true when an entry has it."""
    found = {}
    for entry in entries:
        program = found.setdefault(entry['name'], {'check': entry['check'], 'owners': {}})
        if 'expect' in entry and 'expect' not in program:
            program['expect'] = entry['expect']
        if entry.get('each_clone') is True:
            program['each_clone'] = True
        owner = entry.get('owner') or 'the project'
        program['owners'][owner] = higher(program['owners'].get(owner), entry.get('version'))
        program['version'] = higher(program.get('version'), entry.get('version'))
    for program in found.values():
        if program['version'] is None:
            del program['version']
    return found


def floor_owner(program):
    """The owner whose floor is the floor of the program, or the first owner."""
    owners = program.get('owners') or {}
    for owner, floor in owners.items():
        if floor is not None and floor == program.get('version'):
            return owner
    return next(iter(owners), 'the project')


def problem(name, program, run=None, which=shutil.which):
    """Run the check of one program, and return None when it passes, else one line that says why. The line names the
    floor, the version found, the path of the program, and the owner. run(argv) returns the exit code, the output and
    the error output, and which(name) the path of a program. The output must hold expect. The version is the first
    one in the output, else in the error output, since some programs print it there."""
    run = run or run_check
    argv = shlex.split(program['check'])
    floor = program.get('version')
    owner = floor_owner(program)
    others = [other for other in program.get('owners') or {} if other != owner]
    needs = f'{name} (for {owner}{", also " + ", ".join(others) if others else ""}) needs ' \
            + (floor if floor else 'its check to pass')
    path = which(argv[0])
    if path is None:
        return f'{needs}, but {argv[0]} is not on PATH, so no version was found.'
    code, output, errors = run(argv)
    at = f', at {path}'
    if code != 0:
        late = ' It took too long.' if code == 124 and (errors or '').startswith('the check took more than') else ''
        # The check of a setup of each clone says why it fails, such as a config without the hooks of a role.
        said = ((errors or '').strip() or (output or '').strip()).splitlines()[-3:] if program.get('each_clone') else []
        why = (' It said: ' + ' / '.join(line.strip() for line in said)) if said else ''
        # The words of the check may end without a full stop, and the next sentence follows them.
        why += '.' if why and why[-1] not in '.!?' else ''
        return f'{needs}, but {program["check"]} failed with exit {code}{at}.{late}{why}'
    if program.get('expect') and program['expect'] not in output:
        return f'{needs}, but {program["check"]} did not print {program["expect"]}{at}.'
    if floor:
        version = found_version(output) or found_version(errors)
        if version is None:
            return f'{needs}, but {program["check"]} printed no version{at}.'
        if version < parse_floor(floor):
            return f'{needs}, but found {text_of(version)}{at}.'
    return None


def run_check(argv, cwd=None, env=None):
    """Run a check without a shell and without input, and return its exit code, its output and its error output. A
    check that takes more than CHECK_SECONDS stops, with each process that it started, and fails with exit 124."""
    env = dict(os.environ if env is None else env, **NO_DOWNLOADS)
    try:
        # A session of its own, so that a timeout stops each process of the check, not only the first.
        started = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, errors='replace', start_new_session=True)
    except OSError:
        return 127, '', ''
    try:
        out, err = started.communicate(timeout=CHECK_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(started.pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            started.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        return 124, '', f'the check took more than {CHECK_SECONDS} seconds, so it was stopped'
    except BaseException:
        try:
            os.killpg(started.pid, signal.SIGKILL)
        except OSError:
            pass
        raise
    return started.returncode, out, err


def check_entry(entry, where):
    """Check the shape of one program of the project or of a package. Return the reason that it is malformed, or
    None."""
    if not isinstance(entry, dict) or not isinstance(entry.get('name'), str) or not NAME.fullmatch(entry['name']):
        return f'{where}: each program needs a name of letters, digits and the signs _ . + -'
    name = entry['name']
    try:
        argv = shlex.split(entry['check']) if isinstance(entry.get('check'), str) else None
    except ValueError:
        argv = None
    if not argv:
        return f'{where}: the program {name} needs a check, a command as a string'
    if '/' in argv[0]:
        return f'{where}: the check of the program {name} must start with a program on PATH, not a path'
    try:
        parse_floor(entry.get('version'))
    except ValueError as exc:
        return f'{where}: the version of the program {name}: {exc}'
    if 'expect' in entry and not (isinstance(entry['expect'], str) and entry['expect']):
        return f'{where}: the expect of the program {name} must be a text'
    return None


def project_programs(record, where='project_programs of .agents/stack.json'):
    """The programs of the project, from the key project_programs of the record, each with the owner the project.
    ValueError when the key is malformed."""
    listed = record.get('project_programs', [])
    if not isinstance(listed, list):
        raise ValueError(f'{where} must be a list of programs')
    found = []
    for entry in listed:
        reason = check_entry(entry, where)
        if reason:
            raise ValueError(reason)
        unknown = sorted(set(entry) - PROJECT_KEYS)
        if unknown:
            raise ValueError(f'{where}: the program {entry["name"]} has the unknown key(s) {", ".join(unknown)}')
        found.append(dict(entry, owner='the project'))
    return found


def recorded(record):
    """The programs to check: those of the key programs of the record, and the programs of the project, which the
    project can change before the next just install. ValueError when the record is malformed."""
    programs = record.get('programs', {})
    if not isinstance(programs, dict):
        raise ValueError('programs of .agents/stack.json must be a map of names to programs')
    entries = []
    for name, program in programs.items():
        owners = program.get('owners') if isinstance(program, dict) else None
        reason = check_entry(dict(program, name=name) if isinstance(program, dict) else None,
                             'programs of .agents/stack.json')
        if reason or not isinstance(owners, dict) or not owners:
            raise ValueError(reason or f'programs of .agents/stack.json: the program {name} needs its owners')
        for owner, floor in owners.items():
            try:
                parse_floor(floor)
            except ValueError as exc:
                raise ValueError(f'programs of .agents/stack.json: the floor of {owner} for {name}: {exc}')
            # The project's own floors come from project_programs as it is now, so an edit counts at once.
            if owner == 'the project':
                continue
            entry = {'name': name, 'check': program['check'], 'owner': owner}
            entry.update({key: value for key, value in (('version', floor), ('expect', program.get('expect')),
                                                        ('each_clone', program.get('each_clone') or None))
                          if value is not None})
            entries.append(entry)
    return merge(entries + project_programs(record))


def manifest_programs(manifest):
    """The required executables of a skill-package.json, each with the owner the package. An entry without a check
    is left out, as the installer only looks for it on PATH. ValueError when the file has the wrong shape."""
    if not isinstance(manifest, dict):
        raise ValueError('skill-package.json is not a JSON object')
    repository, executables = manifest.get('repository', {}), manifest.get('executables', {})
    required = executables.get('required', []) if isinstance(executables, dict) else None
    if not isinstance(repository, dict) or not isinstance(required, list):
        raise ValueError('repository and executables.required of skill-package.json have the wrong shape')
    owner = repository.get('name') or 'the package'
    entries = []
    for entry in required:
        if isinstance(entry, dict) and 'check' not in entry:
            continue
        reason = check_entry(entry, 'executables.required of skill-package.json')
        if reason:
            raise ValueError(reason)
        entries.append(dict(entry, owner=owner))
    return merge(entries)


def outside_venv():
    """Leave the virtual environment that uv run gives this script: uv run finds the .venv of the project, sets
    VIRTUAL_ENV and puts its bin folder first on PATH. A uv or just from the dependencies of the project would then
    stand in for the program of the machine, which the recipes use."""
    venv = os.environ.pop('VIRTUAL_ENV', None)
    if venv:
        inside = os.path.realpath(os.path.join(venv, 'bin'))
        os.environ['PATH'] = os.pathsep.join(
            part for part in os.environ.get('PATH', '').split(os.pathsep)
            if not part or os.path.realpath(part) != inside)


def in_ci():
    """True when CI is set, as on GitHub Actions, and is not 0 or false."""
    return os.environ.get('CI', '').strip().lower() not in ('', '0', 'false')


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    outside_venv()
    try:
        if args[:1] == ['--manifest'] and len(args) == 2:
            programs = manifest_programs(json.loads(Path(args[1]).read_text()))
        elif not args or (args[:1] == ['--record'] and len(args) == 2):
            path = Path(args[1] if args else '.agents/stack.json')
            if not path.is_file():
                print(f'tools-check: {path} is not here, so no program is recorded to check.')
                return 0
            record = json.loads(path.read_text())
            if not isinstance(record, dict):
                raise ValueError(f'{path} is not a JSON object')
            if 'programs' not in record and not record.get('project_programs'):
                print(f'tools-check: {path} records no programs yet. Run just install to record them.')
                return 0
            programs = recorded(record)
        else:
            print('Use: tools_check.py [--record FILE | --manifest FILE]', file=sys.stderr)
            return 2
    except (OSError, ValueError) as exc:
        print(f'tools-check: {exc}', file=sys.stderr)
        return 2
    if in_ci():
        skipped = [name for name, program in programs.items() if program.get('each_clone')]
        if skipped:
            print(f'tools-check: CI is set, so {", ".join(skipped)} is not checked: it is a setup of each clone.')
        programs = {name: program for name, program in programs.items() if name not in skipped}
    problems = []
    for name, program in programs.items():
        line = problem(name, program)
        if line:
            problems.append(line + (' Run just install, which sets it up in this clone.' if program.get('each_clone')
                                    else ' Install or update it, then run just tools-check again.'))
    for line in problems:
        print(f'tools-check: {line}', file=sys.stderr)
    if not problems:
        print(f'tools-check: {len(programs)} programs are there, at their floors.')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
