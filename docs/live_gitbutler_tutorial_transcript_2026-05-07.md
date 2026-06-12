# Live Git/GitButler Tutorial Transcript

Date: 2026-05-07

Run ID: `20260507T141932Z`

Owner: `rahuldave`

This is a clean rerun of the four Git/GitButler tutorial examples against live
temporary GitHub repositories. The transcript was captured while acting as both
the user and the agent. The temporary repositories were deleted at the end with
`gh repo delete --yes`.

## Step 1: Ordinary Git Branch PR

$ git init -b main
Initialized empty Git repository in /private/tmp/agent-gest-clean-live-tutorial-runs/20260507T141932Z/git/plain/.git/

$ git config user.name tutorial-agent

$ git config user.email tutorial-agent@example.invalid

$ gh repo create rahuldave/agent-gest-git-tutorial-plain --private --source=. --remote=origin --disable-issues --disable-wiki
https://github.com/rahuldave/agent-gest-git-tutorial-plain

$ cat > README.md <<'EOF'
plain tutorial base
EOF

$ git add README.md

$ git commit -m 'chore: initialize tutorial repo'
[main (root-commit) afeb8da] chore: initialize tutorial repo
 1 file changed, 1 insertion(+)
 create mode 100644 README.md

$ git push -u origin main
To github.com:rahuldave/agent-gest-git-tutorial-plain.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.

$ git checkout -b tutorial/plain
Switched to a new branch 'tutorial/plain'

$ cat > plain.txt <<'EOF'
plain branch change
EOF

$ git add plain.txt

$ git commit -m 'test: add plain branch change'
[tutorial/plain c425152] test: add plain branch change
 1 file changed, 1 insertion(+)
 create mode 100644 plain.txt

$ git push -u origin tutorial/plain
remote:
remote: Create a pull request for 'tutorial/plain' on GitHub by visiting:
remote:      https://github.com/rahuldave/agent-gest-git-tutorial-plain/pull/new/tutorial/plain
remote:
To github.com:rahuldave/agent-gest-git-tutorial-plain.git
 * [new branch]      tutorial/plain -> tutorial/plain
branch 'tutorial/plain' set up to track 'origin/tutorial/plain'.

$ gh pr create --repo rahuldave/agent-gest-git-tutorial-plain --base main --head tutorial/plain --title 'test: plain git branch flow' --body 'Tutorial plain git branch flow.'
https://github.com/rahuldave/agent-gest-git-tutorial-plain/pull/1

$ gh pr view tutorial/plain --repo rahuldave/agent-gest-git-tutorial-plain --json state,baseRefName,headRefName,title
{"baseRefName":"main","headRefName":"tutorial/plain","state":"OPEN","title":"test: plain git branch flow"}

## Step 2: Ordinary Git Multi-Commit PR

$ git init -b main
Initialized empty Git repository in /private/tmp/agent-gest-clean-live-tutorial-runs/20260507T141932Z/git/multi/.git/

$ git config user.name tutorial-agent

$ git config user.email tutorial-agent@example.invalid

$ gh repo create rahuldave/agent-gest-git-tutorial-multi --private --source=. --remote=origin --disable-issues --disable-wiki
https://github.com/rahuldave/agent-gest-git-tutorial-multi

$ cat > README.md <<'EOF'
multi tutorial base
EOF

$ git add README.md

$ git commit -m 'chore: initialize tutorial repo'
[main (root-commit) acc94c2] chore: initialize tutorial repo
 1 file changed, 1 insertion(+)
 create mode 100644 README.md

$ git push -u origin main
To github.com:rahuldave/agent-gest-git-tutorial-multi.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.

$ git checkout -b tutorial/multi
Switched to a new branch 'tutorial/multi'

$ cat > session.txt <<'EOF'
session edit one
EOF

$ git add session.txt

$ git commit -m 'test: add first session edit'
[tutorial/multi d7b2eb9] test: add first session edit
 1 file changed, 1 insertion(+)
 create mode 100644 session.txt

$ cat >> session.txt <<'EOF'
session edit two
EOF

$ git add session.txt

