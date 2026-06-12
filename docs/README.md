# Documentation Map

Start with one document:

- `TUTORIAL.md`: deterministic, step-by-step GitHub tutorial for a new user.

Use the rest only when you need reference material:

- `g_commands_cheatsheet.md`: quick guide to the `g*` skills.
- `gest_codex_workflow.md`: advanced workflow playbook for agents.
- `tag_dependency_workflow.md`: tag classification and ast-grep dependency checks.
- `just_command_contract.md`: stable Justfile command contract guidance,
  including optional dynamic `agent-*` context targets, `AGENT_TASK v1`
  handoff packets, and `AGENT_RESULT v1` subagent reports.
- `cx_incremental_pipelines.md`: `cx` guidance for incremental builds and
  file-artifact pipelines, including one pipeline example and one C build
  example.
- `gsu_typescript_hello_world.md`: tiny setup example.
- `gsu_language_profile_labs.md`: live local end-to-end setup labs for the
  Python, TypeScript, Go, and Rust setup/profile templates. These are command
  contract profiles, not language reasoning skills.
- `live_gitbutler_tutorial_transcript_2026-05-07.md`: historical live GitHub
  transcript for the four Git/GitButler tutorial examples.

The beginner tutorial is the source of truth for the supported review shapes:

1. ordinary git branch PR
2. ordinary git multi-commit PR
3. GitButler stacked PRs for dependent slices
4. physical git worktrees for independent slices

It also includes a deterministic tag classification and ast-grep dependency
check. Only the third review-shape step uses GitButler as the main tool.
