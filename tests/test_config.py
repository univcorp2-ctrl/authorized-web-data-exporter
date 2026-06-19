from __future__ import annotations

from pathlib import Path

from authorized_web_exporter.config import apply_runtime_overrides, authorization_acknowledged, load_profile


def test_load_profile_and_env_override(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    profile_path = tmp_path / "profile.yml"
    profile_path.write_text(
        """
name: test
login_url: https://example.com/login
allowed_domains: [example.com]
credential_env:
  username: TEST_USER
  password: TEST_PASS
start_urls:
  - https://example.com/a
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("WEB_EXPORT_START_URLS", "https://example.com/b\nhttps://example.com/c")

    profile, output_dir = apply_runtime_overrides(load_profile(profile_path), output_dir="out")

    assert profile.start_urls == ["https://example.com/b", "https://example.com/c"]
    assert output_dir == "out"


def test_authorization_acknowledged(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("WEB_EXPORT_ACKNOWLEDGE_AUTHORIZED", "true")
    assert authorization_acknowledged(False)
    assert authorization_acknowledged(True)
