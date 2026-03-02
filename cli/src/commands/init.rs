use cliclack::{intro, log, multiselect, outro, select, spinner};

use crate::installer::{self, Scope};
use crate::registry;

const BANNER: &str = concat!(
    "\n",
    " ███████╗██████╗ ███████╗ ██████╗\n",
    " ██╔════╝██╔══██╗██╔════╝██╔════╝\n",
    " ███████╗██████╔╝█████╗  ██║     \n",
    " ╚════██║██╔═══╝ ██╔══╝  ██║     \n",
    " ███████║██║     ███████╗╚██████╗\n",
    " ╚══════╝╚═╝     ╚══════╝ ╚═════╝\n",
    "                    by workers.io\n",
);

pub fn run() {
    println!("{}", BANNER);
    intro("@workersio/spec").expect("Failed to show intro");

    let marketplace = match registry::load() {
        Ok(m) => m,
        Err(e) => {
            log::error(format!("{}", e)).expect("Failed to show error");
            outro("Failed to load marketplace.").expect("Failed to show outro");
            return;
        }
    };

    log::info("Browse and install plugins to extend your Claude Code experience.")
        .expect("Failed to show info");

    let plugins = &marketplace.plugins;
    if plugins.is_empty() {
        outro("No plugins available in the marketplace.").expect("Failed to show outro");
        return;
    }

    let mut prompt = multiselect("Which plugins would you like to install?");
    for plugin in plugins {
        let label = format!("{} — {}", plugin.name, plugin.description);
        prompt = prompt.item(plugin.name.clone(), label, "");
    }
    let selected: Vec<String> = match prompt.interact() {
        Ok(s) => s,
        Err(_) => {
            outro("Cancelled.").expect("Failed to show outro");
            return;
        }
    };

    if selected.is_empty() {
        outro("No plugins selected.").expect("Failed to show outro");
        return;
    }

    let scope: Scope = match select("Where should we install the plugins?")
        .item(
            Scope::Project,
            "Project",
            ".claude/settings.json in current directory",
        )
        .item(Scope::User, "User", "~/.claude/settings.json")
        .interact()
    {
        Ok(s) => s,
        Err(_) => {
            outro("Cancelled.").expect("Failed to show outro");
            return;
        }
    };

    let selected_plugins: Vec<_> = plugins
        .iter()
        .filter(|p| selected.contains(&p.name))
        .cloned()
        .collect();

    let sp = spinner();
    sp.start("Installing plugins...");

    match installer::install(&selected_plugins, &scope) {
        Ok(()) => {
            sp.stop("Plugins installed.");
        }
        Err(e) => {
            sp.stop(format!("Failed to install: {}", e));
            outro("Installation failed.").expect("Failed to show outro");
            return;
        }
    }

    let path = installer::settings_path(&scope);
    log::info(format!("Enabled in {}", path.display())).expect("Failed to show info");

    outro("Done! Restart Claude Code to load your new plugins.")
        .expect("Failed to show outro");
}
