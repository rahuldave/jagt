# The recipes of the tasker role: Git worktrees for the g* skills. just install imports this file in a project that
# jnterfaces started. The script is in the gtw skill: .agents/skills/gtw/scripts/worktree.py.

jn_worktree := "uv run --no-project --quiet --no-python-downloads --python '>=3.9' python .agents/skills/gtw/scripts/worktree.py"

# Print the tasker variant: git (a branch in the main checkout) or gitwt (each task in its own worktree)
tasker-mode:
    @{{jn_worktree}} mode

# Make branch NAME from BASE (default main) in ../<repo>.worktrees/NAME, set it up, then run just setup. --no-setup skips just setup
[positional-arguments]
worktree-new NAME *args:
    @{{jn_worktree}} new "$@"

# Set up this worktree from the main checkout: copy the files of .worktreeinclude, link the paths of .worktreelink
worktree-sync:
    @{{jn_worktree}} sync

# List the worktrees: clean or dirty, merged or not, and whether each is ready to prune
[positional-arguments]
worktrees *args:
    @{{jn_worktree}} list "$@"

# Remove the worktrees that are clean, merged and idle for 2 hours, with git worktree remove and no --force. Takes --dry-run and --min-age HOURS
[positional-arguments]
worktrees-prune *args:
    @{{jn_worktree}} prune "$@"
