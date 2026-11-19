"""The rule of the API pages of the rust profile: is_api(path) tells the commit gate whether a file feeds them.

The commit gate of agent_gest_git_skills loads this file from the parent commit and calls is_api on each changed path.
A change to such a file, such as a doc comment of a public function, then needs a record of the docs and of the prose.

The rule is the rule of api-check, in steps.py and smalldocs, which runs rustdoc on each crate:

- With the key api in docs/_smalldocs.yml and a section with language: rust, each such section names a crate by its
  manifest, a Cargo.toml from docs/. With no manifest, the crate is the Cargo.toml of root, which smalldocs reads as a
  folder from docs/.
- Without the key api, or with no Rust section in it, the crates are the folders with a Cargo.toml, as cargo metadata
  finds the packages of the workspace.
- rustdoc reads the files of the library of a crate: src/lib.rs and the modules under src/. A crate with only a binary
  has no library, so smalldocs documents the binary: src/main.rs and the modules under src/. The binaries in src/bin/,
  the tests, the examples, the benches and build.rs are outside the pages. A crate with neither file has its binaries in
  src/bin/, and smalldocs documents one of them, so each file under src/ counts. A library at another path, with path in
  [lib] of Cargo.toml, does not count: the rule reads no TOML. A file of the tools or of .agents/generated.txt does not
  count.
- Only a Rust file counts.

is_api is False for each path in a project without the api tool or without the docs role, as .agents/stack.json
records them. When the rule cannot read the api settings, it is True for each Rust file outside the folders of the
tools and .agents/generated.txt, as the rules of the python and typescript profiles, so the gate stays on.

The file stands alone: it needs Python 3.9 or later and its standard library only, and no YAML library, so it reads
the key api with a small reader of its own, the reader of the python profile. It writes nothing. Its paths are
relative to the current folder, the top of the repository, which is also the top of the project.
"""
import json
import os
import re

STACK = '.agents/stack.json'
DOCS_CONFIG = 'docs/_smalldocs.yml'
GENERATED = '.agents/generated.txt'
# The folders of the agents and the tools.
TOOL_FOLDERS = ('.agents/', '.claude/', '.codex/')
# The files that make smalldocs read docs/ as the root, as read_other of smalldocs.api has them for Rust.
ROOT_MARKS = ('Cargo.toml', 'package.json', '.git')


def is_api(path):
    """True when PATH, relative to the top of the repository, is a source file of the API pages.

    Without the api tool or the docs role, it is False. When the rule cannot read the api settings, it is True for
    each Rust file outside the folders of the tools and .agents/generated.txt, so that the gate asks for a record
    rather than let a change of the API pages through without notice. It never raises.
    """
    try:
        path = clean(path)
        if not path or not path.endswith('.rs') or not api_on():
            return False
    except Exception:  # noqa: BLE001 - a path or a record that cannot be read gives no page of the API
        return False
    try:
        return in_api(path)
    except Exception:  # noqa: BLE001 - settings that cannot be read count each Rust file, so the gate stays on
        return fail_closed(path)


def fail_closed(path):
    """is_api when the settings cannot be read: True for a Rust file outside the tools and generated.txt."""
    if path.startswith(TOOL_FOLDERS):
        return False
    try:
        return not generated(path)
    except Exception:  # noqa: BLE001 - a list that cannot be read exempts nothing
        return True


def in_api(path):
    """True when PATH is a source file of the API pages, whether or not the project has the api tool. steps.py takes
    the changed files of api-prose-check by it. It raises on api settings that it cannot read: a form of YAML out of
    its scope, an empty key api, a path out of the repository, or a manifest that is no file."""
    path = clean(path)
    if not path or not path.endswith('.rs') or excluded(path):
        return False
    text = read(DOCS_CONFIG)
    if text is not None and re.search(r'^api\s*:', text, re.MULTILINE):
        sections = api_sections(text)
        if not sections:
            raise ValueError('the key api is empty')
        crates = section_crates(sections)
        # As api_settings of steps.py: settings with no Rust section leave the crates of the workspace.
        if crates:
            return any(in_crate(path, crate) for crate in crates)
    crate = crate_of(path)
    return crate is not None and in_crate(path, crate)


