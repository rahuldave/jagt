# The integration tool of the rust profile: the test targets, such as the files of the folder tests, with cargo
# llvm-cov. just install integration adds it, and jnprofile-rust installs this file.

# Run the integration tests with coverage into target/llvm-cov/integration.lcov. Extra arguments go to cargo llvm-cov test: just integration parse. Alone, it saves JLOG_RUN
integration *args:
    {{rust_py}} {{rust_steps}} run integration "$@"
