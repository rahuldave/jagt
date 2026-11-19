# The test tool of the rust profile: cargo llvm-cov and diff-cover. just install test adds it, and jnprofile-rust
# installs this file.

# Run the unit tests, of the library and the binaries, with coverage into target/llvm-cov/test.lcov. Extra arguments go to cargo llvm-cov test: just test parse. Alone, it saves JLOG_RUN
test *args:
    {{rust_py}} {{rust_steps}} run test "$@"

# Fail on each changed line of code that no test runs, and on the first commit on each line. A line that test or integration runs passes; the report of integration counts when integration is in the steps of just check. It reads each report only from the same run of just, JLOG_RUN, and the same tree. Otherwise it runs those tests first
coverage-check:
    {{rust_py}} {{rust_steps}} fresh test || {{rust_py}} {{rust_steps}} run test
    {{rust_py}} {{rust_steps}} fresh integration || {{rust_py}} {{rust_steps}} run integration
    {{rust_py}} {{rust_steps}} coverage

# Run the tests of some files in the folder tests, without coverage: just test-paths tests/parse.rs
test-paths *paths:
    {{rust_py}} {{rust_steps}} test-paths "$@"
