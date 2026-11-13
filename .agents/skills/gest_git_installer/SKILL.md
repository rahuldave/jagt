---
name: gest_git_installer
description: Install the Git Gest skills, hooks, hook settings and AGENTS.md starter into a repository with the jnterfaces installer, for example after npx installed the skills only. Use when the user asks to install or refresh the Gest package.
license: MIT, copyright (c) 2026 Rahul Dave. The full text is in the LICENSE file of https://github.com/rahuldave/agent_gest_git_skills
---

# Gest Git Installer

The Gest skills are the role `tasker` of the jnterfaces installer. jnterfaces
holds the only installer. It copies the skills of this package, its hook
scripts in `.claude/hooks` and `.codex/hooks`, and its hook settings. It also writes `AGENTS.md` from `AGENTS.starter.md` when the repository has
no `AGENTS.md`. It writes the rules to `.agents/instructions/tasker.md`, and
adds a line to `AGENTS.md` that points to them.

Claude Code imports the rules through `CLAUDE.md`, which imports `AGENTS.md`.
The SessionStart hook of Codex prints the rules. The hook of Claude Code
prints them only when it does not find that import.

The `g*` skills need the `just` skill of jnterfaces, and the installer always
installs it. If jnterfaces is not installed, the `install` recipe is missing
too, so use the helper of this skill below.

## Install or refresh

In a repository that has the `install` recipe of jnterfaces, run this:

```bash
just install tasker
```

Otherwise, run the helper from this skill folder. It clones jnterfaces when no
clone is there, and then it runs the same installer:

```bash
bash .agents/skills/gest_git_installer/scripts/install_gest_git_package.sh .
```

The machine needs `just`, `uv` and `git`. The helper reports the other
workflow tools that are missing, such as `gest`. A missing tool is not a reason
that the install failed.

Ask the user before you run either command. The install changes hook settings
and can write `AGENTS.md`.

## What the installer keeps

- **Edited files.** It never overwrites or removes a file that the user edited
  after an install. It stops with a conflict instead, and writes nothing.
- **Other hooks and settings.** It adds its hook commands to the existing
  settings, and it stops on a hook command that differs.
- **`AGENTS.md`.** It writes the file only when it is absent.

The source revision and a hash of each file are in
`.agents/gest-git-install.json`. `just uninstall tasker` takes the package out
again, with its hook commands. It keeps each file that the user edited.

## Clones

The packages are Git clones in `$SKILL_PACKAGES_DIR`, by default
`~/.local/share/skill-packages`. A missing clone is cloned from GitHub.
`JNTERFACES_DIR` names one jnterfaces clone, and
`AGENT_GEST_GIT_SKILLS_SOURCE` names one clone of this package.
