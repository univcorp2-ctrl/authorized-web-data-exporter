from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="Build runtime site profile for GitHub Actions export workflow.")
    parser.add_argument("--base-profile", default="profiles/kenbiya.yml")
    parser.add_argument("--start-urls-file", required=True)
    parser.add_argument("--output", default="profile.runtime.yml")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--max-items", type=int, default=0)
    parser.add_argument("--save-html", default="false")
    args = parser.parse_args()

    profile = yaml.safe_load(Path(args.base_profile).read_text(encoding="utf-8"))
    start_urls = [
        line.strip()
        for line in Path(args.start_urls_file).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not start_urls:
        raise SystemExit("start_urls input is empty")

    profile["start_urls"] = start_urls
    profile.setdefault("limits", {})["max_pages"] = args.max_pages
    profile.setdefault("limits", {})["max_items"] = args.max_items if args.max_items > 0 else None
    profile.setdefault("limits", {})["save_html"] = args.save_html.lower() in {"1", "true", "yes"}

    Path(args.output).write_text(yaml.safe_dump(profile, allow_unicode=True, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
