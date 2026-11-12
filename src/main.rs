//! The `jagt` command. It runs [`jagt::run_cli`], and on a [`jagt::JagtError`] it exits with that
//! error's exit code.

/// Run the command, print any error to standard error, and exit with its code.
fn main() {
    if let Err(error) = jagt::run_cli() {
        eprintln!("{error}");
        std::process::exit(error.exit_code());
    }
}