$ git commit -m 'test: add second session edit'
[tutorial/multi efdc896] test: add second session edit
 1 file changed, 1 insertion(+)

$ git push -u origin tutorial/multi
remote:
remote: Create a pull request for 'tutorial/multi' on GitHub by visiting:
remote:      https://github.com/rahuldave/agent-gest-git-tutorial-multi/pull/new/tutorial/multi
remote:
To github.com:rahuldave/agent-gest-git-tutorial-multi.git
 * [new branch]      tutorial/multi -> tutorial/multi
branch 'tutorial/multi' set up to track 'origin/tutorial/multi'.

$ gh pr create --repo rahuldave/agent-gest-git-tutorial-multi --base main --head tutorial/multi --title 'test: multi commit git branch flow' --body 'Tutorial multi-commit git branch flow.'
https://github.com/rahuldave/agent-gest-git-tutorial-multi/pull/1

$ gh pr view tutorial/multi --repo rahuldave/agent-gest-git-tutorial-multi --json state,baseRefName,headRefName,title,commits
{"baseRefName":"main","commits":[{"authoredDate":"2026-05-07T14:19:48Z","authors":[{"email":"tutorial-agent@example.invalid","id":"","login":"","name":"tutorial-agent"}],"committedDate":"2026-05-07T14:19:48Z","messageBody":"","messageHeadline":"test: add first session edit","oid":"d7b2eb9469732a8f5f98caddcddf2002bd835dd2"},{"authoredDate":"2026-05-07T14:19:48Z","authors":[{"email":"tutorial-agent@example.invalid","id":"","login":"","name":"tutorial-agent"}],"committedDate":"2026-05-07T14:19:48Z","messageBody":"","messageHeadline":"test: add second session edit","oid":"efdc89696fe954130d5dfc47abd31a64ecbeb556"}],"headRefName":"tutorial/multi","state":"OPEN","title":"test: multi commit git branch flow"}

## Step 3: GitButler Stacked PRs

$ git init -b main
Initialized empty Git repository in /private/tmp/agent-gest-clean-live-tutorial-runs/20260507T141932Z/git/stack/.git/

$ git config user.name tutorial-agent

$ git config user.email tutorial-agent@example.invalid

$ gh repo create rahuldave/agent-gest-git-tutorial-stack --private --source=. --remote=origin --disable-issues --disable-wiki
https://github.com/rahuldave/agent-gest-git-tutorial-stack

$ cat > README.md <<'EOF'
stack tutorial base
EOF

$ git add README.md

$ git commit -m 'chore: initialize tutorial repo'
[main (root-commit) f958c26] chore: initialize tutorial repo
 1 file changed, 1 insertion(+)
 create mode 100644 README.md

$ git push -u origin main
To github.com:rahuldave/agent-gest-git-tutorial-stack.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.

$ but setup
Setting up GitButler project...

→ Adding repository to GitButler project registry
  ✓ Repository already in project registry

→ Configuring default target branch
  ✓ Using existing push remote: origin
  ✓ No remote HEAD found, using origin/main
  ✓ Set default target to: origin/main

GitButler project setup complete!
Target branch: origin/main
Remote: origin


Setting up your project for GitButler tooling. Some things to note:

- Switching you to a special `gitbutler/workspace` branch to enable parallel branches
- Installing Git hooks to help manage commits on the workspace branch

To undo these changes and return to normal Git mode, either:

    - Directly checkout a branch (`git checkout main`)
    - Run `but teardown`

More info: https://docs.gitbutler.com/workspace-branch



 ██████▄      ▄██████    ██████╗ ██╗   ██╗████████╗
 ██▀▀▀▀██▄  ▄██▀▀▀▀██    ██╔══██╗██║   ██║╚══██╔══╝
 ██     ▀████▀     ██    ██████╔╝██║   ██║   ██║
 ██▄▄▄▄██▀  ▀██▄▄▄▄██    ██╔══██╗██║   ██║   ██║
 ██████▀      ▀██████    ██████╔╝╚██████╔╝   ██║

The command-line interface for GitButler

