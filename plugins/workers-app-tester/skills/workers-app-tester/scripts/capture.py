#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from mitmproxy import ctx
from mitmproxy import http

OUT_DIR = Path(os.environ.get("ANDROID_APP_TESTER_OUT_DIR", ".")).expanduser()
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = OUT_DIR / "traffic.jsonl"
PACKAGE_NAME = os.environ.get("ANDROID_APP_TESTER_PACKAGE", "")
PRESERVE_AUTH = os.environ.get("ANDROID_APP_TESTER_PRESERVE_AUTH", "0") == "1"
SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "proxy-authorization",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
}


def _trim(value: str, limit: int = 1000) -> str:
    if len(value) <= limit:
      return value
    return value[: limit - 3] + "..."


def _sanitize_headers(headers: http.Headers) -> dict[str, str]:
    clean: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADERS and not PRESERVE_AUTH:
            clean[key] = "<redacted>"
        else:
            clean[key] = _trim(value, 240)
    return clean


def _body_preview(message: http.Message) -> str:
    content = message.raw_content or b""
    if not content:
        return ""
    preview = content[:2048].decode("utf-8", errors="replace")
    return _trim(preview.replace("\n", "\\n"), 1000)


def _request_fields(flow: http.HTTPFlow) -> dict[str, object]:
    request = flow.request
    return {
        "package": PACKAGE_NAME,
        "method": request.method,
        "scheme": request.scheme,
        "host": request.host,
        "port": request.port,
        "path": request.path,
        "pretty_url": request.pretty_url,
        "request_headers": _sanitize_headers(request.headers),
        "request_content_type": request.headers.get("content-type", ""),
        "request_body_preview": _body_preview(request),
    }


def _response_fields(flow: http.HTTPFlow) -> dict[str, object]:
    response = flow.response
    if response is None:
        return {}
    return {
        "status_code": response.status_code,
        "reason": response.reason,
        "response_headers": _sanitize_headers(response.headers),
        "response_content_type": response.headers.get("content-type", ""),
        "response_body_preview": _body_preview(response),
    }


def _emit(event: str, flow: http.HTTPFlow, **extra: object) -> None:
    record = {
        "event": event,
        "flow_id": flow.id,
        "timestamp": time.time(),
        **_request_fields(flow),
        **extra,
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load(_: object) -> None:
    ctx.log.info(f"android-app-tester writing capture logs to {LOG_PATH}")


def request(flow: http.HTTPFlow) -> None:
    _emit("request", flow)


def response(flow: http.HTTPFlow) -> None:
    _emit("response", flow, **_response_fields(flow))


def error(flow: http.HTTPFlow) -> None:
    _emit("error", flow, error=str(flow.error))
