# The packet file and the layers of a packet

`jagt render` prints an `AGENT_TASK v1` packet for a fresh agent. In a git
worktree, it also saves a packet file in the shared log folder. The fresh
agent later returns a result with the same nonce. A hook of the commit gates
then reads the file, and turns the result into a record. The spec of the commit gates is
`docs/specs/commit-gates.md` in agent_gest_git_skills.

## Terms

| Term | Meaning |
|---|---|
| Fresh agent | An agent that a harness starts for one task, for example a subagent. |
| Nonce | A random value of 32 lowercase hex digits, of which the first is a letter. The packet and its result both hold it. |
| Log folder | The folder `.agents/log/` of a checkout. Git ignores it. |
| Main checkout | The first worktree of a repository, the one that `git clone` made. |
| Shared log folder | The log folder of the main checkout. All worktrees of a repository save their packet files there. |
| Worktree tree | The tree hash of all the files in the worktree, staged or not. Ignored files are not in it. |
| Layer | One part of the prompt text of a packet. |

## What the packet file holds

`jagt render` saves the file `.agents/log/packets/<nonce>.json` in the
shared log folder. The file holds one JSON object:

```json
{
  "version": 1,
  "nonce": "d5a8c0e4f1b2937a6c4e8d0b2f7a9c31",
  "target": "review",
  "input_tree": "0221b630c3468902934e27f4ab7116febf23c716",
  "worktree": "/Users/me/Projects/app-feature",
  "packet_sha256": "d10df5f7dddfbc88db620563d5437673c4a815265861a9b61722bcffc8fe8b64"
}
```

| Field | Meaning |
|---|---|
| `version` | The version of the form of the file, now 1. |
| `nonce` | The nonce of the packet. The name of the file holds it too. |
| `target` | The target of the packet. |
| `input_tree` | The worktree tree when `jagt render` ran. |
| `worktree` | The absolute path of the top folder of the worktree in which `jagt render` ran. |
| `packet_sha256` | The SHA-256 hash of the packet text, the exact bytes that `jagt render` prints. |

The hash covers the whole packet text, with the joined layers and the nonce.
The file has no time and no argv, because the gate needs neither.

## How jagt finds the folders

- **The worktree** is the output of `git rev-parse --show-toplevel`. So
  `jagt render` works from any subfolder of a worktree.
- **The main checkout** is the first entry of `git worktree list --porcelain`.
  Git lists the main checkout first, also from a linked worktree. The parent
  of `git rev-parse --git-common-dir` is not always the checkout, for example
  in a submodule. So jagt does not use it.
- **A bare repository** has no main checkout, so it has no shared log folder.
  In a worktree of a bare repository, `jagt render` stops with an error.
  `--no-save` still works there.
- **The variables of a git hook** have no effect. A git hook or
  `git rebase --exec` sets variables such as `GIT_DIR` and `GIT_WORK_TREE`.
  jagt removes each variable that `git rev-parse --local-env-vars` lists, and
  finds the repository from the current folder alone.

jagt makes `.agents`, `.agents/log` and `.agents/log/packets` when they are
missing. If one of them is a symlink, or is not a folder, `jagt render` stops
and writes nothing. So a symlink in a repository cannot send a packet file
out of the log folder.

When `.agents/log/.gitignore` is missing, jagt writes it with the one line `*`.
`jlog` writes the same file. jagt also writes `packets/.gitignore` with `*`. It
leaves an existing `.gitignore` file alone. With the second file, the packets
stay out of every worktree tree, also when an older log `.gitignore` lacks
`*`.

## How jagt computes the input tree

jagt computes the worktree tree with a temporary index, so the real index does
not change:

```sh
GIT_INDEX_FILE=<tmp> git read-tree HEAD
GIT_INDEX_FILE=<tmp> git add -A
GIT_INDEX_FILE=<tmp> git write-tree
```

Before the first commit, there is no `HEAD`, so jagt leaves out the first
line. The temporary index is in the temporary folder of the system, outside
the repository. jagt removes it after the last line. A `GIT_INDEX_FILE` in the
environment of the caller has no effect on the tree.

`git add -A` has two effects outside the packet file:

- **It writes objects.** Git stores each new or changed file as an object in
  `.git/objects`, as any `git add` does. `git gc` removes the objects that no
  commit uses.
- **It runs clean filters.** A filter such as Git LFS runs on each changed
  file, so a render in a large worktree can be slow.

## The nonce

jagt draws 16 random bytes from the operating system for each packet. If the
hex form of the bytes starts with a digit, jagt draws again. A YAML reader
then always reads the nonce as a string, and never as a number such as
`123e45`. The packet text holds the nonce in a top-level field, after `mode`.
The field `result_rules` tells the fresh agent to return it:

```yaml
target: review
mode: agentic
nonce: d5a8c0e4f1b2937a6c4e8d0b2f7a9c31
result_rules:
  - 'Put the top-level field nonce: d5a8c0e4f1b2937a6c4e8d0b2f7a9c31 in the AGENT_RESULT v1 block. A result without this nonce gives no record.'
```

