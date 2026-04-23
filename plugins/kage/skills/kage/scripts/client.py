#!/usr/bin/env python3
"""Shared helpers for Kage probe scripts.

One place for the HTTP wrapper + header normalization so every probe
script doesn't reinvent them. Probe scripts should import make_request()
and lowercase_headers() instead of rebuilding them locally.
"""
import os
import sys

# Ensure sibling scripts can import tls.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tls import request as _tls_request


def lowercase_headers(headers):
    """Return a new dict with header names lowercased. HTTP header names are
    case-insensitive; normalise once at the boundary so downstream lookups
    use a single canonical form."""
    return {k.lower(): v for k, v in (headers or {}).items()}


def make_request(url, method="GET", token=None, data=None, extra_headers=None,
                 truncate=1000, timeout=15, impersonate=None):
    """Single HTTP wrapper around tls.request().

    Returns a dict with:
        status   — HTTP status code (or None on network failure)
        body     — response body, truncated to `truncate` chars
        length   — len(untruncated body) so callers can see if truncation happened
        headers  — response headers, lowercased
        error    — network-level error string, or None
        via      — transport label from tls.py
    """
    headers = dict(extra_headers or {})
    if token:
        headers["Authorization"] = token

    resp = _tls_request(method, url, headers=headers, data=data,
                        impersonate=impersonate, timeout=timeout)

    full_body = resp.get("body", "")
    # truncate <= 0 means "no truncation" — pass through the full body.
    # diff.py needs this; most probes don't.
    body = full_body if truncate <= 0 else full_body[:truncate]
    return {
        "status": resp.get("status"),
        "body": body,
        "length": len(full_body),
        "headers": lowercase_headers(resp.get("headers")),
        "error": resp.get("error"),
        "via": resp.get("via"),
    }
