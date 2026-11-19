#!/usr/bin/env python3
"""Make the next release tag vX.Y.Z on HEAD, by semantic versioning, push it, and check it on the remote.

Run it as `just release`, on a clean checkout of the integration branch, after the post-merge CI passed. It uses the
standard library only, and Python 3.9 or later.

The last tag is the newest tag vX.Y.Z that is an ancestor of HEAD. The script reads the conventional commit messages
since that tag, and skips the merge commits:

- A `!` after the type, as in `feat!: ...`, or a line `BREAKING CHANGE:` in the body, raises MAJOR. Below 1.0.0 it
  raises MINOR.
- `feat` raises MINOR. `fix`, `perf` and `refactor` raise PATCH.
- `docs`, `test`, `ci`, `chore` and `style` give no release.
- Any other type, and a message that is not a conventional commit, raises PATCH.
- A conventional subject in a bullet line of the body, such as `* feat!: drop the flag`, counts too. A squash commit
  of GitHub lists the commits of its PR that way. The bullet counts only when its type is feat, fix, perf, refactor,
  docs, test, chore, ci, build, style or revert, in lower case. A labelled bullet such as `- Removed: the old copies`
  is not a commit, and asks for no bump.

With no tag yet, the next tag is v0.1.0.

A language profile can give the version of its manifest. The script runs `just <profile>::version` for each name in
the key `profiles` of `.agents/stack.json`. The recipe prints X.Y.Z, or nothing when the manifest has no version, and
exits 2 when it cannot read the manifest. A profile without the recipe gives no version. When a profile gives a
version, the tag is v<version>, and the script makes it only when that tag does not exist yet. The script fails when
two profiles give different versions, when the version is lower than the last tag, and when it is lower than the bump
that the commits ask for. A version higher than the commits ask for is allowed. With no tag yet, the tag is the
version.

`--check` is the step release-check of `just check`. It reads no remote and needs no network. It fails on the errors
of the version only: profiles that disagree, and a version lower than the last tag or than the bump of the commits.
In a shallow checkout, a checkout with no release tag, or a repository with no commit, it says so and passes.

`--dry-run` prints the next tag and the reason, and changes nothing. Without it, the script makes an annotated tag on
HEAD, pushes it, and checks with `git ls-remote` that the remote tag points at HEAD. It never moves or deletes a tag.
When there is nothing to tag, it prints "no release" and exits 0. A tag at or above the next number on a later
commit also gives no release: a later commit was released first. A failure exits 1, also for a shallow checkout and
for a remote tag that this checkout lacks or has on another commit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import List, Optional, Tuple

Version = Tuple[int, int, int]

TAG = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
PLAIN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SUBJECT = re.compile(r"^(?P<type>[A-Za-z]+)(\([^()]*\))?(?P<bang>!)?: \S")
BREAKING = re.compile(r"^[ \t]*(?:[*-][ \t]+)?BREAKING[ -]CHANGE:", re.MULTILINE)
# A line of the body such as "* feat!: drop the flag", as GitHub lists the commits of a PR in a squash commit. Only a
# known type in lower case counts, so a labelled bullet such as "- Removed: the old copies" asks for no bump.
BULLET_TYPES = ("feat", "fix", "perf", "refactor", "docs", "test", "chore", "ci", "build", "style", "revert")
BULLET = re.compile(r"^[ \t]*[*-][ \t]+(?P<subject>(?:%s)(?:\([^()\n]*\))?!?: \S.*)$" % "|".join(BULLET_TYPES),
                    re.MULTILINE)
NO_RELEASE = {"docs", "test", "ci", "chore", "style"}
PATCH_TYPES = {"fix", "perf", "refactor"}
LEVELS = ("none", "patch", "minor", "major")
FIRST: Version = (0, 1, 0)
STACK = ".agents/stack.json"


class ReleaseError(Exception):
    """A reason to stop with exit 1."""


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        raise ReleaseError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def tag_name(version: Version) -> str:
    return "v%d.%d.%d" % version


def parse_tag(name: str) -> Optional[Version]:
    match = TAG.match(name)
    return None if match is None else (int(match[1]), int(match[2]), int(match[3]))


def last_tag(root: Path) -> Optional[Version]:
    """The newest tag vX.Y.Z that is an ancestor of HEAD, or None."""
    versions = [parse_tag(name) for name in git(root, "tag", "--merged", "HEAD", "--list", "v*").split()]
    found = [version for version in versions if version is not None]
    return max(found) if found else None


def subject_level(subject: str) -> Optional[str]:
    """The bump of a conventional subject, or None when the subject is not a conventional commit."""
    match = SUBJECT.match(subject.strip())
    if match is None:
        return None
    if match["bang"]:
        return "major"
    kind = match["type"].lower()
    if kind == "feat":
        return "minor"
    if kind in NO_RELEASE:
        return "none"
    return "patch"


def commit_level(message: str) -> str:
    """The bump that one commit message asks for: none, patch, minor or major. A conventional subject in a bullet
    line of the body counts too, since a squash commit lists the commits of its PR that way."""
    if BREAKING.search(message):
        return "major"
    subject, _, body = message.partition("\n")
    levels = [subject_level(subject) or "patch"]
    levels += [level for level in (subject_level(m["subject"]) for m in BULLET.finditer(body)) if level]
    return max(levels, key=LEVELS.index)


def commits_since(root: Path, since: Version) -> List[Tuple[str, str]]:
    """The hash and the message of each commit since the tag, without the merge commits."""
    text = git(root, "log", "--no-merges", "--format=%H%x1f%B%x1e", f"{tag_name(since)}..HEAD")
    commits = []
    for entry in text.split("\x1e"):
        entry = entry.strip("\n")
        if entry:
            sha, _, message = entry.partition("\x1f")
            commits.append((sha, message))
    return commits


def bump(version: Version, level: str) -> Version:
    major, minor, patch = version
    if level == "major" and major == 0:
        level = "minor"
    if level == "major":
        return (major + 1, 0, 0)
    if level == "minor":
        return (major, minor + 1, 0)
    if level == "patch":
        return (major, minor, patch + 1)
    return version


def profile_names(root: Path) -> List[str]:
    path = root / STACK
    if not path.is_file():
        return []
    try:
        stack = json.loads(path.read_text())
    except ValueError as error:
        raise ReleaseError(f"{STACK} is not JSON: {error}") from error
    names = stack.get("profiles") if isinstance(stack, dict) else None
    if not isinstance(names, list):
        return []
    # The same names as commit_gate.py takes: a name with a / or . or .. names no folder of .agents/just/.
    return [name for name in names if isinstance(name, str) and name not in ("", ".", "..")
            and all(c.isalnum() or c in "-_." for c in name)]


def profile_versions(root: Path) -> List[Tuple[str, Version]]:
    """The version that each profile gives, from its recipe <profile>::version."""
    names = profile_names(root)
    if not names:
        return []
    summary = subprocess.run(["just", "--summary"], cwd=root, capture_output=True, text=True)
    if summary.returncode != 0:
        raise ReleaseError(f"just --summary failed: {summary.stderr.strip()}")
    recipes = set(summary.stdout.split())
    versions = []
    for name in names:
        recipe = f"{name}::version"
        if recipe not in recipes:
            continue
        result = subprocess.run(["just", recipe], cwd=root, capture_output=True, text=True)
        if result.returncode == 2:
            raise ReleaseError(f"just {recipe} cannot read the manifest: {result.stderr.strip()}")
        if result.returncode != 0:
            raise ReleaseError(f"just {recipe} failed with exit {result.returncode}: {result.stderr.strip()}")
        text = result.stdout.strip()
        if not text:
            continue
        match = PLAIN.match(text)
        if match is None:
            raise ReleaseError(f"just {recipe} printed {text!r}, which is not a version X.Y.Z")
        versions.append((name, (int(match[1]), int(match[2]), int(match[3]))))
    return versions


def manifest_version(root: Path) -> Optional[Tuple[str, Version]]:
    versions = profile_versions(root)
    if not versions:
        return None
    if len({version for _, version in versions}) > 1:
        given = ", ".join(f"{name} gives {'%d.%d.%d' % version}" for name, version in versions)
        raise ReleaseError(f"the profiles give different versions: {given}. Make the manifests agree")
    return versions[0]


def tag_commit(root: Path, name: str) -> Optional[str]:
    """The commit of a local tag, or None when the tag does not exist."""
    result = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{name}^{{commit}}"], cwd=root,
                            capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def check_remote_tags(root: Path, remote: str) -> None:
    """Fail when the remote has a release tag that the checkout lacks, since the next number would then be wrong."""
    if remote not in git(root, "remote").split():
        return
    result = subprocess.run(["git", "ls-remote", "--tags", remote], cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        raise ReleaseError(f"git ls-remote --tags {remote} failed: {result.stderr.strip()}")
    remote_commits = {}
    for line in result.stdout.splitlines():
        sha, _, ref = line.partition("\t")
        name = ref[len("refs/tags/"):]
        peeled = name.endswith("^{}")
        name = name[:-3] if peeled else name
        if parse_tag(name) is not None and (peeled or name not in remote_commits):
            remote_commits[name] = sha
    missing = sorted(name for name in remote_commits if tag_commit(root, name) is None)
    if missing:
        raise ReleaseError(f"{remote} has the tags {', '.join(missing)}, which this checkout lacks. Run "
                           f"git fetch --tags {remote}, then run the release again")
    differ = sorted(name for name, sha in remote_commits.items() if tag_commit(root, name) != sha)
    if differ:
        raise ReleaseError(f"the tags {', '.join(differ)} point at other commits on {remote} than here. A pushed tag "
                           "never moves, so delete the local tags and fetch them again")


def is_ancestor(root: Path, older: str, newer: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=root,
                          capture_output=True).returncode == 0


def newer_release(root: Path, version: Version, head: str) -> Optional[str]:
    """A tag at or above VERSION on a commit after HEAD, or None. Such a tag means a later commit was released first,
    for example when the CI of an older push finishes last, so this commit needs no tag of its own."""
    for name in git(root, "tag", "--list", "v*").split():
        found = parse_tag(name)
        if found is not None and found >= version:
            commit = tag_commit(root, name)
            if commit and commit != head and is_ancestor(root, head, commit):
                return name
    return None


def plan(root: Path) -> Tuple[Optional[Version], str]:
    """The next tag, or None for no release, and the reason."""
    last = last_tag(root)
    manifest = manifest_version(root)
    if last is None:
        if manifest is not None:
            return manifest[1], f"no tag yet, and the profile {manifest[0]} gives the version"
        return FIRST, "no tag yet"
    commits = commits_since(root, last)
    level = max((commit_level(message) for _, message in commits), key=LEVELS.index, default="none")
    asked = bump(last, level)
    since = f"{len(commits)} commit(s) since {tag_name(last)} ask for {level}"
    if manifest is None:
        if level == "none":
            return None, since
        return asked, since
    profile, version = manifest
    shown = "%d.%d.%d" % version
    if version < last:
        raise ReleaseError(f"the profile {profile} gives {shown}, which is lower than the last tag {tag_name(last)}")
    if version < asked:
        raise ReleaseError(f"{since}, so the version must be at least {'%d.%d.%d' % asked}, but the profile "
                           f"{profile} gives {shown}. Raise the version of the manifest in a pull request")
    if version == last:
        return None, f"{since}, and the profile {profile} gives {shown}, which is tagged"
    return version, f"{since}, and the profile {profile} gives {shown}"


def release(root: Path, remote: str, dry_run: bool) -> str:
    if git(root, "rev-parse", "--is-shallow-repository").strip() == "true":
        raise ReleaseError("the checkout is shallow, so the last tag and the commits since it are unknown. Fetch the "
                           "whole history, for example with fetch-depth: 0 in actions/checkout")
    check_remote_tags(root, remote)
    version, reason = plan(root)
    if version is None:
        return f"no release: {reason}"
    name = tag_name(version)
    head = git(root, "rev-parse", "HEAD").strip()
    newer = newer_release(root, version, head)
    if newer is not None:
        return f"no release: {newer} is on a later commit, so a later release has this commit"
    existing = tag_commit(root, name)
    if existing is not None:
        if existing == head:
            return f"no release: {name} is already on HEAD"
        raise ReleaseError(f"{name} already exists on {existing[:12]}, which is not HEAD. A pushed tag never moves")
    if dry_run:
        return f"next tag: {name} ({reason})"
    git(root, "tag", "-a", name, "-m", name, head)
    git(root, "push", remote, f"refs/tags/{name}:refs/tags/{name}")
    pushed = git(root, "ls-remote", remote, f"refs/tags/{name}^{{}}").split()
    if not pushed or pushed[0] != head:
        raise ReleaseError(f"{remote} does not show {name} on {head[:12]} after the push")
    return f"tagged {name} on {head[:12]} and pushed it to {remote} ({reason})"


def check(root: Path) -> str:
    """The step release-check: the plan without the network and without the remote. It fails on the errors of the
    version only, which a commit or a pull request can fix: profiles that disagree, and a version lower than the last
    tag or than the bump that the commits ask for. A shallow checkout has no last tag to compare with, so it passes."""
    if subprocess.run(["git", "rev-parse", "--verify", "--quiet", "HEAD"], cwd=root, capture_output=True).returncode:
        return "release-check: no commit yet, so there is nothing to check"
    if git(root, "rev-parse", "--is-shallow-repository").strip() == "true":
        return ("release-check: the checkout is shallow, so the tags and the commits since the last tag are unknown. "
                "Passed without a check. Fetch the whole history with its tags to check the version")
    manifest_version(root)  # profiles that disagree fail with or without a tag
    if not git(root, "tag", "--list", "v*").split():
        return ("release-check: no release tag in this checkout, so there is no version to compare with. Passed. "
                "If the remote has tags, fetch them with git fetch --tags to check the version")
    version, reason = plan(root)
    if version is None:
        return f"release-check: no release ({reason})"
    return f"release-check: the next tag is {tag_name(version)} ({reason})"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Make the next release tag vX.Y.Z on HEAD, push it and check it.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="print the next tag and the reason, and change nothing")
    mode.add_argument("--check", action="store_true",
                      help="the step release-check: check the version against the tags, offline, and change nothing")
    parser.add_argument("--remote", default="origin", help="the remote to push the tag to (default origin)")
    args = parser.parse_args(argv)
    try:
        root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
        print(check(root) if args.check else release(root, args.remote, args.dry_run))
    except ReleaseError as error:
        print(f"release: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"release: cannot run a program, such as git or just: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
