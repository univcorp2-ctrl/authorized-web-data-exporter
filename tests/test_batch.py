from __future__ import annotations

from pathlib import Path

from authorized_web_exporter.batch import discover_profile_paths


def test_discover_profile_paths_with_include(tmp_path: Path) -> None:
    (tmp_path / "a.yml").write_text("name: a\nlogin_required: false\nallowed_domains: [example.com]\n", encoding="utf-8")
    (tmp_path / "b.yml").write_text("name: b\nlogin_required: false\nallowed_domains: [example.com]\n", encoding="utf-8")
    paths = discover_profile_paths(tmp_path, include=["b"])
    assert [path.name for path in paths] == ["b.yml"]
