"""Git worktrees for the tasker role: make, set up, list and prune them.

The recipes of .agents/just/roles/agent_gest_git_skills.just run this script:

    mode           print the tasker variant of the project: git or gitwt
    new NAME [BASE] [--no-setup]
                   make branch NAME from BASE in ../<repo>.worktrees/NAME, set it up, then run `just setup`
    sync           set up the current worktree from the main checkout
    list [--report]
                   list the worktrees; --report prints one note, and only when some are ready to prune
    prune [--dry-run] [--min-age HOURS] [--with-ignored]
                   remove the worktrees that are clean, merged and idle for HOURS (default 2)

Setup follows two files in the main checkout. .worktreeinclude has gitignore patterns: each file that matches and
that git ignores is copied, as Claude Code and Conductor do. .worktreelink has one path on each line: each path is a
symbolic link to the path in the main checkout, as PostHog does. Copy small inputs, such as .env. Link large shared
inputs, such as a data folder. Keep outputs in each worktree.

Merged means that a merge of the worktree into the base branch would change nothing, so rebased and squashed work
counts. A worktree stays when it holds ignored files other than the copies and links of setup, such as outputs or
an edited .env; --with-ignored removes it too. A third file in the main checkout, .worktreedisposable, has gitignore
patterns for the ignored files that a command can make again, such as .venv/ and __pycache__/: those do not keep a
worktree. A detached worktree stays unless a branch has its commits. A removal
uses `git worktree remove` without --force. Branches stay.
"""

from __future__ import annotations

import filecmp
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

RECORD = Path('.agents/stack.json')
VARIANTS = ('git', 'gitwt')


class WorktreeError(Exception):
    pass


def git(*args, cwd, check=True, stdin=None):
    done = subprocess.run(['git', *args], cwd=cwd, input=stdin, capture_output=True, text=True)
    if check and done.returncode != 0:
        raise WorktreeError(done.stderr.strip() or f'git {" ".join(args)} failed')
    return done


def toplevel(cwd):
    done = git('rev-parse', '--show-toplevel', cwd=cwd, check=False)
    if done.returncode != 0:
        raise WorktreeError('this folder is not in a Git repository')
    return Path(done.stdout.strip()).resolve()


def worktrees(cwd):
    """The worktrees from `git worktree list --porcelain`. The first one is the main checkout."""
    entries, entry = [], None
    for line in git('worktree', 'list', '--porcelain', '-z', cwd=cwd).stdout.split('\0'):
        key, _, value = line.partition(' ')
        if key == 'worktree':
            entry = {'path': Path(value).resolve(), 'branch': None, 'locked': False, 'prunable': False}
            entries.append(entry)
        elif entry is None:
            continue
        elif key == 'HEAD':
            entry['head'] = value
        elif key == 'branch':
            entry['branch'] = value.removeprefix('refs/heads/')
        elif key in ('locked', 'prunable', 'bare'):
            entry[key] = True
    if not entries:
        raise WorktreeError('git lists no worktree')
    return entries


def mode(root):
    """The tasker variant that .agents/stack.json records, else git."""
    try:
        record = json.loads((root / RECORD).read_text())
    except (OSError, ValueError):
        return 'git'
    variants = record.get('variants') if isinstance(record, dict) else None
    variant = variants.get('tasker') if isinstance(variants, dict) else None
    return variant if variant in VARIANTS else 'git'


def ref_exists(ref, cwd):
    return git('rev-parse', '--verify', '--quiet', f'{ref}^{{commit}}', cwd=cwd, check=False).returncode == 0


def default_base(main):
    """The default branch of origin, else main, else master, else the branch of the main checkout."""
    done = git('symbolic-ref', '--quiet', '--short', 'refs/remotes/origin/HEAD', cwd=main['path'], check=False)
    names = [done.stdout.strip().removeprefix('origin/')] if done.returncode == 0 else []
    for name in names + ['main', 'master']:
        if name and ref_exists(f'refs/heads/{name}', main['path']):
            return name
    if main['branch']:
        return main['branch']
    raise WorktreeError('found no base branch; name one: just worktree-new NAME BASE')


