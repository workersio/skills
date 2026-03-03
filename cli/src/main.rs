mod commands;
mod installer;
mod registry;

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(
    name = "spec",
    about = "workers.io — A plugin marketplace for Claude Code",
    before_help = concat!(
        "\n",
        " ███████╗██████╗ ███████╗ ██████╗\n",
        " ██╔════╝██╔══██╗██╔════╝██╔════╝\n",
        " ███████╗██████╔╝█████╗  ██║     \n",
        " ╚════██║██╔═══╝ ██╔══╝  ██║     \n",
        " ███████║██║     ███████╗╚██████╗\n",
        " ╚══════╝╚═╝     ╚══════╝ ╚═════╝\n",
        "                    by workers.io\n",
    )
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Browse and install plugins from the workers.io marketplace
    Init,
    /// Install a specific plugin by name
    Install {
        /// Name of the plugin to install
        name: String,
        /// Installation scope: "project" or "user" (skips interactive prompt)
        #[arg(long)]
        scope: Option<String>,
    },
}

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Init => commands::init::run(),
        Commands::Install { name, scope } => commands::install::run(&name, scope.as_deref()),
    }
}
