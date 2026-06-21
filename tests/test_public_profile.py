from __future__ import annotations

from pathlib import Path

from authorized_web_exporter.config import load_credentials, load_profile


def test_public_no_login_profile_does_not_require_credentials(tmp_path: Path) -> None:
    profile_path = tmp_path / "public.yml"
    profile_path.write_text(
        """
name: public-example
login_required: false
allowed_domains: [example.com]
start_urls:
  - https://example.com/search
""",
        encoding="utf-8",
    )
    profile = load_profile(profile_path)
    assert profile.login_required is False
    assert profile.login_url is None
    assert load_credentials(profile) == ("", "")


def test_login_profile_still_requires_credentials_env(tmp_path: Path) -> None:
    profile_path = tmp_path / "login.yml"
    profile_path.write_text(
        """
name: login-example
login_required: true
login_url: https://example.com/login
allowed_domains: [example.com]
credential_env:
  username: TEST_USER
  password: TEST_PASS
start_urls:
  - https://example.com/search
""",
        encoding="utf-8",
    )
    profile = load_profile(profile_path)
    assert profile.login_required is True
    assert profile.credential_env is not None
