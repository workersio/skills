# Testing Methodology

What to do with each finding from `analyze.py`.

## IDOR Findings

For each candidate the `idor` mode reports:

1. Get the full request with `traffic.py --show-body`
2. Change the ID to another user's value
3. Replay the request
4. If the response contains another user's data, it is an IDOR

Common patterns:
- Sequential numeric IDs in paths: `/api/orders/1001` -> try `/api/orders/1002`
- UUIDs in paths: substitute another user's UUID
- ID-like query params: `?user_id=123` -> `?user_id=124`

## Auth Findings

Follow the test suggestions from `auth` mode:

- **Token removal**: Strip the auth header and replay. Does the endpoint still respond with data?
- **Token replay**: After logout, replay the old token. Does it still work?
- **Role escalation**: If JWT contains `role: user`, modify to `role: admin` and replay
- **Expired tokens**: Does the API enforce token expiry from the `exp` claim?
- **Token in URL**: Check if tokens appear in query params (gets logged, leaked via Referer)

## Exposure Findings

The `exposure` mode flags PII patterns (emails, phones, credit cards, API keys, AWS keys, Firebase keys, JWTs, SSN patterns, private keys) and large responses (>50KB) as potential over-fetching.

Check if the flagged data is necessary for the UI. If the response returns more than the screen shows, it is over-fetching.

## Header Findings

The `headers` mode checks: missing HSTS, missing CSP, missing X-Content-Type-Options, missing X-Frame-Options, CORS `Allow-Origin: *` with credentials, and server version disclosure.

## Local Storage

Apps often store tokens, credentials, and PII in plaintext on disk.

SharedPreferences:

```bash
adb shell "su -c 'ls /data/data/<package>/shared_prefs/'"
adb shell "su -c 'cat /data/data/<package>/shared_prefs/*.xml'"
```

Databases:

```bash
adb shell "su -c 'ls /data/data/<package>/databases/'"
adb shell "su -c 'sqlite3 /data/data/<package>/databases/<name>.db \".tables\"'"
adb shell "su -c 'sqlite3 /data/data/<package>/databases/<name>.db \"SELECT * FROM users LIMIT 10\"'"
```

Cache and files:

```bash
adb shell "su -c 'ls /data/data/<package>/cache/'"
adb shell "su -c 'ls /data/data/<package>/files/'"
```

Look for: auth tokens, session IDs, passwords, API keys, PII stored without encryption.

## Exported Components

Check the attack surface — exported activities, services, providers, receivers:

```bash
adb shell dumpsys package <package> | grep -A5 "exported=true"
```

Launch an exported activity directly (bypasses normal navigation):

```bash
adb shell am start -n <package>/<activity_class>
```

Send a broadcast to an exported receiver:

```bash
adb shell am broadcast -a <action>
```

Start an exported service:

```bash
adb shell am startservice -n <package>/<service_class>
```

## Deeplinks

Extract deeplink schemes from the manifest:

```bash
adb shell dumpsys package <package> | grep -E "scheme|host|pathPrefix|pathPattern"
```

Test a deeplink:

```bash
adb shell am start -a android.intent.action.VIEW -d "scheme://host/path"
```

Deeplinks that handle sensitive actions (password reset, account linking, payment) without proper validation are high-severity bugs.

## Logging

Monitor what the app logs at runtime. Apps sometimes log tokens, passwords, or user data:

```bash
adb logcat --pid=$(adb shell pidof -s <package>) 2>/dev/null
```

Grep for sensitive keywords in logs:

```bash
adb logcat --pid=$(adb shell pidof -s <package>) | grep -iE "token|password|secret|key|auth|session|bearer"
```

## Sensitive Keyword Grep (Static)

After decompiling an APK (with apktool or jadx), search for hardcoded secrets:

Keywords to search: `accesskey`, `admin`, `aes`, `api_key`, `apikey`, `checkClientTrusted`, `crypt`, `http:`, `password`, `pinning`, `secret`, `SHA256`, `SharedPreferences`, `superuser`, `token`, `X509TrustManager`, `insert into`.

```bash
grep -EHirn --include=*.{smali,xml,java,txt} "api_key|apikey|secret|password|token|accesskey" <decompiled_folder>/
```

## Vulnerability Classes

From real bug bounty reports, the most common Android findings:

| Category | What to look for |
|----------|-----------------|
| Hardcoded credentials | API keys, secrets, passwords in source/strings.xml |
| WebView vulnerabilities | `setJavaScriptEnabled(true)` + `addJavascriptInterface` + loading external URLs |
| Insecure deeplinks | Deeplinks that perform actions without auth validation |
| Content provider injection | SQL injection via exported content providers |
| Insecure local storage | Plaintext tokens/passwords in SharedPreferences or SQLite |
| Weak cryptography | ECB mode, hardcoded keys, MD5/SHA1 for security |
| Session theft | Tokens in logs, URLs, or accessible storage |
| Broadcast hijacking | Sensitive data in broadcasts without permissions |
| Screenshot exposure | App doesn't set `FLAG_SECURE`, sensitive screens can be captured |
