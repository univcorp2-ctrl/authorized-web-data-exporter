from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from urllib.robotparser import RobotFileParser


@dataclass(slots=True)
class RobotsGroup:
    user_agents: list[str] = field(default_factory=list)
    allow: list[str] = field(default_factory=list)
    disallow: list[str] = field(default_factory=list)
    crawl_delay: str | None = None


@dataclass(slots=True)
class RobotsSnapshot:
    robots_url: str
    status: str
    text: str = ""
    error: str | None = None
    groups: list[RobotsGroup] = field(default_factory=list)
    sitemaps: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RobotsDecision:
    url: str
    allowed: bool
    reason: str


class RobotsDeniedError(RuntimeError):
    """Raised when robots.txt disallows a URL and enforcement is enabled."""


def robots_url_for(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"


def fetch_robots_txt(url: str, user_agent: str, timeout: int = 20) -> RobotsSnapshot:
    robots_url = robots_url_for(url)
    request = urllib.request.Request(robots_url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            text = raw.decode(response.headers.get_content_charset() or "utf-8", errors="replace")
            snapshot = RobotsSnapshot(robots_url=robots_url, status=f"HTTP {response.status}", text=text)
            snapshot.groups, snapshot.sitemaps = parse_robots_text(text)
            return snapshot
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return RobotsSnapshot(robots_url=robots_url, status="HTTP 404", text="", error="robots.txt not found")
        return RobotsSnapshot(robots_url=robots_url, status=f"HTTP {exc.code}", error=str(exc))
    except Exception as exc:
        return RobotsSnapshot(robots_url=robots_url, status="FETCH_ERROR", error=str(exc))


def parse_robots_text(text: str) -> tuple[list[RobotsGroup], list[str]]:
    groups: list[RobotsGroup] = []
    sitemaps: list[str] = []
    current = RobotsGroup()
    has_rule = False

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()

        if key == "sitemap":
            if value:
                sitemaps.append(value)
            continue

        if key == "user-agent":
            if has_rule and current.user_agents:
                groups.append(current)
                current = RobotsGroup()
                has_rule = False
            current.user_agents.append(value)
            continue

        if key in {"allow", "disallow", "crawl-delay"}:
            has_rule = True
            if key == "allow" and value:
                current.allow.append(value)
            elif key == "disallow" and value:
                current.disallow.append(value)
            elif key == "crawl-delay" and value:
                current.crawl_delay = value

    if current.user_agents:
        groups.append(current)
    return groups, sitemaps


class RobotsInspector:
    def __init__(self, user_agent: str, enforce: bool = True, fail_closed_on_error: bool = False) -> None:
        self.user_agent = user_agent
        self.enforce = enforce
        self.fail_closed_on_error = fail_closed_on_error
        self.snapshots: dict[str, RobotsSnapshot] = {}
        self.parsers: dict[str, RobotFileParser] = {}
        self.decisions: list[RobotsDecision] = []

    def ensure_loaded(self, url: str) -> RobotsSnapshot:
        robots_url = robots_url_for(url)
        if robots_url in self.snapshots:
            return self.snapshots[robots_url]

        snapshot = fetch_robots_txt(url, self.user_agent)
        self.snapshots[robots_url] = snapshot

        parser = RobotFileParser()
        parser.set_url(robots_url)
        if snapshot.text:
            parser.parse(snapshot.text.splitlines())
        elif snapshot.status == "HTTP 404":
            parser.parse([])
        self.parsers[robots_url] = parser
        return snapshot

    def can_fetch(self, url: str) -> RobotsDecision:
        snapshot = self.ensure_loaded(url)
        if snapshot.error and snapshot.status != "HTTP 404":
            allowed = not self.fail_closed_on_error
            decision = RobotsDecision(url=url, allowed=allowed, reason=f"robots fetch error: {snapshot.error}")
            self.decisions.append(decision)
            return decision

        if snapshot.status == "HTTP 404":
            decision = RobotsDecision(url=url, allowed=True, reason="robots.txt not found; default allow")
            self.decisions.append(decision)
            return decision

        parser = self.parsers[robots_url_for(url)]
        allowed = parser.can_fetch(self.user_agent, url)
        reason = "allowed by robots.txt" if allowed else "disallowed by robots.txt"
        decision = RobotsDecision(url=url, allowed=allowed, reason=reason)
        self.decisions.append(decision)
        return decision

    def assert_allowed(self, url: str) -> None:
        decision = self.can_fetch(url)
        if self.enforce and not decision.allowed:
            raise RobotsDeniedError(f"{decision.reason}: {url}")

    def write_report(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        lines.append("Authorized Web Data Exporter robots.txt report")
        lines.append(f"User-agent used for checks: {self.user_agent}")
        lines.append(f"Enforce mode: {self.enforce}")
        lines.append("")

        for snapshot in self.snapshots.values():
            lines.append("=" * 80)
            lines.append(f"robots_url: {snapshot.robots_url}")
            lines.append(f"status: {snapshot.status}")
            if snapshot.error:
                lines.append(f"error: {snapshot.error}")
            if snapshot.sitemaps:
                lines.append("sitemaps:")
                for sitemap in snapshot.sitemaps:
                    lines.append(f"  - {sitemap}")
            for index, group in enumerate(snapshot.groups, start=1):
                lines.append(f"group {index}:")
                lines.append(f"  user_agents: {', '.join(group.user_agents)}")
                if group.crawl_delay:
                    lines.append(f"  crawl_delay: {group.crawl_delay}")
                for item in group.allow:
                    lines.append(f"  allow: {item}")
                for item in group.disallow:
                    lines.append(f"  disallow: {item}")
            lines.append("")

        lines.append("URL decisions:")
        for decision in self.decisions:
            status = "ALLOW" if decision.allowed else "DENY"
            lines.append(f"- {status}: {decision.url} ({decision.reason})")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
