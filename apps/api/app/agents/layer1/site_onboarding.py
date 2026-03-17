"""
SiteOnboardingAgent — Layer 1 orchestrator for the full site onboarding pipeline.

Coordinates: domain validation → robots/sitemap → crawl planning →
             metadata extraction → product understanding.

This agent acts as a subgraph entry point in LangGraph.
"""
import uuid
from typing import ClassVar

from pydantic import BaseModel, HttpUrl

from app.agents.base import AgentMetadata, AgentRunContext, LLMAgent


class SiteOnboardingInput(BaseModel):
    site_id: uuid.UUID
    crawl_id: uuid.UUID
    url: str
    max_pages: int = 100


class SiteOnboardingOutput(BaseModel):
    site_id: uuid.UUID
    domain_valid: bool
    pages_queued: int
    robots_txt_found: bool
    sitemap_found: bool
    product_summary: str | None = None
    category: str | None = None
    icp_summary: str | None = None
    errors: list[str] = []
    warnings: list[str] = []


class SiteOnboardingAgent(LLMAgent[SiteOnboardingInput, SiteOnboardingOutput]):
    metadata: ClassVar[AgentMetadata] = AgentMetadata(
        name="SiteOnboardingAgent",
        layer=1,
        description="Orchestrates full site onboarding pipeline",
        max_retries=2,
        timeout_seconds=300,
    )

    async def _execute(
        self,
        input_data: SiteOnboardingInput,
        context: AgentRunContext,
    ) -> SiteOnboardingOutput:
        self._log.info("onboarding.start", site_id=str(input_data.site_id), url=input_data.url)

        errors: list[str] = []
        warnings: list[str] = []

        # Step 1: Domain validation
        domain_valid = await self._validate_domain(input_data.url)
        if not domain_valid:
            return SiteOnboardingOutput(
                site_id=input_data.site_id,
                domain_valid=False,
                pages_queued=0,
                robots_txt_found=False,
                sitemap_found=False,
                errors=["Domain validation failed"],
            )

        # Step 2: Robots.txt + sitemap discovery
        robots_found, sitemap_found, sitemap_urls = await self._discover_robots_sitemap(input_data.url)
        if not robots_found:
            warnings.append("robots.txt not found — will crawl with default rules")

        # Step 3: Queue crawl pages
        pages_queued = await self._plan_crawl(
            site_id=input_data.site_id,
            crawl_id=input_data.crawl_id,
            seed_url=input_data.url,
            sitemap_urls=sitemap_urls,
            max_pages=input_data.max_pages,
        )

        # Step 4: Product understanding (LLM)
        product_summary, category, icp_summary = await self._understand_product(
            url=input_data.url, context=context
        )

        self._log.info(
            "onboarding.complete",
            site_id=str(input_data.site_id),
            pages_queued=pages_queued,
        )

        return SiteOnboardingOutput(
            site_id=input_data.site_id,
            domain_valid=True,
            pages_queued=pages_queued,
            robots_txt_found=robots_found,
            sitemap_found=sitemap_found,
            product_summary=product_summary,
            category=category,
            icp_summary=icp_summary,
            errors=errors,
            warnings=warnings,
        )

    async def _validate_domain(self, url: str) -> bool:
        """Quick HTTP check to verify domain is reachable."""
        import httpx
        from app.core.config.settings import get_settings
        settings = get_settings()

        try:
            async with httpx.AsyncClient(
                timeout=settings.crawl_timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": settings.crawl_user_agent},
            ) as client:
                r = await client.head(url)
                return r.status_code < 500
        except Exception as e:
            self._log.warning("domain_validation_failed", url=url, error=str(e))
            return False

    async def _discover_robots_sitemap(
        self, base_url: str
    ) -> tuple[bool, bool, list[str]]:
        """Fetch and parse robots.txt, discover sitemap URLs."""
        import httpx
        from urllib.parse import urljoin

        robots_url = urljoin(base_url, "/robots.txt")
        robots_found = False
        sitemap_found = False
        sitemap_urls: list[str] = []

        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                r = await client.get(robots_url)
                if r.status_code == 200:
                    robots_found = True
                    for line in r.text.splitlines():
                        if line.lower().startswith("sitemap:"):
                            sitemap_url = line.split(":", 1)[1].strip()
                            sitemap_urls.append(sitemap_url)
                            sitemap_found = True
        except Exception:
            pass

        # Fallback: try common sitemap locations
        if not sitemap_found:
            for path in ["/sitemap.xml", "/sitemap_index.xml"]:
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        r = await client.head(urljoin(base_url, path))
                        if r.status_code == 200:
                            sitemap_urls.append(urljoin(base_url, path))
                            sitemap_found = True
                            break
                except Exception:
                    pass

        return robots_found, sitemap_found, sitemap_urls

    async def _plan_crawl(
        self,
        site_id: uuid.UUID,
        crawl_id: uuid.UUID,
        seed_url: str,
        sitemap_urls: list[str],
        max_pages: int,
    ) -> int:
        """
        Build initial crawl queue.
        In a full implementation, this writes to a Redis queue or DB table.
        Currently: stores seed URL count as placeholder.
        """
        # In production, parse sitemaps and seed the crawl queue
        # For now: return 1 (seed URL)
        return max(1, len(sitemap_urls))

    async def _understand_product(
        self,
        url: str,
        context: AgentRunContext,
    ) -> tuple[str | None, str | None, str | None]:
        """Use LLM to produce product summary, category, ICP."""
        if context.demo_mode or not self._llm:
            return (
                f"Demo product summary for {url}. This is a SaaS product.",
                "SaaS",
                "Small to mid-size B2B companies",
            )

        system = (
            "You are a product analyst. Given a website URL, produce a concise product summary, "
            "category classification, and ideal customer profile (ICP) summary. "
            "Be factual and concise. Respond in JSON."
        )
        user = f"Analyze this product website: {url}"

        class ProductAnalysis(BaseModel):
            product_summary: str
            category: str
            icp_summary: str

        result, _ = await self._call_llm_structured(system, user, ProductAnalysis)
        if result:
            return result.product_summary, result.category, result.icp_summary
        return None, None, None
