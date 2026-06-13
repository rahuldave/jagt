# Fixtures

Future implementation work should add focused fixtures here:

- `agent_task/valid`: accepted `AGENT_TASK v1` packets.
- `agent_task/invalid`: rejected `AGENT_TASK v1` packets.
- `agent_result/valid`: accepted `AGENT_RESULT v1` packets.
- `agent_result/invalid`: rejected `AGENT_RESULT v1` packets.
- `agent_task_draft/valid`: accepted `AGENT_TASK_DRAFT v1` proposal packets.
- `agent_task_draft/invalid`: rejected `AGENT_TASK_DRAFT v1` proposal packets.

Prefer small fixtures with one reason to pass or fail. Golden render snapshots
can live here or in `tests/snapshots/` if the project adopts `insta`.
