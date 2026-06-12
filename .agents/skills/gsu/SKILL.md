---
name: gsu
description: Gest Setup. Bootstrap or refresh a Gest-tracked repository workflow surface across tool checks, project command contracts, Justfile targets, AGENTS.md mappings, docs, tests, and setup follow-ups.
---

# GSU: Gest Setup

Use when a repository needs first-time setup, workflow refresh, command-contract
normalization, project tool selection, or migration toward reusable Gest/Codex
skills.

`gsu` deals in project concepts. It should not bake one language, package
manager, or test runner into the reusable skills. Instead, it helps the user
choose tools, records those choices in `AGENTS.md`, and creates or updates the
executable command interface, preferably a `Justfile`.

## Core Concepts

Identify which of these concepts apply to the project:

- environment bootstrap
- VCS initialization
- ignore rules
- dependency installation
- local tool installation
- run app or service
- format
- lint
- typecheck
- static or compile check
- build
- unit tests
- regression tests
- integration tests
- smoke checks
- browser spot checks
- browser/UI verification
- incremental build or artifact pipeline
- database/migration checks
- API docs
- user docs
- internal/developer docs
- release or CI checks

## Workflow

1. Inspect the repository shape: VCS state, `.gitignore`, `AGENTS.md`,
   existing `.agents/skills`,
   `Justfile`, `.envrc`, package manifests, lockfiles, CI configs, docs, test
   directories, source directories, and app entrypoints.
2. Initialize Git or Gest only when missing and after confirming the desired
   repository root. Use `git init` and `gest init --local` for this Git-oriented
   skill family; keep jj support in a separate parallel skill repository.
3. Check required workflow executables: `git`, `gest`, `just`, and `uv`.
   Missing tools should be reported clearly without blocking skill
   installation. Treat `direnv` as recommended unless the project contract
   requires it. Check `cx` only when the project has or wants explicit
   file-producing incremental build/pipeline stages.
4. Infer likely project profiles from files and user context. Examples:
   - Python: `pyproject.toml`, `uv.lock`, `pixi.toml`, notebooks, FastAPI,
     Django, Flask, pytest, ruff, ty, pyright, mypy.
   - TypeScript/JavaScript: `package.json`, lockfiles, Vite, Next, ESLint,
     Biome, TypeScript, Vitest, Jest, Playwright.
   - Rust: `Cargo.toml`, Cargo workspaces, clippy, rustfmt, rustdoc.
   - C/C++ or native build: `Makefile`, `CMakeLists.txt`,
     `compile_commands.json`, `src/*.c`, `src/*.cc`, `include/`, object files,
     custom compile/link recipes.
5. Ask the user to choose when multiple plausible tools exist, when profile
   tradeoffs affect committed files, or when installation
   would change the machine or repository. Prefer one concise question at a
   time.
6. Create or update ignore rules for generated files, local environments,
   caches, logs, build artifacts, and project-local tool installs. Start from a
   base ignore snippet, then layer on language/runtime snippets.
7. Create or update `.env.example`, `.envrc`, and project-local PATH setup when
   the project uses environment variables or local tool installs.
8. Install or sync project dependencies through the chosen package manager when
   the user approves.
9. Define the project command contract in `AGENTS.md`. Map each applicable
   concept to the command agents should run, including focused arguments.
10. Create or update the `Justfile` when the project uses `just`. Keep target
   names stable and let targets call the project-specific tools.
11. Create or update setup docs, docs/test directory expectations, and
   project-specific invariants in `AGENTS.md`.
12. Run setup verification: command discovery (`just --list`), the cheapest
   static checks, and targeted commands that prove argument passing works.
13. Record remaining setup gaps as Gest follow-ups rather than hiding them.

## Package Install Handoff

For a normal target repository, `gsu` runs after the package-specific installer
has already handled package extras. Do not use `skill-package-maker` for this
handoff. That skill is for authoring skill packages, not for setting up a repo
that just installed the Git/GitButler Gest skills.

Before ordinary setup work, verify that the expected package handoff is present:

- `.agents/skills/gest_git_installer/SKILL.md`
- at least one core workflow skill such as `.agents/skills/gtw/SKILL.md`
- skill-local support material under `.agents/skills/*/references/`,
  `.agents/skills/*/scripts/`, and `.agents/skills/*/assets/` as needed
- `.agents/skills/gsu/assets/templates/`
- `.agents/skills/gsu/scripts/gest_mermaid_graph.py`
- `.claude/settings.json` and `.claude/hooks/`
- `.codex/hooks.json` and `.codex/hooks/`
- `AGENTS.md`, or a clear note that an existing `AGENTS.md` was preserved and
  still needs the template guidance merged

