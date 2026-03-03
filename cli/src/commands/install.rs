use cliclack::{intro, log, outro, select, spinner};

use crate::installer::{self, Scope};
use crate::registry;

pub fn run(name: &str, scope_flag: Option<&str>) {
    intro("@workersio/spec").expect("Failed to show intro");

    let marketplace = match registry::load() {
        Ok(m) => m,
        Err(e) => {
            log::error(format!("{}", e)).expect("Failed to show error");
            outro("Failed to load marketplace.").expect("Failed to show outro");
            return;
        }
    };

    let plugin = match marketplace.plugins.iter().find(|p| p.name == name) {
        Some(p) => p.clone(),
        None => {
            let available: Vec<&str> = marketplace.plugins.iter().map(|p| p.name.as_str()).collect();
            log::error(format!(
                "Plugin '{}' not found. Available plugins: {}",
                name,
                available.join(", ")
            ))
            .expect("Failed to show error");
            outro("Installation cancelled.").expect("Failed to show outro");
            return;
        }
    };

    log::info(format!("Installing plugin: {}", name)).expect("Failed to show info");

    let scope: Scope = if let Some(s) = scope_flag {
        match s {
            "project" => Scope::Project,
            "user" => Scope::User,
            _ => {
                log::error(format!(
                    "Invalid scope '{}'. Use 'project' or 'user'.",
                    s
                ))
                .expect("Failed to show error");
                outro("Installation cancelled.").expect("Failed to show outro");
                return;
            }
        }
    } else {
        match select("Where should we install?")
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
        }
    };

    let sp = spinner();
    sp.start("Installing plugin...");

    match installer::install(&[plugin], &scope) {
        Ok(()) => {
            sp.stop("Plugin installed.");
        }
        Err(e) => {
            sp.stop(format!("Failed to install: {}", e));
            outro("Installation failed.").expect("Failed to show outro");
            return;
        }
    }

    let path = installer::settings_path(&scope);
    log::info(format!("Enabled in {}", path.display())).expect("Failed to show info");

    outro("Done! Restart Claude Code to load your new plugin.")
        .expect("Failed to show outro");
}
