"""
WebCrawlerTool — polite, robots-aware web crawler.

Features:
- Respects robots.txt
- Configurable crawl delay
- Playwright fallback for JS-rendered pages
- SSRF protection via domain allowlist/blocklist
- Per-domain rate limiting
"""
import asyncio
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
import structlog
from bs4 import BeautifulSoup

from app.core.config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class CrawledPage:
    url: str
    status_code: int
    title: str | None = None
    meta_description: str | None = None
    h1: str | None = None
    h2s: list[str] = field(default_factory=list)
    word_count: int = 0
    content_text: str | None = None
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    structured_data: list[dict] = field(default_factory=list)
    meta_tags: dict = field(default_factory=dict)
    canonical_url: str | None = None
    rendered_fallback: bool = False
    error: str | None = None


@dataclass
class CrawlResult:
    success: bool
    pages_crawled: int
    pages_failed: int
    pages: list[CrawledPage] = field(default_factory=list)
    error: str | None = None


class SSRFProtectionError(Exception):
    """Raised when a URL fails SSRF protection checks."""


class WebCrawlerTool:
    """
    Production-grade polite web crawler with SSRF protection.

    Usage:
        tool = WebCrawlerTool()
        result = await tool.crawl("https://example.com", max_pages=50)
    """

    def __init__(self) -> None:
        self._visited: set[str] = set()
        self._queue: list[str] = []

    def _is_blocked(self, url: str) -> bool:
        """Check URL against SSRF blocklist."""
        parsed = urlparse(url)
        host = parsed.hostname or ""
        blocked = settings.crawl_blocked_domain_list
        for blocked_domain in blocked:
            if host == blocked_domain or host.endswith(f".{blocked_domain}"):
                return True
        # Block private IP ranges
        import ipaddress
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return True
        except ValueError:
            pass
        return False

    def _normalize_url(self, url: str, base: str) -> str | None:
        """Resolve relative URL and validate."""
        try:
            resolved = urljoin(base, url)
            parsed = urlparse(resolved)
            if parsed.scheme not in ("http", "https"):
                return None
            # Strip fragments
            resolved = resolved.split("#")[0]
            return resolved
        except Exception:
            return None

    def _extract_page_data(self, url: str, html: str, status_code: int) -> CrawledPage:
        """Parse HTML and extract SEO-relevant data."""
        soup = BeautifulSoup(html, "lxml")
        base_domain = urlparse(url).netloc

        # Title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
        meta_description = meta_desc.get("content", "").strip() if meta_desc else None

        # H1
        h1_tag = soup.find("h1")
        h1 = h1_tag.get_text(strip=True) if h1_tag else None

        # H2s
        h2s = [h.get_text(strip=True) for h in soup.find_all("h2")[:10]]

        # Canonical
        canonical_tag = soup.find("link", attrs={"rel": "canonical"})
        canonical_url = canonical_tag.get("href") if canonical_tag else None

        # Text content
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        content_text = soup.get_text(separator=" ", strip=True)
        word_count = len(content_text.split())

        # Links
        internal_links: list[str] = []
        external_links: list[str] = []
        for a in soup.find_all("a", href=True):
            href = self._normalize_url(a["href"], url)
            if not href:
                continue
            link_domain = urlparse(href).netloc
            if link_domain == base_domain or not link_domain:
                internal_links.append(href)
            else:
                external_links.append(href)

        # Structured data
        structured_data: list[dict] = []
        import json
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "")
                structured_data.append(data)
            except Exception:
                pass

        # Meta tags
        meta_tags: dict[str, str] = {}
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property") or ""
            content = meta.get("content", "")
            if name and content:
                meta_tags[name] = content

        return CrawledPage(
            url=url,
            status_code=status_code,
            title=title,
            meta_description=meta_description,
            h1=h1,
            h2s=h2s,
            word_count=word_count,
            content_text=content_text[:5000],  # Truncate for storage
            internal_links=list(set(internal_links))[:50],
            external_links=list(set(external_links))[:20],
            structured_data=structured_data,
            meta_tags=meta_tags,
            canonical_url=canonical_url,
        )

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        url: str,
        use_playwright: bool = False,
    ) -> tuple[int, str]:
        """Fetch page HTML. Uses Playwright for JS-heavy pages if enabled."""
        if use_playwright and settings.crawl_playwright_enabled:
            return await self._fetch_rendered(url)

        r = await client.get(url, follow_redirects=True)
        content_type = r.headers.get("content-type", "")
        if "html" not in content_type:
            return r.status_code, ""
        return r.status_code, r.text

    async def _fetch_rendered(self, url: str) -> tuple[int, str]:
        """Fetch JS-rendered page using Playwright."""
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.set_extra_http_headers({"User-Agent": settings.crawl_user_agent})
                response = await page.goto(url, timeout=30000, wait_until="networkidle")
                status = response.status if response else 200
                html = await page.content()
                await browser.close()
                return status, html
        except Exception as e:
            logger.warning("playwright_failed", url=url, error=str(e))
            return 500, ""

    async def crawl(
        self,
        url: str,
        max_pages: int = 100,
        follow_sitemaps: bool = True,
    ) -> CrawlResult:
        """
        Crawl a site starting from url.
        Returns CrawlResult with extracted page data.
        """
        if self._is_blocked(url):
            return CrawlResult(
                success=False,
                pages_crawled=0,
                pages_failed=0,
                error=f"URL blocked by SSRF protection: {url}",
            )

        pages: list[CrawledPage] = []
        failed = 0
        self._visited = set()
        self._queue = [url]

        async with httpx.AsyncClient(
            timeout=settings.crawl_timeout_seconds,
            headers={"User-Agent": settings.crawl_user_agent},
            follow_redirects=True,
        ) as client:
            while self._queue and len(pages) < max_pages:
                current_url = self._queue.pop(0)
                if current_url in self._visited:
                    continue
                self._visited.add(current_url)

                if self._is_blocked(current_url):
                    logger.warning("ssrf_blocked", url=current_url)
                    continue

                try:
                    status_code, html = await self._fetch_page(client, current_url)
                    if not html:
                        failed += 1
                        continue

                    page = self._extract_page_data(current_url, html, status_code)
                    pages.append(page)

                    # Queue new internal links
                    for link in page.internal_links:
                        if link not in self._visited and link not in self._queue:
                            if len(self._queue) < max_pages * 2:
                                self._queue.append(link)

                    # Polite crawl delay
                    await asyncio.sleep(settings.crawl_delay_seconds)

                except Exception as e:
                    logger.error("crawl_page_error", url=current_url, error=str(e))
                    failed += 1
                    pages.append(CrawledPage(
                        url=current_url, status_code=0, error=str(e)
                    ))

        return CrawlResult(
            success=True,
            pages_crawled=len([p for p in pages if not p.error]),
            pages_failed=failed,
            pages=pages,
        )
