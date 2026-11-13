# Changelog

This file lists the changes of each version of jagt. The newest version comes
first.

## 0.4.0

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
