# The docstring tool of the rust profile: the lints missing_docs and clippy::missing_docs_in_private_items. just
# install docstring adds it, and jnprofile-rust installs this file.

# Fail on each item with no doc comment, public or private, and name its file and line
docstring-check:
    {{rust_py}} {{rust_steps}} docs
