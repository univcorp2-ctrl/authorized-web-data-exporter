from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from authorized_web_exporter.config import DiscoverySettings, ExtractionSettings, FieldRule
from authorized_web_exporter.models import DataRecord

SPACE_RE = re.compile(r"\s+")


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return SPACE_RE.sub(" ", value.replace("\xa0", " ")).strip()


def unique_keep_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def absolute_url(href: str, base_url: str) -> str:
    return urljoin(base_url, href.strip())


def same_site_http_url(url: str, allowed_domains: list[str] | None = None) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if allowed_domains is None:
        return True
    return parsed.netloc in set(allowed_domains)


def stable_id_from_url(url: str) -> str:
    numbers = re.findall(r"\d+", urlparse(url).path)
    if numbers:
        return numbers[-1]
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def extract_links_by_rules(
    html: str,
    base_url: str,
    selectors: list[str],
    regexes: list[str],
    allowed_domains: list[str] | None = None,
) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[str] = []

    for selector in selectors:
        try:
            for anchor in soup.select(selector):
                href = anchor.get("href")
                if href:
                    candidates.append(absolute_url(href, base_url))
        except Exception:
            continue

    compiled = [re.compile(pattern) for pattern in regexes]
    for anchor in soup.find_all("a"):
        href = anchor.get("href")
        if not href:
            continue
        absolute = absolute_url(href, base_url)
        if any(regex.search(href) or regex.search(absolute) for regex in compiled):
            candidates.append(absolute)

    filtered = [url for url in candidates if same_site_http_url(url, allowed_domains)]
    return unique_keep_order(filtered)


def extract_detail_links(
    html: str,
    base_url: str,
    discovery: DiscoverySettings,
    allowed_domains: list[str] | None = None,
) -> list[str]:
    return extract_links_by_rules(
        html,
        base_url,
        discovery.detail_link_selectors,
        discovery.detail_url_regexes,
        allowed_domains,
    )


def extract_next_links(
    html: str,
    base_url: str,
    discovery: DiscoverySettings,
    allowed_domains: list[str] | None = None,
) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[str] = []

    for selector in discovery.next_page_selectors:
        try:
            for anchor in soup.select(selector):
                href = anchor.get("href")
                if href:
                    candidates.append(absolute_url(href, base_url))
        except Exception:
            continue

    for anchor in soup.find_all("a"):
        text = clean_text(anchor.get_text(" "))
        href = anchor.get("href")
        if href and text in set(discovery.next_texts):
            candidates.append(absolute_url(href, base_url))

    filtered = [url for url in candidates if same_site_http_url(url, allowed_domains)]
    return unique_keep_order(filtered)


def parse_key_values(soup: BeautifulSoup) -> dict[str, str]:
    pairs: dict[str, str] = {}

    for tr in soup.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        key = clean_text(cells[0].get_text(" "))
        value = clean_text(" ".join(cell.get_text(" ") for cell in cells[1:]))
        if key and value:
            pairs[key] = value

    for dl in soup.find_all("dl"):
        pending_key: str | None = None
        for child in dl.find_all(["dt", "dd"], recursive=False):
            if child.name == "dt":
                pending_key = clean_text(child.get_text(" "))
            elif child.name == "dd" and pending_key:
                value = clean_text(child.get_text(" "))
                if value:
                    pairs[pending_key] = value
                pending_key = None

    return pairs


def extract_from_selector(soup: BeautifulSoup, rule: FieldRule) -> str | None:
    for selector in rule.selectors:
        try:
            node = soup.select_one(selector)
        except Exception:
            continue
        if not node:
            continue
        if rule.attr:
            value = clean_text(node.get(rule.attr))
        elif node.name == "meta":
            value = clean_text(node.get("content"))
        else:
            value = clean_text(node.get_text(" "))
        if value:
            return apply_regex(value, rule.regex)
    return None


def apply_regex(value: str, pattern: str | None) -> str:
    if not pattern:
        return value
    match = re.search(pattern, value)
    if not match:
        return value
    if match.groups():
        return clean_text(match.group(1))
    return clean_text(match.group(0))


def pick_by_labels(key_values: dict[str, str], labels: list[str], regex: str | None = None) -> str | None:
    for key, value in key_values.items():
        normalized = clean_text(key)
        if any(label in normalized for label in labels):
            return apply_regex(value, regex)
    return None


def extract_title(soup: BeautifulSoup, extraction: ExtractionSettings) -> str | None:
    for selector in extraction.title_selectors:
        try:
            node = soup.select_one(selector)
        except Exception:
            continue
        if not node:
            continue
        if node.name == "meta":
            text = clean_text(node.get("content"))
        else:
            text = clean_text(node.get_text(" "))
        if text:
            return text
    return None


def extract_images(soup: BeautifulSoup, base_url: str) -> list[str]:
    urls: list[str] = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-original")
        if not src:
            continue
        absolute = absolute_url(src, base_url)
        if absolute.startswith("http"):
            urls.append(absolute)
    return unique_keep_order(urls)


def extract_page_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    links: list[str] = []
    for anchor in soup.find_all("a"):
        href = anchor.get("href")
        if href:
            links.append(absolute_url(href, base_url))
    return unique_keep_order([url for url in links if url.startswith("http")])


def parse_detail_page(
    html: str,
    source_url: str,
    extraction: ExtractionSettings,
    html_file: str | None = None,
) -> DataRecord:
    soup = BeautifulSoup(html, "html.parser")

    for removable in soup(["script", "style", "noscript"]):
        removable.decompose()

    key_values = parse_key_values(soup)
    fields: dict[str, str] = {}
    for rule in extraction.fields:
        value = extract_from_selector(soup, rule) or pick_by_labels(key_values, rule.labels, rule.regex)
        if value:
            fields[rule.name] = value

    return DataRecord(
        source_url=source_url,
        record_id=stable_id_from_url(source_url),
        title=extract_title(soup, extraction),
        fields=fields,
        key_values=key_values,
        images=extract_images(soup, source_url),
        links=extract_page_links(soup, source_url),
        raw_text=clean_text(soup.get_text(" ")),
        html_file=html_file,
    )