$ but branch new <name>                       Create a new branch
$ but status                                  View workspace status
$ but commit -m <message>                     Commit changes to current branch
$ but push                                    Push all branches
$ but teardown                                Return to normal Git mode

Learn more at https://docs.gitbutler.com/cli-overview


$ but branch new tutorial/stack-base
Initiated a background sync...
✓ Created branch tutorial/stack-base

$ cat > stack.txt <<'EOF'
stack base
EOF

$ but commit tutorial/stack-base -m 'test: add stack base'
Initiated a background sync...
✓ Created commit b3c7d3e on branch tutorial/stack-base

$ but branch new --anchor tutorial/stack-base tutorial/stack-child
Initiated a background sync...
✓ Created branch tutorial/stack-child stacked on tutorial/stack-base

$ cat >> stack.txt <<'EOF'
stack child
EOF

$ but commit tutorial/stack-child -m 'test: add stack child'
Initiated a background sync...
✓ Created commit 8cac0d1 on branch tutorial/stack-child

$ but push tutorial/stack-base

$ but push tutorial/stack-child

$ but pr new tutorial/stack-base -m ... --json
{
  "published": [
    {
      "htmlUrl": "https://github.com/rahuldave/agent-gest-git-tutorial-stack/pull/1",
      "number": 1,
      "title": "test: stack base flow",
      "body": "Tutorial GitButler stack base flow.",
      "author": {
        "id": 43227,
        "login": "rahuldave",
        "name": null,
        "email": null,
        "avatarUrl": "https://avatars.githubusercontent.com/u/43227?v=4",
        "isBot": false
      },
      "labels": [],
      "draft": false,
      "sourceBranch": "tutorial/stack-base",
      "targetBranch": "main",
      "sha": "b3c7d3eb8b402263b5e582a792d7ad3e72256047",
      "createdAt": "2026-05-07T14:20:04Z",
      "modifiedAt": "2026-05-07T14:20:04Z",
      "mergedAt": null,
      "closedAt": null,
      "repositorySshUrl": "git@github.com:rahuldave/agent-gest-git-tutorial-stack.git",
      "repositoryHttpsUrl": "https://github.com/rahuldave/agent-gest-git-tutorial-stack.git",
      "repoOwner": "rahuldave",
      "reviewers": [],
      "unitSymbol": "#",
      "lastSyncAt": "2026-05-07T10:20:06.011362"
    }
  ],
  "alreadyExisting": []
}
Observed: GitButler forge PR creation succeeded for tutorial/stack-base.

$ but pr new tutorial/stack-child --default --json
Error: Failed to create forge review for branch.

Caused by:
    0: Failed to create pull request
    1: Failed to create pull request: 422 Unprocessable Entity
Observed: GitButler forge PR creation returned GitHub 422 for the child stack PR, so the agent used gh pr create with base tutorial/stack-base.

$ gh pr create --repo rahuldave/agent-gest-git-tutorial-stack --base tutorial/stack-base --head tutorial/stack-child --title 'test: stack child flow' --body 'Tutorial GitButler stack child flow.'
https://github.com/rahuldave/agent-gest-git-tutorial-stack/pull/2

$ gh pr list --repo rahuldave/agent-gest-git-tutorial-stack --state open --json title,baseRefName,headRefName
[{"baseRefName":"tutorial/stack-base","headRefName":"tutorial/stack-child","title":"test: stack child flow"},{"baseRefName":"main","headRefName":"tutorial/stack-base","title":"test: stack base flow"}]

## Step 4: Physical Git Worktrees

$ git init -b main
Initialized empty Git repository in /private/tmp/agent-gest-clean-live-tutorial-runs/20260507T141932Z/git/worktrees/.git/

$ git config user.name tutorial-agent

$ git config user.email tutorial-agent@example.invalid

$ gh repo create rahuldave/agent-gest-git-tutorial-worktrees --private --source=. --remote=origin --disable-issues --disable-wiki
https://github.com/rahuldave/agent-gest-git-tutorial-worktrees

$ cat > README.md <<'EOF'
worktree tutorial base
EOF

$ git add README.md