def folder_of(main, name):
    return main['path'].parent / f'{main["path"].name}.worktrees' / name.replace('/', '-')


def say(text):
    print(text, flush=True)


# Setup


def include_files(main):
    """The files that .worktreeinclude names and that git ignores, relative to the main checkout."""
    patterns = main / '.worktreeinclude'
    if not patterns.is_file():
        return []
    named = git('ls-files', '-z', '--others', '--ignored', f'--exclude-from={patterns}', cwd=main).stdout
    if not named:
        return []
    done = git('check-ignore', '-z', '--stdin', cwd=main, stdin=named, check=False)
    if done.returncode not in (0, 1):
        raise WorktreeError(done.stderr.strip())
    return sorted(path for path in done.stdout.split('\0') if path)


def link_paths(main):
    """The paths of .worktreelink: one on each line, # starts a note."""
    listing = main / '.worktreelink'
    if not listing.is_file():
        return []
    paths = []
    for number, line in enumerate(listing.read_text().splitlines(), 1):
        line = line.split('#', 1)[0].strip().strip('/')
        if not line:
            continue
        if line.startswith('~') or '..' in Path(line).parts or '*' in line:
            raise WorktreeError(f'.worktreelink line {number}: {line} must be a plain path inside the project')
        paths.append(line)
    return paths


def under_link(top, relative):
    """True when a folder above the path in the worktree is a symbolic link."""
    parent = Path(relative).parent
    while parent != Path('.'):
        if (top / parent).is_symlink():
            return True
        parent = parent.parent
    return False


def sync(top, main):
    """Copy the files of .worktreeinclude and link the paths of .worktreelink from the main checkout into top.
    A path that is already in the worktree stays as it is."""
    if top == main:
        raise WorktreeError('this is the main checkout; run it in a worktree, or use just worktree-new')
    copied = linked = 0
    for relative in link_paths(main):
        source, target = main / relative, top / relative
        if not os.path.lexists(source):
            say(f'Skipped the link {relative}: the main checkout has no {relative}.')
            continue
        if git('ls-files', '--error-unmatch', '--', relative, cwd=main, check=False).returncode == 0:
            say(f'Skipped the link {relative}: git tracks it, so each worktree has its own copy.')
            continue
        if target.is_symlink() and Path(os.readlink(target)) == source:
            continue
        if os.path.lexists(target) or under_link(top, relative):
            say(f'Kept {relative}: the worktree has it already.')
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(source, target)
        except OSError as error:
            say(f'Skipped the link {relative}: {error.strerror}.')
            continue
        linked += 1
        # A link is a file to git, so the pattern data/ does not cover the link data. Then git sees a new file.
        if git('check-ignore', '-q', '--', relative, cwd=top, check=False).returncode != 0:
            say(f'Warning: git does not ignore the link {relative}. Add /{relative} without a final / to .gitignore.')
    for relative in include_files(main):
        source, target = main / relative, top / relative
        if under_link(top, relative):
            continue
        if os.path.lexists(target):
            if not (target.is_file() and source.is_file() and filecmp.cmp(source, target, shallow=False)):
                say(f'Kept {relative}: the worktree has its own version.')
            continue
        if not source.is_file():
            say(f'Skipped {relative}: it is a link to nothing.')
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        except OSError as error:
            say(f'Skipped {relative}: {error.strerror}.')
            continue
        copied += 1
    say(f'Set up {top}: copied {copied} file(s), linked {linked} path(s).')


def has_recipe(name, cwd):
    done = subprocess.run(['just', '--summary'], cwd=cwd, capture_output=True, text=True)
    return done.returncode == 0 and name in done.stdout.split()


