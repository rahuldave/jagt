# GSU Language Profile Labs

These disposable labs verify that `gsu` can compose setup snippets for multiple
project types. They are examples, not golden project generators. Use them to
test the workflow in a new chat or clean project, then delete the lab folders.

The checked-in live local end-to-end harness is:

```bash
just language-profile-labs
```

That command creates four disposable repositories for Python/UV, TypeScript/NPM,
Go, and Rust/Cargo; initializes Git and local Gest in each one; composes the
profile `.gitignore`, `.envrc`, and `Justfile` snippets; and runs the setup and
verification commands. It does not create GitHub remotes or pull requests,
because these are language setup profiles rather than PR-flow tutorials.

Each lab should prove:

- Git initialization.
- Local Gest initialization with `gest init --local`.
- A base `.gitignore` plus profile-specific ignore rules.
- A stable `Justfile` command contract.
- Local dependency/cache state where appropriate.
- `just verify` including lint/typecheck/build/test/smoke/diff checks.

## Python With UV

Profile snippets:

- `templates/gitignore/base.gitignore`
- `templates/gitignore/python-uv.gitignore`
- `templates/env/env.example`
- `templates/env/envrc.local-bin`
- `templates/env/python-uv.envrc`
- `templates/just/python-uv.just`

Important local state:

- `.venv/` for dependencies.
- `.local/uv-cache` for uv cache.
- `.envrc` can expose `.local/bin` and `UV_CACHE_DIR`.
- `uv.lock` should be committed when generated.

Hello-world verification used:

```bash
git init
git branch -m main
gest init --local
direnv allow .
just setup
direnv exec . just verify
```

Verified command contract:

```just
export UV_CACHE_DIR := ".local/uv-cache"

setup:
  uv sync

lint path=".":
  uv run ruff check {{path}}

typecheck:
  uv run ty check

build:
  uv run python -m compileall hello.py tests

test target="tests":
  uv run python -m pytest {{target}}

smoke:
  uv run python hello.py

diff-check:
  git diff --check

verify: lint typecheck build test smoke diff-check
```

Lesson: prefer `uv run python -m ...` forms when invoking Python tools so the
project runs through Python's normal module startup behavior.

## TypeScript With NPM

Profile snippets:

- `templates/gitignore/base.gitignore`
- `templates/gitignore/typescript-npm.gitignore`
- `templates/env/typescript-npm.envrc`
- `templates/just/npm-local-cache.just`
- `templates/just/typescript-npm.just`

Important local state:

- `node_modules/` for dependencies.
- `.local/npm-cache` for npm cache.
- `.envrc` can expose `.local/bin` and `npm_config_cache`.
- `package-lock.json` should be committed when generated.

Hello-world verification used:

```bash
git init
git branch -m main
gest init --local
direnv allow .
just setup
direnv exec . just verify
```

Verified command contract:

```just
export npm_config_cache := ".local/npm-cache"

setup:
  npm install

lint path="src package.json tsconfig.json":
  npm exec -- biome check {{path}}

typecheck:
  npm exec -- tsc --noEmit

build:
  npm exec -- tsc

test target="":
  npm exec -- tsc
  node --test dist/*.test.js {{target}}

smoke:
  npm exec -- tsc
  node dist/index.js

diff-check:
  git diff --check

verify: lint typecheck build test smoke diff-check
```

Lessons: include `@types/node` for Node-targeted TypeScript; lint source/config
by default, not generated `dist/`.

## Go

Profile snippets:

- `templates/gitignore/base.gitignore`
- `templates/gitignore/go.gitignore`
- `templates/env/go.envrc`
- `templates/just/go.just`

Important local state:

- `.local/go-build` for `GOCACHE`.
- `.local/go-mod` for `GOMODCACHE`.
- `.envrc` can expose `.local/bin`, `GOCACHE`, and `GOMODCACHE`.
- `go.mod` pins the Go language version.
- `go.sum` should be committed when generated.

Hello-world verification used:

```bash
git init
git branch -m main
gest init --local
direnv allow .
direnv exec . just verify
```

Verified command contract:

```just
fmt:
  gofmt -w .

lint:
  GOCACHE="$PWD/.local/go-build" GOMODCACHE="$PWD/.local/go-mod" go vet ./...

typecheck:
  GOCACHE="$PWD/.local/go-build" GOMODCACHE="$PWD/.local/go-mod" go test ./... -run '^$'

build:
  GOCACHE="$PWD/.local/go-build" GOMODCACHE="$PWD/.local/go-mod" go build ./...

test target="./...":
  GOCACHE="$PWD/.local/go-build" GOMODCACHE="$PWD/.local/go-mod" go test {{target}}

smoke:
  GOCACHE="$PWD/.local/go-build" GOMODCACHE="$PWD/.local/go-mod" go run .

diff-check:
  git diff --check

verify: fmt lint typecheck build test smoke diff-check
```

Lesson: `GOCACHE` must be an absolute path; `$PWD/.local/go-build` works well
inside Just recipes.

## Rust With Cargo

Profile snippets:

- `templates/gitignore/base.gitignore`
- `templates/gitignore/rust-cargo.gitignore`
- `templates/env/rust-cargo.envrc`
- `templates/rust/rust-toolchain.toml`
- `templates/just/rust-cargo.just`

Important local state:

- `target/` for Cargo build artifacts.
- `rust-toolchain.toml` pins the Rust toolchain channel.
- Commit `Cargo.lock` for apps/binaries; ask before ignoring it for libraries.

Hello-world verification used:

```bash
git init
git branch -m main
gest init --local
direnv allow .
direnv exec . just verify
```

Verified command contract:

```just
fmt:
  cargo fmt --all

lint:
  cargo clippy --all-targets --all-features -- -D warnings

typecheck:
  cargo check --all-targets --all-features

build:
  cargo build --all-targets --all-features

test target="":
  cargo test --all-features {{target}}

smoke:
  cargo run --quiet

diff-check:
  git diff --check

verify: fmt lint typecheck build test smoke diff-check
```

Lesson: the toolchain is external, but the repo can pin it with
`rust-toolchain.toml`; build artifacts stay local under `target/`.

## Extending Profiles

When a new project type appears, `gsu` should synthesize candidate snippets,
ask the user about real policy choices, run a disposable lab or focused setup
check, then promote the stable snippets into `templates/`.

Good next candidates:

- Python machine learning with `uv` or `pixi`.
- Python notebooks.
- TypeScript browser UI with browser spot checks.
- Rust library vs Rust binary profiles.
- Go service with generated OpenAPI/protobuf artifacts.
