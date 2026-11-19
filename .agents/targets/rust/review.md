# Rust rules for the review

These rules add to the review lenses for the Rust code of the change.

- **Unwraps and panics.** Check each new `unwrap()`, `expect()`, `panic!`, index with `[]` and integer cast with
  `as`. A library function returns a `Result` for a failure that a caller can meet. A panic is correct only for a
  bug in the program, and its message says which rule was broken.
- **Unsafe code.** Each new `unsafe` block has a `// SAFETY:` comment that says why the block is sound. If the
  comment is missing or does not match the code, report a finding.
- **Errors.** An error keeps its cause, for example with `?` and `From`, or with a `source()`. Do not accept an
  error that becomes a `String` and loses its type in library code.
- **Public items.** A new `pub` item is part of the API of the crate. Check that it must be public, and that
  `pub(crate)` is not enough.
- **The docs lens.** A doc comment says what the item is for, beyond what its name says. A function that returns
  a `Result` has a section `# Errors`. A function that can panic has a section `# Panics`. A function that is
  `unsafe` has a section `# Safety`. A stub, for example `/// Returns the result.`, is a finding.
- **Allowed lints.** Each new `#[allow(...)]` or `#[expect(...)]` names a reason, in a comment or with
  `reason = "..."`. A new `#[allow(missing_docs)]` or `#[allow(clippy::missing_docs_in_private_items)]` hides
  an item from `docstring-check`, so it needs a reason as strong as an entry in the exclude list.