def new(cwd, name, base=None, setup=True):
    entries = worktrees(cwd)
    main = entries[0]
    if git('check-ref-format', '--branch', name, cwd=cwd, check=False).returncode != 0:
        raise WorktreeError(f'{name} is not a valid branch name')
    folder = folder_of(main, name)
    if os.path.lexists(folder):
        raise WorktreeError(f'{folder} is there already')
    if ref_exists(f'refs/heads/{name}', main['path']):
        if base:
            raise WorktreeError(f'the branch {name} is there already, so it takes no base')
        git('worktree', 'add', str(folder), name, cwd=main['path'])
        say(f'Made the worktree {folder} for the branch {name}.')
    else:
        base = base or default_base(main)
        if not ref_exists(base, main['path']):
            raise WorktreeError(f'found no base {base}')
        git('worktree', 'add', '-b', name, str(folder), base, cwd=main['path'])
        say(f'Made the worktree {folder} with the new branch {name} from {base}.')
    sync(folder.resolve(), main['path'])
    if setup and has_recipe('setup', folder):
        say('Running just setup in the worktree.')
        if subprocess.run(['just', 'setup'], cwd=folder).returncode != 0:
            say('just setup failed; the worktree is there. Fix it, then run just setup in it.')
    say(f'Work there: cd {folder}')


# Listing and pruning


def bases(cwd, main):
    """The refs that a finished worktree is merged into: the base branch and its branch on origin."""
    try:
        name = default_base(main)
    except WorktreeError:
        return []
    return [ref for ref in (f'refs/heads/{name}', f'refs/remotes/origin/{name}') if ref_exists(ref, cwd)]


def merged(head, refs, cwd):
    """True when the content of head is in a base: head is an ancestor of the base, or a merge of head into the base
    changes nothing. The second test finds rebased and squashed work, and it fails when a revert took the work out."""
    for ref in refs:
        if git('merge-base', '--is-ancestor', head, ref, cwd=cwd, check=False).returncode == 0:
            return True
        done = git('merge-tree', '--write-tree', ref, head, cwd=cwd, check=False)
        tree = git('rev-parse', f'{ref}^{{tree}}', cwd=cwd).stdout.strip()
        if done.returncode == 0 and done.stdout.split('\n', 1)[0].strip() == tree:
            return True
    return False


def ancestor(head, refs, cwd):
    return any(git('merge-base', '--is-ancestor', head, ref, cwd=cwd, check=False).returncode == 0 for ref in refs)


def last_active(path):
    """The newest change time of the index, HEAD and the HEAD log of the worktree, and of its top files and folders.
    A job that writes outputs changes the time of their folder."""
    done = git('rev-parse', '--absolute-git-dir', cwd=path, check=False)
    if done.returncode != 0:
        return time.time()
    folder = Path(done.stdout.strip())
    items = [folder / 'index', folder / 'HEAD', folder / 'logs' / 'HEAD'] + [
        item for item in path.iterdir() if item.name != '.git']
    times = [item.lstat().st_mtime for item in items if os.path.lexists(item)]
    return max(times, default=time.time())


def ignored_entries(path):
    """The files and folders that git ignores in the worktree, as git lists them. git worktree remove deletes them."""
    done = git('ls-files', '-z', '--others', '--ignored', '--exclude-standard', '--directory', cwd=path, check=False)
    return [name.rstrip('/') for name in done.stdout.split('\0') if name]


def ignored_tops(entries):
    return sorted({name.split('/', 1)[0] for name in entries})


def disposable_paths(path, main):
    """The ignored files and folders in the worktree that .worktreedisposable of the main checkout names.

    Patterns match with letter case, also on macOS. A file that a ! line names is kept, with each folder above it,
    even under a folder that a pattern excludes, where gitignore would not bring the file back."""
    patterns = main / '.worktreedisposable'
    if not patterns.is_file():
        return set()
    listing = ['-c', 'core.ignorecase=false', 'ls-files', '-z', '--others', '--ignored']
    done = git(*listing, f'--exclude-from={patterns}', '--directory', cwd=path)
    found = {name.rstrip('/') for name in done.stdout.split('\0') if name}
    kept = [line[1:] for line in patterns.read_text(errors='replace').splitlines() if line.startswith('!')]
    if kept and found:
        # Ask git which files the ! lines name, as plain patterns, through a pattern file outside the worktree.
        with tempfile.NamedTemporaryFile('w', suffix='.patterns', delete=False) as handle:
            handle.write('\n'.join(kept) + '\n')
        try:
            named = git(*listing, f'--exclude-from={handle.name}', cwd=path).stdout
        finally:
            os.unlink(handle.name)
        for name in filter(None, named.split('\0')):
            parts = Path(name).parts
            found -= {Path(*parts[:end]).as_posix() for end in range(1, len(parts) + 1)}
    return found


