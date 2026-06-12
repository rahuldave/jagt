const HELP: &str = "\
jagt 0.1.0
Deterministic renderer and validator scaffold for AGENT_TASK v1 packets.

USAGE:
    jagt --help

NEXT:
    Review jagt_deterministic_renderer_spec.md and promote accepted MVP scope
    through Gest before implementing render/lint/explain commands.
";

fn main() {
    let wants_help = std::env::args()
        .skip(1)
        .any(|arg| arg == "--help" || arg == "-h");

    if wants_help {
        print!("{HELP}");
    } else {
        println!(
            "jagt scaffold ready. Run `jagt --help` and review jagt_deterministic_renderer_spec.md."
        );
    }
}
