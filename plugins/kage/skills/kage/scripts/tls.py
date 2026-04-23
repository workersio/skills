#!/usr/bin/env python3
"""
TLS-Fingerprinted HTTP Request Helper

Uses curl_cffi (curl-impersonate) to make requests that mimic real browser
TLS/HTTP2 fingerprints. WAFs can't detect these as bot traffic.

Usage as library:
    from tls import request, tls_get, tls_post, TLSSession

    resp = tls_get("https://target.com/api/users", token="Bearer eyJ...")
    resp = tls_post("https://target.com/api/login", json_data={"user": "x"})

Usage as CLI:
    python3 tls.py GET "https://target.com/api/users" --token "Bearer eyJ..."
    python3 tls.py POST "https://target.com/api/login" --data '{"user":"x"}'

Falls back to urllib if curl_cffi is not installed.
"""
import json
import sys
import os
import random

# Supported browser fingerprints for rotation
_FINGERPRINTS = ["chrome124", "chrome131", "safari17_0", "firefox133"]

# Try curl_cffi first, fall back to urllib
_cffi_available = False
try:
    from curl_cffi import requests as curl_requests
    _cffi_available = True
except ImportError:
    pass

if not _cffi_available:
    import urllib.request
    import urllib.error
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    print("[tls-request] WARNING: curl_cffi not installed. Using urllib (detectable by WAF).", file=sys.stderr)
    print("[tls-request] Install: pip install curl_cffi", file=sys.stderr)


# ── TLS Client Session (reused across calls) ──────────────

_session = None

def _get_session(impersonate=None):
    global _session
    if _session is None and _cffi_available:
        fp = impersonate or random.choice(_FINGERPRINTS)
        _session = curl_requests.Session(impersonate=fp)
    return _session


# ── Request via curl_cffi ────────────────────────────────

def _via_cffi(method, url, headers=None, data=None, impersonate=None, timeout=15):
    session = _get_session(impersonate)
    kwargs = {"headers": headers or {}, "timeout": timeout}

    if data:
        if isinstance(data, dict):
            kwargs["json"] = data
        else:
            kwargs["data"] = data

    try:
        resp = session.request(method.upper(), url, **kwargs)
        fp_used = impersonate or getattr(session, "impersonate", None) or "unknown"
        return {
            "status": resp.status_code,
            "body": resp.text,
            "headers": dict(resp.headers),
            "via": f"curl_cffi ({fp_used})",
        }
    except Exception as e:
        return {"status": None, "body": "", "headers": {}, "error": str(e), "via": "curl_cffi"}


# ── Fallback via urllib ───────────────────────────────────

def _via_urllib(method, url, headers=None, data=None, timeout=15):
    hdrs = headers or {}
    body = None
    if data:
        if isinstance(data, dict):
            body = json.dumps(data).encode()
            hdrs.setdefault("Content-Type", "application/json")
        else:
            body = data.encode() if isinstance(data, str) else data

    req = urllib.request.Request(url, method=method.upper(), headers=hdrs, data=body)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return {
            "status": resp.status,
            "body": resp.read().decode(errors="replace"),
            "headers": dict(resp.headers),
            "via": "urllib-fallback",
        }
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace") if e.fp else ""
        return {
            "status": e.code,
            "body": body_text,
            "headers": dict(e.headers) if e.headers else {},
            "via": "urllib-fallback",
        }
    except Exception as e:
        return {"status": None, "body": "", "headers": {}, "error": str(e), "via": "urllib-fallback"}


# ── Public API ────────────────────────────────────────────

def request(method, url, headers=None, data=None, client_id=None, impersonate=None, timeout=15):
    """HTTP request with TLS fingerprint evasion. Falls back to urllib."""
    fp = impersonate or client_id
    if _cffi_available:
        return _via_cffi(method, url, headers, data, fp, timeout)
    return _via_urllib(method, url, headers, data, timeout)


def tls_get(url, headers=None, token=None, client_id=None, impersonate=None, timeout=15):
    if token:
        headers = headers or {}
        headers["Authorization"] = token
    return request("GET", url, headers=headers, impersonate=impersonate or client_id, timeout=timeout)


def tls_post(url, headers=None, data=None, json_data=None, token=None, client_id=None, impersonate=None, timeout=15):
    if token:
        headers = headers or {}
        headers["Authorization"] = token
    return request("POST", url, headers=headers, data=json_data or data, impersonate=impersonate or client_id, timeout=timeout)


class TLSSession:
    """Session with persistent cookies and TLS fingerprint evasion."""

    def __init__(self, client_identifier=None, impersonate=None):
        fp = impersonate or client_identifier or random.choice(_FINGERPRINTS)
        self.impersonate = fp
        if _cffi_available:
            self._session = curl_requests.Session(impersonate=fp)
        else:
            self._session = None
        self.cookies = {}

    def _do(self, method, url, headers=None, data=None, timeout=15):
        h = dict(headers or {})
        if self.cookies:
            h["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())

        resp = request(method, url, headers=h, data=data, impersonate=self.impersonate, timeout=timeout)

        # Extract cookies from response
        set_cookie = resp.get("headers", {}).get("Set-Cookie", resp.get("headers", {}).get("set-cookie", ""))
        if set_cookie:
            for part in set_cookie.split(","):
                if "=" in part:
                    name, val = part.strip().split("=", 1)
                    self.cookies[name.strip()] = val.split(";")[0].strip()
        return resp

    def get(self, url, **kw):
        return self._do("GET", url, **kw)

    def post(self, url, **kw):
        return self._do("POST", url, **kw)

    def put(self, url, **kw):
        return self._do("PUT", url, **kw)

    def delete(self, url, **kw):
        return self._do("DELETE", url, **kw)


# ── CLI ───────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TLS-fingerprinted HTTP request")
    parser.add_argument("method", help="GET, POST, PUT, DELETE")
    parser.add_argument("url")
    parser.add_argument("--token", default=None)
    parser.add_argument("--data", default=None, help="JSON body")
    parser.add_argument("--impersonate", default=None, help="Browser fingerprint (e.g. chrome124, safari17_0, firefox133)")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    headers = {}
    if args.token:
        headers["Authorization"] = args.token
    data = json.loads(args.data) if args.data else None

    resp = request(args.method, args.url, headers=headers, data=data, impersonate=args.impersonate)
    output = json.dumps(resp, indent=2)
    print(output)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
