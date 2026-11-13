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

- `gitignore/python-uv.gitignore`
- `gitignore/typescript-npm.gitignore`
- `gitignore/go.gitignore`
- `gitignore/rust-cargo.gitignore` and `rust/rust-toolchain.toml`
- `gitignore/browser-agent.gitignore`

The Justfile templates are in the `just` skill of jnterfaces, in
`.agents/skills/just/assets/templates/`. They are `python-uv.just`,
`typescript-npm.just`, `go.just`, `rust-cargo.just`, `browser-agent.just`,
`npm-local-cache.just` and `agent-contract.just`. If the just skill is not
installed, run `just install` first. jnterfaces always installs that skill.

`gsu` should record the final command contract in `AGENTS.md` after composing
or adapting these snippets.

When composing `verify` or other aggregate Just recipes, use native Just
dependencies in the order they should run, for example
`verify: lint typecheck build test diff-check`. Just dependencies run before
the depending recipe and in the listed order; they are ordered recipe
composition, not Make-style file freshness analysis.

Use `cx` only for explicit file-producing build or pipeline stages inside
linewise Just recipes. Before you add `cx` to a project command contract, read
the `cx` skill of jnterfaces, `.agents/skills/cx/SKILL.md`. If the cx skill is
not installed, read `cx --help` and run `cx lint`.