def disposable(relative, paths):
    """True when the path, or a folder above it, is in paths."""
    parts = Path(relative).parts
    return any(Path(*parts[:end]).as_posix() in paths for end in range(1, len(parts) + 1))


def setup_only(path, main, entries):
    """True when each ignored file is a link of .worktreelink, a copy of .worktreeinclude that nobody changed, or a
    file that .worktreedisposable names."""
    links = {main / relative for relative in link_paths(main)}
    included = set(include_files(main))
    remade = disposable_paths(path, main)
    for name in entries:
        item = path / name
        # A whole folder that .worktreedisposable names, such as .venv, needs no walk through its files.
        if disposable(name, remade):
            continue
        if item.is_symlink() and Path(os.readlink(item)) in links:
            continue
        files = [item] if not item.is_dir() or item.is_symlink() else [
            Path(folder) / file for folder, _, names in os.walk(item) for file in names]
        for file in files:
            relative = file.relative_to(path).as_posix()
            if disposable(relative, remade):
                continue
            source = main / relative
            if relative not in included or file.is_symlink() or not source.is_file() or not filecmp.cmp(
                    source, file, shallow=False):
                return False
    return True


def survey(cwd, min_age, with_ignored=False):
    """Each worktree but the main checkout, with its state and the reason it stays, if it stays."""
    entries = worktrees(cwd)
    main = entries[0]
    refs = bases(cwd, main)
    here = toplevel(cwd)
    found = []
    for entry in entries[1:]:
        path = entry['path']
        # Only an entry that git itself marks prunable goes; a folder on a disk that is not there now stays.
        if entry['prunable']:
            entry.update(state='missing', stays='its folder is gone; git worktree prune removes its entry')
            found.append(entry)
            continue
        if not path.is_dir():
            entry.update(state='not found', stays='git does not mark it prunable')
            found.append(entry)
            continue
        # Read the age first. --no-optional-locks keeps git status from writing the index, which would make it young.
        hours = (time.time() - last_active(path)) / 3600
        status = git('--no-optional-locks', 'status', '--porcelain', '--untracked-files=all', cwd=path)
        dirty = bool(status.stdout.strip())
        entries_ignored = ignored_entries(path)
        entry.update(hours=hours, ignored=ignored_tops(entries_ignored), state='dirty' if dirty else 'clean')
        # The cheap checks first; the merge check runs only for a worktree that could go.
        if entry['locked']:
            entry['stays'] = 'it is locked'
        elif path == here:
            entry['stays'] = 'you are in it'
        elif dirty:
            entry['stays'] = 'it has changes or new files'
        elif not refs:
            entry['stays'] = 'found no base branch to check it against'
        elif hours < min_age:
            entry['stays'] = f'it changed {hours:.1f} hours ago, under {min_age:g}'
        elif not merged(entry['head'], refs, cwd):
            entry['state'] += ', not merged'
            entry['stays'] = 'its commits are not in ' + ' or '.join(r.split('/', 2)[2] for r in refs)
        elif not entry['branch'] and not ancestor(entry['head'], refs, cwd):
            entry['state'] += ', merged'
            entry['stays'] = 'its commits are on no branch; git branch NAME keeps them'
        elif not with_ignored and not setup_only(path, main['path'], entries_ignored):
            entry['state'] += ', merged'
            entry['stays'] = ('it has ignored files that setup did not put there and .worktreedisposable does not name; '
                              '--with-ignored removes them too')
        else:
            entry['state'] += ', merged'
            entry['stays'] = None
        found.append(entry)
    return main, found


def label(entry):
    return entry['branch'] or f'detached at {entry["head"][:9]}'


