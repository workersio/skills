# workers-app-tester

Test Android apps on a rooted device. Give a coding agent access to a phone — it observes the screen, taps buttons, intercepts traffic, and finds vulnerabilities autonomously.

## Requirements

- Rooted Android device or emulator (Magisk via [rootAVD](https://gitlab.com/newbit/rootAVD))
- ADB connected
- [mitmproxy](https://mitmproxy.org/) installed
- [Frida](https://frida.re/) installed (for SSL pinning bypass)
- Python 3.10+

## What's included

| File | Purpose |
|------|---------|
| `scripts/ui.py` | Parse UI hierarchy into numbered interactive elements |
| `scripts/capture.py` | mitmproxy addon — logs HTTP flows to JSONL |
| `scripts/traffic.py` | Summarize recent traffic by time window |
| `scripts/analyze.py` | Security analyzer — IDORs, auth, exposure, headers |
| `scripts/bypass.js` | Frida SSL pinning bypass (8 hook targets) |
| `references/frida.md` | Frida setup, codeshare scripts, hooking patterns |
| `references/testing-methodology.md` | What to do with each finding type |
| `references/agents/reverse-agent.md` | APK decompilation sub-agent |

## Install

```bash
npx skills add workersio/spec
```

## Usage

Tell the agent to test an app:

```
Test com.example.app. creds: user@example.com / password123
```

The agent will set up the proxy, launch the app, login, intercept traffic, and find vulnerabilities.

## The loop

1. **Observe** — dump the screen with `ui.py`, get a numbered list of interactive elements
2. **Act** — tap, type, or scroll via ADB
3. **Intercept** — read the traffic that action produced with `traffic.py`
4. **Decide** — pick the next action based on what it sees

Repeat until done.
