from __future__ import annotations

from authorized_web_exporter.robots import RobotsInspector, parse_robots_text


def test_parse_robots_text_groups_and_sitemaps() -> None:
    text = """
    User-agent: *
    Disallow: /private/
    Allow: /private/public/
    Crawl-delay: 5
    Sitemap: https://example.com/sitemap.xml
    """

    groups, sitemaps = parse_robots_text(text)

    assert len(groups) == 1
    assert groups[0].user_agents == ["*"]
    assert groups[0].disallow == ["/private/"]
    assert groups[0].allow == ["/private/public/"]
    assert groups[0].crawl_delay == "5"
    assert sitemaps == ["https://example.com/sitemap.xml"]


def test_robots_inspector_can_fetch_with_injected_snapshot(tmp_path) -> None:  # noqa: ANN001
    inspector = RobotsInspector(user_agent="AuthorizedWebDataExporter", enforce=True)
    text = "User-agent: *\nDisallow: /private/\nAllow: /private/public/\n"
    from urllib.robotparser import RobotFileParser
    from authorized_web_exporter.robots import RobotsSnapshot, robots_url_for

    robots_url = robots_url_for("https://example.com/private/page")
    snapshot = RobotsSnapshot(robots_url=robots_url, status="HTTP 200", text=text)
    snapshot.groups, snapshot.sitemaps = parse_robots_text(text)
    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(text.splitlines())
    inspector.snapshots[robots_url] = snapshot
    inspector.parsers[robots_url] = parser

    assert not inspector.can_fetch("https://example.com/private/page").allowed
    assert inspector.can_fetch("https://example.com/private/public/page").allowed
    report = tmp_path / "robots_report.txt"
    inspector.write_report(report)
    assert "Disallow" not in report.read_text(encoding="utf-8")
    assert "disallow: /private/" in report.read_text(encoding="utf-8")