def show(cwd, report=False, min_age=2.0, with_ignored=False):
    main, found = survey(cwd, min_age, with_ignored)
    ready = [entry for entry in found if entry['stays'] is None]
    if report:
        if ready:
            names = ', '.join(''.join(c if c.isprintable() else '?' for c in str(entry['path'])) for entry in ready)
            say(f'{len(ready)} Git worktree(s) are clean, merged and idle: {names}. '
                'just worktrees lists them, and just worktrees-prune removes them.')
        return
    say(f'main checkout  {main["path"]}  ({label(main)})')
    for entry in found:
        why = 'ready to prune' if entry['stays'] is None else f'stays: {entry["stays"]}'
        say(f'worktree  {entry["path"]}  ({label(entry)})  {entry["state"]}  {why}')
        if entry.get('ignored'):
            say(f'    ignored files, which a removal deletes: {", ".join(entry["ignored"])}')
    if not found:
        say('No other worktree.')


def prune(cwd, dry_run=False, min_age=2.0, with_ignored=False):
    main, found = survey(cwd, min_age, with_ignored)
    if any(entry['state'] == 'missing' for entry in found) and not dry_run:
        git('worktree', 'prune', cwd=cwd)
        say('Removed the entries of the worktrees whose folders are gone.')
    removed = 0
    for entry in found:
        if entry['state'] in ('missing', 'not found'):
            if entry['state'] == 'not found':
                say(f'Kept {entry["path"]}: {entry["stays"]}.')
            continue
        if entry['stays']:
            say(f'Kept {entry["path"]} ({label(entry)}): {entry["stays"]}.')
            continue
        going = f' Its ignored files go too: {", ".join(entry["ignored"])}.' if entry['ignored'] else ''
        if dry_run:
            say(f'Would remove {entry["path"]} ({label(entry)}).{going}')
            continue
        done = git('worktree', 'remove', str(entry['path']), cwd=main['path'], check=False)
        if done.returncode != 0:
            say(f'Kept {entry["path"]}: {done.stderr.strip()}')
            continue
        removed += 1
        kept = ' Its branch stays; git branch -d deletes a merged branch.' if entry['branch'] else ''
        say(f'Removed {entry["path"]} ({label(entry)}).{going}{kept}')
    shelf = main['path'].parent / f'{main["path"].name}.worktrees'
    if not dry_run and shelf.is_dir() and not any(shelf.iterdir()):
        shelf.rmdir()
    if not dry_run:
        say(f'Removed {removed} worktree(s).')


def number(text):
    try:
        value = float(text)
    except ValueError:
        value = -1
    if not math.isfinite(value) or value < 0:
        raise WorktreeError(f'--min-age takes a number of hours, not {text}')
    return value


def main(argv):
    cwd = Path.cwd()
    command, args = (argv[0], argv[1:]) if argv else ('help', [])
    flags, words, min_age = set(), [], 2.0
    args = iter(args)
    for arg in args:
        if arg == '--min-age':
            min_age = number(next(args, ''))
            flags.add(arg)
        elif arg.startswith('--'):
            flags.add(arg)
        else:
            words.append(arg)
    allowed = {'new': {'--no-setup'}, 'list': {'--report', '--min-age', '--with-ignored'},
               'prune': {'--dry-run', '--min-age', '--with-ignored'}}.get(command, set())
    if flags - allowed:
        raise WorktreeError(f'{command} takes no {", ".join(sorted(flags - allowed))}')
    if command == 'mode' and not words:
        say(mode(toplevel(cwd)))
    elif command == 'new' and 1 <= len(words) <= 2:
        new(cwd, *words, setup='--no-setup' not in flags)
    elif command == 'sync' and not words:
        sync(toplevel(cwd), worktrees(cwd)[0]['path'])
    elif command == 'list' and not words:
        show(cwd, report='--report' in flags, min_age=min_age, with_ignored='--with-ignored' in flags)
    elif command == 'prune' and not words:
        prune(cwd, dry_run='--dry-run' in flags, min_age=min_age, with_ignored='--with-ignored' in flags)
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except WorktreeError as error:
        print(f'worktree: {error}', file=sys.stderr)
        sys.exit(1)
