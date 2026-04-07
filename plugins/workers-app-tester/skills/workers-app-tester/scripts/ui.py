#!/usr/bin/env python3
"""UI hierarchy parser for Android. Filters to interactive elements only.

Usage:
    python3 ui.py              # Dump from device via adb, parse, print
    python3 ui.py --xml f.xml  # Parse a local XML file
    python3 ui.py --json       # Output JSON instead of text
    python3 ui.py --help       # Show help
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

MIN_DIST = 30  # Spatial dedup threshold in pixels

# Map Android widget classes to short type tags
TYPE_MAP = {
    "button": "btn", "imagebutton": "btn", "floatingactionbutton": "fab",
    "materialbutton": "btn", "appcompatbutton": "btn", "chipgroup": "chips",
    "chip": "chip",
    "edittext": "input", "autocompleteedittext": "input",
    "textinputedittext": "input", "searchview": "search",
    "textview": "text", "checkedtextview": "text",
    "imageview": "img", "appcompatimageview": "img",
    "switch": "switch", "togglebutton": "switch", "switchcompat": "switch",
    "checkbox": "check", "radiobutton": "radio",
    "recyclerview": "list", "listview": "list", "scrollview": "scroll",
    "nestedscrollview": "scroll",
    "viewpager": "pager", "viewpager2": "pager",
    "tablayout": "tab", "bottomnavigationview": "nav",
    "navigationrailview": "nav", "toolbar": "toolbar",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Parse Android UI hierarchy into a compact interactive element list."
    )
    p.add_argument("--xml", help="Path to a local XML file. If omitted, dumps from device via adb.")
    p.add_argument("--json", action="store_true", help="Output JSON instead of text.")
    p.add_argument("--all", action="store_true", help="Include non-interactive elements too.")
    p.add_argument("--min-dist", type=int, default=MIN_DIST,
                   help=f"Dedup distance in pixels (default: {MIN_DIST}).")
    return p.parse_args()


def dump_ui_xml() -> str:
    """Run uiautomator dump on device and return the XML string."""
    subprocess.run(
        ["adb", "shell", "uiautomator", "dump", "/sdcard/window_dump.xml"],
        capture_output=True, text=True, check=True,
    )
    result = subprocess.run(
        ["adb", "shell", "cat", "/sdcard/window_dump.xml"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


def parse_bounds(bounds_str: str) -> tuple[int, int, int, int]:
    """Parse '[left,top][right,bottom]' -> (left, top, right, bottom)."""
    parts = bounds_str.replace("][", ",").strip("[]").split(",")
    return int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])


def classify_type(class_name: str) -> str:
    cn = class_name.rsplit(".", 1)[-1].lower()
    for key, val in TYPE_MAP.items():
        if key in cn:
            return val
    return "view"


def make_label(attrib: dict) -> str:
    """Build human-readable label: text > content-desc > resource-id tail > class short."""
    text = (attrib.get("text") or "").strip()
    if text and len(text) <= 50:
        return text
    desc = (attrib.get("content-desc") or "").strip()
    if desc and len(desc) <= 50:
        return desc
    rid = attrib.get("resource-id", "")
    if rid:
        return rid.rsplit("/", 1)[-1]
    cn = attrib.get("class", "")
    return cn.rsplit(".", 1)[-1] if cn else "unknown"


def is_duplicate(cx: int, cy: int, existing: list[dict], min_dist: int) -> bool:
    for e in existing:
        dist = math.sqrt((cx - e["cx"]) ** 2 + (cy - e["cy"]) ** 2)
        if dist <= min_dist:
            return True
    return False


def sanitize_xml(raw: str) -> str:
    """Fix common malformed XML from uiautomator dumps."""
    # Replace bare & with &amp; (but not already-escaped ones)
    raw = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;)", "&amp;", raw)
    return raw


def parse_xml(xml_content: str, include_all: bool = False, min_dist: int = MIN_DIST) -> list[dict]:
    """Parse UI XML, return only interactive elements with spatial dedup.

    Two-pass algorithm (from AppAgent and_controller.py:56-86):
    Pass 1: collect clickable="true" elements
    Pass 2: collect focusable="true" not already covered
    """
    xml_content = sanitize_xml(xml_content)
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        print(f"XML parse error: {exc}", file=sys.stderr)
        return []

    clickable: list[dict] = []
    all_elems: list[dict] = []

    def _make(node, interaction: str) -> dict | None:
        a = node.attrib
        bounds_str = a.get("bounds", "[0,0][0,0]")
        try:
            left, top, right, bottom = parse_bounds(bounds_str)
        except (ValueError, IndexError):
            return None
        if right - left <= 0 or bottom - top <= 0:
            return None
        cx, cy = (left + right) // 2, (top + bottom) // 2
        return {
            "label": make_label(a),
            "type": classify_type(a.get("class", "")),
            "cx": cx, "cy": cy,
            "bounds": [left, top, right, bottom],
            "interaction": interaction,
            "resource_id": a.get("resource-id", ""),
            "content_desc": a.get("content-desc", ""),
            "text": a.get("text", ""),
            "class": a.get("class", ""),
        }

    # Pass 1: clickable
    for node in root.iter("node"):
        if include_all or node.attrib.get("clickable") == "true":
            elem = _make(node, "clickable")
            if elem and not is_duplicate(elem["cx"], elem["cy"], clickable, min_dist):
                clickable.append(elem)

    all_elems = list(clickable)

    if not include_all:
        # Pass 2: focusable not already covered
        for node in root.iter("node"):
            if node.attrib.get("focusable") == "true" and node.attrib.get("clickable") != "true":
                elem = _make(node, "focusable")
                if elem and not is_duplicate(elem["cx"], elem["cy"], all_elems, min_dist):
                    all_elems.append(elem)

    # Number sequentially
    for i, e in enumerate(all_elems, 1):
        e["index"] = i

    return all_elems


def format_plain(elements: list[dict]) -> str:
    if not elements:
        return "No interactive elements found on screen."
    lines = [f"elements={len(elements)}"]
    for e in elements:
        l, t, r, b = e["bounds"]
        lines.append(
            f'[{e["index"]}] "{e["label"]}" {e["type"]} '
            f'@ ({e["cx"]},{e["cy"]}) '
            f'bounds=[{l},{t}][{r},{b}] {e["interaction"]}'
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    if args.xml:
        try:
            with open(args.xml, "r", encoding="utf-8") as f:
                xml_content = f.read()
        except FileNotFoundError:
            print(f"File not found: {args.xml}", file=sys.stderr)
            return 1
    else:
        try:
            xml_content = dump_ui_xml()
        except subprocess.CalledProcessError as exc:
            print(f"adb error: {exc.stderr}", file=sys.stderr)
            return 1
        except FileNotFoundError:
            print("adb not found. Install Android SDK platform-tools.", file=sys.stderr)
            return 1

    elements = parse_xml(xml_content, include_all=args.all, min_dist=args.min_dist)

    if args.json:
        print(json.dumps(elements, indent=2))
    else:
        print(format_plain(elements))
    return 0


if __name__ == "__main__":
    sys.exit(main())