If hooks/settings or AGENTS guidance are missing, tell the user to invoke
`gest_git_installer` first. Once the handoff is present, proceed with normal
`gsu` work: tool checks, ignore rules, dependency setup, command contracts,
Justfile targets, verification commands, and follow-up tasks.

## Skill Repository Packaging

Only when the target repository is itself a skill repository, look for
`skill-package.json`, `skills/*/SKILL.md`, `.agents/skills/*/SKILL.md`, and
the repo-level installer script. If the `skill-package-maker` skill is installed or
available in the current source checkout, use it for packaging checks before
declaring setup complete.

Preferred checks:

```bash
uv run python ~/.agents/skills/skill-package-maker/scripts/lint_skill_bundle.py .
uv run python ~/.agents/skills/skill-package-maker/scripts/render_package_plan.py .
```

If the skill was installed project-locally instead of globally, use the same
script paths under `.agents/skills/skill-package-maker/`. If the standalone
checkout is available, use:

```bash
uv run python /Users/rahul/Projects/agent_skill_package_maker/skills/skill-package-maker/scripts/lint_skill_bundle.py .
```

Require skill repos to declare their package-specific installer skill, custom
installers, and executable prerequisites in `skill-package.json`. For packages
installed with `npx skills`, hooks/settings and target-repo extras should be
installed by the package's explicit installer skill after `npx skills add`, not
as a hidden install side effect. Skill runtime references, templates, helper
scripts, and assets should live inside the skill folder that needs them.
Installer scripts must report every required workflow
executable without blocking the skill copy and mention optional executables
that unlock extra flows.

Required workflow executables are `git`, `gest`, `just`, and `uv`; optional
executables include `rsync`, `gh`, `but`, `ast-grep`, `direnv`, and `cx`.
Runtime commands should re-check tools they actually need.

## Snippet Templates

This skill includes composable snippets under `assets/templates/`. Use them as
starting points, not as blind overwrites:

- `assets/templates/gitignore/base.gitignore`
- `assets/templates/gitignore/python-uv.gitignore`
- `assets/templates/gitignore/typescript-npm.gitignore`
- `assets/templates/gitignore/browser-agent.gitignore`
- `assets/templates/env/envrc.local-bin`
- `assets/templates/env/*profile*.envrc` and related profile env snippets
- `assets/templates/env/env.example`
- `assets/templates/just/*.just`

Every setup should include the base ignore concepts. Add profile snippets only
when the project needs them. If existing project files already cover the same
patterns, preserve the local style and avoid duplicate churn.

## Profile Synthesis

When the project profile is not covered by existing snippets, synthesize a
candidate profile instead of stopping. Work in this order:

1. Identify the project type, package manager, runtime, build tool, test tool,
   docs tool, and any generated artifacts.
2. Ask the smallest necessary questions where defaults have real consequences.
   Examples: Rust app vs library for `Cargo.lock`, Python app vs package,
   whether ML datasets/models should be ignored or versioned, or which Node
   package manager should own the lockfile.
3. Draft candidate `.gitignore`, `Justfile`, `.env.example`, `.envrc`, and
   `AGENTS.md` command-contract snippets.
4. Apply them to a disposable project or current repo after confirmation.
5. Run setup verification and revise the snippets.
6. If the profile is generally useful, add it to `assets/templates/` and
   document the questions/tradeoffs.

Do not silently invent project policy for expensive or irreversible choices.
Ask before ignoring data directories, generated code, model artifacts, lockfiles,
or credentials.

## Command Contract

Prefer `just` targets when present. `AGENTS.md` should say which command maps
to each workflow concept and how arguments are passed. See
`references/just_command_contract.md` for the reusable Just command-contract model. A
typical contract might include:

```text
Format: just fmt [path]
Lint: just lint [path]
Typecheck: just typecheck
Static/compile check: just static
Build: just build
Focused tests: just test [target]
Full tests: just test
Smoke checks: just smoke
Run app: just dev [port]
Browser spot check: just browser [url-or-flow]
Integration flow: just integration [flow]
Docs check: just docs
```

For browser-based integration tests or spot checks, include both sides of the
contract: a run-app target such as `just dev [port]`, and a browser target such
as `just browser [url-or-flow]`. Browser checks should either start from the
documented run-app target or explicitly confirm that the expected server is
already running.

The reusable `gfm`, `gte`, and `gdo` skills should read this project contract
instead of hard-coding language tools.

## Tool Installation Policy

Check the required toolchain before running setup commands. If a required tool
is missing, ask the user before installing it and prefer the least surprising
installer for their platform/project. Use the project package manager where
possible. Examples:

- Python: prefer `uv`, `pixi`, or the tool already chosen by the project.
- TypeScript/JavaScript: prefer the detected package manager (`pnpm`, `npm`,
  `bun`, or `yarn`) and use package-manager exec commands.