def clean(path):
    """PATH as a plain relative path with /, or '' for a path out of the repository."""
    path = str(path).replace('\\', '/')
    while path.startswith('./'):
        path = path[2:]
    parts = [part for part in path.split('/') if part not in ('', '.')]
    if path.startswith('/') or '..' in parts:
        return ''
    return '/'.join(parts)


def read(name):
    """The text of the file NAME, or None when there is none."""
    try:
        with open(name, encoding='utf-8') as file:
            return file.read()
    except (OSError, UnicodeDecodeError):
        return None


def api_on():
    """True when .agents/stack.json records the api tool of the rust profile and the docs role."""
    data = json.loads(read(STACK) or '{}')
    tools = data.get('tools') or []
    choices = data.get('choices') or {}
    return isinstance(tools, list) and 'rust:api' in tools and isinstance(choices, dict) and choices.get('docs') is True


def glob_regex(pattern):
    """A glob as smalldocs reads it: * and ? stop at /, ** crosses folders, and **/ is any folders or none."""
    out, i = '', 0
    while i < len(pattern):
        if pattern.startswith('**/', i):
            out, i = out + '(?:.*/)?', i + 3
        elif pattern.startswith('**', i):
            out, i = out + '.*', i + 2
        elif pattern[i] == '*':
            out, i = out + '[^/]*', i + 1
        elif pattern[i] == '?':
            out, i = out + '[^/]', i + 1
        elif pattern[i] == '[' and pattern.find(']', i + 1) > i:
            end = pattern.find(']', i + 1)
            body = pattern[i + 1:end]
            out, i = out + '[' + ('^' + body[1:] if body.startswith('!') else body) + ']', end + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + r'\Z')


# The small reader of the key api: a mapping, or a list of mappings, of plain values and lists.

def scalar(text):
    """A plain value of YAML: a quoted or a bare string, with no comment."""
    text = text.strip()
    if text[:1] in ('"', "'"):
        end = text.find(text[0], 1)
        if end < 0:
            raise ValueError(f'a quote is not closed: {text}')
        return text[1:end]
    return re.sub(r'\s+#.*$', '', text).strip()


def value(text):
    """A value on the line of its key: a flow list [a, b], or a plain value."""
    text = re.sub(r'\s+#.*$', '', text.strip()) if text.strip()[:1] not in ('"', "'") else text.strip()
    if text.startswith('['):
        if not text.endswith(']'):
            raise ValueError(f'a list is not closed: {text}')
        return [scalar(item) for item in text[1:-1].split(',') if item.strip()]
    return scalar(text)


def mapping(lines):
    """The mapping of LINES, (indent, text) pairs of one level: key: value, or key: and a block list under it."""
    out, i = {}, 0
    while i < len(lines):
        indent, text = lines[i]
        found = re.match(r'([A-Za-z_][\w-]*)\s*:(?:\s+(.*))?$', text)
        if not found:
            raise ValueError(f'not a key: {text}')
        key, rest = found.group(1), (found.group(2) or '').strip()
        i += 1
        if rest and not rest.startswith('#'):
            out[key] = value(rest)
            continue
        items = []
        while i < len(lines) and lines[i][0] >= indent and lines[i][1].startswith('- '):
            items.append(scalar(lines[i][1][2:]))
            i += 1
        while i < len(lines) and lines[i][0] > indent:
            i += 1  # a deeper mapping, which the rule does not read
        out[key] = items
    return out


