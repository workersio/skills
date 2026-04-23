#!/usr/bin/env python3
"""Generate Google search URLs from templated dorks.

Loads dork templates from `assets/dorks.json` (organised by category:
credentials, pii, admin, errors, cloud, subdomains, params, leaks,
github, juicy). Outputs JSON to stdout by default; pass --output to
write JSON to a file. Progress goes to stderr.
"""
import argparse
import json
import os
import sys
import urllib.parse

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DORKS = os.path.join(_SCRIPT_DIR, "..", "assets", "dorks.json")


def load_dorks(path):
    with open(path) as f:
        return json.load(f)


def google_url(dork):
    return "https://www.google.com/search?q=" + urllib.parse.quote(dork) + "&num=50"


def main():
    parser = argparse.ArgumentParser(description="Generate dork URLs for a target.")
    parser.add_argument("-d", "--domain", required=True, help="Target domain")
    parser.add_argument("-c", "--category", default="all",
                        help="Dork category name from dorks.json, or 'all' (default)")
    parser.add_argument("--dorks-file", default=_DEFAULT_DORKS,
                        help="Path to dorks.json (default: assets/dorks.json)")
    parser.add_argument("-o", "--output", default=None,
                        help="Write JSON output to this file instead of stdout")
    args = parser.parse_args()

    categories = load_dorks(args.dorks_file)

    if args.category == "all":
        templates = [(cat, d) for cat, ds in categories.items() for d in ds]
    elif args.category in categories:
        templates = [(args.category, d) for d in categories[args.category]]
    else:
        print(f"[dork-runner] unknown category: {args.category}", file=sys.stderr)
        print(f"[dork-runner] available: {', '.join(categories)}", file=sys.stderr)
        sys.exit(2)

    results = [
        {"category": cat, "dork": tmpl.replace("{target}", args.domain),
         "url": google_url(tmpl.replace("{target}", args.domain))}
        for cat, tmpl in templates
    ]

    payload = {"target": args.domain, "category": args.category,
               "total": len(results), "dorks": results}
    output = json.dumps(payload, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"[dork-runner] {len(results)} dorks for {args.domain} -> {args.output}",
              file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
