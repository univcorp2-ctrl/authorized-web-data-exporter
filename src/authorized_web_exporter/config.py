from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class CredentialEnv(BaseModel):
    username: str
    password: str


class BrowserSettings(BaseModel):
    headless: bool = True
    navigation_timeout_ms: int = 45_000
    user_agent: str | None = None


class RateLimitSettings(BaseModel):
    request_delay_seconds: float = 5.0
    request_jitter_seconds: float = 3.0
    max_retries: int = 3

    @field_validator("request_delay_seconds", "request_jitter_seconds")
    @classmethod
    def non_negative_delay(cls, value: float) -> float:
        if value < 0:
            raise ValueError("delay values must be zero or greater")
        return value


class LimitSettings(BaseModel):
    max_pages: int | None = 100
    max_items: int | None = None
    save_html: bool = False


class RobotsSettings(BaseModel):
    enabled: bool = True
    user_agent: str = "AuthorizedWebDataExporter"
    check_login_url: bool = True
    enforce: bool = True
    fail_closed_on_error: bool = False
    report_path: str = "robots_report.txt"


class LoginSelectors(BaseModel):
    username: list[str] = Field(default_factory=list)
    password: list[str] = Field(default_factory=list)
    submit: list[str] = Field(default_factory=list)
    logged_in: list[str] = Field(default_factory=list)


class DiscoverySettings(BaseModel):
    detail_link_selectors: list[str] = Field(default_factory=list)
    detail_url_regexes: list[str] = Field(default_factory=list)
    next_page_selectors: list[str] = Field(default_factory=list)
    next_texts: list[str] = Field(default_factory=lambda: ["Next", "次", "次へ", ">", "›", "»"])


class FieldRule(BaseModel):
    name: str
    labels: list[str] = Field(default_factory=list)
    selectors: list[str] = Field(default_factory=list)
    attr: str | None = None
    regex: str | None = None


class ExtractionSettings(BaseModel):
    title_selectors: list[str] = Field(default_factory=lambda: ["h1", "h2", "title"])
    fields: list[FieldRule] = Field(default_factory=list)


class SiteProfile(BaseModel):
    name: str
    description: str | None = None
    login_required: bool = True
    login_url: str | None = None
    allowed_domains: list[str]
    credential_env: CredentialEnv | None = None
    start_urls: list[str] = Field(default_factory=list)
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    limits: LimitSettings = Field(default_factory=LimitSettings)
    robots: RobotsSettings = Field(default_factory=RobotsSettings)
    login_selectors: LoginSelectors = Field(default_factory=LoginSelectors)
    challenge_keywords: list[str] = Field(default_factory=list)
    discovery: DiscoverySettings = Field(default_factory=DiscoverySettings)
    extraction: ExtractionSettings = Field(default_factory=ExtractionSettings)

    @field_validator("start_urls")
    @classmethod
    def strip_start_urls(cls, value: list[str]) -> list[str]:
        return [url.strip() for url in value if url and url.strip() and "REPLACE_WITH" not in url]

    @model_validator(mode="after")
    def validate_login_settings(self) -> "SiteProfile":
        if self.login_required:
            if not self.login_url:
                raise ValueError("login_url is required when login_required is true")
            if self.credential_env is None:
                raise ValueError("credential_env is required when login_required is true")
        return self


def load_profile(path: str | Path) -> SiteProfile:
    profile_path = Path(path)
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile file not found: {profile_path}")
    with profile_path.open("r", encoding="utf-8") as file:
        raw: dict[str, Any] = yaml.safe_load(file) or {}
    return SiteProfile.model_validate(raw)


def apply_runtime_overrides(
    profile: SiteProfile,
    start_urls: list[str] | None = None,
    output_dir: str | None = None,
    max_pages: int | None = None,
    max_items: int | None = None,
    headed: bool = False,
    save_html: bool | None = None,
) -> tuple[SiteProfile, str]:
    env_urls = os.getenv("WEB_EXPORT_START_URLS")
    resolved_start_urls = start_urls or []
    if env_urls:
        resolved_start_urls.extend([line.strip() for line in env_urls.splitlines() if line.strip()])
    if resolved_start_urls:
        profile = profile.model_copy(update={"start_urls": resolved_start_urls})

    if headed:
        profile = profile.model_copy(update={"browser": profile.browser.model_copy(update={"headless": False})})

    limit_updates: dict[str, Any] = {}
    if max_pages is not None:
        limit_updates["max_pages"] = max_pages
    if max_items is not None:
        limit_updates["max_items"] = max_items
    if save_html is not None:
        limit_updates["save_html"] = save_html
    if limit_updates:
        profile = profile.model_copy(update={"limits": profile.limits.model_copy(update=limit_updates)})

    return profile, output_dir or "outputs"


def load_credentials(profile: SiteProfile, username: str | None = None, password: str | None = None) -> tuple[str, str]:
    if not profile.login_required:
        return "", ""
    if profile.credential_env is None:
        raise RuntimeError("credential_env is required for login profiles")
    resolved_username = username or os.getenv(profile.credential_env.username)
    resolved_password = password or os.getenv(profile.credential_env.password)
    if not resolved_username or not resolved_password:
        raise RuntimeError(
            f"Missing credentials. Set {profile.credential_env.username} and {profile.credential_env.password}."
        )
    return resolved_username, resolved_password


def authorization_acknowledged(flag: bool) -> bool:
    env_value = os.getenv("WEB_EXPORT_ACKNOWLEDGE_AUTHORIZED", "").strip().lower()
    return flag or env_value in {"1", "true", "yes", "y"}
