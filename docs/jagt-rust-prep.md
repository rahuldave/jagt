# jagt Rust Project Prep

This repo has already been prepared as a Rust binary project for phase A:

- `cargo init --bin --edition 2024` scaffold.
- Git repository initialized.
- `rust-toolchain.toml` pinned to stable.
- `Justfile` command contract added.
- `.gitignore` covers Cargo build output, local Gest state, local caches,
  secrets, editor files, and `.jagt/tmp/`.
- Local Gest/Git skills and workflow docs copied in.
- Preliminary jagt spec and protocol references copied in.

Local tool versions observed during bootstrap:

- `cargo 1.95.0`
- `rustc 1.95.0`
- `just 1.50.0`
- `gest 0.5.6`
- `git 2.54.0`

## Before Implementation

1. Review `jagt_deterministic_renderer_spec.md` and decide which parts are
   accepted MVP scope. Promote the accepted plan through Gest with `gtw`,
   likely using `gsp` or `gpl` before `gim`.
2. Confirm the protocol source of truth for `AGENT_TASK v1` and
   `AGENT_RESULT v1`. The copied files in `docs/reference/` are context, but
   future work should notice if the reusable skill specs have changed.
3. Decide whether `.jagt/config.toml` remains the config path or whether the
   accepted design chooses another name such as `.agent-task/`.
4. Choose the schema strategy: Rust structs only, JSON Schema, or both. If both,
   decide which one is generated from the other.
5. Choose CLI and parsing crates. Likely candidates are `clap`, `serde`,
   `serde_yaml`, `toml`, `thiserror`, and a glob/wildcard crate for secret
   redaction patterns.
6. Choose testing crates. Likely candidates are `assert_cmd`, `predicates`,
   `tempfile`, and possibly `insta` for golden packet snapshots.
7. Fill the fixture matrix for valid/invalid `AGENT_TASK v1` and
   `AGENT_RESULT v1` packets before or alongside the first linter.
8. Decide how strict linting should be compared with the shell reference
   validators in `tools/reference/`.
9. Decide whether `jagt render` should compute a stable `task_ref` digest in
   MVP or leave that as follow-up.
10. Decide repository publication details before first push: GitHub remote,
    license, CI workflow, and release/package plan.

## Suggested First Implementation Slice

A conservative first slice would avoid config files and frontmatter:

1. Add CLI parsing for `jagt render <target> --arg ... --input ...`.
2. Render a deterministic `AGENT_TASK v1` envelope to stdout.
3. Add a fixture and a test that pipes the rendered packet through the initial
   Rust linter.
4. Keep result linting, config TOML, prompt frontmatter, env interpolation, and
   schema generation for later slices.

That gives the project a small verified core while preserving room to revise
the broader spec.
