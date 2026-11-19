"""stack-prs: open the PRs of a stack of branches in order, from the bottom branch up.

A stack is a chain of branches, each one started from the branch below it. The PR of each branch has the branch
below it as its base, and the PR of the bottom branch has BASE. First the script checks the whole stack, and stops
with no change when:

- a branch appears twice, or is BASE
- a branch does not contain the branch below it, so the branches are not a stack in that order
- a branch has an upstream other than origin/<branch>, or origin/<branch> has commits that the branch does not
- an open PR of a branch has another base, so the stack and GitHub disagree

Then, for each branch, from the bottom up, it:

1. Pushes the branch to origin with `git push -u`, when it has no upstream or is ahead of it. It never forces a
   push.
2. Opens its PR with `gh pr create --base <branch below> --head <branch> --fill`, when it has no open PR.

With --dry-run it prints each step and changes nothing. It exits 1 when it stops, and 0 when each branch has its PR.

Usage: stack_prs.py [--dry-run] BASE BRANCH... (the bottom branch first)
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import List, Optional, Tuple


class Stop(Exception):
    pass


def run(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise Stop(f"`{' '.join(args)}` failed: {(result.stderr or result.stdout).strip()}")
    return result


def upstream(branch: str) -> Optional[str]:
    """The upstream of BRANCH, such as origin/BRANCH, or None."""
    run_ = run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", f"{branch}@{{upstream}}"], check=False)
    return run_.stdout.strip() if run_.returncode == 0 else None


def contains(lower: str, upper: str) -> bool:
    return run(["git", "merge-base", "--is-ancestor", lower, upper], check=False).returncode == 0


def open_pr(branch: str) -> Optional[dict]:
    """The open PR whose head is BRANCH, or None."""
    out = run(["gh", "pr", "list", "--head", branch, "--state", "open", "--json", "number,baseRefName,url"]).stdout
    prs = json.loads(out or "[]")
    return prs[0] if prs else None


def plan(base: str, branches: List[str]) -> List[Tuple[str, str, str, Optional[dict]]]:
    """Check the whole stack, and give for each branch its base, its push ("push", "fast-forward" or "") and its
    open PR. It stops before any change when the branches are not a stack in that order, when a branch has another
    upstream, when GitHub has a commit that the branch does not, or when a PR has another base."""
    if len(set(branches)) != len(branches) or base in branches:
        raise Stop("each branch of the stack must appear once, and not be the base")
    steps = []
    for below, branch in zip([base, *branches], branches):
        if not contains(below, branch):
            raise Stop(f"{branch} does not contain {below}, so it is not the next branch of the stack")
        up = upstream(branch)
        if up is None:
            push = "push"
        elif up != f"origin/{branch}":
            raise Stop(f"the upstream of {branch} is {up}, not origin/{branch}. Run "
                       f"`git branch --unset-upstream {branch}`, and the script pushes it")
        elif run(["git", "rev-parse", branch]).stdout == run(["git", "rev-parse", up]).stdout:
            push = ""
        elif contains(up, branch):
            push = "fast-forward"
        else:
            raise Stop(f"origin/{branch} has commits that {branch} does not. Bring them in, or push with "
                       "--force-with-lease yourself")
        pr = open_pr(branch)
        if pr is not None and pr["baseRefName"] != below:
            raise Stop(f"the PR of {branch}, {pr['url']}, has the base {pr['baseRefName']} and not {below}. Run "
                       f"`gh pr edit {pr['number']} --base {below}` when the stack is right")
        steps.append((below, branch, push, pr))
    return steps


def stack_prs(base: str, branches: List[str], dry_run: bool) -> None:
    for below, branch, push, pr in plan(base, branches):
        if push:
            print(f"stack-prs: {'would push' if dry_run else 'pushes'} {branch} to origin")
            if not dry_run:
                run(["git", "push", "-u", "origin", branch])
        if pr is None:
            print(f"stack-prs: {'would open' if dry_run else 'opens'} the PR of {branch} on {below}")
            if not dry_run:
                print(run(["gh", "pr", "create", "--base", below, "--head", branch, "--fill"]).stdout.strip())
        else:
            print(f"stack-prs: {branch} has its PR on {below}, {pr['url']}")


def main(argv: List[str]) -> int:
    dry_run = argv[:1] == ["--dry-run"]
    args = argv[1:] if dry_run else argv
    if len(args) < 2:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    try:
        stack_prs(args[0], args[1:], dry_run)
    except Stop as stop:
        print(f"stack-prs: {stop}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
