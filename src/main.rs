fn main() {
    if let Err(error) = jagt::run_cli() {
        eprintln!("{error}");
        std::process::exit(error.exit_code());
    }
}