$ git commit -m 'chore: initialize tutorial repo'
[main (root-commit) 48e887b] chore: initialize tutorial repo
 1 file changed, 1 insertion(+)
 create mode 100644 README.md

$ git push -u origin main
To github.com:rahuldave/agent-gest-git-tutorial-worktrees.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.

$ GEST_VCS_EXECUTION=git-worktrees git worktree add -b tutorial/worktree-a /tmp/agent-gest-clean-live-tutorial-runs/20260507T141932Z/git/worktree-a main
Preparing worktree (new branch 'tutorial/worktree-a')
HEAD is now at 48e887b chore: initialize tutorial repo

$ GEST_VCS_EXECUTION=git-worktrees git worktree add -b tutorial/worktree-b /tmp/agent-gest-clean-live-tutorial-runs/20260507T141932Z/git/worktree-b main
Preparing worktree (new branch 'tutorial/worktree-b')
HEAD is now at 48e887b chore: initialize tutorial repo

$ cat > worktree-a.txt <<'EOF'
worktree a isolated change
EOF

$ git add worktree-a.txt

$ git commit -m 'test: add worktree a change'
[tutorial/worktree-a 0c9b8b0] test: add worktree a change
 1 file changed, 1 insertion(+)
 create mode 100644 worktree-a.txt

$ git push -u origin tutorial/worktree-a
remote:
remote: Create a pull request for 'tutorial/worktree-a' on GitHub by visiting:
remote:      https://github.com/rahuldave/agent-gest-git-tutorial-worktrees/pull/new/tutorial/worktree-a
remote:
To github.com:rahuldave/agent-gest-git-tutorial-worktrees.git
 * [new branch]      tutorial/worktree-a -> tutorial/worktree-a
branch 'tutorial/worktree-a' set up to track 'origin/tutorial/worktree-a'.

$ gh pr create --repo rahuldave/agent-gest-git-tutorial-worktrees --base main --head tutorial/worktree-a --title 'test: worktree a flow' --body 'Tutorial physical worktree A flow.'
https://github.com/rahuldave/agent-gest-git-tutorial-worktrees/pull/1

$ cat > worktree-b.txt <<'EOF'
worktree b isolated change
EOF

$ git add worktree-b.txt

$ git commit -m 'test: add worktree b change'
[tutorial/worktree-b ec983a3] test: add worktree b change
 1 file changed, 1 insertion(+)
 create mode 100644 worktree-b.txt

$ git push -u origin tutorial/worktree-b
remote:
remote: Create a pull request for 'tutorial/worktree-b' on GitHub by visiting:
remote:      https://github.com/rahuldave/agent-gest-git-tutorial-worktrees/pull/new/tutorial/worktree-b
remote:
To github.com:rahuldave/agent-gest-git-tutorial-worktrees.git
 * [new branch]      tutorial/worktree-b -> tutorial/worktree-b
branch 'tutorial/worktree-b' set up to track 'origin/tutorial/worktree-b'.

$ gh pr create --repo rahuldave/agent-gest-git-tutorial-worktrees --base main --head tutorial/worktree-b --title 'test: worktree b flow' --body 'Tutorial physical worktree B flow.'
https://github.com/rahuldave/agent-gest-git-tutorial-worktrees/pull/2

$ gh pr list --repo rahuldave/agent-gest-git-tutorial-worktrees --state open --json title,baseRefName,headRefName
[{"baseRefName":"main","headRefName":"tutorial/worktree-b","title":"test: worktree b flow"},{"baseRefName":"main","headRefName":"tutorial/worktree-a","title":"test: worktree a flow"}]

$ git worktree remove /tmp/agent-gest-clean-live-tutorial-runs/20260507T141932Z/git/worktree-a

$ git worktree remove /tmp/agent-gest-clean-live-tutorial-runs/20260507T141932Z/git/worktree-b

## Cleanup

Deleted temporary repositories with `gh repo delete --yes`:

- `rahuldave/agent-gest-git-tutorial-plain`
- `rahuldave/agent-gest-git-tutorial-multi`
- `rahuldave/agent-gest-git-tutorial-stack`
- `rahuldave/agent-gest-git-tutorial-worktrees`