- Rust: prefer `rustup`/`cargo` conventions already present in the project.
- Go: prefer the standard Go toolchain first (`gofmt`, `go test`, `go build`,
  `go vet`) unless the project already uses a separate tool.

Common checks:

```bash
git --version
gest --version
just --version
uv --version
rsync --version
direnv version
node --version
npm --version
go version
cargo --version
rustc --version
cx --help
```

Profile install prompts should be concrete:

- Python/uv: ask before installing `uv`; then use `uv sync`.
- TypeScript/npm: ask before installing Node/npm or an alternate package
  manager; then use the chosen install command.
- Go: ask before installing Go; then use `go mod tidy` or `go test ./...` to
  populate module state.
- Rust: ask before installing Rust via `rustup`; then use Cargo commands.
- Browser UI: ask before installing browser-agent runtime with
  `npx agent-browser install` or the global `agent-browser install`.

Prefer project-local dependency state and version pins:

- Python/uv: dependencies live in `.venv/`; commit `uv.lock` when present.
  Prefer `UV_CACHE_DIR=.local/uv-cache` when setup should avoid ambient caches.
- TypeScript/npm: dependencies live in `node_modules/`; commit
  `package-lock.json`; use a project-local npm cache such as
  `.local/npm-cache` when useful.
- Browser-agent in Node projects: prefer a dev dependency plus
  `npm exec -- agent-browser ...` for a pinned project-local CLI. Use
  `npx agent-browser ...` when the project has no Node package setup or the user
  wants on-demand execution.
- Go: commit `go.mod` and `go.sum` when generated; the Go toolchain itself is
  usually external but versioned by the `go` directive. Prefer
  absolute local cache paths such as `GOCACHE="$PWD/.local/go-build"` and
  `GOMODCACHE="$PWD/.local/go-mod"` when setup should avoid ambient caches.
- Rust: commit `rust-toolchain.toml` when the project wants a pinned toolchain;
  Cargo build artifacts stay local under `target/`.

For tools that should be available only inside this repository, prefer an
explicit project-local path such as `.local/bin` exposed through `.envrc`:

```sh
PATH_add .local/bin
```

Use `direnv` for project activation when local tools or cache variables should
be in force for every command. For example, a Python/uv project can use:

```sh
PATH_add .local/bin
export UV_CACHE_DIR="$PWD/.local/uv-cache"
```

Keep critical environment assumptions visible in `AGENTS.md` and the command
contract even when `.envrc` sets them, because CI or non-direnv shells may need
the same variables.
Running `direnv allow` writes to user-level direnv state, so treat it as a
setup action that may require approval in sandboxed environments.

Do not silently rely on ambient global tools when the project contract says a
local toolchain is required. If installation needs network or writes outside
the sandbox, request approval and explain the tool being installed.

## cx Incremental Build And Pipeline Setup

`cx` is for incremental builds and file-artifact pipelines in linewise Just
recipes. It is not a test runner. Use it only when a command reads explicit
files and writes durable output files.

Good setup candidates:

- ML/AI or data pipelines with intermediate artifacts, such as raw data to
  features to model to report.
- Generated artifact workflows where schemas, prompts, scripts, or configs
  produce generated files.
- Document, book, image, audio, or data conversion pipelines.
- Hand-written C/C++ compile/link recipes with object files and binaries as
  explicit outputs.

Do not add `cx` for tests, lint, format, typecheck, browser checks, ordinary
`cargo build`, `go build`, `tsc`, or commands without durable file outputs.
Those stay ordinary project command-contract targets.

When adding `cx`:

- keep Just recipe dependencies for recipe ordering;
- wrap only individual file-producing command lines with
  `cx --in ... --out ... -- COMMAND ...`;
- include scripts, schemas, prompts, config, and parameter files in `--in`
  when they affect outputs;
- add `cx lint` or `just cx-lint` to the static/check contract when useful;
- ignore `.cx/state.json`, `.cx/graph.json`, and `.cx/tmp/`, but leave
  `.cx/config.toml` committable unless the project decides otherwise;
- verify the pipeline/build by running once, running again to observe
  `up-to-date`, then changing one input and confirming the expected downstream
  artifacts rerun.

For reusable examples, read `references/cx_incremental_pipelines.md` and run
`just cx-examples-lab` in this skill repository.

For npm projects, prefer a project-local cache when the user wants explicit
per-project tooling or the global npm cache is unreliable:

```just
export npm_config_cache := ".local/npm-cache"
```

## Profile Notes

For a simple Node-targeted TypeScript project, a good starting profile is:

- package manager: `npm` unless another lockfile is present
- formatter/linter: Biome for a small single-tool default, or the project's
  existing ESLint/Prettier setup
- typecheck/build: TypeScript
- tests: Node's built-in `node:test` for tiny projects, or the detected test
  runner for existing projects
- dev dependencies: `typescript`, `@types/node`, and the chosen formatter/linter
- lint defaults: source and config files, not generated outputs such as `dist/`

For a simple Rust/Cargo project, a good starting profile is:

- formatter: `cargo fmt --all`
- lint: `cargo clippy --all-targets --all-features -- -D warnings`
- typecheck: `cargo check --all-targets --all-features`
- build: `cargo build --all-targets --all-features`
- tests: `cargo test --all-features`
- docs: `cargo doc --no-deps`
- ask whether to commit `Cargo.lock`; apps usually should, libraries may not

For a simple Go project, a good starting profile is:

- formatter: `gofmt -w .`
- lint/static check: `go vet ./...`
- typecheck/build: `go build ./...`
- tests: `go test ./...`
- docs: `go doc ./...` when useful

## Browser Setup

When a project has browser UI, ask the user whether browser-agent checks should
be part of the command contract. `npx agent-browser install` installs the
browser runtime used by the CLI; it does not install this repository's Codex
skill into `.agents/skills`. Prefer `npx agent-browser` for a simple
project-local/on-demand setup:

```just
browser-setup:
  npx agent-browser install

browser url="http://127.0.0.1:3000":
  npx agent-browser open {{url}}
```

For Node projects that want pinned folder-local CLI dependencies, add
`agent-browser` to `devDependencies` and use:

```just
browser-setup:
  npm exec -- agent-browser install

browser url="http://127.0.0.1:3000":
  npm exec -- agent-browser open {{url}}
```

If the team wants the faster global CLI, document and verify:

```bash
npm i -g agent-browser
agent-browser install
agent-browser skills get core
```

Record which form the project uses in `AGENTS.md`. Keep two browser concepts
separate:

- Browser spot checks: exploratory visual/interaction checks during
  implementation, often run against the current dev server before tests are
  formalized.
- Browser integration tests: durable, rerunnable scripts or tests under
  `integration_tests/`, `e2e/`, or the project's chosen test location.

## Ignore Rules

When creating or refreshing `.gitignore`, cover the project profile without
hiding important source artifacts. Common setup-owned ignores include:

- local environment directories such as `.venv/`
- project-local tool installs such as `.local/`
- language caches such as `.ruff_cache/`, `.pytest_cache/`, `node_modules/`,
  `target/`, and build outputs
- browser-agent local state and artifacts such as `.agent-browser-home/`,
  `browser-data/`, screenshots, and recordings
- local secrets such as `.env`
- generated logs, coverage outputs, and temporary files

## Environment Files

If the project needs environment variables, commit `.env.example` and ignore
`.env`. Use `.envrc` when the project needs per-repo PATH, local tool setup, or
cache variables, such as exposing `.local/bin`:

```sh
PATH_add .local/bin
```

Do not put secrets in `AGENTS.md`, `.envrc`, or committed templates. Document
variable names and expected purpose in `.env.example` or setup docs.

## Just Arguments

Just targets declare parameters after the target name:

```just
lint path=".":
  <lint-command> {{path}}

test target="tests":
  <test-command> {{target}}

dev port="8001":
  <run-command> --port {{port}}
```

Agents pass arguments positionally:

```bash
just lint scripts/foo.py
just test tests/test_foo.py
just dev 8001
```

Use quotes when passing an argument that contains spaces.

## Just Recipe Composition

When creating or updating a `Justfile`, consult:

- Just dependencies: https://just.systems/man/en/dependencies.html
- Just skill reference: https://raw.githubusercontent.com/casey/just/refs/heads/master/skills/just/SKILL.md

For Just, dependency order is meaningful: dependencies run before the recipe
that depends on them, and in the listed order. Use native recipe dependencies
for ordered aggregate recipes, such as:

```just
diff-check:
  git diff --check

verify: lint typecheck static test smoke diff-check
```

Prefer this over recursively calling `just lint`, `just typecheck`, and so on
inside `verify`. Dependencies with the same arguments run once per `just`
invocation. This is ordered recipe composition, not Make-style file freshness
analysis.

## Deliverable

Report:

- detected project profile and chosen tools
- required/recommended executable status
- files created or updated
- command contract mappings
- verification commands run and results
- open follow-ups, especially missing tests, missing docs, or unset CI/hooks

## Setup For Dependency Impact

When refreshing repository setup, check whether `ast-grep` is available or documented for dependency-impact checks. If setup changes shared tooling, hooks, generated code, or command contracts, use `ast-grep` or targeted structured searches to find dependent surfaces.
