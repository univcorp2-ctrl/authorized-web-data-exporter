from __future__ import annotations

from pathlib import Path

import yaml

from authorized_web_exporter.config import load_profile


def test_source_catalog_referenced_profiles_exist() -> None:
    catalog = yaml.safe_load(Path("data/source_catalog.yml").read_text(encoding="utf-8"))
    missing: list[str] = []
    for source in catalog["sources"]:
        profile = source.get("profile")
        if profile and profile.startswith("profiles/") and not Path(profile).exists():
            missing.append(profile)
    assert missing == []


def test_all_source_profiles_load() -> None:
    errors: dict[str, str] = {}
    for path in sorted(Path("profiles/sources").glob("*.yml")):
        try:
            profile = load_profile(path)
            assert profile.allowed_domains
            assert profile.start_urls
        except Exception as exc:  # pragma: no cover - assertion helper
            errors[str(path)] = str(exc)
    assert errors == {}
