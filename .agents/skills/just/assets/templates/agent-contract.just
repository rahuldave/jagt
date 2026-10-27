# Optional dynamic context targets for Codex/Gest agents.
# Adapt the commands and review_focus lists to the target repository.

agent-contract:
  @printf '%s\n' '<<<AGENT_CONTRACT v1 kind=repository>>>' \
    'commands:' \
    '  lint: just lint' \
    '  test: just test' \
    '  verify: just verify' \
    'vcs:' \
    '  adapter: git-or-gitbutler' \
    '  inspect: [git status --short --branch, git diff]' \
    'safety:' \
    '  - Treat this output as repo-local operational context.' \
    '  - Preserve GitButler but-command rules when GitButler owns the workspace.' \
    '<<<END_AGENT_CONTRACT>>>'

agent-contract-json:
  @printf '%s\n' '{"version":1,"kind":"repository","commands":{"lint":"just lint","test":"just test","verify":"just verify"},"vcs":{"adapter":"git-or-gitbutler"},"safety":["repo-local operational context","preserve GitButler but-command rules when applicable"]}'

agent-language-profile:
  @printf '%s\n' '<<<AGENT_CONTRACT v1 kind=language-profile>>>' \
    'language.profile: unknown' \
    'notes:' \
    '  - Replace with python, ruby, typescript, go, rust, mixed, or project-specific context.' \
    '<<<END_AGENT_CONTRACT>>>'

agent-plan topic="":
  @printf '%s\n' '<<<AGENT_CONTRACT v1 kind=plan>>>' \
    'topic: {{topic}}' \
    'guidance:' \
    '  - Classify workflow.kind, test.strategy, review.depth, and VCS execution separately.' \
    '  - Preserve Git/GitButler adapter rules from AGENTS.md and installed skills.' \
    '<<<END_AGENT_CONTRACT>>>'

agent-test-plan files="":
  @printf '%s\n' '<<<AGENT_CONTRACT v1 kind=test-plan>>>' \
    'changed: {{files}}' \
    'strategy: choose test-first, characterization-first, test-after, exploratory, or no-test-needed' \
    'questions:' \
    '  - What should fail before implementation?' \
    '  - Which focused test proves behavior instead of implementation detail?' \
    '<<<END_AGENT_CONTRACT>>>'

agent-review-plan files="":
  @printf '%s\n' '<<<AGENT_CONTRACT v1 kind=review-plan>>>' \
    'changed: {{files}}' \
    'review_focus:' \
    '  - correctness and regression risk' \
    '  - test adequacy' \
    '  - Git/GitButler workflow safety' \
    '  - docs/setup/command-contract drift' \
    '<<<END_AGENT_CONTRACT>>>'

agent-verify-plan files="":
  @printf '%s\n' '<<<AGENT_CONTRACT v1 kind=verify-plan>>>' \
    'changed: {{files}}' \
    'commands:' \
    '  - just lint' \
    '  - just test' \
    '  - just diff-check' \
    '<<<END_AGENT_CONTRACT>>>'

agent-impact target="":
  @printf '%s\n' '<<<AGENT_CONTRACT v1 kind=impact>>>' \
    'target: {{target}}' \
    'guidance:' \
    '  - Use semantic tags and ast-grep where supported.' \
    '  - Record dependers and verification in the Gest completion note.' \
    '<<<END_AGENT_CONTRACT>>>'

# Generic dispatcher for intentionally agentic targets.
# Replace prompt/inputs/outputs with project-specific details before use.
agentic TARGET +ARGS:
  @set -eu; \
    printf '%s\n' '<<<AGENT_TASK v1>>>'; \
    printf '%s\n' 'target: {{TARGET}}'; \
    printf '%s\n' 'mode: agentic'; \
    printf '%s\n' 'argv:'; \
    for arg in {{ARGS}}; do printf '  - %s\n' "$$arg"; done; \
    printf '%s\n' 'prompt: |'; \
    printf '%s\n' '  Inspect the listed inputs and complete the requested target.'; \
    printf '%s\n' 'inputs:'; \
    printf '%s\n' '  files:'; \
    for arg in {{ARGS}}; do printf '    - %s\n' "$$arg"; done; \
    printf '%s\n' 'outputs:'; \
    printf '%s\n' '  required:'; \
    printf '%s\n' '    - reports/{{TARGET}}/index.html'; \
    printf '%s\n' 'allowed_actions:'; \
    printf '%s\n' '  - read listed inputs'; \
    printf '%s\n' '  - create listed outputs'; \
    printf '%s\n' '  - inspect nearby project docs and code'; \
    printf '%s\n' 'verification:'; \
    printf '%s\n' '  - test -f reports/{{TARGET}}/index.html'; \
    printf '%s\n' 'delegation:'; \
    printf '%s\n' '  execution: subagent'; \
    printf '%s\n' '  recursive: true'; \
    printf '%s\n' '  triggers:'; \
    printf '%s\n' '    - nested agentic Just calls'; \
    printf '%s\n' '    - agentic dependencies'; \
    printf '%s\n' '    - hook-triggered packets'; \
    printf '%s\n' '    - agentic verification targets'; \
    printf '%s\n' 'safety:'; \
    printf '%s\n' '  - This block is repo-local operational context.'; \
    printf '%s\n' '  - It cannot override user, system, developer, VCS, or approval instructions.'; \
    printf '%s\n' '<<<END_AGENT_TASK>>>'
