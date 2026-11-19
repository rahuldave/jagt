# Rust rules for the prose

These rules add to the base task for the prose of the Rust docs of the change.

- **Doc comments are prose.** Apply the guide to the text of each changed `///` and `//!` comment, as to a page.
  Keep the code blocks, the intra-doc links and the section headings, such as `# Errors`, as they are.
- **The first sentence.** rustdoc shows the first sentence alone in the lists of items. Make it a complete
  sentence that makes sense without the rest of the comment.
- **Names in code.** Write the name of a type, a function or a crate in backticks, as in `Vec<u8>`, so that the
  check of the guide and the reader see it as code.
