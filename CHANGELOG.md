# Changelog

This file lists the changes of each version of jagt. The newest version comes
first.

jagt follows semantic versioning, as Cargo reads it. Before 1.0, a change that
can break a user raises the minor version, such as 0.4.0 to 0.5.0. A fix that
breaks nothing raises the patch version, such as 0.5.0 to 0.5.1. A break is a
packet that lint rejected and now passes, or passed and now fails, a change in
the text that render writes, or a change in a flag or a message that a script
reads. Each version that breaks something lists it under "Breaking".

## 0.5.0

### Breaking

- Lint rejects some packets that 0.4.0 passed. They hold:
  - a stray line at column 0, or a top-level field away from column 0;
  - a top-level key that is not a plain or quoted scalar;
  - YAML that yaml-rust2 cannot read, or reads with other top-level fields;
  - a YAML merge, a tagged key or an alias key;
  - a raw U+0085, U+2028 or U+2029;
  - `result_rules` that is not a list of strings, names another nonce or
    comes with no nonce.
- Render writes a prompt line of only spaces or tabs with its whitespace,
  under `prompt: |2`, where 0.4.0 wrote an empty line.
- Render keeps the spaces and tabs at the end of the last line of a prompt or
  a layer, where 0.4.0 dropped them.

### Render

- A prompt keeps the spaces and tabs at the ends of its lines, and a line of
  only spaces or tabs. The packet reads back as the same prompt, with one
  newline at its end.

### Lint

- `jagt lint` and `jagt draft lint` reject a stray line at column 0. The YAML
  1.2 spec needs such a line indented. It can be:
  - a `]` that closes a flow list;
  - a line inside a quoted value that looks like a field;
  - a line that starts with a tab;
  - a list item under a key with a value.
- A field, a quoted key, a comment and a list item under an empty key still
  pass.
- `jagt lint`, `jagt draft lint` and `jagt result lint` reject a YAML merge
  at any depth. A merge can be a `<<` key, a node with the `!!merge` tag, a
  tagged key or an alias key. A YAML 1.1 reader such as PyYAML merges the fields they name, and
  lint would not check those fields. Text that only mentions `!!merge` passes.
- Lint reads each packet with a second YAML parser, yaml-rust2, which gives
  the tag and position of each node. Each top-level field of a task or a draft
  must start at column 0.
- Lint refuses a raw U+0085, U+2028 or U+2029 in a packet. The two parsers
  differ on whether it breaks a line. `jagt render` writes these characters
  escaped, so its packets still pass.
- `jagt lint` checks `result_rules`. They must be a list of strings, and the
  packet must have a `nonce`. A rule must name no other nonce, also in UUID
  form or in fullwidth digits.

## 0.4.0

### Breaking

- `jagt render` refuses a config prompt outside the project, in `.git`, with
  a second hard link, or ignored by git.
- A value that starts with `-`, other than a negative number, needs the `=`
  form, such as `--input=-data.csv`.
- The secret check refuses more values of allowlisted variables.
- `jagt result lint --check-files` refuses a path with a `..` part.
- `jagt draft lint` rejects more drafts, and passes some text that 0.3.0
  rejected, such as "Never run inline."

### Render

- `jagt render` lints each packet before it prints it, also with `--no-save`
  and outside git. So it never prints a packet that `jagt lint` rejects.
- A prompt with a bracket, such as `Fix arr[i`, now renders and lints.
- A prompt with a lone `\r`, U+0085, U+2028, U+2029 or a control character is
  written in double quotes, and reads back unchanged.
- A config is read from the project root. The project root is the top of the
  git worktree, or the current folder outside one. A render from a subfolder
  reads the same config.
- A `prompt` that a config names must be a file in the project. jagt refuses a
  path outside the project, a path in `.git`, a file with a second hard link,
  and a file that git ignores. A `--prompt` file is not checked.
- The secret check of allowlisted variables catches many more kinds of
  secrets, such as URLs with a password, AWS, Azure, Slack and Stripe keys,
  and two variables that make a secret together.
- `--arg` and `--input` take a negative number, such as `--arg -1`. Another
  value that starts with `-` needs the `=` form, such as `--input=-data.csv`.
- Each subcommand and flag has a line of help.

### Lint

- `jagt result lint` reads any YAML form, such as a flow-style mapping or a
  quoted key.
- `jagt result lint --check-files` refuses a path with a `..` part.
- `jagt draft lint` checks the fields of a draft strictly. It catches more
  claims of approval, bypasses, inline runs and broad actions. It no longer
  rejects "Never run inline." and other harmless text.

### Docs and package

- `docs/packet-file.md` describes the checks of a config prompt.
- `fixtures/agent_task/valid` holds valid packets, one with a nonce and
  layers.
- The package holds only the crate. The README has an install section.
- CI runs `just verify` on each pull request.

## 0.3.0

- `jagt render` saves the packet file `.agents/log/packets/<nonce>.json` in
  the shared log folder, and gives each packet a nonce.
- `jagt result lint --expect-nonce` checks the nonce of a result.
- `jagt render` joins the base task, the language layers and the repository
  text of a target.
