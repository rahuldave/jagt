# Setup Snippets

These snippets are inputs for `gsu`, not files to copy blindly.

Use the base snippets for every repository, then layer on language/runtime
snippets and browser snippets only when the project needs them. Merge carefully
with existing project files so local conventions are preserved.

## Baseline

- `gitignore/base.gitignore`: project-local installs, caches, secrets, logs,
  coverage, `.cx` runtime state, and editor/OS files.
- `env/envrc.local-bin`: `direnv` snippet for adding `.local/bin` to PATH.
- `env/env.example`: minimal committed `.env.example` placeholder.
- `env/python-uv.envrc`, `env/typescript-npm.envrc`, `env/go.envrc`, and
  `env/rust-cargo.envrc`: profile-specific `direnv` environment snippets.

## Profiles

- `gitignore/python-uv.gitignore` and `just/python-uv.just`
- `gitignore/typescript-npm.gitignore` and `just/typescript-npm.just`
- `gitignore/go.gitignore` and `just/go.just`
- `gitignore/rust-cargo.gitignore` and `just/rust-cargo.just`
- `rust/rust-toolchain.toml`
- `gitignore/browser-agent.gitignore` and `just/browser-agent.just`
- `just/npm-local-cache.just`
- `just/agent-contract.just`: optional dynamic agent context targets such as
  `agent-contract`, `agent-test-plan`, and `agent-review-plan`.

`gsu` should record the final command contract in `AGENTS.md` after composing
or adapting these snippets.

When composing `verify` or other aggregate Just recipes, use native Just
dependencies in the order they should run, for example
`verify: lint typecheck build test diff-check`. Just dependencies run before
the depending recipe and in the listed order; they are ordered recipe
composition, not Make-style file freshness analysis.

Use `cx` only for explicit file-producing build or pipeline stages inside
linewise Just recipes. See `docs/cx_incremental_pipelines.md` before adding
`cx` to a project command contract.
