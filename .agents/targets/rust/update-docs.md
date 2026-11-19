# Rust rules for the docs

These rules add to the base task for the docs of the Rust code of the change.

- **A doc for each item.** Write a `///` comment for each function, method, struct, enum, variant, field, trait,
  constant and module, public or private. Start each crate root and each module file with a `//!` comment.
  `docstring-check` fails on an item without one.
- **The first line.** The first line of a doc comment is one sentence that says what the item is for. rustdoc
  shows it in the lists of items.
- **The sections.** Use the headings that rustdoc and clippy know:
  - `# Examples` with a code block that compiles and runs as a doctest, a test that `cargo test` makes from
    the code block of a doc comment. Give one for each public function whose
    use is not plain from its signature.
  - `# Errors` for a function that returns a `Result`. Say when it returns each kind of error.
  - `# Panics` for a function that can panic. Say on which input.
  - `# Safety` for an `unsafe` function or trait. Say what the caller must make sure of.
- **Links.** Name another item with an intra-doc link, a link to the item by its Rust path, as in ``[`Parser::parse`]``, so that `cargo doc` checks
  the link.
- **The README.** A crate that is published gives its README in `Cargo.toml` with the key `readme`. Keep the
  example of the README in step with the example of the crate root.
