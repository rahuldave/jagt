# Installed by jnterfaces, and kept up to date by just install. The Justfile imports it: import? '.agents/install.just'
# The machine needs just and uv only. The packages are Git clones in $SKILL_PACKAGES_DIR, and a missing clone is cloned
# from GitHub. JNTERFACES_DIR names one jnterfaces clone; without SKILL_PACKAGES_DIR, the packages are next to it. With
# neither, the folder is ~/.local/share/skill-packages.

# The recipes of the profiles and roles: just install writes .agents/just/index.just, and this line imports it
import? 'just/index.just'

# copier makes files from a template, and copier update brings in a later version of the template and keeps your edits.
# uv runs it, so every recipe can use it with no install: {{jn_copier}} copy TEMPLATE FOLDER. The jn_ prefix keeps the
# name apart from the variables of the project.
jn_copier := "uvx --from 'copier==9.*' copier"

# Install roles, tools or profiles, and save them in .agents/stack.json: just install lint tasker. Alone, install what is saved. just install --help lists the rest
[positional-arguments]
install *args:
    #!/usr/bin/env sh
    set -eu
    dir="${JNTERFACES_DIR:-${SKILL_PACKAGES_DIR:-$HOME/.local/share/skill-packages}/jnterfaces}"
    if [ ! -f "$dir/scripts/install_stack.py" ]; then
        mkdir -p "$(dirname "$dir")"
        git clone --quiet https://github.com/rahuldave/jnterfaces "$dir"
    fi
    case " $* " in *" --update "*) git -C "$dir" pull --ff-only --quiet ;; esac
    # The command as the user typed it, for .agents/stack-log.jsonl and the comments of the blocks in the line files.
    JNTERFACES_COMMAND="${JNTERFACES_COMMAND:-just install${*:+ $*}}"
    export JNTERFACES_COMMAND
    exec uv run --quiet --script "$dir/scripts/install_stack.py" --target "{{justfile_directory()}}" "$@"

# Take roles or tools out, and save that: just uninstall reporter lint
[positional-arguments]
uninstall +names:
    #!/usr/bin/env sh
    set -eu
    list=""
    for name in "$@"; do list="$list${list:+,}$name"; done
    JNTERFACES_COMMAND="just uninstall $*"
    export JNTERFACES_COMMAND
    exec just --justfile "{{justfile()}}" install --without "$list"