The nonce is the one part of `jagt render` that is not deterministic. The
rest of the packet text is the same for the same inputs.

- **A packet file is never replaced.** If a file with the same nonce exists,
  `jagt render` stops with an error.
- **The file comes first.** jagt checks the packet text with its own lint,
  saves the packet file, and then prints the packet. So every printed packet
  with a nonce has its file. If the print fails, for example on a broken pipe,
  jagt removes the file.
- **`jagt lint` checks the form.** A packet with a `nonce` field of another
  form fails the lint.
- **`jagt result lint --expect-nonce <nonce>`** fails a result that holds
  another nonce, holds no nonce, or holds two `nonce` fields. It also fails
  when its argument is not a nonce, for example an empty string. A hook can run
  it before it writes a record.

## The layers of the prompt text

`jagt render` joins the layers of the prompt text in this order:

1. **The base task.** It is the prompt from `--prompt-text`, `--prompt`, the
   config or the prompt file, as before. The target recipe passes the base task
   of its skill, for example `references/targets/review.md` of the `grv` skill.
2. **The language layers.** For each name in the `profiles` list of
   `.agents/stack.json`, jagt reads `.agents/targets/<language>/<target>.md`.
   The order is the order of the list, and a repeated name counts once.
3. **The repository text.** It is `.agents/targets/<target>.md`.

jagt reads the files from the worktree in which it runs, not from the main
checkout. So a change to a layer file in a linked worktree takes effect in
that worktree. A layer file can be a symlink, but its real path must be inside
`.agents/targets` of the worktree. The real path of `stack.json` must be the
file `.agents/stack.json` itself. A symlink that leads elsewhere stops the
render. So a layer cannot put a file such as `.env`, `.git/config` or a key
into the packet.

- **A missing layer is not an error.** A missing file, a missing
  `stack.json`, or a file of blank lines adds no layer.
- **At least one layer must have text.** With no layer, `jagt render` stops
  with "missing prompt text", and saves no file.
- **One blank line** goes between two layers.
- **A first line with an indent** is kept. jagt then writes `prompt: |2`, so
  that YAML reads the indent of the block correctly.
- **Some characters cannot go in a block.** A YAML reader reads a lone `\r`,
  U+0085, U+2028 and U+2029 as line breaks, and refuses a control character
  such as U+0001. A prompt with one of them is written as `prompt: "..."`, in
  double quotes with escapes. Each `\r\n` becomes `\n` first, as in a block.
- **A profile name must be a plain name.** It starts with a letter or a digit,
  and holds only letters, digits, `_`, `.` and `-`. So a name such as `..`
  cannot read a file outside `.agents/targets`. A bad name stops the render.

The `provenance` of the packet lists the layers that it holds:

```yaml
provenance:
  renderer: jagt
  renderer_version: 0.3.0
  layers:
    - base task
    - 'language layer: .agents/targets/python/docs.md'
    - 'repository text: .agents/targets/docs.md'
```

## The prompt file of a config

jagt reads the config `.jagt/config.toml` from the project root. The project
root is the top of the git worktree, or the current folder outside a worktree.
So a render from a subfolder reads the same config. A relative `prompt` path in
a config is read from the project root too.

A config file comes with the repository, like a layer. So jagt checks the
`prompt` that a config names, in `[defaults]` or in a target, before it reads
the file. Each of these stops the render:

- **A path outside the project root.** jagt compares real paths, so an
  absolute path, a `..` path or a symlink that leads elsewhere counts.
- **A part of the path that is `.git`.**
- **A file with more than one hard link**, on Unix. A hard link can name a file
  outside the folder.
- **A file that a repository ignores**, such as an ignored `.env`. jagt asks
  each repository from the folder of the file up to the project root. So a
  submodule and the repository around it both answer, and one "ignored" is
  enough.
- **A file that the nearest repository cannot answer for.** When a folder
  above the file holds `.git`, and git cannot start or gives an error, jagt
  cannot tell whether git ignores the file.
- **A hidden file outside any repository.** With no `.git` above the file,
  there is no ignore list. A part of the path that starts with `.` then stops
  the render. The folders `.agents` and `.jagt` are allowed.

The check does not cover a file that is neither tracked nor ignored, such as a
new `creds.json` in the folder. A prompt file from `--prompt` is the choice of
the caller, so jagt reads it with no check.

## When jagt saves no file

jagt checks the text with its own lint in these cases too, as for a saved
packet. So `jagt render` never prints a packet that `jagt lint` rejects.


- **`--no-save`** renders the text only. The text has no nonce, and jagt saves
  no file. Use it for a demo or a draft that needs no record. With
  `--no-save`, jagt needs git only to find the top of the worktree for the
  layers. When git is missing, or the main repository is bare, jagt reads the
  layers from the current folder.
- **Outside a git worktree**, or when git cannot start, there is no input tree. jagt renders the text
  with no nonce, saves no file, and prints a warning on stderr. jagt then reads
  the layers from the current folder. The protocol demo of the `jagt-protocol`
  skill runs this way.

A target recipe of the commit gates always runs in a git worktree, so it
always gets a nonce and a packet file.
