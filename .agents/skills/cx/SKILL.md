---
name: cx
description: Use when a Just recipe has expensive stages that read files and write files, for example a data or model pipeline, a conversion pipeline, generated code or a C build, and you want a stage to run only when its inputs change. Also use it to review cx lines and to run cx lint.
---

# cx

`cx` runs one command line in a Just recipe only when the line is out of date.
`just` still owns the order of recipes. `cx` decides only whether one declared
line must run again.

A `cx` line declares its input files, its output files and the command:

```just
features: prepare
    cx --in data/raw.txt --in scripts/features.sh --out build/features.txt -- bash scripts/features.sh data/raw.txt build/features.txt
```

The first run runs the command. A later run checks the hashes of the inputs,
the outputs and the command. If nothing changed, `cx` prints
`up-to-date: build/features.txt` and does not run the command.

## When to use cx

Use `cx` for stages that read files and write durable files, for example:

- a data or model pipeline, such as raw data to features to model to report
- a conversion of documents, books, images, audio or data
- code or files that a generator makes from a schema
- a hand-written C or C++ build with object files and a binary

## When not to use cx

Do not use `cx` for these commands:

- tests, lint, format, type checks or checks in a browser
- `cargo build`, `go build`, `tsc` or a package manager build, because these
  tools have their own cache
- a command that writes no durable file
- a command that reads hidden inputs, for example the network, a database or an
  undeclared environment variable
- an aggregate recipe such as `check`. Use Just dependencies for order, and use
  `cx` only on single lines that make files.

## Rules for a cx line

1. Give each line at least one `--out`.
2. Declare every real input with `--in`. Include scripts, schemas, prompts,
   configuration and parameter files.
3. Make the command write only the declared outputs.
4. Put `cx` lines in linewise recipes, not in shebang or `[script]` recipes.
   `cx lint` reports an error for a `cx` line in a script recipe.
5. Add `.cx/state.json` and `.cx/tmp/` to `.gitignore`. cx writes them as
   local state. `cx graph` prints to the terminal and writes no file.
6. If the project later adds `.cx/config.toml`, keep it in version control. The
   current cx does not read it.

## How to run cx lint

Run `cx lint` from the directory of the Justfile. It reads the recipes through
`just --dump --dump-format json` and checks the shape of each `cx` line. For
example, it fails when a line has no `--out`. `cx graph` prints the files and
lines that it sees.

`cx lint` checks declarations only. It does not test behavior. If the project
maps a `cx-lint` recipe, run that recipe. Add it to the static checks of the
project when the Justfile has `cx` lines.

## How to check a cx pipeline

1. Run the build or pipeline recipe once from clean outputs.
2. Run it again, and confirm the `up-to-date` lines.
3. Change one input, and confirm that only the expected later stages run.
4. Run `cx lint`.

If `cx` is not on the PATH, ask the user before you install it. The source is
https://github.com/rahuldave/cx.

Read `references/incremental_pipelines.md` for worked examples and a review
checklist.
