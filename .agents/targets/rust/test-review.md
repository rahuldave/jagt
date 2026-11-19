# Rust rules for the test review

These rules add to the base task for the Rust tests of the change.

- **Where the tests are.** A unit test is in a module `#[cfg(test)] mod tests` in the file of its code. An
  integration test is a file in `tests/`, and it uses only the public API of the crate. A test of a private
  function belongs in the unit tests.
- **Test-parent and unit tests.** A unit test is in the same file as its code. A copy of that file in the parent
  commit brings the new code too, so the key `tests` of the profile names only `tests/**`. When no changed file
  matches it, `test-parent` runs no test and records that no test ran on the parent. Judge each new unit test from
  the diff alone, and also each test of a workspace member, such as `crates/x/tests/a.rs`, which `tests/**` misses.
- **Each test checks a result.** A test calls `assert!`, `assert_eq!` or `assert_ne!`, or it returns a `Result`
  and uses `?` on a value that it checks. A test that only calls the code and checks nothing is a finding.
  `#[should_panic]` names the text of the panic with `expected = "..."`.
- **The exclude list.** Stable Rust has no pragma that leaves out one line from the coverage. So the profile reads
  `.agents/coverage-exclude.txt`, a list of files and globs, from the parent commit. Each new entry needs a reason
  in a comment line above it, for example `# the main function only parses the arguments`. An entry without a
  reason, or an entry that names a file with logic that a test can reach, is a finding.
- **Files that a list already excludes.** A change to a file that the parent commit already lists in
  `coverage-exclude.txt` or `generated.txt` passes `coverage-check` without a test. Judge each such change, and
  report new logic in it that a test can reach.
- **Code that the coverage cannot see.** cargo llvm-cov sets `cfg(coverage)`, so code under
  `#[cfg(not(coverage))]` does not count, as with a pragma. A `#[path]` attribute that puts library code in a
  folder `tests` or `benches` hides it from the report, and `coverage-check` does not count those folders. Report
  each new case.
- **Macros.** LLVM counts the code of a `macro_rules!` macro at the line that calls it. So `coverage-check` cannot
  see a branch of a macro that no test runs. Check each branch of a new or changed macro by hand.
- **Features and platforms.** The steps run with `--all-features`, on the platform of the machine. Code for
  another platform, such as `#[cfg(windows)]`, or behind a feature that cannot be on with the others, runs in no
  step. Check that such code has a test that runs on a platform where it compiles.
- **Ignored tests.** Each new `#[ignore]` names a reason, as in `#[ignore = "needs a network"]`. An ignored test
  does not run in `just test`, so its lines do not count as covered.
