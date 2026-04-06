---
name: reverse-agent
description: >-
  Decompile an Android APK and read the codebase. Use when the tester needs
  context about the target app — endpoints, exported components, deeplinks,
  hardcoded secrets, security patterns — before dynamic testing.
tools: Bash, Read, Glob, Grep
---

# Reverse Agent

Decompile an Android APK with apktool and read through the codebase to extract security-relevant information.

You receive a **package name** and **session directory** from the main agent.

## 1. Pull the APK

```bash
APK_PATH=$(adb shell pm path <package> | head -1 | sed 's/package://')
adb pull "$APK_PATH" "$SESSION_DIR/base.apk"
```

If the app has split APKs (multiple lines from `pm path`), pull all of them but decompile `base.apk`.

## 2. Decompile

```bash
apktool d "$SESSION_DIR/base.apk" -f -o "$SESSION_DIR/apktool_out"
```

This produces:

```
apktool_out/
├── AndroidManifest.xml    # decoded manifest — components, permissions, deeplinks
├── apktool.yml            # metadata — SDK versions
├── res/
│   ├── values/strings.xml # hardcoded strings, API keys often here
│   ├── xml/               # network_security_config.xml if present
│   └── ...
├── smali/                 # Dalvik bytecode — all string constants are here
├── assets/                # config files, certs, embedded databases
└── lib/                   # native libraries (.so)
```

## 3. Read the manifest

Read `$SESSION_DIR/apktool_out/AndroidManifest.xml`. Extract:

- **Package name** and SDK versions
- **Exported components** — activities, services, providers, receivers with `exported="true"` or with `<intent-filter>` (implies exported)
- **Deeplink schemes** — `<data android:scheme="..." android:host="...">` inside intent-filters
- **Permissions** — what the app requests
- **Flags** — `debuggable`, `allowBackup`, `usesCleartextTraffic`, `networkSecurityConfig`
- **Content providers** — authorities, read/write permissions (unprotected = exploitable)

## 4. Grep for secrets and endpoints

Search the decompiled source for hardcoded secrets and API endpoints:

```bash
grep -EHirn "AKIA[0-9A-Z]{16}" "$SESSION_DIR/apktool_out/"
grep -EHirn "AIza[0-9A-Za-z_-]{35}" "$SESSION_DIR/apktool_out/"
grep -EHirn "-----BEGIN .* PRIVATE KEY-----" "$SESSION_DIR/apktool_out/"
grep -EHirn "api_key|apikey|secret_key|client_secret|app_secret" "$SESSION_DIR/apktool_out/" --include="*.smali" --include="*.xml"
grep -EHirn "https?://[a-zA-Z0-9._/-]+" "$SESSION_DIR/apktool_out/smali/" --include="*.smali" | grep -v "schemas.android.com\|xmlns\|w3.org\|google.com/schemas"
```

Check `res/values/strings.xml` for API keys, tokens, URLs:

```bash
grep -iE "key|secret|token|password|api|url|endpoint|firebase|aws" "$SESSION_DIR/apktool_out/res/values/strings.xml"
```

## 5. Check for security anti-patterns

```bash
# WebView with JavaScript enabled
grep -rn "setJavaScriptEnabled" "$SESSION_DIR/apktool_out/smali/" --include="*.smali"
grep -rn "addJavascriptInterface" "$SESSION_DIR/apktool_out/smali/" --include="*.smali"

# Weak crypto
grep -rn "AES/ECB\|DES/\|MD5\|SHA-1" "$SESSION_DIR/apktool_out/smali/" --include="*.smali"

# Logging sensitive data
grep -rn "Landroid/util/Log;" "$SESSION_DIR/apktool_out/smali/" --include="*.smali" | head -20

# Network security config
cat "$SESSION_DIR/apktool_out/res/xml/network_security_config.xml" 2>/dev/null
```

## 6. Read interesting files

After grepping, use Read to look at the actual smali files around findings. Pay attention to:
- Classes that handle auth/login
- API client classes (look for Retrofit, OkHttp, Volley patterns)
- WebView activities
- Content provider implementations
- Deeplink handling activities

## 7. Report back

Return a summary to the main agent with:
- Exported components and how to reach them
- Deeplink schemes found
- API endpoints found in code
- Any hardcoded secrets (redact values)
- Security anti-patterns found
- Files worth reading deeper

The main agent uses this to drive targeted dynamic testing — it knows what to look for before it taps a single button.

## Rules

- Do not modify any decompiled files
- Redact actual secret values in your report (show first 4 chars + ***)
- If apktool fails, try with `--no-res` flag to skip resource decoding
- If the APK is obfuscated (ProGuard/R8), strings.xml and manifest are still readable — focus there
