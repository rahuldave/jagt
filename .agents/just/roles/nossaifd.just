# The recipe of the prose role: the writing checker of nossaifd. just install imports this file in a project that
# jnterfaces started. It fills the step prose-check of just check. The name prose stays free for the agentic
# target just prose of the tasker role.
# The index of jnterfaces sets jlog as the shell, so this file sets no shell. Its last line records the step for
# jlog pass, and runs only when the check passed. That line fails without the shell jlog, so a project without the
# index of jnterfaces copies the recipe of the README of nossaifd instead of this file.

# The second line runs the recipe api-prose-check of the project, when the project has one. The api tool of the
# python profile, jnprofile-python, gives that recipe: it checks the API page of each module changed since HEAD. From
# jnprofile-python #17 on, it also takes --base REF, and in CI or with --base it compares with the base that
# base_commit of prose_gate.py gives, as check-changed does. The line passes --base REF and --base=REF on, each
# argument whole, and drops -v, so that an api-prose-check from before #17, which takes no argument, still runs with
# -v. With --base, such an older recipe fails, as just finds no recipe named --base. With names of pages or --, the
# line skips the recipe and says so, because it takes no page. A failure of api-prose-check, or of just --summary,
# fails the recipe before the step line.

# Check the pages that changed since HEAD against the writing guide, each with its checker. In CI, or with --base REF, also the pages since a base. Then the API pages of the modules changed, when the project has api-prose-check. With names of pages, check those pages only. -v also shows the soft notes
[positional-arguments]
prose-check *args:
    uv run --no-project --quiet python .agents/skills/nossaifd/scripts/prose_gate.py check-changed "$@"
    recipes="$(just --justfile {{quote(justfile())}} --summary)" && if printf '%s\n' $recipes | grep -qx api-prose-check; then b=; for a in "$@"; do shift; if [ -n "$b" ]; then b=; set -- "$@" "$a"; else case "$a" in -v) ;; --base) b=1; set -- "$@" "$a" ;; --base=*) set -- "$@" "$a" ;; *) echo "prose-check: no API pages with names of pages or --"; exit 0 ;; esac; fi; done; just --justfile {{quote(justfile())}} api-prose-check "$@"; fi
    jlog step prose-check