def api_sections(text):
    """The sections of the key api of the config TEXT: one mapping, or each mapping of a list."""
    lines = text.splitlines()
    start = next(n for n, line in enumerate(lines) if re.match(r'api\s*:', line))
    rest = re.sub(r'^api\s*:', '', lines[start]).strip()
    if rest and not rest.startswith('#'):
        raise ValueError('the rule reads the key api only as a block')
    block = []
    for line in lines[start + 1:]:
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip(' '))
        # YAML lets the items of a list under a key start at the column of the key: api: then - packages: [pkg].
        if indent == 0 and not (line.startswith('- ') and (not block or block[0] == (0, block[0][1]))):
            break
        block.append((indent, line.strip()))
    if not block:
        return []
    if not block[0][1].startswith('- '):
        return [mapping(block)]
    sections, current = [], None
    for indent, line in block:
        if line.startswith('- ') and indent == block[0][0]:
            current = [(indent + 2, line[2:].strip())]
            sections.append(current)
        else:
            current.append((indent, line))
    return [mapping(section) for section in sections]


def inside(path):
    """PATH, a path from docs/, as a folder relative to the top: '' for the top. It raises for a path out of the
    repository."""
    found = os.path.normpath(os.path.join('docs', path))
    if found == '.':
        return ''
    if found.startswith('..') or os.path.isabs(found):
        raise ValueError('a path of the api settings is out of the repository')
    return found.replace(os.sep, '/')


def section_crates(sections):
    """The folders of the crates of the Rust sections of SECTIONS, relative to the top. A manifest names its crate,
    from docs/. Without one, the crate is the Cargo.toml of root, which is docs/ when docs/ holds a Cargo.toml, a
    package.json or a .git, and the top of the project otherwise."""
    crates = []
    for section in sections:
        if str(section.get('language', 'python')) != 'rust':
            continue
        manifest = section.get('manifest')
        if manifest:
            if not os.path.isfile(inside(str(manifest))):
                raise ValueError(f'the manifest {manifest} of the api settings is no file')
            crates.append(os.path.dirname(inside(str(manifest))))
            continue
        at_docs = any(os.path.exists(os.path.join('docs', mark)) for mark in ROOT_MARKS)
        crates.append(inside(str(section.get('root', '.' if at_docs else '..'))))
    return crates


def crate_of(path):
    """The folder of the crate that holds PATH, the nearest folder with a Cargo.toml, relative to the top: '' for the
    top. None when no folder above PATH has one."""
    folder = os.path.dirname(path)
    while True:
        if os.path.isfile(os.path.join(folder or '.', 'Cargo.toml')):
            return folder
        if not folder:
            return None
        folder = os.path.dirname(folder)


def in_crate(path, crate):
    """True when PATH is a file that rustdoc reads for the pages of the crate in the folder CRATE: under its src/,
    not in src/bin/, and of the library, or of the binary of a crate with no library. The nearest Cargo.toml above
    PATH must be that of CRATE, so a file of another crate inside it does not count."""
    prefix = crate + '/' if crate else ''
    if not path.startswith(prefix) or crate_of(path) != crate:
        return False
    parts = path[len(prefix):].split('/')
    if len(parts) < 2 or parts[0] != 'src':
        return False
    source = os.path.join(crate or '.', 'src')
    if os.path.isfile(os.path.join(source, 'lib.rs')):
        return parts[1] != 'bin' and parts[1:] != ['main.rs']
    if os.path.isfile(os.path.join(source, 'main.rs')):
        return parts[1] != 'bin'
    # With no src/lib.rs and no src/main.rs, smalldocs documents a binary of src/bin/: the one named after the
    # package, else the first. The rule reads no TOML, so every file under src/ counts. A Cargo.toml with no [package]
    # table is a workspace with no package of its own, which has no pages.
    text = read(os.path.join(crate or '.', 'Cargo.toml')) or ''
    return re.search(r'^[ \t]*\[package\][ \t]*(#.*)?$', text, re.MULTILINE) is not None


def generated(path):
    """True when a pattern of .agents/generated.txt names PATH, as a git pathspec with the magic word glob."""
    for line in (read(GENERATED) or '').splitlines():
        pattern = line.strip().lstrip('/')
        if not pattern or pattern.startswith('#'):
            continue
        if glob_regex(pattern).match(path) or path.startswith(pattern.rstrip('/') + '/'):
            return True
    return False


def excluded(path):
    """True when PATH is a file of the tools or a file of .agents/generated.txt."""
    return path.startswith(TOOL_FOLDERS) or generated(path)
