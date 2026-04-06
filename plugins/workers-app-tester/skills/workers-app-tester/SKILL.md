---
name: workers-app-tester
description: >-
  Test Android apps on a rooted device. Decompile APKs, intercept traffic,
  parse UI, test for IDORs, bypass SSL pinning, hook methods with Frida,
  inspect exported components, read local storage, and find sensitive data.
  Use when asked to "test this app", "find bugs", "pentest", "reverse
  engineer", "decompile", "intercept requests", "check for IDORs", "bypass
  cert pinning", "hook this method", or "check deeplinks".
metadata:
  author: workers.io
  version: "3.0.0"
---

# Workers App Tester

Pentest Android apps through a rooted device. Drives the device UI, intercepts network traffic, and uses Frida for runtime analysis.

For detailed guides, load these on demand:
- [references/testing-methodology.md](references/testing-methodology.md) — IDOR, auth, exposure, local storage, deeplinks, exported components, logging
- [references/frida.md](references/frida.md) — SSL bypass, root bypass, codeshare scripts, hooking patterns, custom certs
- [agents/reverse-agent.md](agents/reverse-agent.md) — APK decompilation sub-agent, reads codebase for endpoints, secrets, components

## Session Setup

### 1. Pick the target

```bash
adb shell pm list packages -3
adb shell dumpsys activity activities | grep -m 1 -E 'topResumedActivity=|ResumedActivity:|mFocusedApp='
```

### 2. Create session directory

```bash
SESSION_DIR=/tmp/workers-app-tester-$(date +%Y%m%d-%H%M%S)
mkdir -p "$SESSION_DIR"
```

### 3. Start traffic interception

Set `PRESERVE_AUTH=1` so auth headers are logged in full, not redacted.

```bash
adb shell settings put global http_proxy 10.0.2.2:8080

ANDROID_APP_TESTER_OUT_DIR="$SESSION_DIR" \
ANDROID_APP_TESTER_PACKAGE="<package>" \
ANDROID_APP_TESTER_PRESERVE_AUTH=1 \
nohup mitmdump --set block_global=false --listen-host 0.0.0.0 --listen-port 8080 \
  -s scripts/capture.py >"$SESSION_DIR/mitmdump.log" 2>&1 &
echo $! >"$SESSION_DIR/mitmdump.pid"
```

For physical devices, replace `10.0.2.2` with the host IP.

### 4. Launch the app

```bash
adb shell am force-stop <package> || true
adb shell monkey -p <package> -c android.intent.category.LAUNCHER 1
```

### 5. If no HTTPS traffic appears

The app uses SSL pinning. See [references/frida.md](references/frida.md) — start frida-server, then spawn the app with `bypass.js`.

## Static Analysis

Dispatch to the **reverse-agent** with the package name and session directory. It will:
1. Pull the APK from the device
2. Decompile with apktool (manifest, smali, resources)
3. Grep for hardcoded secrets, API endpoints, security anti-patterns
4. Read through interesting files for deeper context

Returns: exported components, deeplink schemes, API endpoints, hardcoded secrets, security issues.

Use these findings to drive targeted testing in The Loop.

## The Loop

### 1. Observe

```bash
python3 scripts/ui.py
```

Returns a compact numbered list of interactive elements:

```
[1] "Sign In" btn @ (540,1200) bounds=[380,1150][700,1250] clickable
[2] "Email" input @ (540,400) bounds=[100,350][980,450] focusable
```

### 2. Act

One action per cycle. Tap element [1]:

```bash
adb shell input tap 540 1200
```

For text fields, tap then type:

```bash
adb shell input tap 540 400
adb shell input text "test@example.com"
```

### 3. Intercept

```bash
python3 scripts/traffic.py --input "$SESSION_DIR/traffic.jsonl" --since-seconds 15 --limit 10
```

With headers and bodies:

```bash
python3 scripts/traffic.py --input "$SESSION_DIR/traffic.jsonl" --since-seconds 15 --show-headers --show-body
```

### 4. Decide next step and repeat

## Security Analysis

After exercising the app's main flows, run the analyzer:

```bash
python3 scripts/analyze.py --input "$SESSION_DIR/traffic.jsonl" --mode full
```

Individual modes: `endpoints`, `idor`, `auth`, `exposure`, `headers`.

See [references/testing-methodology.md](references/testing-methodology.md) for what to do with each finding.

## ADB Reference

| Action      | Command                                              |
|-------------|------------------------------------------------------|
| Tap         | `adb shell input tap <x> <y>`                        |
| Type        | `adb shell input text "hello%sworld"` (%s = space)   |
| Scroll down | `adb shell input swipe 540 1500 540 500 300`         |
| Scroll up   | `adb shell input swipe 540 500 540 1500 300`         |
| Back        | `adb shell input keyevent KEYCODE_BACK`              |
| Home        | `adb shell input keyevent KEYCODE_HOME`              |
| Enter       | `adb shell input keyevent KEYCODE_ENTER`             |
| Long press  | `adb shell input swipe <x> <y> <x> <y> 1000`        |
| Launch app  | `adb shell monkey -p <pkg> -c android.intent.category.LAUNCHER 1` |
| Force stop  | `adb shell am force-stop <pkg>`                      |

## Session Teardown

```bash
kill "$(cat "$SESSION_DIR/mitmdump.pid")" 2>/dev/null || true
adb shell settings delete global http_proxy
adb shell "su -c 'pkill frida-server'" 2>/dev/null || true
```

## Rules

- One UI action per cycle. Observe, act, intercept, then decide.
- Always run `ui.py` before acting so coordinates match the current screen.
- Always tear down the session when done. The proxy setting persists across reboots.
- Document findings: endpoint, vulnerability type, reproduction steps, evidence.
- NEVER use `sleep` in any command. No `sleep 1`, no `sleep 2`, no `sleep && command`. Run commands directly. `ui.py` handles its own timing. Chain with `&&` if needed.
- Be fast. No unnecessary delays between actions.

## Bundled Scripts

| Script | Purpose |
|--------|---------|
| `scripts/ui.py` | Smart UI parser. Filters to interactive elements with spatial dedup. |
| `scripts/capture.py` | mitmproxy addon. Logs to JSONL. Set `PRESERVE_AUTH=1` to keep auth headers. |
| `scripts/traffic.py` | Traffic viewer. `--since-seconds`, `--show-headers`, `--show-body`. |
| `scripts/analyze.py` | Security analyzer. Modes: `endpoints`, `idor`, `auth`, `exposure`, `headers`, `full`. |
| `scripts/bypass.js` | SSL pinning bypass. TrustManagerImpl, OkHttp3, SSLContext, Conscrypt. |
