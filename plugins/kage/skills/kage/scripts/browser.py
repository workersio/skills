#!/usr/bin/env python3
"""
Browser-Based HTTP Request Helper (Camoufox)

Uses Camoufox (anti-detection Firefox) for targets where curl_cffi gets blocked.
Real browser = real TLS fingerprint + JS execution + full cookie handling.

Use this when:
- Target has Cloudflare Turnstile / advanced bot detection
- JS execution is required (cookie walls, challenge pages)
- curl_cffi requests are getting 403/captcha responses

Usage as library:
    from browser import browser_get, browser_post, BrowserSession

    resp = browser_get("https://protected-target.com/api/users")
    resp = browser_post("https://target.com/login", data={"user": "x", "pass": "y"})

Usage as CLI:
    python3 browser.py GET "https://target.com"
    python3 browser.py POST "https://target.com/api" --data '{"key":"val"}'

Returns same format as tls.py: {"status", "body", "headers", "via", "error"}
"""
import json
import sys

_camoufox_available = False
try:
    from camoufox.sync_api import Camoufox
    _camoufox_available = True
except ImportError:
    pass

if not _camoufox_available:
    print("[browser-request] WARNING: camoufox not installed.", file=sys.stderr)
    print("[browser-request] Install: pip install camoufox && python3 -m camoufox fetch", file=sys.stderr)


def browser_get(url, headers=None, proxy=None, timeout=30):
    """GET request using real browser. Slow but undetectable."""
    return browser("GET", url, headers=headers, proxy=proxy, timeout=timeout)


def browser_post(url, headers=None, data=None, proxy=None, timeout=30):
    """POST request using real browser."""
    return browser("POST", url, headers=headers, data=data, proxy=proxy, timeout=timeout)


def browser(method, url, headers=None, data=None, proxy=None, timeout=30):
    """HTTP request via Camoufox browser. Returns same format as tls.py."""
    if not _camoufox_available:
        return {"status": None, "body": "", "headers": {}, "error": "camoufox not installed", "via": "browser-unavailable"}

    camoufox_kwargs = {"headless": True}
    if proxy:
        camoufox_kwargs["proxy"] = {"server": proxy}

    try:
        with Camoufox(**camoufox_kwargs) as browser:
            page = browser.new_page()
            page.set_default_timeout(timeout * 1000)

            if headers:
                page.set_extra_http_headers(headers)

            if method.upper() == "GET":
                response = page.goto(url, wait_until="networkidle")
            elif method.upper() == "POST" and data:
                # For POST, use page.evaluate to make fetch request from browser context
                js_headers = json.dumps(headers or {})
                js_body = json.dumps(data) if isinstance(data, dict) else json.dumps(data)
                fetch_script = f"""
                async () => {{
                    const resp = await fetch("{url}", {{
                        method: "POST",
                        headers: {{...{js_headers}, "Content-Type": "application/json"}},
                        body: {js_body},
                        credentials: "include"
                    }});
                    const body = await resp.text();
                    const headers = Object.fromEntries(resp.headers.entries());
                    return {{status: resp.status, body: body, headers: headers}};
                }}
                """
                # Navigate to origin first to avoid CORS
                origin = "/".join(url.split("/")[:3])
                page.goto(origin, wait_until="networkidle")
                result = page.evaluate(fetch_script)
                page.close()
                return {
                    "status": result["status"],
                    "body": result["body"],
                    "headers": result["headers"],
                    "via": "camoufox-browser",
                }
            else:
                response = page.goto(url, wait_until="networkidle")

            body = page.content()
            status = response.status if response else None
            resp_headers = response.all_headers() if response else {}
            page.close()

            return {
                "status": status,
                "body": body,
                "headers": dict(resp_headers),
                "via": "camoufox-browser",
            }
    except Exception as e:
        return {"status": None, "body": "", "headers": {}, "error": str(e), "via": "camoufox-browser"}


class BrowserSession:
    """Persistent browser session with cookies and state."""

    def __init__(self, proxy=None, headless=True):
        if not _camoufox_available:
            raise ImportError("camoufox not installed. Run: pip install camoufox && python3 -m camoufox fetch")
        self.proxy = proxy
        self.headless = headless
        self._browser = None
        self._context = None
        self._page = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.close()

    def start(self):
        kwargs = {"headless": self.headless}
        if self.proxy:
            kwargs["proxy"] = {"server": self.proxy}
        from camoufox.sync_api import Camoufox
        self._cm = Camoufox(**kwargs)
        self._browser = self._cm.__enter__()
        self._page = self._browser.new_page()

    def close(self):
        if self._page:
            self._page.close()
        if self._cm:
            self._cm.__exit__(None, None, None)

    def get(self, url, timeout=30):
        self._page.set_default_timeout(timeout * 1000)
        response = self._page.goto(url, wait_until="networkidle")
        return {
            "status": response.status if response else None,
            "body": self._page.content(),
            "headers": dict(response.all_headers()) if response else {},
            "via": "camoufox-session",
        }

    def post_fetch(self, url, data=None, headers=None, timeout=30):
        """POST via fetch() from browser context (maintains cookies)."""
        self._page.set_default_timeout(timeout * 1000)
        js_headers = json.dumps(headers or {})
        js_body = json.dumps(data) if isinstance(data, dict) else json.dumps(data)
        result = self._page.evaluate(f"""
        async () => {{
            const resp = await fetch("{url}", {{
                method: "POST",
                headers: {{...{js_headers}, "Content-Type": "application/json"}},
                body: {js_body},
                credentials: "include"
            }});
            const body = await resp.text();
            const headers = Object.fromEntries(resp.headers.entries());
            return {{status: resp.status, body: body, headers: headers}};
        }}
        """)
        return {
            "status": result["status"],
            "body": result["body"],
            "headers": result["headers"],
            "via": "camoufox-session",
        }

    def execute_js(self, script):
        """Run arbitrary JS in browser context."""
        return self._page.evaluate(script)

    def cookies(self):
        """Get all cookies from browser context."""
        return self._page.context.cookies()


# ── CLI ───────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Browser-based HTTP request (Camoufox)")
    parser.add_argument("method", help="GET or POST")
    parser.add_argument("url")
    parser.add_argument("--data", default=None, help="JSON body for POST")
    parser.add_argument("--proxy", default=None, help="Proxy URL")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    data = json.loads(args.data) if args.data else None
    resp = browser(args.method, args.url, data=data, proxy=args.proxy)
    output = json.dumps(resp, indent=2)
    print(output)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
