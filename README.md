# jagt

`jagt` means "just agent task." This repository is a phase A scaffold for a
future Rust CLI that deterministically renders, lints, and explains agentic
Just handoff envelopes.

The core proposal lives in `jagt_deterministic_renderer_spec.md`. That file is
preliminary context, not an accepted Gest implementation plan. The first real
implementation session should review it, revise it if needed, then promote the
accepted slice into Gest tasks.

## Current Scaffold

- Rust binary crate initialized with Cargo.
- Stable command contract in `Justfile`.
- Local Gest/Git Codex skills copied into `.agents/skills/`.
- Reusable workflow docs, templates, hooks, and graph tooling copied from
  `agent_gest_git_skills`.
- `AGENT_TASK v1` and `AGENT_RESULT v1` references copied under
  `docs/reference/`.
- Fixture directories created for future valid and invalid task/result packets.

## Commands

```bash
just setup
just fmt
just fmt-check
just lint
just typecheck
just build
just test
just smoke
just docs
just verify
```

`just verify` is the normal local gate. It currently checks formatting, clippy,
typecheck, build, tests, smoke help output, and whitespace hygiene.

## Fresh Codex Kickoff

For a new Codex project session, open this folder directly:

```bash
cd /Users/rahul/Projects/jagt
```

Then start with `gtw` for any implementation or project work. The new session
should treat `jagt_deterministic_renderer_spec.md` as a proposal to review, not
as already-accepted task scope.

## Next Decisions

See `docs/jagt-rust-prep.md` for the remaining Rust and product decisions. The
big ones are accepting/revising the MVP command set, choosing the schema/parser
strategy, and deciding whether `.jagt/config.toml` remains the default config
path.
