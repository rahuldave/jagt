# cx Incremental Builds And Pipelines

`cx` is for incremental builds and file-artifact pipelines inside `just`
recipes. It is not a test runner.

Use `cx` when a Just recipe contains expensive stages that read explicit files
and write durable intermediate files. `just` still owns recipe order and recipe
dependencies; `cx` only decides whether one declared command line is already
fresh.

## Mental Model

A linewise Just recipe can wrap one command:

```just
build: prepare
  cx --in data/input.txt --out build/output.txt -- transform data/input.txt build/output.txt
```

On the first run, `cx` runs the command after `--`. On a later run, if the
declared inputs, declared outputs, and command identity are unchanged, `cx`
exits successfully and reports `up-to-date: build/output.txt`.

Important boundaries:

- `cx` requires at least one `--out`.
- `cx` tracks content hashes in `.cx/state.json`.
- `.cx/state.json`, `.cx/graph.json`, and `.cx/tmp/` are local state and should
  not be committed.
- Keep `.cx/config.toml` committable if the project later uses it for policy.
- Static `cx` analysis is for linewise Just recipes. Do not put `cx` calls
  inside shebang or `[script]` recipes unless the project has explicitly
  accepted opaque runtime-only behavior.
- `cx lint` validates `cx` line shape in the current Justfile; it is not a
  behavior test.

## When To Use `cx`

Good fits:

- machine-learning or AI pipelines with file stages such as raw data to
  features, features to model, model to report;
- document, book, image, audio, or data conversion pipelines with expensive
  intermediate artifacts;
- schema/code generation where generated files depend on schema files and
  generator scripts;
- hand-written C or C++ compile/link flows where object files and binaries are
  explicit outputs;
- any project-specific build pipeline where the stages are file-in/file-out and
  rerunning every stage wastes time.

Poor fits:

- tests, lint, format, typecheck, or browser verification commands;
- ordinary `cargo build`, `go build`, `tsc`, or package-manager builds that
  already own a dependency graph/cache;
- commands without durable file outputs;
- commands whose real inputs are hidden in network calls, databases,
  environment variables, or undeclared configuration;
- Just aggregate recipes such as `verify`; use Just dependencies for ordering
  and `cx` only around individual file-producing lines.

## Example 1: Artifact Pipeline

The reusable lab builds this shape:

```text
data/raw.txt -> build/features.txt -> models/model.txt -> reports/report.txt
```

The Justfile shape is:

```just
prepare:
  mkdir -p build models reports

features: prepare
  cx --in data/raw.txt --in scripts/features.sh --out build/features.txt -- bash scripts/features.sh data/raw.txt build/features.txt

train: features
  cx --in build/features.txt --in scripts/train.sh --out models/model.txt -- bash scripts/train.sh build/features.txt models/model.txt

report: train
  cx --in models/model.txt --in scripts/report.sh --out reports/report.txt -- bash scripts/report.sh models/model.txt reports/report.txt
```

The verification lab proves:

- first run creates all artifacts;
- second run reports all three outputs `up-to-date`;
- changing `data/raw.txt` reruns the whole downstream chain and updates the
  final report.

This is the model to copy for ML, AI, conversion, and generated-artifact
pipelines. Include scripts, parameters, prompts, schemas, and config files as
`--in` when they affect an output.

## Example 2: Incremental C Build

The reusable lab builds this shape:

```text
src/main.c + include/app.h -> build/main.o
src/util.c + include/app.h -> build/util.o
build/main.o + build/util.o -> build/app
```

The Justfile shape is:

```just
prepare:
  mkdir -p build

objects: prepare
  cx --in src/main.c --in include/app.h --out build/main.o -- cc -Iinclude -c src/main.c -o build/main.o
  cx --in src/util.c --in include/app.h --out build/util.o -- cc -Iinclude -c src/util.c -o build/util.o

app: objects
  cx --in build/main.o --in build/util.o --out build/app -- cc build/main.o build/util.o -o build/app
```

The verification lab proves:

- first run compiles and links;
- second run reports both object files and the binary `up-to-date`;
- changing `src/util.c` leaves `build/main.o` fresh, rebuilds `build/util.o`,
  and relinks `build/app`;
- changing `include/app.h` rebuilds both object files and relinks.

This is the right teaching example for explicit incremental builds. Do not
wrap Cargo or Go builds unless the project has a separate file-producing stage
outside those tools.

## Command Contract Guidance

When a project uses `cx`, document the build or pipeline target in `AGENTS.md`
as an ordinary command-contract target, for example:

```bash
Build pipeline: just pipeline
Incremental build: just build
cx lint: cx lint
```

For repository setup, `gsu` should check `cx --help` only when the project has
or wants `cx`-backed build/pipeline targets. If `cx` is required and missing,
ask before installing it.

For verification of a `cx`-backed build or pipeline, run the real build or
pipeline target:

1. run once from a clean output directory;
2. run again and confirm expected `up-to-date` lines;
3. change a source input and confirm only the expected downstream artifacts
   rerun;
4. run `cx lint` for Justfile declaration shape.

This verification checks the build/pipeline behavior. It does not replace
focused tests for callable code.

## Review Checklist

Review `cx` lines as build declarations:

- Are all real file inputs declared with `--in`, including scripts, schemas,
  prompts, model/config files, and parameters?
- Are all durable file outputs declared with `--out`?
- Does each `cx` line have at least one output?
- Do Just recipe dependencies still order producer recipes before consumer
  recipes?
- Does the command write only the declared outputs?
- Are local `.cx` state files ignored without hiding future config?
- Is the project using `cx` for build/pipeline stages rather than tests,
  linting, formatting, or package-manager builds?

For non-trivial workflow changes, run clean-slate verification and review in
independent sub-agents when available and authorized, then integrate the
findings centrally.
