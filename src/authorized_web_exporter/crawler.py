from __future__ import annotations

import asyncio
import random
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError, async_playwright
from rich.console import Console
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from authorized_web_exporter.checkpoint import CheckpointStore
from authorized_web_exporter.config import SiteProfile
from authorized_web_exporter.investment_analysis import export_investment_analysis
from authorized_web_exporter.models import CrawlError
from authorized_web_exporter.parser import extract_detail_links, extract_next_links, parse_detail_page
from authorized_web_exporter.robots import RobotsDeniedError, RobotsInspector
from authorized_web_exporter.storage import export_records


class GenericCrawler:
    def __init__(
        self,
        profile: SiteProfile,
        output_dir: Path,
        username: str,
        password: str,
        console: Console | None = None,
        generate_analysis: bool = True,
        enable_api_comparison: bool = True,
    ) -> None:
        self.profile = profile
        self.output_dir = output_dir
        self.username = username
        self.password = password
        self.console = console or Console()
        self.generate_analysis = generate_analysis
        self.enable_api_comparison = enable_api_comparison
        self.state_dir = Path(".crawler-state") / profile.name
        self.checkpoint = CheckpointStore(self.state_dir / "checkpoint.json")
        self.detail_queue: deque[str] = deque()
        self.queued_detail_urls: set[str] = set()
        self.robots = RobotsInspector(
            user_agent=profile.robots.user_agent,
            enforce=profile.robots.enforce,
            fail_closed_on_error=profile.robots.fail_closed_on_error,
        )

    async def run(self) -> None:
        if not self.profile.start_urls:
            raise RuntimeError("No start_urls configured. Add authorized list/search URLs to the profile or --start-url.")

        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint.load()
        self.preflight_robots_check()

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self.profile.browser.headless)
            context_kwargs = {}
            if self.profile.browser.user_agent:
                context_kwargs["user_agent"] = self.profile.browser.user_agent
            browser_state_path = self.state_dir / "browser_state.json"
            if browser_state_path.exists():
                context_kwargs["storage_state"] = str(browser_state_path)
            context = await browser.new_context(**context_kwargs)
            context.set_default_timeout(self.profile.browser.navigation_timeout_ms)
            page = await context.new_page()

            try:
                await self.ensure_login(page, context, browser_state_path)
                await self.collect_detail_urls(page)
                await self.collect_detail_pages(page)
            finally:
                await context.storage_state(path=str(browser_state_path))
                await context.close()
                await browser.close()

        export_records(self.output_dir, self.checkpoint.records, self.checkpoint.errors)
        if self.generate_analysis:
            export_investment_analysis(
                self.output_dir,
                self.checkpoint.records,
                enable_api=self.enable_api_comparison,
            )
        self.robots.write_report(self.output_dir / self.profile.robots.report_path)
        self.console.print(
            f"[green]Export completed:[/green] records={len(self.checkpoint.records)} "
            f"errors={len(self.checkpoint.errors)} output={self.output_dir}"
        )

    def preflight_robots_check(self) -> None:
        if not self.profile.robots.enabled:
            return
        urls = list(self.profile.start_urls)
        if self.profile.robots.check_login_url:
            urls.insert(0, self.profile.login_url)
        for url in urls:
            self.robots.assert_allowed(url)
        self.robots.write_report(self.output_dir / self.profile.robots.report_path)

    async def polite_delay(self) -> None:
        delay = self.profile.rate_limit.request_delay_seconds + random.uniform(
            0, self.profile.rate_limit.request_jitter_seconds
        )
        if delay > 0:
            await asyncio.sleep(delay)

    def allowed_domain_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and parsed.netloc in set(self.profile.allowed_domains)

    @retry(
        retry=retry_if_exception_type((PlaywrightTimeoutError, RuntimeError)),
        wait=wait_exponential_jitter(initial=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def goto(self, page: Page, url: str) -> str:
        if not self.allowed_domain_url(url):
            raise RuntimeError(f"URL is outside allowed_domains: {url}")
        if self.profile.robots.enabled:
            self.robots.assert_allowed(url)
        await self.polite_delay()
        self.console.print(f"[cyan]GET[/cyan] {url}")
        response = await page.goto(url, wait_until="domcontentloaded", timeout=self.profile.browser.navigation_timeout_ms)
        try:
            await page.wait_for_load_state("networkidle", timeout=8_000)
        except PlaywrightTimeoutError:
            pass
        if response and response.status >= 500:
            raise RuntimeError(f"Server returned HTTP {response.status}: {url}")
        return await page.content()

    async def selector_exists(self, page: Page, selector: str) -> bool:
        try:
            return await page.locator(selector).count() > 0
        except Exception:
            return False

    async def fill_first(self, page: Page, selectors: list[str], value: str) -> bool:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() > 0:
                    await locator.fill(value)
                    return True
            except Exception:
                continue
        return False

    async def click_first(self, page: Page, selectors: list[str]) -> bool:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() > 0:
                    await locator.click()
                    return True
            except Exception:
                continue
        return False

    async def has_logged_in_signal(self, page: Page) -> bool:
        for selector in self.profile.login_selectors.logged_in:
            if await self.selector_exists(page, selector):
                return True
        has_password = any(
            [await self.selector_exists(page, selector) for selector in self.profile.login_selectors.password]
        )
        return "login" not in page.url.lower() and not has_password

    async def ensure_login(self, page: Page, context: BrowserContext, browser_state_path: Path) -> None:
        await self.goto(page, self.profile.login_url)
        if await self.has_logged_in_signal(page):
            self.console.print("[green]Existing authenticated session is available.[/green]")
            await context.storage_state(path=str(browser_state_path))
            return

        username_filled = await self.fill_first(page, self.profile.login_selectors.username, self.username)
        password_filled = await self.fill_first(page, self.profile.login_selectors.password, self.password)
        if not username_filled or not password_filled:
            raise RuntimeError("Could not find login username/password fields. Update login_selectors in the profile.")

        clicked = await self.click_first(page, self.profile.login_selectors.submit)
        if not clicked:
            await page.keyboard.press("Enter")

        try:
            await page.wait_for_load_state("networkidle", timeout=self.profile.browser.navigation_timeout_ms)
        except PlaywrightTimeoutError:
            pass
        await asyncio.sleep(2)

        page_text = (await page.locator("body").inner_text(timeout=5_000)).lower()
        if any(word.lower() in page_text for word in self.profile.challenge_keywords):
            raise RuntimeError("Login challenge/CAPTCHA/MFA was detected. The exporter stops instead of bypassing it.")

        if not await self.has_logged_in_signal(page):
            raise RuntimeError("Login did not complete. Check credentials or update logged_in selectors in the profile.")

        await context.storage_state(path=str(browser_state_path))
        self.console.print("[green]Login completed and browser state saved.[/green]")

    async def collect_detail_urls(self, page: Page) -> None:
        list_queue: deque[str] = deque(self.profile.start_urls)
        queued_list_pages: set[str] = set(self.profile.start_urls)
        processed_count = 0

        while list_queue:
            if self.profile.limits.max_pages is not None and processed_count >= self.profile.limits.max_pages:
                self.console.print(f"[yellow]max_pages reached: {self.profile.limits.max_pages}[/yellow]")
                break

            url = list_queue.popleft()
            if url in self.checkpoint.visited_list_pages:
                continue

            try:
                html = await self.goto(page, url)
                detail_links = extract_detail_links(html, url, self.profile.discovery, self.profile.allowed_domains)
                for link in detail_links:
                    if link not in self.checkpoint.visited_detail_urls and link not in self.queued_detail_urls:
                        self.detail_queue.append(link)
                        self.queued_detail_urls.add(link)

                next_links = extract_next_links(html, url, self.profile.discovery, self.profile.allowed_domains)
                for link in next_links:
                    if link not in self.checkpoint.visited_list_pages and link not in queued_list_pages:
                        list_queue.append(link)
                        queued_list_pages.add(link)

                self.checkpoint.add_list_page(url)
                processed_count += 1
                self.console.print(
                    f"[blue]list page parsed[/blue] details+={len(detail_links)} next+={len(next_links)} queue={len(self.detail_queue)}"
                )
            except RobotsDeniedError as exc:
                self.checkpoint.add_error(CrawlError(url=url, phase="robots", message=str(exc)))
                self.console.print(f"[red]robots denied[/red] {url}: {exc}")
            except Exception as exc:
                self.checkpoint.add_error(CrawlError(url=url, phase="list", message=str(exc)))
                self.console.print(f"[red]list failed[/red] {url}: {exc}")

    async def collect_detail_pages(self, page: Page) -> None:
        collected = len(self.checkpoint.records)
        while self.detail_queue:
            if self.profile.limits.max_items is not None and collected >= self.profile.limits.max_items:
                self.console.print(f"[yellow]max_items reached: {self.profile.limits.max_items}[/yellow]")
                break

            url = self.detail_queue.popleft()
            if url in self.checkpoint.visited_detail_urls:
                continue

            try:
                html = await self.goto(page, url)
                if "login" in page.url.lower() and page.url != url:
                    await self.ensure_login(page, page.context, self.state_dir / "browser_state.json")
                    html = await self.goto(page, url)

                html_file = None
                if self.profile.limits.save_html:
                    html_dir = self.output_dir / "raw_html"
                    html_dir.mkdir(parents=True, exist_ok=True)
                    html_file = f"{collected + 1:06d}.html"
                    (html_dir / html_file).write_text(html, encoding="utf-8")

                record = parse_detail_page(
                    html,
                    source_url=url,
                    extraction=self.profile.extraction,
                    html_file=html_file,
                )
                self.checkpoint.add_record(record)
                collected += 1
                self.console.print(f"[green]record saved[/green] {collected}: {record.title or url}")
            except RobotsDeniedError as exc:
                self.checkpoint.add_error(CrawlError(url=url, phase="robots", message=str(exc)))
                self.console.print(f"[red]robots denied[/red] {url}: {exc}")
            except Exception as exc:
                self.checkpoint.add_error(CrawlError(url=url, phase="detail", message=str(exc)))
                self.console.print(f"[red]detail failed[/red] {url}: {exc}")
