use serde::Deserialize;

const MARKETPLACE_URL: &str =
    "https://raw.githubusercontent.com/workersio/spec/main/.claude-plugin/marketplace.json";

#[derive(Deserialize)]
pub struct Marketplace {
    pub plugins: Vec<Plugin>,
}

#[derive(Deserialize, Clone)]
pub struct Plugin {
    pub name: String,
    pub source: String,
    pub description: String,
}

pub fn load() -> Result<Marketplace, String> {
    let body = ureq::get(MARKETPLACE_URL)
        .call()
        .map_err(|e| format!("Failed to fetch marketplace: {}", e))?
        .body_mut()
        .read_to_string()
        .map_err(|e| format!("Failed to read response: {}", e))?;

    serde_json::from_str(&body).map_err(|e| format!("Failed to parse marketplace.json: {}", e))
}
